from __future__ import annotations

import html
import math
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw
import streamlit as st

import core_logic as cl

FORMATS = ((".pdf", "PDF"), (".dxf", "DXF"))
STEPS = (
    (0.06, "Lendo o PDF da Requisição de Compra"),
    (0.16, "Verificando o acesso à pasta de origem"),
    (0.21, "Varrendo os desenhos no servidor"),
    (0.71, "Selecionando as versões mais recentes"),
    (0.81, "Copiando os desenhos para a Área de Trabalho"),
    (1.01, "Concluído"),
)
FREE_STEPS = (
    (0.06, "Identificando os códigos no texto"),
    (0.16, "Verificando o acesso à pasta de origem"),
    (0.21, "Varrendo os desenhos no servidor"),
    (0.71, "Selecionando as versões mais recentes"),
    (0.81, "Copiando os desenhos para a Área de Trabalho"),
    (1.01, "Concluído"),
)


def build_page_icon(size: int = 256) -> Image.Image:
    scale = 4
    side = size * scale
    icon = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    black = (17, 17, 17, 255)
    white = (255, 255, 255, 255)

    margin = side * 0.015
    draw.rounded_rectangle(
        [margin, margin, side - margin, side - margin],
        radius=side * 0.23,
        fill=black,
    )

    center_x = side * 0.435
    center_y = side * 0.415
    outer_radius = side * 0.235
    stroke = side * 0.085
    draw.ellipse(
        [
            center_x - outer_radius,
            center_y - outer_radius,
            center_x + outer_radius,
            center_y + outer_radius,
        ],
        fill=white,
    )
    inner_radius = outer_radius - stroke
    draw.ellipse(
        [
            center_x - inner_radius,
            center_y - inner_radius,
            center_x + inner_radius,
            center_y + inner_radius,
        ],
        fill=black,
    )

    angle = math.radians(45)
    direction_x = math.cos(angle)
    direction_y = math.sin(angle)
    handle_start = (
        center_x + direction_x * (outer_radius - stroke * 0.5),
        center_y + direction_y * (outer_radius - stroke * 0.5),
    )
    handle_end = (
        center_x + direction_x * (outer_radius + side * 0.175),
        center_y + direction_y * (outer_radius + side * 0.175),
    )
    draw.line([handle_start, handle_end], fill=white, width=int(stroke))
    cap = stroke / 2
    draw.ellipse(
        [
            handle_end[0] - cap,
            handle_end[1] - cap,
            handle_end[0] + cap,
            handle_end[1] + cap,
        ],
        fill=white,
    )

    return icon.resize((size, size), Image.LANCZOS)


