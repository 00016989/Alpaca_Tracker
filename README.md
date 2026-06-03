# 📈 ALDash — Multi-Account Alpaca Dashboard

A Streamlit dashboard for managing multiple Alpaca trading accounts (live + paper
mixed) in one place: floating PnL, consolidated positions, order management,
bracket-order placement, and free news.

## Features

- **Portfolio header** — combined equity, **floating (unrealized) PnL**, today's
  PnL, and cash across all accounts, plus a per-account strip.
- **Consolidated positions** — one row per ticker showing
  `ticker · side · qty · avg entry · current · SL · TP · worth · float PnL`.
  Alpaca splits a bracket into 3 separate orders (entry + take-profit leg +
  stop-loss leg); ALDash stitches them back into a single line so you see the
  SL, TP, and current worth together.
- **Open orders** — view and cancel individual or all orders per account.
- **Trade Log** — closed **round-trip trades** reconstructed by FIFO-matching your
  filled orders: entry, exit, qty, **realized PnL**, return %, and holding time.
  Plus summary stats (win rate, avg win/loss, profit factor) and CSV export.
- **Trade** — place a bracket order (entry + SL + TP in one ticket), market or
  limit, with a live-account confirmation guard.
- **News** — Alpaca's built-in **free** news API (Benzinga-sourced), auto-scoped
  to the tickers you hold. *No Yahoo Finance needed.*
- **Auto-refresh** — optional live update (5–60s) for positions and PnL.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your account credentials — pick ONE of these:

#   Option A: .env file (simplest)
copy .env.example .env            # Windows   (cp on macOS/Linux)
#   then edit .env with your real keys

#   Option B: Streamlit secrets
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
#   then edit .streamlit/secrets.toml

# 3. Run
streamlit run app.py
```

Open http://localhost:8501 in your browser. (`.env` is checked first, then
`secrets.toml`.)

## 📱 Use it like an app on your phone

The dashboard is a web app, so the phone "app" is just the browser opened to it
and added to your home screen. Pick how the phone reaches it:

### A) Same Wi-Fi (easiest, keys never leave your PC)
1. On your PC, run it bound to the network:
   ```bash
   streamlit run app.py --server.address 0.0.0.0
   ```
   Streamlit prints a **Network URL** like `http://192.168.1.20:8501`.
2. First time only — allow it through Windows Firewall:
   ```powershell
   New-NetFirewallRule -DisplayName "ALDash" -Direction Inbound -LocalPort 8501 -Protocol TCP -Action Allow
   ```
3. On your phone (same Wi-Fi) open that Network URL.
4. **Add to Home Screen** (Safari: Share → Add to Home Screen / Chrome: ⋮ → Add to
   Home screen). It now opens fullscreen like a native app.

> Your PC must be on and running the app. Best for home use.

### B) Anywhere, securely (Tailscale — free)
Install [Tailscale](https://tailscale.com) on your PC **and** phone, sign into both.
Then open `http://<your-pc-tailscale-ip>:8501` from the phone anywhere in the world.
Your API keys stay on your PC; Tailscale is a private encrypted network. PC must be on.

### C) True cloud (no PC needed) — Streamlit Community Cloud
Push this repo to GitHub (private), deploy free at
[share.streamlit.io](https://share.streamlit.io), and paste your accounts into the
app's **Secrets** box. Accessible from any device, PC off.
⚠️ **Trade-off:** your *live* trading keys are then stored on Streamlit's servers.
Fine for paper accounts; think carefully before putting live keys in the cloud.

**Recommendation:** A) at home, or B) if you want it from anywhere while keeping
live keys on your own machine.

### Getting API keys

1. Go to https://app.alpaca.markets
2. Account menu → **API Keys** → generate a key + secret per account.
3. Paper-account keys come from the **paper trading** dashboard; live keys from
   the live dashboard.
4. Put each account in `.streamlit/secrets.toml`, setting `paper = true` for
   paper accounts and `paper = false` for live accounts.

```toml
[[accounts]]
name = "Main (Live)"
api_key = "AK..."
api_secret = "..."
paper = false

[[accounts]]
name = "Test (Paper)"
api_key = "PK..."
api_secret = "..."
paper = true
```

> 🔒 `secrets.toml` is git-ignored. Never commit your keys.

## A note on news / data sources

The dashboard uses **Alpaca's own news API**, which is free with your existing
keys — so there's nothing extra to sign up for. If you later want more sources,
free options worth considering:

| Source | Free tier | Notes |
|---|---|---|
| **Alpaca News** (used here) | Yes, with keys | Real-time, ticker-tagged |
| Finnhub | 60 calls/min free | Company news + sentiment |
| Marketaux | 100 req/day free | Good entity/ticker tagging |
| NewsAPI.org | 100 req/day (dev) | General, not finance-specific |

Yahoo Finance has no official free API; the common `yfinance` package scrapes it
and breaks often — Alpaca News is more reliable for this use case.

## Project layout

```
app.py                  Streamlit UI (header, tabs, forms)
aldash/
  config.py             Load accounts from .env / secrets
  client.py             Alpaca trading + news client wrapper
  positions.py          Consolidate position + SL/TP legs → one row
  tradelog.py           FIFO-match fills → round-trip trades + realized PnL
  format.py             $ / % display helpers
.env.example            Credential template (copy to .env)
.streamlit/
  config.toml           Dark theme
  secrets.toml.example  Alternative credential template
```

## Safety

- Live accounts are flagged 🔴 everywhere; paper accounts 🟡.
- Placing an order on a live account requires ticking a confirmation box.
- One account failing (bad keys, etc.) won't break the rest of the dashboard.
