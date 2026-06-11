"""Visual layer: global CSS + reusable card / table styling helpers.

Keeps app.py focused on data + wiring while this module owns the "looks like a
real product" styling (KPI cards, colored PnL, app header, tabs, tables).
"""
from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd
import streamlit as st

GREEN = "#0a9d63"
RED = "#e0233a"
MUTED = "#5a6675"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root{
  --bg:#0e1117; --surface:#161b24; --surface-2:#1b212c;
  --border:#232b38; --border-strong:#33404f;
  --text:#e7ecf3; --text-2:#9aa6b6; --text-3:#6b7787;
  --accent:#10b981; --accent-strong:#0d9b6c; --accent-weak:rgba(16,185,129,.13);
  --pos:#16c784; --neg:#f4525f; --amber:#f59e0b;
  --shadow-sm:0 1px 2px rgba(0,0,0,.28), 0 1px 3px rgba(0,0,0,.22);
  --shadow-md:0 6px 20px rgba(0,0,0,.38), 0 2px 6px rgba(0,0,0,.28);
}

html, body, [class*="css"], .stMarkdown, .stMetric { font-family: 'Inter', system-ui, sans-serif; }
.stApp { background: var(--bg); }
body, .stMarkdown, p, span, label { color: var(--text); }

.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1480px; }

/* hide default Streamlit chrome */
#MainMenu, footer { visibility: hidden; height: 0; }
header[data-testid="stHeader"] { background: transparent; height: 0; }

/* ---------- app header ---------- */
.app-header {
  display:flex; align-items:center; justify-content:space-between;
  padding: 18px 24px; border-radius: 18px; margin-bottom: 22px;
  background: linear-gradient(135deg, #18202b 0%, #142420 100%);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}
.app-header .brand { display:flex; align-items:center; }
.app-header .sub { color:var(--text-2); font-size:13px; text-align:right; line-height:1.6; }
.side-brand { display:flex; align-items:center; gap:9px; margin:2px 0 10px 0; }

/* ---------- KPI cards ---------- */
.kpi-grid {
  display:grid; grid-template-columns: repeat(auto-fit, minmax(190px,1fr));
  gap:14px; margin: 4px 0 16px 0;
}
.kpi-card {
  background:var(--surface); border:1px solid var(--border); border-radius:16px;
  padding:17px 19px; box-shadow:var(--shadow-sm);
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
}
.kpi-card:hover { border-color:var(--border-strong); transform: translateY(-2px); box-shadow:var(--shadow-md); }
.kpi-label { color:var(--text-3); font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.8px; margin-bottom:10px; }
.kpi-value { font-size:26px; font-weight:800; color:var(--text); line-height:1.05; letter-spacing:-.6px; font-variant-numeric:tabular-nums; }
.kpi-sub { font-size:12.5px; font-weight:600; margin-top:8px; }

/* ---------- account cards ---------- */
.acct-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr)); gap:12px; margin-bottom:6px; }
.acct-card {
  background:var(--surface); border:1px solid var(--border); border-left:3px solid var(--accent);
  border-radius:14px; padding:14px 16px; box-shadow:var(--shadow-sm);
  transition: transform .15s ease, box-shadow .15s ease;
}
.acct-card:hover { transform:translateY(-1px); box-shadow:var(--shadow-md); }
.acct-card.live  { border-left-color:var(--neg); }
.acct-card.paper { border-left-color:var(--amber); }
.acct-top { display:flex; justify-content:space-between; align-items:center; }
.acct-name { font-weight:700; color:var(--text); font-size:13.5px; }
.acct-tag { font-size:9.5px; font-weight:700; padding:3px 8px; border-radius:6px; letter-spacing:.5px; }
.acct-tag.live { background:rgba(244,82,95,.16); color:#ff6b75; }
.acct-tag.paper{ background:rgba(245,158,11,.16); color:#fbbf24; }
.acct-eq { font-size:21px; font-weight:800; color:var(--text); margin-top:9px; line-height:1.1; letter-spacing:-.5px; font-variant-numeric:tabular-nums; }
.acct-eq-label { color:var(--text-3); font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.6px; margin-top:2px; }
.acct-foot { display:flex; gap:10px; margin-top:12px; padding-top:11px; border-top:1px solid var(--border); }
.acct-stat { flex:1; min-width:0; }
.acct-stat .k { color:var(--text-3); font-size:9.5px; font-weight:600; text-transform:uppercase; letter-spacing:.5px; }
.acct-stat .v { font-size:13.5px; font-weight:700; color:var(--text); margin-top:3px; font-variant-numeric:tabular-nums; }

.pos { color:var(--pos); }
.neg { color:var(--neg); }
.neu { color:var(--text-3); }

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] { gap:4px; border-bottom:1px solid var(--border); }
.stTabs [data-baseweb="tab"] {
  height:44px; padding:0 18px; background:transparent; color:var(--text-2);
  font-weight:600; font-size:14px; border-radius:10px 10px 0 0;
}
.stTabs [data-baseweb="tab"]:hover { color:var(--text); background:var(--surface-2); }
.stTabs [aria-selected="true"] { color:var(--accent) !important; border-bottom:2px solid var(--accent); }
.stTabs [data-baseweb="tab-highlight"] { background:var(--accent); }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] { background:var(--surface); border-right:1px solid var(--border); }
section[data-testid="stSidebar"] .stMarkdown h1 { font-size:20px; color:var(--text); }

