"""ALDash FastAPI backend.

Serves a pixel-perfect static frontend (server/static) and a small JSON API
backed by the existing `aldash` Alpaca code. Single Python service:

    uvicorn server.main:app --reload

Auth: set ALDASH_PASSWORD (or app_password in Streamlit secrets). If unset, the
app runs unprotected (fine for local use only).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import List, Optional

from fastapi import Body, Cookie, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from aldash import store
from aldash.client import AccountClient
from aldash.config import AccountConfig, load_accounts, read_secrets
from aldash.positions import consolidate
from aldash.tradelog import fetch_filled_orders, fifo_round_trips, summarize

STATIC_DIR = Path(__file__).parent / "static"
COOKIE = "aldash_auth"

app = FastAPI(title="ALDash")


# ──────────────────────────────────────────────────────────────────────────
# Auth (stateless signed cookie; no-op when no password is configured)
# ──────────────────────────────────────────────────────────────────────────
def _expected_password() -> Optional[str]:
    return read_secrets().get("app_password") or os.getenv("ALDASH_PASSWORD")


def _token(pw: str) -> str:
    return hmac.new(pw.encode(), b"aldash-auth-v1", hashlib.sha256).hexdigest()


def _is_authed(cookie: Optional[str]) -> bool:
    pw = _expected_password()
    if not pw:
        return True  # unprotected
    return bool(cookie) and hmac.compare_digest(cookie, _token(pw))


def _require(cookie: Optional[str]) -> None:
    if not _is_authed(cookie):
        raise HTTPException(status_code=401, detail="Not authenticated")


# ──────────────────────────────────────────────────────────────────────────
# Client cache + per-account fetch (fault-isolated)
# ──────────────────────────────────────────────────────────────────────────
_clients: dict[tuple, AccountClient] = {}
_series_cache: dict[str, tuple[float, list]] = {}    # name -> (ts, series)
_payload_cache: dict[str, tuple[float, dict]] = {}   # name -> (ts, payload)
_fills_cache: dict[tuple, tuple[float, list]] = {}   # (name, days) -> (ts, fills)

PAYLOAD_TTL = 12.0    # switches read cache (instant); auto-refresh asks for fresh
FILLS_TTL = 120.0     # trade-log fills change rarely


def _client(cfg: AccountConfig) -> AccountClient:
    key = (cfg.name, cfg.api_key, cfg.paper)
    if key not in _clients:
        _clients[key] = AccountClient(cfg)
    return _clients[key]


def _accounts() -> List[AccountConfig]:
    return load_accounts()


def _find(name: str) -> Optional[AccountConfig]:
    return next((a for a in _accounts() if a.name == name), None)


def _scoped(scope: str) -> List[AccountConfig]:
    if scope == "all":
        return _accounts()
    one = _find(scope)
    return [one] if one else _accounts()


def _invalidate(name: str) -> None:
    """Drop caches for an account after a mutating action (close/trade/cancel)."""
    _payload_cache.pop(name, None)
    for k in [k for k in _fills_cache if k[0] == name]:
        _fills_cache.pop(k, None)


def _equity_series(cfg: AccountConfig) -> list:
    hit = _series_cache.get(cfg.name)
    if hit and (time.time() - hit[0]) < 60:
        return hit[1]
    try:
        series = _client(cfg).get_equity_series()
    except Exception:
        series = []
    _series_cache[cfg.name] = (time.time(), series)
    return series


def _account_payload(cfg: AccountConfig) -> dict:
    out = {"cfg": cfg, "error": None, "equity": 0.0, "last_equity": 0.0,
           "cash": 0.0, "floating": 0.0, "rows": []}
    try:
        client = _client(cfg)
        acct = client.get_account()
        orders = client.get_open_orders()
        positions = client.get_positions()
        rows = consolidate(cfg.name, positions, orders)
        out["equity"] = float(getattr(acct, "equity", 0) or 0)
        out["last_equity"] = float(getattr(acct, "last_equity", 0) or 0)
        out["cash"] = float(getattr(acct, "cash", 0) or 0)
        out["floating"] = sum(r.unrealized_pl for r in rows)
        out["rows"] = rows
    except Exception as exc:
        out["error"] = str(exc)
    return out


def _payload(cfg: AccountConfig, fresh: bool = False) -> dict:
    """Account payload, cached so switching accounts is instant.

    `fresh=True` (auto-refresh / Refresh now) bypasses the cache for live data.
    """
    if not fresh:
        hit = _payload_cache.get(cfg.name)
        if hit and (time.time() - hit[0]) < PAYLOAD_TTL:
            return hit[1]
    p = _account_payload(cfg)
    if not p["error"]:
        _payload_cache[cfg.name] = (time.time(), p)
    return p


def _fills(cfg: AccountConfig, days: int) -> list:
    key = (cfg.name, days)
    hit = _fills_cache.get(key)
    if hit and (time.time() - hit[0]) < FILLS_TTL:
        return hit[1]
    try:
        f = fetch_filled_orders(_client(cfg), days=days)
    except Exception:
        f = []
    _fills_cache[key] = (time.time(), f)
    return f


def _combine_series(serieses: list) -> list:
    usable = [s for s in serieses if len(s) >= 2]
    if not usable:
        return []
    m = min(len(s) for s in usable)
    return [sum(s[-m:][i] for s in usable) for i in range(m)]


# ──────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────
@app.get("/api/me")
def me(aldash_auth: Optional[str] = Cookie(None)):
    return {"authed": _is_authed(aldash_auth), "protected": bool(_expected_password())}


@app.post("/api/login")
def login(resp: Response, password: str = Body(..., embed=True)):
    pw = _expected_password()
    if not pw:
        return {"ok": True}
    if not hmac.compare_digest(str(password), str(pw)):
        raise HTTPException(status_code=401, detail="Incorrect password")
    resp.set_cookie(COOKIE, _token(pw), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return {"ok": True}


@app.post("/api/logout")
def logout(resp: Response):
    resp.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard(scope: str = "all", fresh: int = 0, aldash_auth: Optional[str] = Cookie(None)):
    _require(aldash_auth)
    accounts = _accounts()
    acct_list = [{"name": a.name, "paper": a.paper, "managed": a.managed} for a in accounts]

    if scope == "all":
        selected = accounts
    else:
        one = _find(scope)
        selected = [one] if one else accounts
        scope = scope if one else "all"

    data = [_payload(cfg, fresh=bool(fresh)) for cfg in selected]
    ok = [d for d in data if not d["error"]]

    total_eq = sum(d["equity"] for d in ok)
    total_float = sum(d["floating"] for d in ok)
    total_day = sum(d["equity"] - d["last_equity"] for d in ok)
    total_cash = sum(d["cash"] for d in ok)
    all_rows = [r for d in ok for r in d["rows"]]

    day_pct = (total_day / (total_eq - total_day) * 100.0) if (total_eq - total_day) else 0.0
    float_pct = (total_float / (total_eq - total_float) * 100.0) if (total_eq - total_float) else 0.0

    # positions
    paper_map = {a.name: a.paper for a in accounts}
    positions = []
    for r in all_rows:
        positions.append({
            "account": r.account, "paper": paper_map.get(r.account, True),
            "symbol": r.symbol, "side": r.side, "qty": abs(r.qty),
            "entry": r.avg_entry, "current": r.current_price, "worth": r.market_value,
            "sl": r.stop_loss, "tp": r.take_profit,
            "sl_pnl": r.sl_amount, "tp_pnl": r.tp_amount,
            "rr": r.risk_reward, "float": r.unrealized_pl, "pct": r.unrealized_plpc,
        })

    # hero (scoped)
    if scope == "all" or len(ok) != 1:
        hero = {
            "name": "All accounts" if scope == "all" else f"{len(ok)} accounts",
            "paper": None, "equity": total_eq, "balance": total_eq - total_float,
            "floating": total_float, "pct": day_pct,
            "series": _combine_series([_equity_series(d["cfg"]) for d in ok]),
        }
    else:
        d = ok[0]
        denom = d["equity"] - (d["equity"] - d["last_equity"])
        hero = {
            "name": d["cfg"].name, "paper": d["cfg"].paper, "equity": d["equity"],
            "balance": d["equity"] - d["floating"], "floating": d["floating"],
            "pct": ((d["equity"] - d["last_equity"]) / denom * 100.0) if denom else 0.0,
            "series": _equity_series(d["cfg"]),
        }

    total_risk = sum(r.sl_amount for r in all_rows if r.sl_amount is not None)
    total_reward = sum(r.tp_amount for r in all_rows if r.tp_amount is not None)
    winners = sum(1 for r in all_rows if r.unrealized_pl > 0)

    return {
        "accounts": acct_list,
        "scope": scope,
        "counts": {"live": sum(1 for a in accounts if not a.paper),
                   "paper": sum(1 for a in accounts if a.paper), "total": len(accounts)},
        "kpis": {"equity": total_eq, "floating": total_float, "float_pct": float_pct,
                 "today": total_day, "today_pct": day_pct, "cash": total_cash,
                 "positions": len(all_rows), "n_accounts": len(ok)},
        "hero": hero,
        "pstats": {"open": len(all_rows), "exposure": sum(r.market_value for r in all_rows),
                   "floating": total_float, "winning": winners, "total": len(all_rows),
                   "risk": total_risk, "reward": total_reward},
        "positions": positions,
        "errors": [{"name": d["cfg"].name, "error": d["error"]} for d in data if d["error"]],
    }


@app.post("/api/close")
def close(payload: dict = Body(...), aldash_auth: Optional[str] = Cookie(None)):
    _require(aldash_auth)
    cfg = _find(payload.get("account", ""))
    if not cfg:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        _client(cfg).close_position(payload["symbol"])
        _invalidate(cfg.name)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/orders")
def orders(scope: str = "all", aldash_auth: Optional[str] = Cookie(None)):
    _require(aldash_auth)
    out = []
    for cfg in _scoped(scope):
        try:
            for o in _client(cfg).get_open_orders():
                out.append({
                    "account": cfg.name, "paper": cfg.paper,
                    "symbol": getattr(o, "symbol", ""),
                    "side": str(getattr(o, "side", "")).split(".")[-1].upper(),
                    "type": str(getattr(o, "order_type", getattr(o, "type", ""))).split(".")[-1],
                    "qty": float(getattr(o, "qty", 0) or 0),
                    "limit": getattr(o, "limit_price", None),
                    "stop": getattr(o, "stop_price", None),
                    "status": str(getattr(o, "status", "")).split(".")[-1],
                    "id": str(getattr(o, "id", "")),
                })
        except Exception as exc:
            out.append({"account": cfg.name, "error": str(exc)})
    return {"orders": out}


@app.post("/api/cancel")
def cancel(payload: dict = Body(...), aldash_auth: Optional[str] = Cookie(None)):
    _require(aldash_auth)
    cfg = _find(payload.get("account", ""))
    if not cfg:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        _client(cfg).cancel_order(payload["id"])
        _invalidate(cfg.name)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/tradelog")
def tradelog(scope: str = "all", days: int = 90, aldash_auth: Optional[str] = Cookie(None)):
    _require(aldash_auth)
    fills = []
    for cfg in _scoped(scope):
        fills.extend(_fills(cfg, days))
    fills.sort(key=lambda f: f.time)
    trips = fifo_round_trips(fills)
    s = summarize(trips)
    return {
        "summary": {**s, "profit_factor": (None if s["profit_factor"] == float("inf") else s["profit_factor"])},
        "trips": [{
            "closed": t.closed_at.strftime("%Y-%m-%d %H:%M"), "account": t.account,
            "symbol": t.symbol, "direction": t.direction, "qty": abs(t.qty),
            "entry": t.entry_price, "exit": t.exit_price, "pnl": t.pnl,
            "return_pct": t.return_pct, "held": t.holding,
        } for t in trips],
    }


@app.get("/api/news")
def news(symbols: str = "", aldash_auth: Optional[str] = Cookie(None)):
    _require(aldash_auth)
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()] or None
    for cfg in _accounts():
        try:
            items = _client(cfg).get_news(symbols=syms, limit=25)
            return {"news": [{
                "headline": str(getattr(n, "headline", "")),
                "summary": str(getattr(n, "summary", "") or "")[:400],
                "url": str(getattr(n, "url", "") or ""),
                "source": str(getattr(n, "source", "")),
                "created": str(getattr(n, "created_at", ""))[:16].replace("T", " "),
                "symbols": list(getattr(n, "symbols", []) or [])[:6],
            } for n in items]}
        except Exception:
            continue
    return {"news": []}


@app.post("/api/trade")
def trade(payload: dict = Body(...), aldash_auth: Optional[str] = Cookie(None)):
    _require(aldash_auth)
    cfg = _find(payload.get("account", ""))
    if not cfg:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        order = _client(cfg).submit_bracket(
            symbol=payload["symbol"], qty=float(payload["qty"]), side=payload["side"],
            take_profit=payload.get("take_profit") or None,
            stop_loss=payload.get("stop_loss") or None,
            limit_price=payload.get("limit_price") or None,
            time_in_force=payload.get("tif", "day"),
        )
        _invalidate(cfg.name)
        return {"ok": True, "id": str(getattr(order, "id", "?"))}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/accounts")
def add_account(payload: dict = Body(...), aldash_auth: Optional[str] = Cookie(None)):
    _require(aldash_auth)
    name = str(payload.get("name", "")).strip()
    key = str(payload.get("api_key", "")).strip()
    secret = str(payload.get("api_secret", "")).strip()
    paper = bool(payload.get("paper", True))
    if not (name and key and secret):
        raise HTTPException(status_code=400, detail="Fill in name, key and secret.")
    if name in {a.name for a in _accounts()}:
        raise HTTPException(status_code=400, detail="That name already exists.")
    try:  # validate keys before saving
        AccountClient(AccountConfig(name=name, api_key=key, api_secret=secret, paper=paper)).get_account()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Keys didn't work: {exc}")
    store.add_account(name, key, secret, paper)
    return {"ok": True}


@app.delete("/api/accounts/{name}")
def delete_account(name: str, aldash_auth: Optional[str] = Cookie(None)):
    _require(aldash_auth)
    cfg = _find(name)
    if cfg:
        store.remove(cfg)
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────
# Static frontend (mounted last so /api/* wins)
# ──────────────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(STATIC_DIR / "favicon-32.png")


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
