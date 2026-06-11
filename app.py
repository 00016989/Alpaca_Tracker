"""ALDash — multi-account Alpaca trading dashboard.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from aldash import format as fmt
from aldash import store, ui
from aldash.auth import logout_button, require_login
from aldash.client import AccountClient
from aldash.config import AccountConfig, load_accounts
from aldash.positions import ConsolidatedPosition, consolidate
from aldash.tradelog import fetch_filled_orders, fifo_round_trips, summarize

st.set_page_config(page_title="ALDash", page_icon="📈", layout="wide")
ui.inject_css()
require_login()  # password gate (no-op if ALDASH_PASSWORD is unset)


# ──────────────────────────────────────────────────────────────────────────
# Clients (cached so we don't rebuild HTTP sessions every rerun)
# ──────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_client(name: str, key: str, secret: str, paper: bool) -> AccountClient:
    return AccountClient(AccountConfig(name=name, api_key=key, api_secret=secret, paper=paper))


def client_for(cfg: AccountConfig) -> AccountClient:
    return get_client(cfg.name, cfg.api_key, cfg.api_secret, cfg.paper)


# ──────────────────────────────────────────────────────────────────────────
# Data fetch (per account, fault-isolated)
# ──────────────────────────────────────────────────────────────────────────
def fetch_account(cfg: AccountConfig) -> dict:
    out = {"cfg": cfg, "error": None, "account": None, "positions": [], "orders": []}
    try:
        client = client_for(cfg)
        out["account"] = client.get_account()
        out["orders"] = client.get_open_orders()
        out["positions"] = client.get_positions()
    except Exception as exc:  # surface, don't crash the whole dashboard
        out["error"] = str(exc)
    return out


def consolidated_rows(data: dict) -> list[ConsolidatedPosition]:
    if data["error"]:
        return []
    return consolidate(data["cfg"].name, data["positions"], data["orders"])


@st.cache_data(ttl=120, show_spinner=False)
def cached_fills(name: str, key: str, secret: str, paper: bool, days: int):
    """Cached so the trade log doesn't re-hit the API on every refresh."""
    client = get_client(name, key, secret, paper)
    return fetch_filled_orders(client, days=days)


# ──────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────
accounts = load_accounts()

st.sidebar.title("📈 ALDash")

if not accounts:
    st.title("Welcome to ALDash")
    st.warning("No accounts configured yet.")
    st.markdown(
        """
        **Setup (1 minute):**
        1. Copy `.env.example` → `.env`  *(or `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`)*
        2. Paste your Alpaca API key + secret for each account
        3. Set `PAPER=true` for paper accounts, `false` for live
        4. Restart the app

        Get keys at **https://app.alpaca.markets** → account menu → *API Keys*.
        """
    )
    st.stop()

name_to_cfg = {a.name: a for a in accounts}

# Single-select account picker as big buttons: clicking one selects only it.
# "All accounts" keeps the combined cross-account view available.
ALL_ACCOUNTS = "__all__"
st.session_state.setdefault("account_choice", ALL_ACCOUNTS)

st.sidebar.markdown("**Accounts**")

if st.sidebar.button(f"★  All accounts  ·  {len(accounts)}", key="accbtn_all", width="stretch",
                     type="primary" if st.session_state["account_choice"] == ALL_ACCOUNTS else "secondary"):
    st.session_state["account_choice"] = ALL_ACCOUNTS
    st.rerun()

for a in accounts:
    badge = "🟡 Paper" if a.paper else "🔴 Live"
    active = st.session_state["account_choice"] == a.name
    col_sel, col_del = st.sidebar.columns([5, 1])
    if col_sel.button(f"{a.name}  ·  {badge}", key=f"accbtn_{a.name}", width="stretch",
                      type="primary" if active else "secondary"):
        st.session_state["account_choice"] = a.name
        st.rerun()
    if col_del.button("🗑️", key=f"trash_{a.name}", width="stretch",
                      help=f"Delete {a.name}"):
        st.session_state["pending_delete"] = a.name
        st.rerun()

    # Two-step confirm so a live account isn't removed by accident.
    if st.session_state.get("pending_delete") == a.name:
        note = "Removes it permanently." if a.managed else "Hides it (restore in ⚙️ Accounts)."
        st.sidebar.caption(f"Delete **{a.name}**? {note}")
        cy, cn = st.sidebar.columns(2)
        if cy.button("✓ Delete", key=f"cfm_{a.name}", type="primary", width="stretch"):
            store.remove(a)
            if st.session_state.get("account_choice") == a.name:
                st.session_state["account_choice"] = ALL_ACCOUNTS
            st.session_state["pending_delete"] = None
            st.rerun()
        if cn.button("Cancel", key=f"cnl_{a.name}", width="stretch"):
            st.session_state["pending_delete"] = None
            st.rerun()

