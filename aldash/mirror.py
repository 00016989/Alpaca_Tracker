"""Copy-trading mirror engine.

Watches ONE source account (your paper account, where your strategy code runs)
and keeps one or more TARGET accounts (live) in sync with it — automatically.

Model: reconciliation, not event-catching. Every cycle we read the source's
open positions, scale them down by a divisor (qty / 100 by default), and bring
each target into that state:

  * source opened a long  -> target buys the scaled qty (market, no SL/TP)
  * source closed it      -> target closes its mirrored position
  * source trimmed/added  -> target sells/buys the difference

This is idempotent and self-healing: a missed cycle or a server restart just
gets corrected on the next pass, because we mirror *state*, not events.

Scope / safety rules baked in:
  * LONG ONLY. Shorts in the source are ignored (fractional shorts aren't
    allowed at Alpaca anyway).
  * Fractional shares are kept as-is (e.g. 47 shares -> 0.47), which is why we
    never attach SL/TP — those legs can't sit on fractional/odd quantities.
  * We only ever CLOSE a symbol on a target that this engine itself opened
    (tracked in mirror_state.json). Manual positions on the target are left
    untouched.

Persistence (both git-ignored, live next to accounts.json):
  * mirror.json        -> the user's settings (enabled, source, targets, divisor)
  * mirror_state.json  -> which symbols/qty we've opened per target
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = _ROOT / "mirror.json"
STATE_PATH = _ROOT / "mirror_state.json"

# Alpaca rejects fractional/notional orders worth less than $1, and tiny qty
# diffs are just noise — so we skip any adjustment below this dollar value.
MIN_NOTIONAL = 1.0
# Treat quantities within this many shares as "equal" (avoids churn from
# floating-point dust when comparing desired vs. held).
QTY_EPS = 1e-4

_lock = threading.Lock()

# In-memory status for the dashboard (last run, recent actions, per-target view).
_status: dict = {
    "last_run": None,
    "last_error": None,
    "running": False,
    "mirrors": [],   # per-target snapshot built each cycle
    "log": [],       # recent action strings (newest last, capped)
}


# ──────────────────────────────────────────────────────────────────────────
# Config + state persistence
# ──────────────────────────────────────────────────────────────────────────
_DEFAULT_CONFIG = {"enabled": False, "source": "", "targets": [], "divisor": 100.0}


def load_config() -> dict:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT_CONFIG)
    cfg = dict(_DEFAULT_CONFIG)
    cfg.update({k: data[k] for k in _DEFAULT_CONFIG if k in data})
    cfg["targets"] = [t for t in (cfg.get("targets") or []) if t and t != cfg.get("source")]
    try:
        cfg["divisor"] = float(cfg["divisor"]) or 100.0
    except (TypeError, ValueError):
        cfg["divisor"] = 100.0
    return cfg


def save_config(enabled: bool, source: str, targets: List[str], divisor: float) -> dict:
    cfg = {
        "enabled": bool(enabled),
        "source": str(source or ""),
        "targets": [str(t) for t in (targets or []) if t and t != source],
        "divisor": float(divisor) if divisor else 100.0,
    }
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


def _load_state() -> dict:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────
def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _enum_str(value) -> str:
    return str(value).split(".")[-1].lower()


def _log(msg: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    _status["log"].append(f"{stamp}  {msg}")
    del _status["log"][:-60]   # keep the last ~60 lines


def status() -> dict:
    """Snapshot of the engine for the dashboard (config merged in)."""
    cfg = load_config()
    return {**cfg, **_status}


# ──────────────────────────────────────────────────────────────────────────
# Core reconcile
# ──────────────────────────────────────────────────────────────────────────
def _desired_from_source(positions, divisor: float) -> dict:
    """Scaled target book from the source's LONG positions: symbol -> {qty, price}."""
    desired: dict[str, dict] = {}
    for p in positions:
        side = _enum_str(getattr(p, "side", "long"))
        qty = _f(getattr(p, "qty", 0))
        if side != "long" or qty <= 0:
            continue                       # long-only mirror
        symbol = str(getattr(p, "symbol", "")).upper()
        if not symbol:
            continue
        desired[symbol] = {
            "qty": qty / divisor,
            "price": _f(getattr(p, "current_price", 0)) or _f(getattr(p, "avg_entry_price", 0)),
        }
    return desired


def _live_map(positions) -> dict:
    """symbol -> signed qty held on a target account."""
    out: dict[str, float] = {}
    for p in positions:
        symbol = str(getattr(p, "symbol", "")).upper()
        if symbol:
            out[symbol] = _f(getattr(p, "qty", 0))
    return out


