"""Visual layer: global CSS + reusable card / table styling helpers.

Keeps app.py focused on data + wiring while this module owns the "looks like a
real product" styling (KPI cards, colored PnL, app header, tabs, tables).
"""
from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd
import streamlit as st

GREEN = "#16c784"
RED = "#ea3943"
MUTED = "#8b97a7"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, .stMetric { font-family: 'Inter', system-ui, sans-serif; }

.block-container { padding-top: 1.1rem; padding-bottom: 2.5rem; max-width: 1480px; }

/* hide default Streamlit chrome */
#MainMenu, footer { visibility: hidden; height: 0; }
header[data-testid="stHeader"] { background: transparent; height: 0; }

/* ---------- app header ---------- */
.app-header {
  display:flex; align-items:center; justify-content:space-between;
  padding: 16px 22px; border-radius: 16px; margin-bottom: 20px;
  background: linear-gradient(120deg, #14243f 0%, #0b1220 60%);
  border: 1px solid #1f2a3a;
  box-shadow: 0 4px 24px rgba(0,0,0,.35);
}
.app-header .brand { font-size: 23px; font-weight: 800; color:#f8fafc; letter-spacing:.3px; }
.app-header .brand span { color:#3b82f6; }
.app-header .sub { color:#8b97a7; font-size:13px; text-align:right; line-height:1.5; }

/* ---------- KPI cards ---------- */
.kpi-grid {
  display:grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr));
  gap:14px; margin: 4px 0 14px 0;
}
.kpi-card {
  background:#121822; border:1px solid #1f2a3a; border-radius:16px;
  padding:16px 18px; transition: all .15s ease;
}
.kpi-card:hover { border-color:#2f3e54; transform: translateY(-2px); box-shadow:0 8px 22px rgba(0,0,0,.3); }
.kpi-label { color:#8b97a7; font-size:11.5px; font-weight:600; text-transform:uppercase; letter-spacing:.7px; margin-bottom:9px; }
.kpi-value { font-size:25px; font-weight:800; color:#f1f5f9; line-height:1.05; }
.kpi-sub { font-size:12.5px; font-weight:600; margin-top:7px; }

/* ---------- account cards ---------- */
.acct-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(210px,1fr)); gap:12px; margin-bottom:6px; }
.acct-card {
  background:#0f141d; border:1px solid #1f2a3a; border-left:3px solid #3b82f6;
  border-radius:13px; padding:13px 15px;
}
.acct-card.live  { border-left-color:#ea3943; }
.acct-card.paper { border-left-color:#eab308; }
.acct-top { display:flex; justify-content:space-between; align-items:center; }
.acct-name { font-weight:600; color:#e5e7eb; font-size:13px; }
.acct-tag { font-size:10px; font-weight:700; padding:2px 7px; border-radius:6px; }
.acct-tag.live { background:rgba(234,57,67,.15); color:#ff6b76; }
.acct-tag.paper{ background:rgba(234,179,8,.15); color:#facc15; }
.acct-eq { font-size:19px; font-weight:800; color:#f1f5f9; margin-top:6px; }

.pos { color:#16c784; }
.neg { color:#ea3943; }
.neu { color:#8b97a7; }

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] { gap:4px; border-bottom:1px solid #1f2a3a; }
.stTabs [data-baseweb="tab"] {
  height:44px; padding:0 20px; background:transparent; color:#8b97a7;
  font-weight:600; font-size:14px; border-radius:10px 10px 0 0;
}
.stTabs [data-baseweb="tab"]:hover { color:#cbd5e1; background:#121822; }
.stTabs [aria-selected="true"] { background:#121822; color:#fff !important; border-bottom:2px solid #3b82f6; }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] { background:#0a0e15; border-right:1px solid #1f2a3a; }
section[data-testid="stSidebar"] .stMarkdown h1 { font-size:20px; }

/* bigger, button-like account selectors in the sidebar */
section[data-testid="stSidebar"] .stButton > button {
  min-height: 48px; padding: 12px 16px; font-size: 14.5px; font-weight: 600;
  border-radius: 11px; border:1px solid #243044; background:#10151d; color:#cbd5e1;
  text-align:left; justify-content:flex-start; transition: all .12s ease;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  border-color:#3b82f6; color:#fff; background:#141b26;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: linear-gradient(120deg,#2563eb,#3b82f6); border-color:#3b82f6;
  color:#fff; box-shadow:0 4px 14px rgba(59,130,246,.35);
}

/* ---------- tables ---------- */
[data-testid="stDataFrame"] { border:1px solid #1f2a3a; border-radius:12px; overflow:hidden; }

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button {
  border-radius:9px; font-weight:600; border:1px solid #2f3e54;
}
.stButton > button[kind="primary"] { background:#3b82f6; border-color:#3b82f6; }

/* ---------- news cards ---------- */
.news-card {
  background:#121822; border:1px solid #1f2a3a; border-radius:13px;
  padding:14px 16px; margin-bottom:10px; transition:.15s;
}
.news-card:hover { border-color:#2f3e54; }
.news-card a { color:#e8eef6; font-weight:600; font-size:15px; text-decoration:none; }
.news-card a:hover { color:#60a5fa; }
.news-meta { color:#8b97a7; font-size:11.5px; margin:6px 0; }
.news-sum { color:#aab4c2; font-size:13px; line-height:1.5; }
.news-sym { display:inline-block; background:rgba(59,130,246,.14); color:#7eb0ff;
  font-size:10.5px; font-weight:600; padding:1px 7px; border-radius:5px; margin-right:5px; }

/* section labels */
.sec-label { color:#8b97a7; font-size:12px; font-weight:600; text-transform:uppercase;
  letter-spacing:.7px; margin:6px 0 10px 0; }

/* ---------- custom data table ---------- */
.tbl-wrap { border:1px solid #1f2a3a; border-radius:13px; overflow:auto; margin:4px 0 10px 0; }
table.dtbl { width:100%; border-collapse:collapse; font-size:13px; }
table.dtbl thead th {
  background:#0f141d; color:#8b97a7; text-transform:uppercase; font-size:10.5px;
  letter-spacing:.6px; padding:11px 13px; text-align:right; white-space:nowrap;
  border-bottom:1px solid #1f2a3a; position:sticky; top:0;
}
table.dtbl thead th.l { text-align:left; }
table.dtbl tbody td { padding:10px 13px; text-align:right; white-space:nowrap;
  border-bottom:1px solid #161d28; color:#dbe2ea; }
table.dtbl tbody td.l { text-align:left; }
table.dtbl tbody tr:hover { background:#121822; }
table.dtbl tbody tr:last-child td { border-bottom:none; }
.tk { font-weight:700; color:#f1f5f9; }
.badge-l { background:rgba(22,199,132,.14); color:#3ddc97; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700; }
.badge-s { background:rgba(234,57,67,.14); color:#ff6b76; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700; }
.sl-val { color:#ff8b93; font-weight:600; }
.tp-val { color:#5fd0a0; font-weight:600; }
.dim { color:#6b7686; }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def header(subtitle_html: str) -> None:
    st.markdown(
        f'<div class="app-header">'
        f'<div class="brand">📈 AL<span>Dash</span></div>'
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


def account_card(name: str, equity: str, float_pl: float, float_pl_text: str, paper: bool) -> str:
    cls = "paper" if paper else "live"
    tag = "PAPER" if paper else "LIVE"
    sub = _sub(float_pl, f"{float_pl_text} floating")
    return (
        f'<div class="acct-card {cls}"><div class="acct-top">'
        f'<span class="acct-name">{name}</span>'
        f'<span class="acct-tag {cls}">{tag}</span></div>'
        f'<div class="acct-eq">{equity}</div>{sub}</div>'
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