choice = st.session_state["account_choice"]
selected = list(accounts) if choice == ALL_ACCOUNTS else [name_to_cfg.get(choice)]
selected = [a for a in selected if a is not None] or list(accounts)

# Quick add-account, right where the account list is.
with st.sidebar.expander("➕  Add account"):
    with st.form("sidebar_add_account", clear_on_submit=True):
        new_name = st.text_input("Name", placeholder="e.g. Swing (Live)")
        new_type = st.selectbox("Type", ["Paper", "Live"])
        new_key = st.text_input("API key")
        new_secret = st.text_input("API secret", type="password")
        add_ok = st.form_submit_button("Add account", type="primary", width="stretch")
    if add_ok:
        is_paper = new_type == "Paper"
        if not new_name.strip() or not new_key.strip() or not new_secret.strip():
            st.warning("Fill in name, key and secret.")
        elif new_name.strip() in {a.name for a in accounts}:
            st.warning("That name already exists.")
        else:
            try:
                AccountClient(AccountConfig(name=new_name.strip(), api_key=new_key.strip(),
                                            api_secret=new_secret.strip(), paper=is_paper)).get_account()
            except Exception as exc:
                st.warning(f"Keys didn't work: {exc}")
            else:
                store.add_account(new_name.strip(), new_key.strip(), new_secret.strip(), is_paper)
                st.success(f"Added {new_name.strip()}")
                st.rerun()
    st.caption("Manage/delete accounts in the ⚙️ Accounts tab.")

st.sidebar.divider()
auto = st.sidebar.toggle("Auto-refresh", value=True, help="Live-update positions & PnL")
# Refresh interval in seconds; default 5 seconds.
_INTERVALS = [5, 10, 30, 60, 300, 600]
_fmt_int = lambda s: f"{s}s" if s < 60 else f"{s // 60}m"
interval = st.sidebar.select_slider(
    "Refresh every", options=_INTERVALS, value=5, disabled=not auto, format_func=_fmt_int,
)
if st.sidebar.button("🔄 Refresh now", width="stretch"):
    st.rerun()

st.sidebar.divider()
logout_button()


