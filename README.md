# 📈 ALDash — Multi-Account Alpaca Dashboard

A fast, pixel-crafted **FastAPI** web app for managing multiple Alpaca trading
accounts (live + paper) in one place: equity, floating & realized PnL,
consolidated positions with risk/reward bars, order management, bracket-order
placement, and free news. Installable on your phone as a PWA.

## Features

- **Dashboard** — combined or per-account **equity** with an intraday sparkline
  (hover for values), **floating PnL**, today's PnL, cash, and open positions.
- **Consolidated positions** — one row per ticker with `side · qty · entry ·
  current · worth`, plus a **Risk/Reward gauge** (Alpaca splits a bracket into 3
  orders; ALDash stitches the entry + SL + TP legs back into one line).
- **Open Orders** — view and cancel orders (scoped to the selected account).
- **Trade Log** — closed **round-trip trades** FIFO-matched from your fills:
  entry, exit, qty, **realized PnL**, return %, holding time + summary stats.
- **Trade** — place a bracket order (entry + SL + TP in one ticket).
- **News** — Alpaca's built-in free news, auto-scoped to your holdings.
- **Account switching** — pick one account or "All accounts"; everything rescopes
  instantly (server-side cache keeps it snappy).
- **PWA** — Add to Home Screen for a fullscreen, native-feeling phone app.

## Run locally

```bash
pip install -r requirements.txt

# add credentials — either .env or .streamlit/secrets.toml (see below)
cp .env.example .env                                  # then edit
# or: cp .streamlit/secrets.toml.example .streamlit/secrets.toml

uvicorn server.main:app --reload --port 8000
# open http://localhost:8000
```

## Configuration

Set a login password and your accounts via **environment variables** (best for
deploys) or **`.streamlit/secrets.toml`** (kept for convenience).

**Env vars** (`.env` locally, or your host's dashboard):

```
ALDASH_PASSWORD=your-strong-password
ALDASH_ACCOUNT_1_NAME=Main (Live)
ALDASH_ACCOUNT_1_KEY=AK...
ALDASH_ACCOUNT_1_SECRET=...
ALDASH_ACCOUNT_1_PAPER=false
# add ALDASH_ACCOUNT_2_*, _3_*, … for more accounts
```

**secrets.toml** (alternative):

```toml
app_password = "your-strong-password"

[[accounts]]
name = "Main (Live)"
api_key = "AK..."
api_secret = "..."
paper = false
```

> 🔒 `.env`, `.streamlit/secrets.toml`, and `accounts.json` are git-ignored.
> Never commit your keys. Get keys at https://app.alpaca.markets → **API Keys**.

## Deploy (web + phone)

See **[DEPLOY_FASTAPI.md](DEPLOY_FASTAPI.md)** — one-click on **Render**
(`render.yaml`) or **Railway** (`Procfile`). You get a URL; open it on your phone
and **Add to Home Screen** to install the PWA.

## Project layout

```
server/
  main.py               FastAPI: auth + JSON API (reuses aldash/)
  static/               Pixel-perfect frontend (HTML/CSS/JS) + PWA assets
aldash/
  config.py             Load accounts from secrets.toml / env vars
  client.py             Alpaca trading + news client wrapper
  positions.py          Consolidate position + SL/TP legs → one row
  tradelog.py           FIFO-match fills → round-trip trades + realized PnL
  store.py              Add/remove dashboard-managed accounts (accounts.json)
Procfile · render.yaml  Deploy configs
```

## Safety

- Always set a strong `ALDASH_PASSWORD` for any public deploy; log out on shared
  devices (sidebar button).
- This app places and cancels **real** orders on live accounts.
- One account failing (bad keys, etc.) won't break the rest of the dashboard.
