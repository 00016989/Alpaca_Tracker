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
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root{
  --bg:#090C12; --surface:#10141D; --surface-2:#141926; --raised:#1A2030;
  --border:rgba(148,163,184,.09); --border-strong:rgba(148,163,184,.16);
  --text:#EAEDF3; --text-2:#8A93A6; --text-3:#576074;
  --accent:#35E0A1; --accent-strong:#1FB07E; --accent-weak:rgba(53,224,161,.14);
  --pos:#35E0A1; --neg:#FF647C; --amber:#F2B544; --live:#FF5470;
  --mono:'JetBrains Mono',ui-monospace,monospace;
  --display:'Space Grotesk',system-ui,sans-serif;
  --body:'Inter',system-ui,sans-serif;
  --shadow-sm:0 1px 2px rgba(0,0,0,.30), 0 1px 3px rgba(0,0,0,.24);
  --shadow-md:0 8px 26px rgba(0,0,0,.42), 0 2px 6px rgba(0,0,0,.30);
}

html, body, [class*="css"], .stMarkdown, .stMetric { font-family: var(--body); }
.stApp { background: var(--bg); }
.stApp::before { content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    radial-gradient(1100px 600px at 78% -8%, rgba(53,224,161,.07), transparent 60%),
    radial-gradient(900px 500px at -5% 110%, rgba(60,110,255,.05), transparent 55%); }
[data-testid="stAppViewContainer"], section[data-testid="stSidebar"] { position:relative; z-index:1; }
body, .stMarkdown, p, span, label { color: var(--text); }
/* monospace for all numeric displays — the "terminal" look */
.kpi-value, .acct-eq, .acct-stat .v, .hero-eq, .hero-stat .v, .num,
.ptbl-row .r, .rr-ratio, .rr-amts, .rr-scale, .p-sub,
table.dtbl tbody td, .kpi-sub { font-family:var(--mono); font-feature-settings:"tnum" 1; }
/* display font for brand + tickers + headings */
.hd-name, .hero-name, .p-sym, .tk { font-family:var(--display); }

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
.kpi-card.feature { background:linear-gradient(140deg,rgba(53,224,161,.10),var(--surface) 55%); border-color:rgba(53,224,161,.22); }
.kpi-label { color:var(--text-3); font-size:10.5px; font-weight:600; text-transform:uppercase; letter-spacing:1.3px; margin-bottom:10px; }
.kpi-value { font-size:24px; font-weight:600; color:var(--text); line-height:1.05; letter-spacing:-.5px; }
.kpi-sub { font-size:12px; font-weight:600; margin-top:8px; }

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
.acct-tag.all  { background:var(--accent-weak); color:var(--accent); }
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

/* ---------- material icons (inline, monochrome) ---------- */
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block');
.msym { font-family:'Material Symbols Rounded'; font-weight:400; font-style:normal;
  line-height:1; vertical-align:-3px; -webkit-font-feature-settings:'liga';
  -webkit-font-smoothing:antialiased; font-size:16px; }

/* ---------- header (rich) ---------- */
.hd { display:flex; align-items:center; justify-content:space-between;
  padding:18px 22px; border-radius:14px; margin-bottom:20px; position:relative; overflow:hidden;
  background:linear-gradient(120deg,rgba(53,224,161,.06),var(--surface) 42%);
  border:1px solid var(--border); box-shadow:var(--shadow-sm); }
.hd::after { content:""; position:absolute; right:-40px; top:-60px; width:240px; height:240px;
  border-radius:50%; background:radial-gradient(circle,rgba(53,224,161,.10),transparent 70%); }