# ──────────────────────────────────────────────────────────────────────────
# Main render (wrapped in a fragment for optional live refresh)
# ──────────────────────────────────────────────────────────────────────────
def render():
    live = sum(1 for a in selected if not a.paper)
    paper = sum(1 for a in selected if a.paper)
    ui.header(
        f"{len(selected)} account(s) · "
        f"<span style='color:#ff6b76'>{live} live</span> · "
        f"<span style='color:#facc15'>{paper} paper</span><br>"
        f"<span style='font-size:11px'>Live trading dashboard</span>"
    )

    if not selected:
        st.info("Select at least one account in the sidebar.")
        return

    account_data = [fetch_account(cfg) for cfg in selected]

    # ---- top: combined floating PnL --------------------------------------
    total_equity = 0.0
    total_float_pl = 0.0      # sum of position unrealized P/L
    total_day_pl = 0.0        # equity - last_equity
    total_cash = 0.0
    n_positions = 0

    per_account_metrics = []
    for d in account_data:
        if d["error"] or d["account"] is None:
            per_account_metrics.append((d["cfg"], None, None, None, None))
            continue
        acct = d["account"]
        equity = float(getattr(acct, "equity", 0) or 0)
        last_equity = float(getattr(acct, "last_equity", 0) or 0)
        cash = float(getattr(acct, "cash", 0) or 0)
        rows = consolidated_rows(d)
        float_pl = sum(r.unrealized_pl for r in rows)
        day_pl = equity - last_equity

        total_equity += equity
        total_cash += cash
        total_float_pl += float_pl
        total_day_pl += day_pl
        n_positions += len(rows)
        per_account_metrics.append((d["cfg"], equity, float_pl, day_pl, cash))

    day_pct = (total_day_pl / (total_equity - total_day_pl) * 100.0) if (total_equity - total_day_pl) else 0.0
    float_pct = (total_float_pl / (total_equity - total_float_pl) * 100.0) if (total_equity - total_float_pl) else 0.0

    ui.kpi_row([
        ui.kpi_card("Total Equity", fmt.money(total_equity)),
        ui.kpi_card("Floating PnL", fmt.money(total_float_pl), total_float_pl, fmt.pct(float_pct)),
        ui.kpi_card("Today's PnL", fmt.money(total_day_pl), total_day_pl, fmt.pct(day_pct)),
        ui.kpi_card("Cash", fmt.money(total_cash)),
        ui.kpi_card("Open Positions", str(n_positions)),
    ])

    # per-account strip
    ui.label("Accounts")
    cards = []
    for cfg, equity, float_pl, day_pl, cash in per_account_metrics:
        if equity is None:
            cards.append(ui.account_card(cfg.name, "—", "—", 0, "error", cfg.paper))
        else:
            balance = equity - float_pl
            cards.append(ui.account_card(cfg.name, fmt.money(equity), fmt.money(balance),
                                         float_pl, fmt.money(float_pl), cfg.paper))
    ui.account_row(cards)

    for d in account_data:
        if d["error"]:
            st.error(f"**{d['cfg'].name}**: {d['error']}")

    st.write("")

    tab_pos, tab_orders, tab_log, tab_trade, tab_news, tab_acct = st.tabs(
        ["📊 Positions", "🧾 Open Orders", "📒 Trade Log", "🛒 Trade", "📰 News", "⚙️ Accounts"]
    )

    with tab_pos:
        render_positions(account_data)
    with tab_orders:
        render_orders(account_data)
    with tab_log:
        render_tradelog()
    with tab_trade:
        render_trade()
    with tab_news:
        render_news(account_data)
    with tab_acct:
        render_accounts_admin()