st.set_page_config(
    page_title="Buscador de Desenhos",
    page_icon=build_page_icon(),
    layout="centered",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
:root {
    --paper: #ffffff;
    --ground: #f7f7f8;
    --ink: #111214;
    --ink-2: #3c3f44;
    --muted: #6b6f76;
    --line: #e7e8ea;
    --line-2: #d3d5d9;
    --accent: #111214;
    --accent-2: #000000;
    --info: #0b57d0;
    --ok-ink: #146c43;
    --ok-bg: #eef7f1;
    --ok-line: #c9e3d5;
    --warn-ink: #8a5a00;
    --warn-bg: #fbf4e4;
    --warn-line: #eadcb8;
    --bad-ink: #b42318;
    --bad-bg: #fcf0ee;
    --bad-line: #f0ccc6;
}

html, body, [class*="css"], .stApp, button, input, textarea, select {
    font-family: "Segoe UI Variable Text", "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
}
.stApp { background: var(--paper); color: var(--ink); }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { width: 100%; max-width: __CONTAINER_WIDTH__; min-width: 0; padding-top: 3rem; padding-bottom: 3.5rem; }
.stApp h1, .stApp h2, .stApp h3 {
    color: var(--ink);
    letter-spacing: -0.02em;
    font-family: "Segoe UI Variable Display", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
}
hr { border-color: var(--line); margin: 2rem 0; }

::selection { background: rgba(17, 18, 20, 0.12); }
:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
input, textarea { caret-color: var(--ink); }
html { scrollbar-color: #c9ced6 transparent; }

/* --- masthead ------------------------------------------------------- */
.rc-masthead { margin: 0 0 2.1rem 0; }
.stApp .rc-title { font-size: 1.75rem; font-weight: 700; line-height: 1.15; margin: 0 0 0.45rem 0; }
.rc-subtitle { font-size: 0.95rem; color: var(--muted); max-width: 58ch; margin: 0; line-height: 1.5; }
.rc-caption { font-size: 0.8rem; color: var(--muted); margin: 0.7rem 0 0 0; line-height: 1.5; }
.rc-spacer { height: 1.25rem; }

/* --- upload --------------------------------------------------------- */
.stApp [data-testid="stFileUploaderDropzone"] {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    border: 1.5px dashed var(--line-2);
    border-radius: 12px;
    background: var(--ground);
    padding: 1.35rem 1.15rem;
    transition: border-color 0.15s ease;
}
.stApp [data-testid="stFileUploaderDropzone"]:hover { border-color: var(--ink-2); }
.stApp [data-testid="stFileUploaderDropzone"]::after {
    content: "Clique ou arraste para selecionar o arquivo...";
    font-size: 0.82rem;
    color: var(--muted);
    line-height: 1.4;
    text-align: center;
}
.stApp [data-testid="stFileUploaderDropzone"] button {
    width: auto !important;
    height: auto !important;
    min-width: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}
.stApp [data-testid="stFileUploaderDropzone"] button:hover {
    background: transparent !important;
    border-color: transparent !important;
}
.stApp [data-testid="stFileUploaderDropzone"] button p { display: none; }
.stApp [data-testid="stFileUploaderDropzone"] button [data-testid="stIconMaterial"] {
    font-size: 22px;
    color: var(--muted);
    transition: color 0.15s ease;
}
.stApp [data-testid="stFileUploaderDropzone"] button:hover [data-testid="stIconMaterial"] {
    color: var(--ink);
}
.stApp [data-testid="stFileUploaderDropzoneInstructions"] { display: none; }
.stApp [data-testid="stFileUploaderDropzone"]:has(> div:has(> span)) {
    border-color: var(--accent);
    background: var(--paper);
    box-shadow: inset 0 0 0 2px var(--accent);
}
.stApp [data-testid="stFileUploaderDropzone"] > div:has(> span) { background: transparent; }
.stApp [data-testid="stFileUploaderDropzone"] > div:has(> span) > span { font-size: 0; }

/* --- settings ------------------------------------------------------- */
[data-testid="stExpander"] {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--paper);
}
[data-testid="stExpander"] summary { font-size: 0.87rem; font-weight: 600; color: var(--ink); }
[data-testid="stExpander"] summary:hover { color: var(--ink); text-decoration: underline; text-underline-offset: 3px; }
[data-testid="stTextInput"] input {
    border: 1px solid var(--line-2);
    border-radius: 8px;
    font-size: 0.86rem;
    padding: 0.48rem 0.65rem;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--ink);
    box-shadow: 0 0 0 3px rgba(17, 18, 20, 0.1);
    outline: none;
}
[data-testid="stCheckbox"] label { font-size: 0.86rem; color: var(--ink-2); }
[data-testid="stCheckbox"] label:has(input:checked) > div:first-of-type {
    background-color: var(--accent);
    border-color: var(--accent);
}
[data-testid="stAlert"] { border-radius: 10px; font-size: 0.85rem; }