def _pending_symbols(open_orders) -> set:
    """Symbols with an in-flight order — skip them this cycle to avoid races."""
    out = set()
    for o in open_orders:
        sym = str(getattr(o, "symbol", "")).upper()
        if sym:
            out.add(sym)
    return out


def _reconcile_target(target_name, client, desired, state) -> dict:
    """Bring one target account into line with `desired`. Returns a UI snapshot."""
    managed = dict(state.get(target_name, {}))   # {symbol: qty we opened}
    snap = {"target": target_name, "error": None, "positions": []}

    try:
        live = _live_map(client.get_positions())
        pending = _pending_symbols(client.get_open_orders())
    except Exception as exc:
        snap["error"] = str(exc)
        return snap

    symbols = set(desired) | set(managed)
    for sym in sorted(symbols):
        want = desired.get(sym, {}).get("qty", 0.0)
        price = desired.get(sym, {}).get("price", 0.0)
        have = live.get(sym, 0.0)
        row = {"symbol": sym, "target_qty": round(want, 6), "live_qty": round(have, 6), "status": "ok"}

        if sym in pending:
            row["status"] = "pending"
            snap["positions"].append(row)
            continue

        diff = want - have
        notional = abs(diff) * (price or 0)

        # Symbol left the source's book -> close whatever WE opened here.
        if want <= QTY_EPS:
            if sym in managed and have > QTY_EPS:
                try:
                    client.close_position(sym)
                    _log(f"{target_name}: close {sym} (source closed)")
                    row["status"] = "closing"
                except Exception as exc:
                    row["status"] = "err"; row["error"] = str(exc)
                    _log(f"{target_name}: close {sym} FAILED — {exc}")
            managed.pop(sym, None)
            if want <= QTY_EPS and have <= QTY_EPS:
                continue
            snap["positions"].append(row)
            continue

        # Open or top up.
        if diff > QTY_EPS:
            if notional < MIN_NOTIONAL:
                row["status"] = "skip<$1"
            else:
                try:
                    client.submit_bracket(symbol=sym, qty=round(diff, 6), side="buy",
                                          take_profit=None, stop_loss=None, time_in_force="day")
                    _log(f"{target_name}: buy {round(diff,4)} {sym}")
                    row["status"] = "buying"
                    managed[sym] = want
                except Exception as exc:
                    row["status"] = "err"; row["error"] = str(exc)
                    _log(f"{target_name}: buy {sym} FAILED — {exc}")
        # Source trimmed -> sell the difference (still long, never short).
        elif diff < -QTY_EPS:
            sell_qty = min(have, -diff)
            if notional < MIN_NOTIONAL or sell_qty <= QTY_EPS:
                row["status"] = "skip<$1"
                managed[sym] = want
            else:
                try:
                    client.submit_bracket(symbol=sym, qty=round(sell_qty, 6), side="sell",
                                          take_profit=None, stop_loss=None, time_in_force="day")
                    _log(f"{target_name}: trim {round(sell_qty,4)} {sym}")
                    row["status"] = "trimming"
                    managed[sym] = want
                except Exception as exc:
                    row["status"] = "err"; row["error"] = str(exc)
                    _log(f"{target_name}: trim {sym} FAILED — {exc}")
        else:
            managed[sym] = want   # already matched; keep tracking

        snap["positions"].append(row)

    if managed:
        state[target_name] = managed
    else:
        state.pop(target_name, None)
    return snap


def reconcile(client_for: Callable, find_cfg: Callable) -> dict:
    """Run one full reconcile pass across all configured targets.

    `client_for(cfg) -> AccountClient` and `find_cfg(name) -> cfg|None` are
    injected so we reuse the server's cached clients.
    """
    cfg = load_config()
    _status["last_run"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not cfg["enabled"] or not cfg["source"] or not cfg["targets"]:
        _status["running"] = False
        _status["mirrors"] = []
        _status["last_error"] = None
        return status()

    _status["running"] = True
    src_cfg = find_cfg(cfg["source"])
    if not src_cfg:
        _status["last_error"] = f"Source account '{cfg['source']}' not found."
        return status()

    try:
        desired = _desired_from_source(client_for(src_cfg).get_positions(), cfg["divisor"])
        _status["last_error"] = None
    except Exception as exc:
        _status["last_error"] = f"Source read failed: {exc}"
        return status()

    with _lock:
        state = _load_state()
        mirrors = []
        for name in cfg["targets"]:
            tcfg = find_cfg(name)
            if not tcfg:
                mirrors.append({"target": name, "error": "account not found", "positions": []})
                continue
            mirrors.append(_reconcile_target(name, client_for(tcfg), desired, state))
        _save_state(state)
        _status["mirrors"] = mirrors

    return status()