# ──────────────────────────────────────────────────────────────────────────
# Positions tab — the consolidated "one row per ticker" view
# ──────────────────────────────────────────────────────────────────────────
def render_positions(account_data: list[dict]):
    all_rows: list[ConsolidatedPosition] = []
    for d in account_data:
        all_rows.extend(consolidated_rows(d))

    if not all_rows:
        st.info("No open positions.")
        return

    total_worth = sum(r.market_value for r in all_rows)
    total_float = sum(r.unrealized_pl for r in all_rows)
    total_risk = sum(r.sl_amount for r in all_rows if r.sl_amount is not None)
    total_reward = sum(r.tp_amount for r in all_rows if r.tp_amount is not None)
    winners = sum(1 for r in all_rows if r.unrealized_pl > 0)
    ui.kpi_row([
        ui.kpi_card("Open Positions", str(len(all_rows))),
        ui.kpi_card("Total Exposure", fmt.money(total_worth)),
        ui.kpi_card("Floating PnL", fmt.money(total_float), total_float,
                    f"{winners}/{len(all_rows)} winning"),
        ui.kpi_card("Risk at SL", fmt.money(total_risk), total_risk, "if all stops hit"),
        ui.kpi_card("Reward at TP", fmt.money(total_reward), total_reward, "if all targets hit"),
    ])

    # SL/TP cell: dollar gain/loss on top, price underneath.
    def sltp_cell(price, amount):
        if price is None or amount is None:
            return ('<span class="dim">—</span>', "r")
        cls = ui.signed_class(amount)
        return (
            f'<span class="{cls}" style="font-weight:700">{fmt.money(amount)}</span>'
            f'<br><span class="dim" style="font-size:11px">@ {fmt.price(price)}</span>',
            "r",
        )

    headers = [
        ("Account", "l"), ("Ticker", "l"), ("Side", "l"), ("Qty", "r"),
        ("Entry", "r"), ("Current", "r"), ("Worth", "r"),
        ("Loss if SL", "r"), ("Gain if TP", "r"), ("R:R", "r"),
        ("Float PnL", "r"), ("PnL %", "r"),
    ]
    rows = []
    for r in all_rows:
        badge = ('<span class="badge-l">LONG</span>' if r.side == "long"
                 else '<span class="badge-s">SHORT</span>')
        rr = f"{r.risk_reward:.2f}" if r.risk_reward is not None else "—"
        rows.append([
            (r.account, "l"),
            (f'<span class="tk">{r.symbol}</span>', "l"),
            (badge, "l"),
            (f"{abs(r.qty):,.2f}", "r"),
            (fmt.price(r.avg_entry), "r"),
            (fmt.price(r.current_price), "r"),
            (fmt.money(r.market_value), "r"),
            sltp_cell(r.stop_loss, r.sl_amount),
            sltp_cell(r.take_profit, r.tp_amount),
            (rr, "r"),
            (f'<span class="{ui.signed_class(r.unrealized_pl)}">{fmt.money(r.unrealized_pl)}</span>', "r"),
            (f'<span class="{ui.signed_class(r.unrealized_plpc)}">{fmt.pct(r.unrealized_plpc)}</span>', "r"),
        ])
    ui.render_table(headers, rows)

    missing = [r.symbol for r in all_rows if r.stop_loss is None or r.take_profit is None]
    if missing:
        st.caption(f"⚠️ No SL and/or TP attached: {', '.join(sorted(set(missing)))}")

    # Quick close
    ui.label("Close a position")
    cc1, cc2 = st.columns([3, 1])
    label_to_row = {f"{r.account} · {r.symbol} ({fmt.money(r.market_value)})": r for r in all_rows}
    pick = cc1.selectbox("Position", list(label_to_row.keys()), label_visibility="collapsed")
    if cc2.button("Close position", type="secondary", width='stretch'):
        row = label_to_row[pick]
        cfg = next(a for a in selected if a.name == row.account)
        try:
            client_for(cfg).close_position(row.symbol)
            st.success(f"Submitted close for {row.symbol} on {row.account}.")
            st.rerun()
        except Exception as exc:
            st.error(f"Failed to close {row.symbol}: {exc}")


# ──────────────────────────────────────────────────────────────────────────
# Orders tab
# ──────────────────────────────────────────────────────────────────────────
def render_orders(account_data: list[dict]):
    any_orders = False
    for d in account_data:
        if d["error"]:
            continue
        orders = d["orders"]
        cfg = d["cfg"]
        badge = "🟡" if cfg.paper else "🔴"
        st.markdown(f"**{badge} {cfg.name}**")
        if not orders:
            st.caption("No open orders.")
            continue
        any_orders = True

        records = []
        for o in orders:
            records.append(
                {
                    "Symbol": getattr(o, "symbol", ""),
                    "Side": str(getattr(o, "side", "")).split(".")[-1].upper(),
                    "Type": str(getattr(o, "order_type", getattr(o, "type", ""))).split(".")[-1],
                    "Qty": getattr(o, "qty", None),
                    "Limit": getattr(o, "limit_price", None),
                    "Stop": getattr(o, "stop_price", None),
                    "Class": str(getattr(o, "order_class", "")).split(".")[-1],
                    "Status": str(getattr(o, "status", "")).split(".")[-1],
                    "ID": str(getattr(o, "id", "")),
                }
            )
        st.dataframe(pd.DataFrame.from_records(records), width='stretch', hide_index=True)

        oc1, oc2 = st.columns([3, 1])
        ids = [r["ID"] for r in records]
        labels = {f"{r['Symbol']} {r['Side']} {r['Type']} · {r['ID'][:8]}": r["ID"] for r in records}
        pick = oc1.selectbox(
            f"Cancel order ({cfg.name})", list(labels.keys()),
            key=f"cancel_{cfg.name}", label_visibility="collapsed",
        )
        if oc2.button("Cancel", key=f"cancelbtn_{cfg.name}", width='stretch'):
            try:
                client_for(cfg).cancel_order(labels[pick])
                st.success("Order cancelled.")
                st.rerun()
            except Exception as exc:
                st.error(f"Cancel failed: {exc}")

        if len(records) > 1 and st.button(
            f"Cancel ALL orders on {cfg.name}", key=f"cancelall_{cfg.name}"
        ):
            try:
                client_for(cfg).cancel_all_orders()
                st.success("All orders cancelled.")
                st.rerun()
            except Exception as exc:
                st.error(f"Cancel-all failed: {exc}")
        st.divider()

    if not any_orders:
        st.info("No open orders across selected accounts.")


