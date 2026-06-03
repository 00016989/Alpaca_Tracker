# Deploying ALDash to the web (free, always-on link)

This guide uses **Streamlit Community Cloud** — free, always on, and what the
**Deploy** button in the app connects to. You'll end up with a link like
`https://aldash-xxxx.streamlit.app` you can open from any device, including your
phone.

> ⚠️ This dashboard can place and cancel **real orders**. It is protected by a
> password (`app_password`). Never deploy without setting a strong one, and keep
> your GitHub repo **private**.

---

## Step 1 — Put the code on GitHub (private repo)

Your `.env` and `secrets.toml` are git-ignored, so your API keys are **not**
uploaded — you'll paste them into Streamlit's secret manager instead (Step 3).

```bash
cd d:\ALDash
git init
git add .
git commit -m "ALDash dashboard"
```

Then create a **private** repo on https://github.com/new and push:

```bash
git remote add origin https://github.com/<your-username>/aldash.git
git branch -M main
git push -u origin main
```

(If you don't have Git installed: https://git-scm.com/download/win — or use
GitHub Desktop.)

## Step 2 — Create the app

1. Go to **https://share.streamlit.io** and sign in with GitHub.
2. Click **New app** → **Deploy a public app from a repo**.
3. Repository: your `aldash` repo · Branch: `main` · Main file: `app.py`.
4. (Optional) Set a custom subdomain under *Advanced settings*.

## Step 3 — Add your secrets (keys + password)

Before clicking Deploy, open **Advanced settings → Secrets** and paste this,
filling in your real values (this is the same format as
`.streamlit/secrets.toml`):

```toml
app_password = "your-strong-password"

[[accounts]]
name = "Main (Live)"
api_key = "AK..."
api_secret = "..."
paper = false

[[accounts]]
name = "cv (Paper)"
api_key = "PK..."
api_secret = "..."
paper = true

[[accounts]]
name = "cnv (Paper)"
api_key = "PK..."
api_secret = "..."
paper = true
```

## Step 4 — Deploy

Click **Deploy**. First build takes ~2–3 minutes. You'll get your permanent link.
Open it → enter your password → you're in.

## Step 5 — Make it an "app" on your phone

1. Open the link in your phone browser (Safari / Chrome).
2. **Share / menu → Add to Home Screen.**
3. It gets an icon and opens fullscreen, just like a native app.

---

## Updating the app later

Any time you change the code, just push to GitHub — Streamlit Cloud
auto-redeploys:

```bash
git add .
git commit -m "update"
git push
```

To change keys or the password, edit them in **App → Settings → Secrets** (no
redeploy needed).

## Keeping it secure

- Use a long, unique `app_password`.
- Keep the GitHub repo private.
- You can further restrict who can even load the app: in the app's settings on
  Streamlit Cloud, set **"Who can view this app"** to specific emails.
- Log out from the sidebar when done on a shared device.
