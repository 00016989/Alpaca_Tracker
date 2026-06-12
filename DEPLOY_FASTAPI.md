# Deploying ALDash (FastAPI version) — pixel-perfect web app + phone PWA

The FastAPI app (`server/main.py`) serves the pixel-perfect dashboard
(`server/static/`) plus a small JSON API backed by your existing Alpaca code.
It's **one Python service**. Unlike the old Streamlit version it does **not**
run on Streamlit Cloud — host it on Render, Railway, or Fly (all have free tiers).

You still get a phone app: it's a **PWA**, so "Add to Home Screen" installs it
with the ALDash icon and opens fullscreen (no browser bar).

---

## Run locally

```bash
pip install -r requirements.txt
# password optional locally; accounts come from .env or .streamlit/secrets.toml
uvicorn server.main:app --reload --port 8000
# open http://localhost:8000
```

## Configuration (environment variables)

| Variable | Purpose |
|---|---|
| `ALDASH_PASSWORD` | Login password. **Always set this for a public deploy.** If unset, the app is open. |
| `ALDASH_ACCOUNT_1_NAME` | Display name, e.g. `Main (Live)` |
| `ALDASH_ACCOUNT_1_KEY` | Alpaca API key |
| `ALDASH_ACCOUNT_1_SECRET` | Alpaca API secret |
| `ALDASH_ACCOUNT_1_PAPER` | `true` for paper, `false` for live |

Add more accounts by incrementing the number: `ALDASH_ACCOUNT_2_NAME`, `_KEY`,
`_SECRET`, `_PAPER`, and so on. (Accounts you add later via the in-app **Add an
account** form are stored in `accounts.json` — note that on free hosts the disk
is ephemeral, so for permanent accounts use the env vars above.)

---

## Free + always-on, no credit card — Render Free + an uptime pinger ⭐

The simplest **free, no-card** path. Render Free sleeps after ~15 min idle, so we
keep it awake with a free uptime monitor that pings `/healthz` every ~10 min.
Net result: always available, $0, no card.

**Step A — deploy on Render (see below).** No card required.

**Step B — keep it awake (free):**
1. Sign up at **https://uptimerobot.com** (free, no card) — or
   **https://cron-job.org** (also free).
2. Add a new **HTTP(s) monitor** pointing at `https://<your-app>.onrender.com/healthz`.
3. Set the interval to **5–10 minutes**.
4. That steady traffic stops Render from idling, so it never cold-starts.

> Note on free tiers: a *true* always-on host with **no card at all** basically
> doesn't exist anymore (Koyeb/Railway/Fly now require a card). This Render +
> pinger combo is the practical no-card way to stay always-on. If you're willing
> to add a card (even on a $0 plan), **Fly.io** or **Oracle Cloud Always Free**
> stay on without a pinger — the included `Dockerfile` works on both.

## Deploy on Render (free)

1. Push this repo to GitHub (private — your keys go in env vars, not the repo).
2. Go to **https://render.com → New + → Blueprint** and select the repo.
   `render.yaml` is detected automatically. (Or **New + → Web Service** and set
   the start command to `uvicorn server.main:app --host 0.0.0.0 --port $PORT`.)
3. Under **Environment**, add `ALDASH_PASSWORD` and the `ALDASH_ACCOUNT_*`
   variables from the table above.
4. Deploy. You get a URL like `https://aldash.onrender.com`.

## Deploy on Railway

1. **https://railway.app → New Project → Deploy from GitHub repo.**
2. Railway reads the `Procfile` (`uvicorn server.main:app --host 0.0.0.0 --port $PORT`).
3. Add the same environment variables under **Variables**.
4. Generate a domain under **Settings → Networking**.

---

## Install on your phone (PWA)

1. Open the deployed URL in Safari (iOS) or Chrome (Android).
2. **Share / menu → Add to Home Screen.**
3. It installs with the ALDash icon and opens fullscreen like a native app.

## Security

- Always set a strong `ALDASH_PASSWORD`.
- Keep the GitHub repo private.
- This app can place and cancel **real** orders on live accounts — log out on
  shared devices (button in the sidebar).