# ──────────────────────────────────────────────────────────────────────────
# Trade Log tab — closed round-trip trades with realized PnL (FIFO matched)
# ──────────────────────────────────────────────────────────────────────────
def render_tradelog():
    lc1, lc2 = st.columns([1, 3])
    days = lc1.selectbox(
        "Lookback", [7, 30, 90, 180, 365], index=2,
        format_func=lambda d: f"Last {d} days", key="log_days",
    )

    all_fills = []
    for cfg in selected:
        try:
            all_fills.extend(cached_fills(cfg.name, cfg.api_key, cfg.api_secret, cfg.paper, days))
        except Exception as exc:
            st.error(f"{cfg.name}: trade log fetch failed — {exc}")
    all_fills.sort(key=lambda f: f.time)

    trips = fifo_round_trips(all_fills)

    # symbol filter
    symbols = sorted({t.symbol for t in trips})
    chosen = lc2.multiselect("Filter tickers", symbols, default=[], key="log_syms")
    if chosen:
        trips = [t for t in trips if t.symbol in chosen]

    s = summarize(trips)
    pf = s["profit_factor"]
    ui.kpi_row([
        ui.kpi_card("Realized PnL", fmt.money(s["pnl"]), s["pnl"], f"{s['n']} trades"),
        ui.kpi_card("Win Rate", f"{s['win_rate']:.0f}%"),
        ui.kpi_card("Avg Win", fmt.money(s["avg_win"]), 1, fmt.money(s["avg_win"])),
        ui.kpi_card("Avg Loss", fmt.money(s["avg_loss"]), -1, fmt.money(s["avg_loss"])),
        ui.kpi_card("Profit Factor", "∞" if pf == float("inf") else f"{pf:.2f}"),
    ])

    if not trips:
        st.info("No closed round-trip trades in this window. "
                "(Open positions show in the Positions tab; trades appear here once closed.)")
        return

    records = []
    for t in trips:
        records.append(
            {
                "Closed": t.closed_at.strftime("%Y-%m-%d %H:%M"),
                "Account": t.account,
                "Ticker": t.symbol,
                "Dir": t.direction.upper(),
                "Qty": t.qty,
                "Entry": t.entry_price,
                "Exit": t.exit_price,
                "PnL": t.pnl,
                "Return %": t.return_pct,
                "Held": t.holding,
                "Opened": t.opened_at.strftime("%Y-%m-%d %H:%M"),
            }
        )
    df = pd.DataFrame.from_records(records)

    headers = [
        ("Closed", "l"), ("Account", "l"), ("Ticker", "l"), ("Dir", "l"),
        ("Qty", "r"), ("Entry", "r"), ("Exit", "r"),
        ("PnL", "r"), ("Return %", "r"), ("Held", "r"),
    ]
    hrows = []
    for t in trips:
        badge = ('<span class="badge-l">LONG</span>' if t.direction == "long"
                 else '<span class="badge-s">SHORT</span>')
        hrows.append([
            (t.closed_at.strftime("%Y-%m-%d %H:%M"), "l"),
            (t.account, "l"),
            (f'<span class="tk">{t.symbol}</span>', "l"),
            (badge, "l"),
            (f"{abs(t.qty):,.2f}", "r"),
            (fmt.price(t.entry_price), "r"),
            (fmt.price(t.exit_price), "r"),
            (f'<span class="{ui.signed_class(t.pnl)}" style="font-weight:700">{fmt.money(t.pnl)}</span>', "r"),
            (f'<span class="{ui.signed_class(t.return_pct)}">{fmt.pct(t.return_pct)}</span>', "r"),
            (f'<span class="dim">{t.holding}</span>', "r"),
        ])
    ui.render_table(headers, hrows)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export CSV", csv, file_name=f"aldash_tradelog_{days}d.csv",
                       mime="text/csv")

    with st.expander(f"Raw fills ({len(all_fills)})"):
        frecords = [
            {
                "Time": f.time.strftime("%Y-%m-%d %H:%M"),
                "Account": f.account,
                "Ticker": f.symbol,
                "Side": f.side.upper(),
                "Qty": f.qty,
                "Price": f.price,
                "Type": f.order_type,
            }
            for f in sorted(all_fills, key=lambda x: x.time, reverse=True)
        ]
        st.dataframe(pd.DataFrame.from_records(frecords), width='stretch', hide_index=True)