/* --- buttons -------------------------------------------------------- */
.stButton > button, .stDownloadButton > button {
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.87rem;
    padding: 0.55rem 1rem;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: var(--accent);
    color: #ffffff;
    border: 1px solid var(--accent);
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
    background: var(--accent-2);
    border-color: var(--accent-2);
    color: #ffffff;
}
.stButton > button[kind="secondary"], .stDownloadButton > button[kind="secondary"] {
    background: var(--paper);
    color: var(--ink);
    border: 1px solid var(--line-2);
}
.stButton > button[kind="secondary"]:hover, .stDownloadButton > button[kind="secondary"]:hover {
    background: var(--ground);
    border-color: #b9bec6;
    color: var(--ink);
}
.stButton > button:disabled {
    background: #eceef1 !important;
    color: #9aa0a8 !important;
    border-color: #eceef1 !important;
}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}

/* --- progress ------------------------------------------------------- */
[data-testid="stExpanderIconSpinner"] { color: var(--info); }
[data-testid="stExpanderIconError"] { color: var(--bad-ink); }
[data-testid="stExpanderIconCheck"] { color: var(--ok-ink); }

/* --- result --------------------------------------------------------- */
.rc-verdict {
    border: 1px solid var(--line);
    border-left: 3px solid var(--ink);
    border-radius: 10px;
    padding: 1.1rem 1.25rem;
    margin: 0 0 1.1rem 0;
    background: var(--paper);
}
.rc-verdict-ok { border-left-color: var(--ok-ink); }
.rc-verdict-warn { border-left-color: var(--warn-ink); }
.rc-verdict-bad { border-left-color: var(--bad-ink); }
.stApp .rc-verdict-title { font-size: 1.22rem; font-weight: 700; margin: 0 0 0.35rem 0; line-height: 1.25; }
.rc-verdict-body { font-size: 0.92rem; color: var(--ink); margin: 0 0 0.3rem 0; line-height: 1.5; }
.rc-verdict-meta { font-size: 0.8rem; color: var(--muted); margin: 0; line-height: 1.5; }

.rc-chip {
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    padding: 0.18rem 0.55rem;
    border: 1px solid transparent;
    border-radius: 999px;
    white-space: nowrap;
}
.rc-chip-ok { background: var(--ok-bg); color: var(--ok-ink); border-color: var(--ok-line); }
.rc-chip-warn { background: var(--warn-bg); color: var(--warn-ink); border-color: var(--warn-line); }
.rc-chip-bad { background: var(--bad-bg); color: var(--bad-ink); border-color: var(--bad-line); }

.rc-pending { margin: 1.6rem 0 0.5rem 0; }
.rc-pending-title { font-size: 0.86rem; font-weight: 600; color: var(--ink); margin: 0 0 0.5rem 0; }
.rc-pending-list { list-style: none; margin: 0; padding: 0; }
.rc-pending-list li {
    display: flex;
    gap: 0.75rem;
    align-items: baseline;
    font-size: 0.85rem;
    color: var(--ink);
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--line);
}
.rc-pending-list li:last-child { border-bottom: none; }
.rc-pending-list code {
    font-family: Consolas, "Courier New", monospace;
    font-size: 0.8rem;
    color: var(--ink);
    background: var(--ground);
    border: 0;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
}
.rc-pending-note { font-size: 0.82rem; }
.rc-pending-warn { color: var(--warn-ink); }
.rc-pending-bad { color: var(--bad-ink); }

.rc-table-wrap { overflow-x: auto; margin-top: 1.8rem; }
.rc-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.rc-table caption {
    caption-side: top;
    text-align: left;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
    padding: 0 0 0.6rem 0;
}
.rc-table th {
    text-align: left;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    background: transparent;
    padding: 0.5rem 0.7rem;
    border-bottom: 1px solid var(--line-2);
    white-space: nowrap;
}
.rc-table td { padding: 0.6rem 0.7rem; border-bottom: 1px solid var(--line); vertical-align: top; }
.rc-table td.mono { font-family: Consolas, "Courier New", monospace; font-size: 0.78rem; white-space: nowrap; }
.rc-table td.rc-cell { width: 31%; }
.rc-table td.rc-cell-missing { color: var(--muted); font-size: 0.8rem; }
.rc-file { font-family: Consolas, "Courier New", monospace; font-size: 0.76rem; overflow-wrap: anywhere; color: var(--ink); }
.rc-file-meta { font-size: 0.72rem; color: var(--muted); margin-top: 0.15rem; font-variant-numeric: tabular-nums; }
.rc-flag { color: var(--info); }
.rc-flag-bad { color: var(--bad-ink); }

