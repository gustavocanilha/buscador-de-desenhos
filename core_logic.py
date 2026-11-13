from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Sequence

import pdfplumber

DEFAULT_DRAWINGS_ROOT = os.environ.get("BUSCADOR_DRAWINGS_ROOT", "").strip()
APP_CONFIG_DIR_NAME = "BuscadorDeDesenhos"
DRAWING_EXTENSIONS = (".pdf", ".dxf")

RC_PATTERN = re.compile(r"RC\s*[:\-]?\s*(\d{2,6})", re.IGNORECASE)
CODE_PATTERNS = (
    re.compile(r"^\d{3,4}-[A-Z]{3}-\d{4}$"),
    re.compile(r"^[A-Z]\d\.\d{4}$"),
)
TEXT_CODE_PATTERN = re.compile(
    r"\b(\d{3,4})\s*-\s*([A-Z]{3})\s*-\s*(\d{4})\b"
    r"|\b([A-Z])\s*(\d)\s*\.\s*(\d{4})\b",
    re.IGNORECASE,
)
ITEM_COLUMN_LIMIT = 60.0
CODE_COLUMN_LEFT = 60.0
CODE_COLUMN_RIGHT = 130.0
ROW_TOP_TOLERANCE = 8.0
ITEM_NUMBER_PATTERN = re.compile(r"^\d{1,4}$")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\-]*")
SHOP_FOLDER_PREFIXES = ("COMPRAS",)
SCAN_WORKERS = 10
CACHE_TTL_SECONDS = 900
CACHE_DIR_NAME = "buscador_desenhos"

ProgressCallback = Callable[[str, float], None]
ScanProgressCallback = Callable[[int], None]


class DrawingsRootError(Exception):
    pass


class RCParseError(Exception):
    pass


class FreeSearchError(Exception):
    pass


@dataclass
class DrawingMatch:
    code: str
    extension: str
    path: Path
    rank: int
    mtime: float
    size: int


@dataclass
class CopyResult:
    code: str
    source: Path
    destination: Path
    status: str
    message: str = ""

    @property
    def extension(self) -> str:
        return self.source.suffix.lower()


@dataclass
class RCReport:
    rc_number: str
    pdf_name: str
    root: Path
    destination: Path | None
    codes: list[str] = field(default_factory=list)
    matches: dict[str, dict[str, DrawingMatch]] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    results: list[CopyResult] = field(default_factory=list)
    scan_errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def copied(self) -> list[CopyResult]:
        return [r for r in self.results if r.status == "copiado"]

    @property
    def skipped(self) -> list[CopyResult]:
        return [r for r in self.results if r.status == "ignorado"]

    @property
    def failed(self) -> list[CopyResult]:
        return [r for r in self.results if r.status == "erro"]

    @property
    def found_file_count(self) -> int:
        return sum(len(per_ext) for per_ext in self.matches.values())

    @property
    def incomplete(self) -> dict[str, list[str]]:
        wanted = {extension.lower() for extension in DRAWING_EXTENSIONS}
        result: dict[str, list[str]] = {}
        for code in self.codes:
            per_extension = self.matches.get(code)
            if not per_extension:
                continue
            missing_extensions = sorted(wanted - set(per_extension))
            if missing_extensions:
                result[code] = missing_extensions
        return result


def extension_label(extension: str) -> str:
    return extension.lstrip(".").upper()