# ──────────────────────────────────────────────────────────────────────────
# Trade tab — place a bracket order (entry + SL + TP in one ticket)
# ──────────────────────────────────────────────────────────────────────────
def render_trade():
    st.markdown("Place a **bracket order**: entry + stop-loss + take-profit in one ticket.")

    acct_name = st.selectbox("Account", [a.name for a in selected], key="trade_acct")
    cfg = name_to_cfg[acct_name]
    if not cfg.paper:
        st.warning("⚠️ This is a **LIVE** account — orders use real money.")

    with st.form("trade_form"):
        f1, f2, f3 = st.columns(3)
        symbol = f1.text_input("Ticker", value="AAPL").strip().upper()
        side = f2.selectbox("Side", ["buy", "sell"])
        qty = f3.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)

        f4, f5, f6 = st.columns(3)
        order_kind = f4.selectbox("Entry type", ["market", "limit"])
        limit_price = f5.number_input("Limit price", min_value=0.0, value=0.0, step=0.01,
                                      help="Only used for limit entries")
        tif = f6.selectbox("Time in force", ["day", "gtc"])

        f7, f8 = st.columns(2)
        stop_loss = f7.number_input("Stop-loss price (SL)", min_value=0.0, value=0.0, step=0.01)
        take_profit = f8.number_input("Take-profit price (TP)", min_value=0.0, value=0.0, step=0.01)

        confirm = True
        if not cfg.paper:
            confirm = st.checkbox("I understand this places a REAL order on a live account")

        submitted = st.form_submit_button("🚀 Submit order", width='stretch')

    if submitted:
        if not symbol or qty <= 0:
            st.error("Enter a ticker and a quantity > 0.")
            return
        if not confirm:
            st.error("Tick the live-account confirmation to proceed.")
            return
        try:
            order = client_for(cfg).submit_bracket(
                symbol=symbol,
                qty=qty,
                side=side,
                take_profit=take_profit or None,
                stop_loss=stop_loss or None,
                limit_price=limit_price if (order_kind == "limit" and limit_price > 0) else None,
                time_in_force=tif,
            )
            st.success(f"Order submitted: {symbol} {side} {qty} — id {getattr(order, 'id', '?')}")
        except Exception as exc:
            st.error(f"Order failed: {exc}")


# ──────────────────────────────────────────────────────────────────────────
# News tab — Alpaca's free news API (Benzinga-sourced)
# ──────────────────────────────────────────────────────────────────────────
def render_news(account_data: list[dict]):
    # Default to symbols you actually hold across accounts.
    held = sorted({r.symbol for d in account_data for r in consolidated_rows(d)})
    default = ", ".join(held[:10])
    raw = st.text_input(
        "Symbols (comma-separated, blank = general market news)",
        value=default,
        key="news_symbols",
    )
    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()] or None

    # Use the first working account's news client (news is account-agnostic).
    client = None
    for d in account_data:
        if not d["error"]:
            client = client_for(d["cfg"])
            break
    if client is None:
        st.info("No working account to fetch news.")
        return

    try:
        items = client.get_news(symbols=symbols, limit=25)
    except Exception as exc:
        st.error(f"News fetch failed: {exc}")
        return

    if not items:
        st.info("No recent news for those symbols.")
        return

    import html as _html

    for n in items:
        headline = _html.escape(str(getattr(n, "headline", "")))
        summary = _html.escape(str(getattr(n, "summary", "") or ""))
        url = str(getattr(n, "url", "") or "")
        source = _html.escape(str(getattr(n, "source", "")))
        created = str(getattr(n, "created_at", ""))[:16].replace("T", " ")
        syms = getattr(n, "symbols", []) or []

        title = f'<a href="{url}" target="_blank">{headline}</a>' if url else f"<span>{headline}</span>"
        sym_tags = "".join(f'<span class="news-sym">{_html.escape(str(s))}</span>' for s in syms[:6])
        meta = " · ".join(filter(None, [source, created]))
        summary_html = (summary[:400] + ("…" if len(summary) > 400 else "")) if summary else ""

        st.markdown(
            f'<div class="news-card">{title}'
            f'<div class="news-meta">{meta}</div>'
            f'<div>{sym_tags}</div>'
            + (f'<div class="news-sum">{summary_html}</div>' if summary_html else "")
            + "</div>",
            unsafe_allow_html=True,
        )