.hd-l, .hd-r { position:relative; z-index:1; }
.hd-l { display:flex; align-items:center; gap:14px; }
.hd-mark { width:52px; height:52px; border-radius:14px; display:flex; align-items:center;
  justify-content:center; background:linear-gradient(135deg,#10b981,#047857);
  box-shadow:0 4px 16px rgba(16,185,129,.32); }
.hd-name { font-size:23px; font-weight:800; letter-spacing:-.5px; color:var(--text); line-height:1.1; }
.hd-name span { color:var(--accent); }
.hd-tag { color:var(--text-3); font-size:12.5px; margin-top:2px; }
.hd-r { text-align:right; }
.hd-counts { font-size:13px; color:var(--text-2); display:flex; align-items:center; gap:8px; justify-content:flex-end; }
.hd-pill { font-size:10.5px; font-weight:700; letter-spacing:.5px; padding:2px 8px; border-radius:20px; }
.hd-pill.live { background:rgba(244,82,95,.16); color:#ff6b75; }
.hd-pill.paper { background:rgba(245,158,11,.16); color:#fbbf24; }
.hd-stream { font-size:11.5px; color:var(--text-3); margin-top:7px; }
.hd-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--pos);
  margin-right:5px; vertical-align:middle; animation:pulse 1.8s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }

/* ---------- KPI label icon ---------- */
.kpi-label .msym { font-size:15px; margin-right:5px; color:var(--text-3); vertical-align:-2px; }

/* ---------- selected-account hero ---------- */
.hero { display:grid; grid-template-columns:1fr 1fr; gap:18px; align-items:center;
  background:var(--surface); border:1px solid var(--border); border-left:3px solid var(--accent);
  border-radius:16px; padding:18px 22px; box-shadow:var(--shadow-sm); margin-bottom:8px; }
.hero.live { border-left-color:var(--neg); } .hero.paper { border-left-color:var(--amber); }
.hero-top { display:flex; align-items:center; gap:10px; }
.hero-name { font-size:16px; font-weight:800; color:var(--text); }
.hero-eqlabel { color:var(--text-3); font-size:10.5px; font-weight:600; text-transform:uppercase;
  letter-spacing:.7px; margin:14px 0 2px; }
.hero-eq { font-size:42px; font-weight:800; letter-spacing:-1.2px; color:var(--text);
  line-height:1.05; font-variant-numeric:tabular-nums; }
.hero-foot { display:flex; gap:34px; margin-top:14px; }
.hero-stat .k { color:var(--text-3); font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.6px; }
.hero-stat .v { font-size:17px; font-weight:700; margin-top:3px; font-variant-numeric:tabular-nums; color:var(--text); }
.hero-chart { position:relative; }
.hero-charttop { display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }
.hero-charttop .lbl { color:var(--text-3); font-size:10.5px; font-weight:600; text-transform:uppercase; letter-spacing:.7px; }

/* ---------- positions (rich rows) ---------- */
.ptbl { border:1px solid var(--border); border-radius:16px; overflow:hidden;
  box-shadow:var(--shadow-sm); background:var(--surface); margin:6px 0 12px; }
.ptbl-head, .ptbl-row { display:grid;
  grid-template-columns: 1.4fr .7fr .55fr .8fr .8fr .95fr 2.5fr 1fr .65fr;
  align-items:center; column-gap:18px; }
.ptbl-head { background:var(--surface-2); border-bottom:1px solid var(--border);
  padding:11px 18px; color:var(--text-3); font-size:10px; font-weight:700;
  text-transform:uppercase; letter-spacing:.6px; }
.ptbl-head .r, .ptbl-row .r { text-align:right; }
.ptbl-row { padding:14px 18px; border-bottom:1px solid var(--border); font-size:13.5px;
  color:var(--text); font-variant-numeric:tabular-nums; }
.ptbl-row:last-child { border-bottom:none; }
.ptbl-row:hover { background:var(--surface-2); }
.p-sym { font-weight:800; font-size:15px; color:var(--text); }
.p-sub { color:var(--text-3); font-size:11px; margin-top:1px; }
.p-badge { display:inline-flex; align-items:center; gap:3px; padding:3px 9px; border-radius:7px;
  font-size:11px; font-weight:700; }
.p-badge.long { background:var(--accent-weak); color:var(--accent); }
.p-badge.short { background:rgba(244,82,95,.16); color:#ff6b75; }
.p-badge .msym { font-size:13px; vertical-align:-2px; }

/* risk:reward gauge — proportional risk vs reward split */
.rr { padding:0 6px; display:flex; flex-direction:column; gap:5px; }
.rr-topline { display:flex; align-items:baseline; justify-content:space-between; font-size:11px; }
.rr-ratio { font-weight:700; color:var(--text); font-size:14px; }
.rr-ratio span { color:var(--text-3); font-weight:500; font-size:10px; margin-left:3px; }
.rr-amts { font-weight:600; font-size:11px; }
.rr-bar { position:relative; height:7px; border-radius:6px; overflow:hidden; display:flex; background:var(--raised); }
.rr-bar .risk { background:linear-gradient(90deg,rgba(255,100,124,.35),var(--neg)); }
.rr-bar .reward { background:linear-gradient(90deg,var(--pos),rgba(53,224,161,.35)); }
.rr-now { position:absolute; top:-3px; width:2px; height:13px; background:#fff; border-radius:2px;
  box-shadow:0 0 6px rgba(255,255,255,.7); }
.rr-scale { display:flex; justify-content:space-between; font-size:9.5px; color:var(--text-3); }
.rr-scale .now { color:var(--text-2); font-weight:600; }
.rr-none { color:var(--text-3); font-size:11.5px; }

/* destructive close-position button */
[class*="st-key-close_pos_btn"] button { background:rgba(244,82,95,.14) !important;
  border-color:rgba(244,82,95,.45) !important; color:#ff6b75 !important; }
[class*="st-key-close_pos_btn"] button:hover { background:var(--neg) !important;
  border-color:var(--neg) !important; color:#fff !important; }
[class*="st-key-close_pos_btn"] button p { color:inherit !important; }

/* ---------- sidebar account dots + tags ---------- */
section[data-testid="stSidebar"] [class*="st-key-accbtn_live_"] button,
section[data-testid="stSidebar"] [class*="st-key-accbtn_paper_"] button {
  position:relative; padding-left:32px !important; border-left:1px solid var(--border) !important; }
section[data-testid="stSidebar"] [class*="st-key-accbtn_live_"] button::before,
section[data-testid="stSidebar"] [class*="st-key-accbtn_paper_"] button::before {
  content:""; position:absolute; left:15px; top:50%; transform:translateY(-50%);
  width:8px; height:8px; border-radius:50%; }
section[data-testid="stSidebar"] [class*="st-key-accbtn_live_"] button::before { background:var(--neg); }
section[data-testid="stSidebar"] [class*="st-key-accbtn_paper_"] button::before { background:var(--amber); }
section[data-testid="stSidebar"] [class*="st-key-accbtn_live_"] button::after,
section[data-testid="stSidebar"] [class*="st-key-accbtn_paper_"] button::after {
  position:absolute; right:14px; top:50%; transform:translateY(-50%);
  font-size:9px; font-weight:700; letter-spacing:.6px; }
section[data-testid="stSidebar"] [class*="st-key-accbtn_live_"] button::after { content:"LIVE"; color:var(--neg); }
section[data-testid="stSidebar"] [class*="st-key-accbtn_paper_"] button::after { content:"PAPER"; color:var(--amber); }
/* selected account: emerald tint instead of solid fill */
section[data-testid="stSidebar"] .stButton > button[kind*="primary"] {
  background:var(--accent-weak) !important; border-color:var(--accent) !important;
  border-left:3px solid var(--accent) !important; color:var(--text) !important; box-shadow:none !important; }
section[data-testid="stSidebar"] .stButton > button[kind*="primary"] p { color:var(--text) !important; }
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


def icon(name: str) -> str:
    """Inline Material Symbols icon (monochrome, inherits color)."""
    return f'<span class="msym">{name}</span>'


def header(n_live: int, n_paper: int, updated: str = "live") -> None:
    n = n_live + n_paper
    pills = ""
    if n_live:
        pills += f'<span class="hd-pill live">● {n_live} LIVE</span>'
    if n_paper:
        pills += f'<span class="hd-pill paper">● {n_paper} PAPER</span>'
    st.markdown(
        f'<div class="hd"><div class="hd-l">'
        f'<div class="hd-mark">{logo_svg(34, "hdr")}</div>'
        f'<div><div class="hd-name">AL<span>Dash</span></div>'
        f'<div class="hd-tag">Live trading dashboard</div></div></div>'
        f'<div class="hd-r"><div class="hd-counts">{n} account(s) {pills}</div>'
        f'<div class="hd-stream"><span class="hd-dot"></span>Streaming · {updated}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _sub(value: Optional[float], text: str) -> str:
    if value is None or text is None:
        return ""
    cls = "pos" if value > 0 else "neg" if value < 0 else "neu"
    return f'<div class="kpi-sub {cls}">{text}</div>'


def kpi_card(label: str, value: str, sub_value: Optional[float] = None,
             sub_text: Optional[str] = None, ic: Optional[str] = None,
             feature: bool = False) -> str:
    icon_html = icon(ic) if ic else ""
    cls = "kpi-card feature" if feature else "kpi-card"
    return (
        f'<div class="{cls}"><div class="kpi-label">{icon_html}{label}</div>'
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


def _money_signed(v: float) -> str:
    return f"{'+' if v >= 0 else '-'}${abs(v):,.2f}"


def sparkline(values, width: int = 440, height: int = 116, idn: str = "s") -> str:
    """Area + line SVG sparkline from a list of equity values."""
    vals = [float(v) for v in (values or [])]
    if len(vals) < 2:
        return '<div class="rr-none" style="padding:38px 0;text-align:center">No intraday equity yet.</div>'
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    n = len(vals)
    pad = 7
    w, h = width, height
    xs = [pad + i * (w - 2 * pad) / (n - 1) for i in range(n)]
    ys = [pad + (1 - (v - lo) / rng) * (h - 2 * pad) for v in vals]
    line = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in zip(xs, ys))
    area = line + f" L {xs[-1]:.1f} {h - pad:.1f} L {xs[0]:.1f} {h - pad:.1f} Z"
    col = "#35E0A1" if vals[-1] >= vals[0] else "#FF647C"
    return (
        f'<svg width="100%" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
        f'<defs><linearGradient id="sp{idn}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{col}" stop-opacity=".30"/>'
        f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></linearGradient></defs>'
        f'<path d="{area}" fill="url(#sp{idn})"/>'
        f'<path d="{line}" fill="none" stroke="{col}" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
        f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="3.2" fill="{col}"/></svg>'
    )


def account_hero(name: str, paper, equity_str: str, balance_str: str,
                 floating_val: float, floating_str: str, spark_html: str,
                 pct_val: float, pct_str: str) -> None:
    if paper is None:                       # aggregate "All accounts" view
        cls, tag, dot = "", "COMBINED", "#10b981"
    else:
        cls = "paper" if paper else "live"
        tag = "PAPER" if paper else "LIVE"
        dot = "#f59e0b" if paper else "#f4525f"
    fl = "pos" if floating_val > 0 else "neg" if floating_val < 0 else "neu"
    pc = "pos" if pct_val > 0 else "neg" if pct_val < 0 else "neu"
    st.markdown(
        f'<div class="hero {cls}"><div>'
        f'<div class="hero-top">'
        f'<span style="width:9px;height:9px;border-radius:50%;background:{dot};display:inline-block"></span>'
        f'<span class="hero-name">{name}</span>'
        f'<span class="acct-tag {cls or "all"}">{tag}</span></div>'
        f'<div class="hero-eqlabel">Account Equity</div>'
        f'<div class="hero-eq">{equity_str}</div>'
        f'<div class="hero-foot">'
        f'<div class="hero-stat"><div class="k">Balance</div><div class="v">{balance_str}</div></div>'
        f'<div class="hero-stat"><div class="k">Floating</div><div class="v {fl}">{floating_str}</div></div>'
        f'</div></div>'
        f'<div class="hero-chart"><div class="hero-charttop">'
        f'<span class="lbl">Equity · Today</span>'
        f'<span class="kpi-sub {pc}" style="margin:0">{pct_str}</span></div>{spark_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _rr_cell(pos) -> str:
    sl, tp, cur = pos.stop_loss, pos.take_profit, pos.current_price
    if sl is None or tp is None:
        return '<div class="rr-none">No SL / TP set</div>'
    sla = pos.sl_amount or 0.0
    tpa = pos.tp_amount or 0.0
    risk, reward = abs(sla), abs(tpa)
    total = (risk + reward) or 1.0
    risk_w = risk / total * 100.0
    reward_w = reward / total * 100.0
    now = max(2.0, min(98.0, (cur - sl) / (tp - sl) * 100.0)) if (tp - sl) else 50.0
    rr = pos.risk_reward
    ratio = f"{rr:.2f}" if rr is not None else "—"
    return (
        f'<div class="rr">'
        f'<div class="rr-topline">'
        f'<span class="rr-ratio">{ratio}<span> R:R</span></span>'
        f'<span class="rr-amts"><span class="neg">{_money_signed(sla)}</span>'
        f'<span class="dim"> / </span><span class="pos">{_money_signed(tpa)}</span></span></div>'
        f'<div class="rr-bar"><div class="risk" style="width:{risk_w:.1f}%"></div>'
        f'<div class="reward" style="width:{reward_w:.1f}%"></div>'
        f'<div class="rr-now" style="left:{now:.1f}%"></div></div>'
        f'<div class="rr-scale"><span>{_price(sl)}</span>'
        f'<span class="now">now {_price(cur)}</span><span>{_price(tp)}</span></div>'
        f'</div>'
    )


def render_positions_table(rows, paper_map: dict) -> None:
    head = (
        '<div class="ptbl"><div class="ptbl-head">'
        '<span>Ticker</span><span>Side</span><span class="r">Qty</span>'
        '<span class="r">Entry</span><span class="r">Current</span><span class="r">Worth</span>'
        '<span>Risk / Reward</span><span class="r">Float PnL</span><span class="r">PnL %</span>'
        '</div>'
    )
    body = ""
    for r in rows:
        is_paper = paper_map.get(r.account, True)
        sub = f'{r.account} · {"paper" if is_paper else "live"}'
        if r.side == "long":
            badge = f'<span class="p-badge long">{icon("north")}LONG</span>'
        else:
            badge = f'<span class="p-badge short">{icon("south")}SHORT</span>'
        plc = signed_class(r.unrealized_pl)
        ppc = signed_class(r.unrealized_plpc)
        body += (
            '<div class="ptbl-row">'
            f'<div><div class="p-sym">{r.symbol}</div><div class="p-sub">{sub}</div></div>'
            f'<div>{badge}</div>'
            f'<div class="r">{abs(r.qty):,.2f}</div>'
            f'<div class="r">{_price(r.avg_entry)}</div>'
            f'<div class="r">{_price(r.current_price)}</div>'
            f'<div class="r">{_money(r.market_value)}</div>'
            f'<div>{_rr_cell(r)}</div>'
            f'<div class="r {plc}" style="font-weight:700">{_money(r.unrealized_pl)}</div>'
            f'<div class="r {ppc}">{r.unrealized_plpc:+.2f}%</div>'
            '</div>'
        )
    st.markdown(head + body + "</div>", unsafe_allow_html=True)


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