def normalize_code(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def is_valid_code(text: str) -> bool:
    return any(pattern.match(text) for pattern in CODE_PATTERNS)


def get_desktop_dir() -> Path:
    home = Path.home()
    candidates = (home / "Desktop", home / "OneDrive" / "Desktop", home / "Area de Trabalho")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    fallback = candidates[0]
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_config_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if not base:
        base = str(Path.home())
    return Path(base) / APP_CONFIG_DIR_NAME / "config.json"


def load_config() -> dict:
    path = get_config_path()
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(updates: dict) -> None:
    path = get_config_path()
    data = load_config()
    data.update(updates)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
    except OSError:
        pass


def get_saved_root() -> str:
    value = load_config().get("drawings_root", "")
    return value.strip() if isinstance(value, str) else ""


def save_drawings_root(root: str | Path) -> None:
    save_config({"drawings_root": str(root).strip()})


def check_drawings_root(root: str | Path) -> Path:
    if not str(root).strip():
        raise DrawingsRootError(
            "Informe a pasta de origem dos desenhos, por exemplo "
            "\\\\servidor\\Engenharia\\Projetos Obras ou o drive mapeado equivalente."
        )
    root_path = Path(root)
    try:
        if not root_path.exists():
            raise DrawingsRootError(
                f"Pasta de origem nao encontrada: {root_path}. Verifique se a unidade de rede "
                "esta mapeada e se a VPN esta conectada."
            )
        if not root_path.is_dir():
            raise DrawingsRootError(f"O caminho informado nao e uma pasta: {root_path}")
        with os.scandir(root_path) as entries:
            next(entries, None)
    except PermissionError as exc:
        raise DrawingsRootError(
            f"Sem permissao de leitura em {root_path}. Contate o responsavel pelo servidor."
        ) from exc
    except DrawingsRootError:
        raise
    except OSError as exc:
        raise DrawingsRootError(
            f"Falha de rede ao acessar {root_path}: {exc.strerror or exc}. "
            "Confirme a conexao com o servidor."
        ) from exc
    return root_path


def _extract_page_codes(words: Sequence[dict]) -> list[str]:
    item_rows = [
        word
        for word in words
        if word["x0"] < ITEM_COLUMN_LIMIT and ITEM_NUMBER_PATTERN.match(word["text"])
    ]
    if not item_rows:
        return []

    chunks: dict[int, list[dict]] = {id(row): [] for row in item_rows}
    for word in words:
        if not (CODE_COLUMN_LEFT <= word["x0"] <= CODE_COLUMN_RIGHT):
            continue
        row = min(item_rows, key=lambda r: abs(r["top"] - word["top"]))
        if abs(row["top"] - word["top"]) <= ROW_TOP_TOLERANCE:
            chunks[id(row)].append(word)

    codes: list[str] = []
    for row in item_rows:
        parts = sorted(chunks[id(row)], key=lambda w: (round(w["top"], 1), w["x0"]))
        code = "".join(part["text"] for part in parts).strip()
        if is_valid_code(code):
            codes.append(code)
    return codes


def extract_rc_data(pdf_path: str | Path) -> tuple[str, list[str]]:
    path = Path(pdf_path)
    codes: list[str] = []
    text_fragments: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                words = page.extract_words()
                codes.extend(_extract_page_codes(words))
                page_text = page.extract_text() or ""
                text_fragments.append(page_text)
    except OSError as exc:
        raise RCParseError(f"Nao foi possivel abrir o PDF da RC: {exc}") from exc
    except Exception as exc:
        raise RCParseError(f"Falha ao ler o PDF da RC: {exc}") from exc

    full_text = "\n".join(text_fragments)
    rc_match = RC_PATTERN.search(full_text)
    rc_number = rc_match.group(1) if rc_match else ""
    if not rc_number:
        fallback = re.search(r"(\d{3,6})", path.stem)
        if fallback:
            rc_number = fallback.group(1)
    if not rc_number:
        raise RCParseError(
            "Numero da RC nao localizado no PDF. Confirme se o arquivo e uma Requisicao de Compra."
        )

    unique_codes: list[str] = []
    seen: set[str] = set()
    for code in codes:
        if code not in seen:
            seen.add(code)
            unique_codes.append(code)

    if not unique_codes:
        raise RCParseError("Nenhum codigo de produto foi identificado no PDF da RC.")

    return rc_number, unique_codes


def extract_codes_from_text(text: str) -> list[str]:
    """Extrai codigos de um texto livre, na ordem em que aparecem e sem repetir."""
    codes: list[str] = []
    seen: set[str] = set()
    for match in TEXT_CODE_PATTERN.finditer(text):
        if match.group(1):
            code = f"{match.group(1)}-{match.group(2).upper()}-{match.group(3)}"
        else:
            code = f"{match.group(4).upper()}{match.group(5)}.{match.group(6)}"
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


def _cache_path(root: Path) -> Path:
    digest = hashlib.md5(str(root).upper().encode("utf-8", "ignore")).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / CACHE_DIR_NAME / f"index_{digest}.json"


def _load_cache(
    root: Path,
    extensions: Sequence[str],
    folder_prefixes: Sequence[str],
    ttl: int,
) -> list[tuple[str, str, float, int]] | None:
    if ttl <= 0:
        return None
    cache_file = _cache_path(root)
    try:
        if not cache_file.is_file():
            return None
        if time.time() - cache_file.stat().st_mtime > ttl:
            return None
        with cache_file.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("root") != str(root).upper():
            return None
        if payload.get("extensions") != sorted(extensions):
            return None
        if payload.get("folders") != sorted(folder_prefixes):
            return None
        entries = []
        for raw in payload.get("entries", []):
            entries.append((str(raw[0]), str(raw[1]), float(raw[2]), int(raw[3])))
        return entries
    except (OSError, ValueError, TypeError, IndexError):
        return None


def _save_cache(
    root: Path,
    extensions: Sequence[str],
    folder_prefixes: Sequence[str],
    entries: list[tuple[str, str, float, int]],
) -> None:
    cache_file = _cache_path(root)
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "root": str(root).upper(),
            "extensions": sorted(extensions),
            "folders": sorted(folder_prefixes),
            "created": datetime.now().isoformat(timespec="seconds"),
            "entries": entries,
        }
        with cache_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)
    except OSError:
        pass