# ──────────────────────────────────────────────────────────────────────────
# Accounts tab — add / remove accounts from the dashboard
# ──────────────────────────────────────────────────────────────────────────
def render_accounts_admin():
    ui.label("Add an account")
    st.caption("Keys are validated against Alpaca before saving, then stored locally "
               "in `accounts.json` (git-ignored).")

    with st.form("add_account_form", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        name = c1.text_input("Account name", placeholder="e.g. Swing (Live)")
        acct_type = c2.selectbox("Type", ["Paper", "Live"])
        key = st.text_input("API key")
        secret = st.text_input("API secret", type="password")
        submitted = st.form_submit_button("➕ Add account", type="primary", width="stretch")

    if submitted:
        paper = acct_type == "Paper"
        if not name.strip() or not key.strip() or not secret.strip():
            st.error("Fill in name, API key and API secret.")
        elif name.strip() in {a.name for a in accounts}:
            st.error(f"An account named “{name.strip()}” already exists.")
        else:
            try:  # validate the keys actually work before saving
                test = AccountClient(AccountConfig(name=name.strip(), api_key=key.strip(),
                                                   api_secret=secret.strip(), paper=paper))
                acct = test.get_account()
                equity = float(getattr(acct, "equity", 0) or 0)
            except Exception as exc:
                st.error(f"Couldn't connect with those keys: {exc}")
            else:
                store.add_account(name.strip(), key.strip(), secret.strip(), paper)
                st.success(f"Added “{name.strip()}” — equity {fmt.money(equity)}.")
                st.rerun()

    st.divider()
    ui.label("Your accounts")
    for a in accounts:
        col1, col2 = st.columns([5, 1])
        badge = "🟡 Paper" if a.paper else "🔴 Live"
        src = "added here" if a.managed else "from .env / secrets"
        col1.markdown(f"**{a.name}** · {badge}  \n<span style='color:#8b97a7;font-size:12px'>{src}</span>",
                      unsafe_allow_html=True)
        if col2.button("🗑️ Delete", key=f"del_{a.name}", width="stretch"):
            store.remove(a)
            if st.session_state.get("account_choice") == a.name:
                st.session_state["account_choice"] = ALL_ACCOUNTS
            st.success(f"{'Removed' if a.managed else 'Hid'} “{a.name}”.")
            st.rerun()

    # Restore any config accounts that were hidden.
    hidden = sorted(store.hidden_names())
    if hidden:
        st.divider()
        ui.label("Hidden accounts")
        st.caption("These config accounts are hidden from the dashboard. Restore to show them again.")
        for name in hidden:
            h1, h2 = st.columns([5, 1])
            h1.markdown(f"**{name}**  \n<span style='color:#8b97a7;font-size:12px'>hidden</span>",
                        unsafe_allow_html=True)
            if h2.button("↩️ Restore", key=f"restore_{name}", width="stretch"):
                store.unhide_account(name)
                st.success(f"Restored “{name}”.")
                st.rerun()


# ──────────────────────────────────────────────────────────────────────────
# Wire up auto-refresh
# ──────────────────────────────────────────────────────────────────────────
if auto:
    st.fragment(render, run_every=interval)()
else:
    render()
