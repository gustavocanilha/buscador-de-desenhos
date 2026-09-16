from __future__ import annotations

import html
import math
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw
import streamlit as st

import core_logic as cl


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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp, button, input, textarea, select {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}
.stApp { background: #ffffff; color: #111111; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { max-width: 860px; padding-top: 3rem; padding-bottom: 4rem; }
h1, h2, h3 { color: #111111; letter-spacing: -0.02em; }
hr { border-color: #e5e5e5; }

.rc-title { font-size: 1.55rem; font-weight: 700; margin: 0 0 0.35rem 0; }
.rc-subtitle { font-size: 0.85rem; color: #6b6b6b; margin: 0 0 1.6rem 0; }

.rc-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #111111;
    margin: 0.2rem 0 0.6rem 0;
}
.rc-caption { font-size: 0.8rem; color: #6b6b6b; }

div[data-testid="stFileUploader"] section,
div[data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed #111111;
    border-radius: 10px;
    background: #ffffff;
    padding: 1.35rem 1.1rem;
    transition: background 0.15s ease;
}
div[data-testid="stFileUploaderDropzone"]:hover { background: #fafafa; }
div[data-testid="stFileUploaderDropzone"] button,
div[data-testid="stFileUploader"] section button {
    background: #111111 !important;
    color: #ffffff !important;
    border: 1px solid #111111 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}
div[data-testid="stFileUploaderDropzone"] small,
div[data-testid="stFileUploaderDropzoneInstructions"] span { color: #6b6b6b !important; }

div[data-testid="stExpander"] {
    border: 1px solid #e5e5e5;
    border-radius: 10px;
    background: #ffffff;
}
div[data-testid="stExpander"] summary { font-size: 0.82rem; font-weight: 600; color: #111111; }

.stButton > button, .stDownloadButton > button {
    width: 100%;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.62rem 1rem;
    transition: opacity 0.15s ease;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: #111111;
    color: #ffffff;
    border: 1px solid #111111;
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
    background: #000000;
    color: #ffffff;
    opacity: 0.92;
}
.stButton > button[kind="secondary"] {
    background: #ffffff;
    color: #111111;
    border: 1px solid #111111;
}
.stButton > button:disabled {
    background: #ededed !important;
    color: #9a9a9a !important;
    border: 1px solid #ededed !important;
}

div[data-testid="stTextInput"] input {
    border: 1px solid #d9d9d9;
    border-radius: 6px;
    font-size: 0.85rem;
}
div[data-testid="stTextInput"] input:focus { border-color: #111111; box-shadow: none; }

div[data-testid="stStatusWidget"] { border: 1px solid #e5e5e5; border-radius: 10px; }

.rc-banner {
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    font-size: 0.86rem;
    line-height: 1.45;
    margin: 0.4rem 0 1rem 0;
}
.rc-banner-ok { background: #f4f4f4; border: 1px solid #111111; color: #111111; }
.rc-banner-warn { background: #fdf8d8; border: 1px solid #e6d97a; color: #4a4210; }
.rc-banner-error { background: #ffffff; border: 1.5px solid #111111; color: #111111; }

.rc-metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.7rem; margin: 0.6rem 0 1.4rem 0; }
.rc-metric { border: 1px solid #d9d9d9; border-radius: 10px; padding: 0.85rem 0.9rem; background: #ffffff; }
.rc-metric-value { font-size: 1.5rem; font-weight: 700; line-height: 1.1; }
.rc-metric-label {
    font-size: 0.62rem; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: #6b6b6b; margin-top: 0.35rem;
}

.rc-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; margin-top: 0.3rem; }
.rc-table th {
    text-align: left; font-size: 0.62rem; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: #111111; background: #f4f4f4;
    padding: 0.55rem 0.7rem; border-bottom: 1px solid #d9d9d9;
}
.rc-table td { padding: 0.55rem 0.7rem; border-bottom: 1px solid #ededed; color: #111111; }
.rc-table td.mono { font-family: 'Consolas', 'Courier New', monospace; font-size: 0.76rem; }
.rc-chip {
    display: inline-block; font-size: 0.62rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; padding: 0.16rem 0.5rem; border-radius: 999px;
}
.rc-chip-copiado { background: #111111; color: #ffffff; }
.rc-chip-ignorado { background: #ffffff; color: #6b6b6b; border: 1px dashed #b5b5b5; }
.rc-chip-erro { background: #ffffff; color: #111111; border: 1px solid #111111; }

.rc-footer { font-size: 0.72rem; color: #9a9a9a; margin-top: 2.4rem; }
</style>
"""


def escape_html(value: object) -> str:
    return html.escape(str(value), quote=True)


def step_status(steps: list[tuple[str, str]], current: int) -> str:
    icons = {"done": "✓", "active": "●", "pending": "○"}
    rows = []
    for index, (label, state) in enumerate(steps):
        style = "color:#111111;font-weight:600;" if state != "pending" else "color:#b5b5b5;"
        rows.append(
            f'<div style="{style}font-size:0.82rem;margin:0.18rem 0;">'
            f'{icons[state]} &nbsp;{escape_html(label)}</div>'
        )
    return "".join(rows)


def render_metrics(report: cl.RCReport) -> None:
    metrics = [
        (str(len(report.codes)), "Códigos lidos"),
        (str(report.found_file_count), "Desenhos encontrados"),
        (str(len(report.missing)), "Não localizados"),
        (str(len(report.incomplete)), "Incompletos"),
        (str(len(report.copied)), "Arquivos copiados"),
    ]
    cards = "".join(
        f'<div class="rc-metric"><div class="rc-metric-value">{value}</div>'
        f'<div class="rc-metric-label">{label}</div></div>'
        for value, label in metrics
    )
    st.markdown(f'<div class="rc-metrics">{cards}</div>', unsafe_allow_html=True)


def render_results(report: cl.RCReport) -> None:
    incomplete = report.incomplete
    missing_extensions = {
        cl.extension_label(extension)
        for extensions in incomplete.values()
        for extension in extensions
    }

    if report.missing:
        st.markdown(
            f'<div class="rc-banner rc-banner-warn">'
            f"<strong>{len(report.missing)} código(s) sem desenho localizado</strong> em "
            f"{escape_html(report.root)}. Verifique o servidor ou anexe manualmente."
            f"</div>",
            unsafe_allow_html=True,
        )
    if incomplete:
        st.markdown(
            f'<div class="rc-banner rc-banner-warn">'
            f"<strong>{len(incomplete)} código(s) com apenas um dos tipos de desenho.</strong> "
            f"Falta {', '.join(sorted(missing_extensions))} de um ou mais itens. "
            "Confira a lista abaixo antes de anexar."
            f"</div>",
            unsafe_allow_html=True,
        )
    if not report.missing and not incomplete:
        st.markdown(
            '<div class="rc-banner rc-banner-ok"><strong>Todos os códigos foram localizados '
            "nos dois formatos.</strong> Os desenhos mais recentes de cada item foram copiados.</div>",
            unsafe_allow_html=True,
        )

    render_metrics(report)

    if report.missing:
        st.markdown('<div class="rc-label">Códigos não localizados</div>', unsafe_allow_html=True)
        st.code("\n".join(report.missing), language=None)

    if incomplete:
        st.markdown('<div class="rc-label">Códigos incompletos (falta desenho)</div>', unsafe_allow_html=True)
        lines = [
            f"{code} — falta {', '.join(cl.extension_label(extension) for extension in extensions)}"
            for code, extensions in sorted(incomplete.items())
        ]
        st.code("\n".join(lines), language=None)

    if report.results:
        st.markdown('<div class="rc-label">Arquivos selecionados</div>', unsafe_allow_html=True)
        chip_class = {"copiado": "rc-chip-copiado", "ignorado": "rc-chip-ignorado", "erro": "rc-chip-erro"}
        rows = []
        for result in report.results:
            rows.append(
                "<tr>"
                f'<td class="mono">{escape_html(result.code)}</td>'
                f'<td class="mono">{escape_html(result.source.name)}</td>'
                f'<td>{cl.format_timestamp(result.source.stat().st_mtime) if result.source.exists() else "-"}</td>'
                f"<td>{cl.human_size(result.source.stat().st_size) if result.source.exists() else '-'}</td>"
                f'<td><span class="rc-chip {chip_class.get(result.status, "rc-chip-erro")}">'
                f"{escape_html(result.status)}</span></td>"
                "</tr>"
            )
        st.markdown(
            '<table class="rc-table"><thead><tr><th>Código</th><th>Arquivo</th>'
            "<th>Modificado</th><th>Tamanho</th><th>Status</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>",
            unsafe_allow_html=True,
        )

    if report.scan_errors:
        with st.expander(f"Falhas de leitura em {len(report.scan_errors)} pasta(s)"):
            st.code("\n".join(report.scan_errors), language=None)

    st.markdown('<div class="rc-label">Pasta de destino</div>', unsafe_allow_html=True)
    st.code(str(report.destination), language=None)

    left, right = st.columns(2)
    with left:
        if st.button("Abrir pasta no Explorer", type="secondary", disabled=not report.destination.exists()):
            try:
                os.startfile(str(report.destination))
            except OSError as exc:
                st.error(f"Não foi possível abrir a pasta: {exc}")
    with right:
        if st.button("Nova análise", type="primary"):
            st.session_state.pop("report", None)
            st.rerun()

    st.markdown(
        f'<div class="rc-footer">RC {escape_html(report.rc_number)} · {escape_html(report.pdf_name)} · '
        f"{len(report.results)} arquivo(s) processado(s) em {report.elapsed_seconds:.1f}s · "
        "origem acessada somente para leitura</div>",
        unsafe_allow_html=True,
    )


st.markdown(CSS, unsafe_allow_html=True)

st.markdown('<div class="rc-title">Buscador de Desenhos</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="rc-subtitle">Leia a RC, encontre os desenhos mais recentes no servidor '
    "e organize tudo em uma pasta na sua Área de Trabalho.</div>",
    unsafe_allow_html=True,
)
st.divider()

st.markdown(
    '<div class="rc-label">01 — Requisição de Compra</div>',
    unsafe_allow_html=True,
)
uploaded = st.file_uploader(
    "Arraste ou clique para selecionar o PDF da RC",
    type=["pdf"],
    label_visibility="collapsed",
)
st.markdown(
    '<div class="rc-caption">Somente arquivos .pdf exportados do ERP.</div>',
    unsafe_allow_html=True,
)

saved_root = cl.get_saved_root()
default_root = saved_root or cl.DEFAULT_DRAWINGS_ROOT

with st.expander("Configurações", expanded=not default_root):
    root_input = st.text_input(
        "Pasta de origem (somente leitura)",
        value=default_root,
        placeholder=r"\\servidor\Engenharia\Projetos Obras",
        help="Informe uma vez. O caminho fica salvo nesta máquina e é preenchido automaticamente nas próximas vezes.",
    )
    overwrite = st.checkbox("Sobrescrever arquivos já existentes na Área de Trabalho", value=False)
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
    if st.button("Testar acesso à pasta", type="secondary"):
        try:
            checked = cl.check_drawings_root(root_input)
            cl.save_drawings_root(checked)
            st.success("Pasta acessível para leitura. Caminho salvo para as próximas vezes.")
        except cl.DrawingsRootError as exc:
            st.error(str(exc))

st.write("")
run = st.button(
    "Processar RC",
    type="primary",
    disabled=uploaded is None or not root_input.strip(),
    use_container_width=True,
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
    st.session_state.pop("report", None)
    steps_labels = [
        "Leitura do PDF da RC",
        f'Busca no drive "{root_input}"',
        "Cópia dos desenhos para a Área de Trabalho",
    ]
    steps = [(label, "pending") for label in steps_labels]
    placeholder = st.empty()
    placeholder.markdown(step_status(steps, 0), unsafe_allow_html=True)

    def progress(message: str, fraction: float) -> None:
        if fraction <= 0.2:
            index = 0
        elif fraction <= 0.7:
            index = 1
        else:
            index = 2
        updated = []
        for position, label in enumerate(steps_labels):
            state = "done" if position < index else "active" if position == index else "pending"
            updated.append((label, state))
        placeholder.markdown(step_status(updated, index), unsafe_allow_html=True)
        detail.write(f"› {message}")

    def scan_progress(count: int) -> None:
        detail.write(f"› {count:,} arquivos catalogados no servidor".replace(",", "."))

    detail = st.empty()
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded.getbuffer())
            temporary_path = Path(temp_file.name)
        report = cl.process_rc(
            temporary_path,
            root=root_input,
            overwrite=overwrite,
            shop_folders_only=not full_scan,
            force_rescan=force_rescan,
            progress=progress,
            scan_progress=scan_progress,
        )
        report.pdf_name = uploaded.name
        cl.save_drawings_root(root_input)
        placeholder.markdown(
            step_status([(label, "done") for label in steps_labels], len(steps_labels)),
            unsafe_allow_html=True,
        )
        detail.empty()
        st.session_state["report"] = report
    except cl.DrawingsRootError as exc:
        detail.empty()
        placeholder.empty()
        st.markdown(
            f'<div class="rc-banner rc-banner-error"><strong>Acesso ao servidor indisponível.</strong><br>'
            f"{escape_html(exc)}</div>",
            unsafe_allow_html=True,
        )
    except cl.RCParseError as exc:
        detail.empty()
        placeholder.empty()
        st.markdown(
            f'<div class="rc-banner rc-banner-error"><strong>Falha ao ler a RC.</strong><br>'
            f"{escape_html(exc)}</div>",
            unsafe_allow_html=True,
        )
    except Exception as exc:
        detail.empty()
        placeholder.empty()
        log_path = cl.log_unexpected_error(exc)
        st.markdown(
            f'<div class="rc-banner rc-banner-error"><strong>Erro inesperado durante o processamento.</strong><br>'
            f"Detalhes técnicos registrados em {escape_html(log_path)}.</div>",
            unsafe_allow_html=True,
        )
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass

report = st.session_state.get("report")
if report is not None:
    st.divider()
    st.markdown('<div class="rc-label">02 — Resultado</div>', unsafe_allow_html=True)
    render_results(report)