.rc-footer {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    font-size: 0.78rem;
    color: var(--muted);
    margin: 2.2rem 0 1rem 0;
    padding-top: 1rem;
    border-top: 1px solid var(--line);
}
.rc-footer-item { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: baseline; }
.rc-footer-label { font-weight: 600; letter-spacing: 0.04em; }
.rc-footer-path { font-family: Consolas, "Courier New", monospace; font-size: 0.76rem; color: var(--ink-2); overflow-wrap: anywhere; }
</style>
"""


def escape_html(value: object) -> str:
    return html.escape(str(value), quote=True)


def format_seconds(value: float) -> str:
    return f"{value:.1f}".replace(".", ",") + " s"


def format_count(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def plural(count: int, singular: str, many: str) -> str:
    return f"{format_count(count)} {singular if count == 1 else many}"


def step_label(fraction: float, steps=STEPS) -> str:
    label = steps[0][1]
    for threshold, text in steps:
        if fraction <= threshold:
            label = text
            break
    return label


def collect_rows(report: cl.RCReport) -> list[dict]:
    """Uma linha por código da RC, com os dois formatos lado a lado."""
    copy_status = {
        (result.code, result.extension): result.status for result in report.results
    }
    rows: list[dict] = []
    for code in report.codes:
        found = report.matches.get(code, {})
        cells = []
        failed = False
        for extension, _label in FORMATS:
            match = found.get(extension)
            status = copy_status.get((code, extension))
            failed = failed or status == "erro"
            cells.append({"match": match, "status": status})
        if not found:
            situation = "nao_localizado"
        elif failed:
            situation = "erro"
        elif len(found) < len(FORMATS):
            situation = "incompleto"
        else:
            situation = "completo"
        rows.append({"code": code, "cells": cells, "situation": situation})
    return rows


def render_cell(cell: dict) -> str:
    match = cell["match"]
    status = cell["status"]
    if match is None:
        return '<td class="rc-cell rc-cell-missing">não encontrado</td>'
    name = escape_html(match.path.name)
    meta = f"{cl.format_timestamp(match.mtime)} &middot; {cl.human_size(match.size)}"
    if status == "ignorado":
        meta += ' &middot; <span class="rc-flag">já existia</span>'
    elif status == "erro":
        meta = '<span class="rc-flag rc-flag-bad">falha ao copiar</span>'
    return (
        f'<td class="rc-cell"><div class="rc-file">{name}</div>'
        f'<div class="rc-file-meta">{meta}</div></td>'
    )


def render_table(rows: list[dict]) -> None:
    body = []
    for row in rows:
        situation = row["situation"]
        if situation == "completo":
            chip, label = "rc-chip-ok", "completo"
        elif situation == "incompleto":
            chip, label = "rc-chip-warn", "falta formato"
        elif situation == "erro":
            chip, label = "rc-chip-bad", "erro na cópia"
        else:
            chip, label = "rc-chip-bad", "não localizado"
        cells = "".join(render_cell(cell) for cell in row["cells"])
        body.append(
            "<tr>"
            f'<td class="mono">{escape_html(row["code"])}</td>'
            f"{cells}"
            f'<td><span class="rc-chip {chip}">{label}</span></td>'
            "</tr>"
        )
    st.markdown(
        '<div class="rc-table-wrap"><table class="rc-table">'
        "<caption>Arquivos por código</caption>"
        "<thead><tr><th>Código</th><th>PDF</th><th>DXF</th><th>Situação</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def collect_pending(report: cl.RCReport) -> list[tuple[str, str, str]]:
    pending: list[tuple[str, str, str]] = []
    for code in report.codes:
        if code in report.missing:
            pending.append((code, "não localizado no servidor", "bad"))
        elif code in report.incomplete:
            missing = ", ".join(
                cl.extension_label(extension) for extension in report.incomplete[code]
            )
            pending.append((code, f"falta {missing}", "warn"))
    return pending


def render_pending(pending: list[tuple[str, str, str]]) -> None:
    items = "".join(
        f"<li><code>{escape_html(code)}</code>"
        f'<span class="rc-pending-note rc-pending-{kind}">{escape_html(note)}</span></li>'
        for code, note, kind in pending
    )
    st.markdown(
        '<div class="rc-pending">'
        '<div class="rc-pending-title">Códigos para tratar manualmente</div>'
        f'<ul class="rc-pending-list">{items}</ul></div>',
        unsafe_allow_html=True,
    )


def render_verdict(report: cl.RCReport, rows: list[dict], pending: list[tuple[str, str, str]]) -> None:
    total = len(report.codes)
    complete = sum(1 for row in rows if row["situation"] == "completo")
    failed = sum(1 for row in rows if row["situation"] == "erro")

    if failed:
        tone = "bad"
        title = f"RC {report.rc_number} processada com {plural(failed, 'erro de cópia', 'erros de cópia')}"
    elif pending:
        tone = "warn"
        title = f"RC {report.rc_number} processada com {plural(len(pending), 'pendência', 'pendências')}"
    else:
        tone = "ok"
        title = f"RC {report.rc_number} processada"

    summary = [f"{complete} de {total} códigos completos"]
    if pending:
        summary.append(plural(len(pending), "código sem desenho completo", "códigos sem desenho completo"))
    if failed:
        summary.append(plural(failed, "arquivo falhou na cópia", "arquivos falharam na cópia"))

    details = [
        f"{plural(len(report.copied), 'arquivo copiado', 'arquivos copiados')} "
        f"para a Área de Trabalho em {format_seconds(report.elapsed_seconds)}"
    ]
    if report.skipped:
        details.append(
            plural(len(report.skipped), "arquivo já existia e foi mantido", "arquivos já existiam e foram mantidos")
        )

    st.markdown(
        f'<div class="rc-verdict rc-verdict-{tone}">'
        f'<h1 class="rc-verdict-title">{escape_html(title)}</h1>'
        f'<p class="rc-verdict-body">{escape_html(" · ".join(summary))}</p>'
        f'<p class="rc-verdict-meta">{escape_html(" · ".join(details))}</p></div>',
        unsafe_allow_html=True,
    )


def clear_free_search() -> None:
    st.session_state.pop("free_report", None)
    st.session_state["free_search_text"] = ""


def render_error_block(title: str, body: str) -> None:
    st.markdown(
        '<div class="rc-verdict rc-verdict-bad">'
        f'<h1 class="rc-verdict-title">{escape_html(title)}</h1>'
        f'<p class="rc-verdict-body">{escape_html(body)}</p></div>',
        unsafe_allow_html=True,
    )


def render_open_folder(destination: Path | None) -> None:
    if destination is None or not destination.exists():
        return
    if st.button(
        "Abrir pasta no Explorer",
        type="primary",
        width="content",
        icon=":material/folder_open:",
    ):
        try:
            os.startfile(str(destination))
        except OSError as exc:
            st.error(f"Não foi possível abrir a pasta: {exc}")


def render_free_result(report: cl.RCReport) -> None:
    rows = collect_rows(report)
    pending = collect_pending(report)
    total = len(report.codes)
    complete = sum(1 for row in rows if row["situation"] == "completo")
    failed = sum(1 for row in rows if row["situation"] == "erro")
    copied = len(report.copied)
    skipped = len(report.skipped)
    missing = len(report.missing)

    if failed:
        tone = "bad"
        title = f"Busca avulsa concluída com {plural(failed, 'erro de cópia', 'erros de cópia')}"
    elif pending:
        tone = "warn"
        title = f"Busca avulsa concluída com {plural(len(pending), 'pendência', 'pendências')}"
    else:
        tone = "ok"
        title = "Busca avulsa concluída"

    summary = [f"{complete} de {total} códigos completos"]
    if copied:
        summary.append(plural(copied, "arquivo copiado", "arquivos copiados"))
    if skipped:
        summary.append(plural(skipped, "arquivo já existia", "arquivos já existiam"))
    if missing:
        summary.append(plural(missing, "código não localizado", "códigos não localizados"))
    if failed:
        summary.append(plural(failed, "arquivo falhou na cópia", "arquivos falharam na cópia"))

    if report.destination is None:
        detail = "Nenhum arquivo localizado; nenhuma pasta foi criada na Área de Trabalho"
    else:
        detail = "Pasta de destino criada na Área de Trabalho"

    st.markdown(
        f'<div class="rc-verdict rc-verdict-{tone}">'
        f'<h1 class="rc-verdict-title">{escape_html(title)}</h1>'
        f'<p class="rc-verdict-body">{escape_html(" · ".join(summary))}</p>'
        f'<p class="rc-verdict-meta">{escape_html(detail + " · " + format_seconds(report.elapsed_seconds))}</p></div>',
        unsafe_allow_html=True,
    )

    render_open_folder(report.destination)
    if pending:
        render_pending(pending)
    render_table(rows)

    destination_label = (
        str(report.destination) if report.destination is not None else "não criada (nenhum arquivo localizado)"
    )
    st.markdown(
        '<div class="rc-footer">'
        '<div class="rc-footer-item"><span class="rc-footer-label">Códigos reconhecidos</span>'
        f'<span class="rc-footer-path">{escape_html(format_count(total))}</span></div>'
        '<div class="rc-footer-item"><span class="rc-footer-label">Pasta de destino</span>'
        f'<span class="rc-footer-path">{escape_html(destination_label)}</span></div>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.button("Limpar busca", type="secondary", width="content", on_click=clear_free_search)


def run_free_search(
    text: str,
    root_input: str,
    overwrite: bool,
    force_rescan: bool,
    full_scan: bool,
) -> None:
    st.session_state.pop("free_report", None)
    status = st.status("Identificando os códigos no texto", expanded=False)

    def progress(_message: str, fraction: float) -> None:
        status.update(label=step_label(fraction, FREE_STEPS))

    def scan_progress(count: int) -> None:
        status.update(label=f"Varrendo o servidor · {format_count(count)} arquivos catalogados")

    try:
        report = cl.process_free_search(
            text,
            root=root_input,
            overwrite=overwrite,
            shop_folders_only=not full_scan,
            force_rescan=force_rescan,
            progress=progress,
            scan_progress=scan_progress,
        )
        cl.save_drawings_root(root_input)
        status.update(label="Concluído", state="complete")
        st.session_state["free_report"] = report
        st.rerun()
    except cl.FreeSearchError as exc:
        status.update(label="Busca interrompida", state="error")
        render_error_block("Nenhum código reconhecido", str(exc))
    except cl.DrawingsRootError as exc:
        status.update(label="Busca interrompida", state="error")
        render_error_block("Acesso ao servidor indisponível", str(exc))
    except Exception as exc:
        status.update(label="Busca interrompida", state="error")
        log_path = cl.log_unexpected_error(exc)
        render_error_block(
            "Erro inesperado durante a busca",
            f"Detalhes técnicos registrados em {log_path}.",
        )


def render_free_search(
    root_input: str,
    overwrite: bool,
    force_rescan: bool,
    full_scan: bool,
) -> None:
    if st.button(
        "Busca avulsa",
        type="secondary",
        width="content",
        icon=":material/search:",
    ):
        st.session_state["free_search_open"] = not st.session_state.get("free_search_open", False)

    if not st.session_state.get("free_search_open", False):
        return

    text = st.text_area(
        "Cole a lista ou o texto com os códigos",
        key="free_search_text",
        height=170,
        placeholder="Ex.: 1234-ABC-5678\nM16.0001\nou cole um texto inteiro; os códigos são extraídos automaticamente.",
    )
    st.markdown(
        '<div class="rc-caption">Aceita um código por linha, lista do Excel ou texto corrido. '
        "Formatos: 1234-ABC-5678 e M16.0001.</div>",
        unsafe_allow_html=True,
    )

    search = st.button(
        "Buscar",
        type="primary",
        width="stretch",
        disabled=not text.strip() or not root_input.strip(),
    )
    if not root_input.strip():
        st.markdown(
            '<div class="rc-caption" style="text-align:center;">'
            "Para liberar a busca: informe a pasta de origem em Configurações.</div>",
            unsafe_allow_html=True,
        )

    if search:
        run_free_search(text, root_input, overwrite, force_rescan, full_scan)

    report = st.session_state.get("free_report")
    if report is not None:
        render_free_result(report)


def render_result(report: cl.RCReport) -> None:
    rows = collect_rows(report)
    pending = collect_pending(report)
    render_verdict(report, rows, pending)

    destination = report.destination
    render_open_folder(destination)

    if pending:
        render_pending(pending)
        st.download_button(
            "Baixar lista (.txt)",
            data="\n".join(f"{code} - {note}" for code, note, _kind in pending),
            file_name=f"codigos-pendentes-RC{report.rc_number}.txt",
            mime="text/plain",
            type="secondary",
            width="content",
        )

    render_table(rows)

    if report.scan_errors:
        with st.expander(f"Falhas de leitura em {len(report.scan_errors)} pasta(s)"):
            st.markdown(
                "<ul>"
                + "".join(
                    f"<li>{escape_html(error)}</li>" for error in report.scan_errors
                )
                + "</ul>",
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div class="rc-footer">'
        '<div class="rc-footer-item"><span class="rc-footer-label">Arquivo</span>'
        f'<span class="rc-footer-path">{escape_html(report.pdf_name)}</span></div>'
        '<div class="rc-footer-item"><span class="rc-footer-label">Pasta de destino</span>'
        f'<span class="rc-footer-path">{escape_html(destination)}</span></div>'
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("Nova análise", type="secondary", width="content"):
        st.session_state.pop("report", None)
        st.session_state.pop("free_report", None)
        st.session_state["upload_seq"] = st.session_state.get("upload_seq", 0) + 1
        st.rerun()


report = st.session_state.get("report")

st.markdown(
    CSS.replace("__CONTAINER_WIDTH__", "940px" if report is not None else "660px"),
    unsafe_allow_html=True,
)

if report is None:
    st.markdown(
        '<div class="rc-masthead">'
        '<h1 class="rc-title">Buscador de Desenhos</h1>'
        '<p class="rc-subtitle">Leia a RC, encontre os desenhos mais recentes no servidor '
        "e organize tudo em uma pasta na sua Área de Trabalho.</p></div>",
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Selecionar o PDF da Requisição de Compra",
        type=["pdf"],
        label_visibility="collapsed",
        key=f"rc_pdf_{st.session_state.get('upload_seq', 0)}",
    )
    free_search_slot = st.container()

    saved_root = cl.get_saved_root()
    default_root = saved_root or cl.DEFAULT_DRAWINGS_ROOT

    with st.expander("Configurações", expanded=not default_root):
        root_input = st.text_input(
            "Pasta de origem (somente leitura)",
            value=default_root,
            placeholder=r"\\servidor\Engenharia\Projetos Obras",
            help="Informe uma vez. O caminho fica salvo nesta máquina e é preenchido automaticamente nas próximas vezes.",
        )
        overwrite = st.checkbox(
            "Sobrescrever arquivos já existentes na Área de Trabalho", value=False
        )
        force_rescan = st.checkbox(
            "Forçar nova varredura no servidor (ignora o cache local)",
            value=False,
            help="O cache local acelera as próximas buscas. Use esta opção se desenhos novos acabaram de ser publicados.",
        )
        full_scan = st.checkbox(
            "Varrer toda a estrutura (não apenas as pastas COMPRAS)",
            value=False,
            help="Por padrão a busca acontece apenas nas pastas COMPRAS Chaparias, COMPRAS Geral e COMPRAS Usinagem.",
        )
        if st.button("Testar acesso à pasta", type="secondary", width="content"):
            try:
                checked = cl.check_drawings_root(root_input)
                cl.save_drawings_root(checked)
                st.success("Pasta acessível para leitura. Caminho salvo para as próximas vezes.")
            except cl.DrawingsRootError as exc:
                st.error(str(exc))

    with free_search_slot:
        render_free_search(root_input, overwrite, force_rescan, full_scan)

    st.markdown('<div class="rc-spacer"></div>', unsafe_allow_html=True)
    run = st.button(
        "Processar RC",
        type="primary",
        disabled=uploaded is None or not root_input.strip(),
        width="stretch",
    )
    pending_hints = []
    if uploaded is None:
        pending_hints.append("anexe o PDF da RC")
    if not root_input.strip():
        pending_hints.append("informe a pasta de origem em Configurações")
    if pending_hints:
        st.markdown(
            f'<div class="rc-caption" style="text-align:center;">Para liberar o processamento: '
            f"{' e '.join(pending_hints)}.</div>",
            unsafe_allow_html=True,
        )

    if run and uploaded is not None:
        st.session_state.pop("free_report", None)
        status = st.status("Lendo o PDF da Requisição de Compra", expanded=False)

        def progress(_message: str, fraction: float) -> None:
            status.update(label=step_label(fraction))

        def scan_progress(count: int) -> None:
            status.update(
                label=f"Varrendo o servidor · {format_count(count)} arquivos catalogados"
            )

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(uploaded.getbuffer())
                temporary_path = Path(temp_file.name)
            new_report = cl.process_rc(
                temporary_path,
                root=root_input,
                overwrite=overwrite,
                shop_folders_only=not full_scan,
                force_rescan=force_rescan,
                progress=progress,
                scan_progress=scan_progress,
            )
            new_report.pdf_name = uploaded.name
            cl.save_drawings_root(root_input)
            status.update(label="Concluído", state="complete")
            st.session_state["report"] = new_report
            st.rerun()
        except cl.DrawingsRootError as exc:
            status.update(label="Processamento interrompido", state="error")
            st.markdown(
                '<div class="rc-verdict rc-verdict-bad">'
                '<h1 class="rc-verdict-title">Acesso ao servidor indisponível</h1>'
                f'<p class="rc-verdict-body">{escape_html(exc)}</p></div>',
                unsafe_allow_html=True,
            )
        except cl.RCParseError as exc:
            status.update(label="Processamento interrompido", state="error")
            st.markdown(
                '<div class="rc-verdict rc-verdict-bad">'
                '<h1 class="rc-verdict-title">Falha ao ler a RC</h1>'
                f'<p class="rc-verdict-body">{escape_html(exc)}</p></div>',
                unsafe_allow_html=True,
            )
        except Exception as exc:
            status.update(label="Processamento interrompido", state="error")
            log_path = cl.log_unexpected_error(exc)
            st.markdown(
                '<div class="rc-verdict rc-verdict-bad">'
                '<h1 class="rc-verdict-title">Erro inesperado durante o processamento</h1>'
                '<p class="rc-verdict-body">Detalhes técnicos registrados em '
                f"{escape_html(log_path)}.</p></div>",
                unsafe_allow_html=True,
            )
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except OSError:
                    pass
else:
    render_result(report)