/* bigger, button-like account selectors in the sidebar */
section[data-testid="stSidebar"] .stButton > button {
  min-height: 46px; padding: 11px 15px; font-size: 14px; font-weight: 600;
  border-radius: 11px; border:1px solid var(--border); background:var(--surface); color:var(--text);
  text-align:left; justify-content:flex-start; transition: all .12s ease; box-shadow:none;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  border-color:var(--accent); color:var(--accent); background:var(--accent-weak);
}
section[data-testid="stSidebar"] .stButton > button[kind*="primary"],
section[data-testid="stSidebar"] .stFormSubmitButton > button[kind*="primary"] {
  background: var(--accent); border-color:var(--accent);
  color:#fff !important; box-shadow:0 2px 8px rgba(5,150,105,.25);
}
section[data-testid="stSidebar"] .stButton > button[kind*="primary"]:hover,
section[data-testid="stSidebar"] .stFormSubmitButton > button[kind*="primary"]:hover {
  background: var(--accent-strong); border-color:var(--accent-strong); color:#fff !important;
}
section[data-testid="stSidebar"] .stButton > button[kind*="primary"] p,
section[data-testid="stSidebar"] .stFormSubmitButton > button[kind*="primary"] p { color:#fff !important; }

/* account select buttons: colored left-accent by type (live=red, paper=amber) */
section[data-testid="stSidebar"] [class*="st-key-accbtn_live_"] button:not([kind*="primary"]) {
  border-left:3px solid var(--neg); padding-left:13px;
}
section[data-testid="stSidebar"] [class*="st-key-accbtn_paper_"] button:not([kind*="primary"]) {
  border-left:3px solid var(--amber); padding-left:13px;
}

/* trash: subtle ghost icon button that goes red on hover */
section[data-testid="stSidebar"] [class*="st-key-trash_"] button {
  min-height:46px; padding:0; border:1px solid var(--border); background:var(--surface-2);
  color:var(--text-3); box-shadow:none; justify-content:center; font-size:15px;
}
section[data-testid="stSidebar"] [class*="st-key-trash_"] button:hover {
  background:rgba(244,82,95,.15); color:var(--neg); border-color:rgba(244,82,95,.4);
}
section[data-testid="stSidebar"] [class*="st-key-trash_"] button p { color:inherit !important; }

/* ---------- tables ---------- */
[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:12px; overflow:hidden; }

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius:10px; font-weight:600; border:1px solid var(--border-strong);
  background:var(--surface); color:var(--text); transition:.12s;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  border-color:var(--accent); color:var(--accent); background:var(--accent-weak);
}
.stButton > button[kind*="primary"], .stFormSubmitButton > button[kind*="primary"] {
  background:var(--accent); border-color:var(--accent); color:#fff !important;
}
.stButton > button[kind*="primary"]:hover, .stFormSubmitButton > button[kind*="primary"]:hover {
  background:var(--accent-strong); border-color:var(--accent-strong); color:#fff !important;
}
.stButton > button[kind*="primary"] p, .stFormSubmitButton > button[kind*="primary"] p { color:#fff !important; }

/* ---------- news cards ---------- */
.news-card {
  background:var(--surface); border:1px solid var(--border); border-radius:14px;
  padding:15px 17px; margin-bottom:11px; box-shadow:var(--shadow-sm); transition:.15s;
}
.news-card:hover { border-color:var(--border-strong); box-shadow:var(--shadow-md); transform:translateY(-1px); }
.news-card a { color:var(--text); font-weight:700; font-size:15px; text-decoration:none; }
.news-card a:hover { color:var(--accent); }
.news-meta { color:var(--text-3); font-size:11.5px; margin:6px 0; }
.news-sum { color:var(--text-2); font-size:13px; line-height:1.55; }
.news-sym { display:inline-block; background:var(--accent-weak); color:var(--accent);
  font-size:10.5px; font-weight:700; padding:2px 8px; border-radius:6px; margin-right:5px; margin-top:4px; }

/* section labels */
.sec-label { color:var(--text-2); font-size:11.5px; font-weight:700; text-transform:uppercase;
  letter-spacing:.8px; margin:14px 0 11px 0; }

/* ---------- forms ---------- */
[data-testid="stForm"] {
  background:var(--surface); border:1px solid var(--border); border-radius:16px;
  padding:20px 22px; box-shadow:var(--shadow-sm);
}

/* ---------- inputs ---------- */
.stTextInput input, .stNumberInput input, .stTextArea textarea {
  border-radius:10px !important; border:1px solid var(--border-strong) !important;
  background:var(--surface) !important; color:var(--text) !important; font-size:14px;
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
  border-color:var(--accent) !important; box-shadow:0 0 0 3px rgba(16,185,129,.2) !important;
}
div[data-baseweb="select"] > div {
  border-radius:10px !important; border-color:var(--border-strong) !important; background:var(--surface) !important;
}
div[data-baseweb="select"] > div:focus-within {
  border-color:var(--accent) !important; box-shadow:0 0 0 3px rgba(16,185,129,.2) !important;
}
.stMultiSelect div[data-baseweb="tag"] { background:var(--accent-weak) !important; }
.stMultiSelect div[data-baseweb="tag"] span { color:var(--accent) !important; }
/* labels above inputs */
.stTextInput label, .stNumberInput label, .stSelectbox label, .stMultiSelect label,
.stSlider label, .stTextArea label, .stRadio label, .stCheckbox label {
  color:var(--text-2) !important; font-size:12.5px !important; font-weight:600 !important;
}
/* toggle / slider accent */
.stSlider [data-baseweb="slider"] div[role="slider"] { background:var(--accent) !important; }
.stCheckbox [data-baseweb="checkbox"] [data-checked="true"],
[data-testid="stToggle"] [aria-checked="true"] { background:var(--accent) !important; }

/* expander */
[data-testid="stExpander"] {
  border:1px solid var(--border) !important; border-radius:12px !important;
  background:var(--surface) !important; box-shadow:var(--shadow-sm);
}
[data-testid="stExpander"] summary:hover { color:var(--accent) !important; }

/* alerts a touch softer */
[data-testid="stAlert"] { border-radius:11px; }

/* hide Streamlit's "Press Enter to submit" / input instruction tells */
[data-testid="InputInstructions"], [data-testid="stTextInputInstructions"],
div[class*="InputInstructions"] { display:none !important; }

/* dividers */
hr { border-color:var(--border) !important; }

/* ---------- custom data table ---------- */
.tbl-wrap { border:1px solid var(--border); border-radius:14px; overflow:auto; margin:6px 0 12px 0;
  box-shadow:var(--shadow-sm); background:var(--surface); }
table.dtbl { width:100%; border-collapse:collapse; font-size:13px; }
table.dtbl thead th {
  background:var(--surface-2); color:var(--text-3); text-transform:uppercase; font-size:10.5px;
  letter-spacing:.6px; padding:12px 14px; text-align:right; white-space:nowrap;
  border-bottom:1px solid var(--border); position:sticky; top:0;
}
table.dtbl thead th.l { text-align:left; }
table.dtbl tbody td { padding:11px 14px; text-align:right; white-space:nowrap;
  border-bottom:1px solid var(--border); color:var(--text); font-variant-numeric:tabular-nums; }
table.dtbl tbody td.l { text-align:left; }
table.dtbl tbody tr:hover { background:var(--surface-2); }
table.dtbl tbody tr:last-child td { border-bottom:none; }
.tk { font-weight:700; color:var(--text); }
.badge-l { background:var(--accent-weak); color:var(--accent); padding:2px 9px; border-radius:6px; font-size:11px; font-weight:700; }
.badge-s { background:rgba(244,82,95,.16); color:#ff6b75; padding:2px 9px; border-radius:6px; font-size:11px; font-weight:700; }
.sl-val { color:var(--neg); font-weight:600; }
.tp-val { color:var(--pos); font-weight:600; }
.dim { color:var(--text-3); }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def logo_svg(size: int = 32, idn: str = "a") -> str:
    """Inline SVG logo mark: emerald rounded tile with an upward trend line.

    `idn` keeps the gradient id unique when several marks share one page.
    """
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 32 32" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" style="flex:none;display:block">'
        f'<rect width="32" height="32" rx="8.5" fill="url(#alg{idn})"/>'
        f'<path d="M6.5 21.5 L12.5 14 L17 17.5 L25.5 8" stroke="#fff" stroke-width="2.4" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="25.5" cy="8" r="2.3" fill="#fff"/>'
        f'<defs><linearGradient id="alg{idn}" x1="3" y1="3" x2="29" y2="29" '
        f'gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="#10b981"/><stop offset="1" stop-color="#047857"/>'
        f'</linearGradient></defs></svg>'
    )


def wordmark(size_px: int = 24, idn: str = "h") -> str:
    """Logo mark + 'ALDash' wordmark as a single inline-flex unit."""
    return (
        f'<span style="display:inline-flex;align-items:center;gap:10px;'
        f'font-size:{size_px}px;font-weight:800;color:var(--text);letter-spacing:-.5px;">'
        f'{logo_svg(round(size_px * 1.35), idn)}'
        f'<span>AL<span style="color:var(--accent)">Dash</span></span></span>'
    )


def header(subtitle_html: str) -> None:
    st.markdown(
        f'<div class="app-header">'
        f'<div class="brand">{wordmark(24, "hdr")}</div>'
        f'<div class="sub">{subtitle_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _sub(value: Optional[float], text: str) -> str:
    if value is None or text is None:
        return ""
    cls = "pos" if value > 0 else "neg" if value < 0 else "neu"
    return f'<div class="kpi-sub {cls}">{text}</div>'


def kpi_card(label: str, value: str, sub_value: Optional[float] = None, sub_text: Optional[str] = None) -> str:
    return (
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>{_sub(sub_value, sub_text)}</div>'
    )


def kpi_row(cards: Iterable[str]) -> None:
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def account_card(name: str, equity: str, cash: str, float_pl: float,
                 float_pl_text: str, paper: bool) -> str:
    cls = "paper" if paper else "live"
    tag = "PAPER" if paper else "LIVE"
    fl_cls = "pos" if float_pl > 0 else "neg" if float_pl < 0 else "neu"
    return (
        f'<div class="acct-card {cls}"><div class="acct-top">'
        f'<span class="acct-name">{name}</span>'
        f'<span class="acct-tag {cls}">{tag}</span></div>'
        f'<div class="acct-eq">{equity}</div>'
        f'<div class="acct-eq-label">Equity</div>'
        f'<div class="acct-foot">'
        f'<div class="acct-stat"><div class="k">Balance</div><div class="v">{cash}</div></div>'
        f'<div class="acct-stat"><div class="k">Floating</div>'
        f'<div class="v {fl_cls}">{float_pl_text}</div></div>'
        f'</div></div>'
    )


def account_row(cards: Iterable[str]) -> None:
    st.markdown(f'<div class="acct-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def label(text: str) -> None:
    st.markdown(f'<div class="sec-label">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Table styling (pandas Styler -> colored PnL, formatted money/%/price)
# ---------------------------------------------------------------------------
def _money(v):
    if pd.isna(v):
        return "—"
    s = "-" if v < 0 else ""
    return f"{s}${abs(v):,.2f}"


def _price(v):
    if pd.isna(v):
        return "—"
    return f"${v:,.2f}"


def _pct(v):
    if pd.isna(v):
        return "—"
    return f"{v:+.2f}%"


def _color_signed(v):
    if isinstance(v, (int, float)) and not pd.isna(v):
        if v > 0:
            return f"color:{GREEN}; font-weight:600;"
        if v < 0:
            return f"color:{RED}; font-weight:600;"
    return ""


def style_table(
    df: pd.DataFrame,
    money_cols: Iterable[str] = (),
    price_cols: Iterable[str] = (),
    pct_cols: Iterable[str] = (),
    signed_cols: Iterable[str] = (),
):
    """Return a Styler with formatted numbers and green/red signed columns."""
    fmt = {}
    for c in money_cols:
        if c in df.columns:
            fmt[c] = _money
    for c in price_cols:
        if c in df.columns:
            fmt[c] = _price
    for c in pct_cols:
        if c in df.columns:
            fmt[c] = _pct

    sty = df.style.format(fmt, na_rep="—")
    signed = [c for c in signed_cols if c in df.columns]
    if signed:
        sty = sty.map(_color_signed, subset=signed)
    sty = sty.hide(axis="index")
    return sty


def render_table(headers, rows) -> None:
    """Render a custom HTML table (reliable formatting + colors).

    headers: list of (label, align) where align is 'l' or 'r'.
    rows:    list of rows; each row is a list of (html_text, css_class) cells.
    """
    thead = "".join(f'<th class="{a}">{h}</th>' for h, a in headers)
    body = ""
    for r in rows:
        tds = "".join(f'<td class="{cls}">{txt}</td>' for txt, cls in r)
        body += f"<tr>{tds}</tr>"
    st.markdown(
        f'<div class="tbl-wrap"><table class="dtbl"><thead><tr>{thead}</tr>'
        f"</thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def signed_class(v) -> str:
    if v is None:
        return "neu"
    return "pos" if v > 0 else "neg" if v < 0 else "neu"