def _collect_shop_dirs(
    root: Path,
    folder_prefixes: Sequence[str],
    executor: concurrent.futures.ThreadPoolExecutor,
    errors: list[str],
) -> list[str]:
    prefixes = tuple(prefix.upper() for prefix in folder_prefixes)
    shops: list[str] = []

    def matches(name: str) -> bool:
        upper = name.upper()
        return any(upper.startswith(prefix) for prefix in prefixes)

    obras: list[str] = []
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if matches(entry.name):
                            shops.append(entry.path)
                        else:
                            obras.append(entry.path)
                except OSError as exc:
                    errors.append(f"{entry.path}: {exc.strerror or exc}")
    except OSError as exc:
        errors.append(f"{root}: {exc.strerror or exc}")
        return []

    def shops_of(path: str) -> list[str]:
        found: list[str] = []
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False) and matches(entry.name):
                            found.append(entry.path)
                    except OSError as exc:
                        errors.append(f"{entry.path}: {exc.strerror or exc}")
        except OSError as exc:
            errors.append(f"{path}: {exc.strerror or exc}")
        return found

    for result in executor.map(shops_of, obras):
        shops.extend(result)
    return shops


def _scan_dirs(
    seed_dirs: Sequence[str],
    extensions: Sequence[str],
    workers: int,
    on_progress: ScanProgressCallback | None,
) -> tuple[list[tuple[str, str, float, int]], list[str]]:
    allowed = {extension.lower() for extension in extensions}
    entries_out: list[tuple[str, str, float, int]] = []
    errors: list[str] = []
    counter = {"found": 0}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {executor.submit(os.scandir, path) for path in seed_dirs}
        while pending:
            finished, pending = concurrent.futures.wait(
                pending, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in finished:
                try:
                    entries = list(future.result())
                except OSError as exc:
                    errors.append(f"{exc.filename}: {exc.strerror or exc}")
                    continue
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            pending.add(executor.submit(os.scandir, entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            if Path(entry.name).suffix.lower() in allowed:
                                stat = entry.stat()
                                entries_out.append(
                                    (entry.name, entry.path, stat.st_mtime, stat.st_size)
                                )
                                counter["found"] += 1
                                if on_progress is not None and counter["found"] % 500 == 0:
                                    on_progress(counter["found"])
                    except OSError as exc:
                        errors.append(f"{entry.path}: {exc.strerror or exc}")
    entries_out.sort(key=lambda item: item[1])
    return entries_out, errors


def list_drawing_files(
    root: str | Path,
    extensions: Sequence[str] = DRAWING_EXTENSIONS,
    folder_prefixes: Sequence[str] = SHOP_FOLDER_PREFIXES,
    workers: int = SCAN_WORKERS,
    cache_ttl: int = CACHE_TTL_SECONDS,
    force_rescan: bool = False,
    on_progress: ScanProgressCallback | None = None,
) -> tuple[list[tuple[str, Path, float, int]], list[str]]:
    root = Path(root).absolute()
    prefixes = tuple(folder_prefixes or ())

    if not force_rescan:
        cached = _load_cache(root, extensions, prefixes, cache_ttl)
        if cached is not None:
            return [
                (Path(path).stem, Path(path), mtime, size)
                for _, path, mtime, size in cached
            ], []

    if prefixes:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            errors: list[str] = []
            shops = _collect_shop_dirs(root, prefixes, executor, errors)
        if shops:
            raw_entries, scan_errors = _scan_dirs(shops, extensions, workers, on_progress)
            errors.extend(scan_errors)
        else:
            raw_entries = []
    else:
        raw_entries, errors = _scan_dirs([str(root)], extensions, workers, on_progress)

    if not errors:
        _save_cache(
            root,
            extensions,
            prefixes,
            [(Path(path).name, path, mtime, size) for _, path, mtime, size in raw_entries],
        )
    return [
        (Path(name).stem, Path(path), mtime, size)
        for name, path, mtime, size in raw_entries
    ], errors


def _tokens(stem: str) -> list[str]:
    return TOKEN_PATTERN.findall(stem)


def match_codes(
    codes: Iterable[str],
    indexed_files: Sequence[tuple[str, Path, float, int]],
) -> dict[str, dict[str, DrawingMatch]]:
    code_list = list(codes)
    code_by_norm = {normalize_code(code): code for code in code_list}
    prefix_index: dict[str, list[str]] = {}
    for normalized in code_by_norm:
        prefix_index.setdefault(normalized[:3], []).append(normalized)
    min_length = min((len(normalized) for normalized in code_by_norm), default=0)

    best: dict[str, dict[str, DrawingMatch]] = {code: {} for code in code_list}
    for stem, path, mtime, size in indexed_files:
        extension = path.suffix.lower()
        for raw_token in _tokens(stem):
            token = normalize_code(raw_token)
            if len(token) < 3:
                continue
            matched = None
            rank = 0
            if token in code_by_norm:
                matched = token
            else:
                for candidate in prefix_index.get(token[:3], ()):
                    if token.startswith(candidate) and (matched is None or len(candidate) > len(matched)):
                        matched = candidate
                        rank = 1
                if matched is None and len(token) >= min_length:
                    for candidate in code_by_norm:
                        if candidate in token:
                            matched = candidate
                            rank = 2
                            break
            if matched is None:
                continue
            code = code_by_norm[matched]
            candidate = DrawingMatch(
                code=code,
                extension=extension,
                path=path,
                rank=rank,
                mtime=mtime,
                size=size,
            )
            current = best[code].get(extension)
            if current is None or (candidate.rank, -candidate.mtime) < (current.rank, -current.mtime):
                best[code][extension] = candidate
    return {code: per_extension for code, per_extension in best.items() if per_extension}


def _safe_destination_name(rc_number: str) -> str:
    sanitized = re.sub(r"[^0-9A-Za-z]", "", rc_number) or "sem_numero"
    return f"Desenhos [RC {sanitized}]"


def _next_result_destination(desktop_dir: Path) -> Path:
    candidate = desktop_dir / "Resultado"
    index = 2
    while candidate.exists():
        candidate = desktop_dir / f"Resultado ({index})"
        index += 1
    return candidate


def _assert_destination_outside_root(destination: Path, root: Path) -> None:
    try:
        destination.resolve().relative_to(root.resolve())
    except ValueError:
        return
    raise DrawingsRootError(
        "A pasta de destino nao pode ficar dentro da pasta de origem. "
        "O servidor e utilizado somente para leitura."
    )


def log_unexpected_error(exc: BaseException) -> Path:
    log_path = Path(tempfile.gettempdir()) / CACHE_DIR_NAME / "erro.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now().isoformat(timespec='seconds')}] {exc.__class__.__name__}\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=handle)
            handle.write("\n")
    except OSError:
        pass
    return log_path


def copy_matches(
    matches: dict[str, dict[str, DrawingMatch]],
    destination_dir: Path,
    overwrite: bool = False,
) -> list[CopyResult]:
    results: list[CopyResult] = []
    try:
        destination_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DrawingsRootError(f"Nao foi possivel criar a pasta de destino: {exc}") from exc

    for code, per_extension in matches.items():
        for match in per_extension.values():
            target = destination_dir / match.path.name
            if target.exists() and not overwrite:
                results.append(
                    CopyResult(code, match.path, target, "ignorado", "Arquivo ja existe no destino.")
                )
                continue
            try:
                # A origem e somente leitura: copy2 le o arquivo e grava apenas no destino.
                shutil.copy2(match.path, target)
            except (FileNotFoundError, PermissionError, OSError) as exc:
                results.append(CopyResult(code, match.path, target, "erro", str(exc)))
                continue
            results.append(CopyResult(code, match.path, target, "copiado"))
    return results


def _find_drawing_matches(
    codes: Sequence[str],
    root: str | Path,
    shop_folders_only: bool,
    cache_ttl: int,
    force_rescan: bool,
    notify: Callable[[str, float], None],
    scan_progress: ScanProgressCallback | None,
) -> tuple[Path, dict[str, dict[str, DrawingMatch]], list[str], list[str]]:
    notify("Verificando acesso a pasta de origem", 0.15)
    root_path = check_drawings_root(root)

    notify("Varrendo os desenhos no servidor", 0.2)
    indexed_files, scan_errors = list_drawing_files(
        root_path,
        folder_prefixes=SHOP_FOLDER_PREFIXES if shop_folders_only else (),
        cache_ttl=cache_ttl,
        force_rescan=force_rescan,
        on_progress=scan_progress,
    )

    notify("Selecionando as versoes mais recentes", 0.7)
    matches = match_codes(codes, indexed_files)
    missing = [code for code in codes if not matches.get(code)]
    return root_path, matches, missing, scan_errors


def process_rc(
    pdf_path: str | Path,
    root: str | Path = DEFAULT_DRAWINGS_ROOT,
    desktop_dir: Path | None = None,
    overwrite: bool = False,
    shop_folders_only: bool = True,
    cache_ttl: int = CACHE_TTL_SECONDS,
    force_rescan: bool = False,
    progress: ProgressCallback | None = None,
    scan_progress: ScanProgressCallback | None = None,
) -> RCReport:
    start = datetime.now()

    def notify(message: str, fraction: float) -> None:
        if progress is not None:
            progress(message, fraction)

    notify("Lendo o PDF da RC", 0.05)
    rc_number, codes = extract_rc_data(pdf_path)

    root_path, matches, missing, scan_errors = _find_drawing_matches(
        codes, root, shop_folders_only, cache_ttl, force_rescan, notify, scan_progress
    )

    destination = (desktop_dir or get_desktop_dir()) / _safe_destination_name(rc_number)
    _assert_destination_outside_root(destination, root_path)

    notify("Copiando os arquivos encontrados", 0.8)
    results = copy_matches(matches, destination, overwrite=overwrite)

    notify("Concluido", 1.0)
    return RCReport(
        rc_number=rc_number,
        pdf_name=Path(pdf_path).name,
        root=root_path,
        destination=destination,
        codes=codes,
        matches=matches,
        missing=missing,
        results=results,
        scan_errors=scan_errors,
        elapsed_seconds=(datetime.now() - start).total_seconds(),
    )


def process_free_search(
    text: str,
    root: str | Path = DEFAULT_DRAWINGS_ROOT,
    desktop_dir: Path | None = None,
    overwrite: bool = False,
    shop_folders_only: bool = True,
    cache_ttl: int = CACHE_TTL_SECONDS,
    force_rescan: bool = False,
    progress: ProgressCallback | None = None,
    scan_progress: ScanProgressCallback | None = None,
) -> RCReport:
    start = datetime.now()

    def notify(message: str, fraction: float) -> None:
        if progress is not None:
            progress(message, fraction)

    notify("Identificando os codigos no texto", 0.05)
    codes = extract_codes_from_text(text)
    if not codes:
        raise FreeSearchError(
            "Nenhum codigo reconhecido no texto. Formatos aceitos: "
            "1234-ABC-5678 e A1.2345."
        )

    root_path, matches, missing, scan_errors = _find_drawing_matches(
        codes, root, shop_folders_only, cache_ttl, force_rescan, notify, scan_progress
    )

    destination: Path | None = None
    results: list[CopyResult] = []
    if matches:
        destination = _next_result_destination(desktop_dir or get_desktop_dir())
        _assert_destination_outside_root(destination, root_path)
        notify("Copiando os arquivos encontrados", 0.8)
        results = copy_matches(matches, destination, overwrite=overwrite)

    notify("Concluido", 1.0)
    return RCReport(
        rc_number="",
        pdf_name="",
        root=root_path,
        destination=destination,
        codes=codes,
        matches=matches,
        missing=missing,
        results=results,
        scan_errors=scan_errors,
        elapsed_seconds=(datetime.now() - start).total_seconds(),
    )


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def format_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")
