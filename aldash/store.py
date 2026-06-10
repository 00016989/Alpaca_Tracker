"""JSON-backed store for dashboard account management.

Two things live in accounts.json (git-ignored, holds secrets):
  - "managed": accounts added through the dashboard (fully deletable)
  - "hidden":  names of config-based accounts (.env / secrets) the user hid

Config-based accounts can't be removed from a file at runtime (especially on
Streamlit Cloud), so "deleting" one just hides it — and it can be restored.

Note: on Streamlit Community Cloud the filesystem is ephemeral, so changes here
persist only until the app reboots/redeploys. For permanent accounts use secrets.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Set

from .config import AccountConfig

STORE_PATH = Path(__file__).resolve().parent.parent / "accounts.json"


def _read() -> dict:
    if not STORE_PATH.exists():
        return {"managed": [], "hidden": []}
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"managed": [], "hidden": []}
    # Migrate the legacy format (a bare list of managed accounts).
    if isinstance(data, list):
        return {"managed": data, "hidden": []}
    if isinstance(data, dict):
        data.setdefault("managed", [])
        data.setdefault("hidden", [])
        return data
    return {"managed": [], "hidden": []}


def _write(data: dict) -> None:
    STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_stored_accounts() -> List[AccountConfig]:
    out: List[AccountConfig] = []
    for e in _read()["managed"]:
        try:
            out.append(
                AccountConfig(
                    name=str(e["name"]),
                    api_key=str(e["api_key"]),
                    api_secret=str(e["api_secret"]),
                    paper=bool(e.get("paper", True)),
                    managed=True,
                )
            )
        except (KeyError, TypeError):
            continue
    return out


def hidden_names() -> Set[str]:
    return set(_read().get("hidden", []))


def add_account(name: str, api_key: str, api_secret: str, paper: bool) -> None:
    data = _read()
    data["managed"] = [a for a in data["managed"] if a.get("name") != name]
    data["managed"].append(
        {"name": name, "api_key": api_key, "api_secret": api_secret, "paper": paper}
    )
    data["hidden"] = [h for h in data.get("hidden", []) if h != name]  # un-hide if needed
    _write(data)


def delete_account(name: str) -> None:
    """Remove a dashboard-managed account entirely."""
    data = _read()
    data["managed"] = [a for a in data["managed"] if a.get("name") != name]
    _write(data)


def hide_account(name: str) -> None:
    """Hide a config-based account (restorable)."""
    data = _read()
    if name not in data.get("hidden", []):
        data.setdefault("hidden", []).append(name)
    _write(data)


def unhide_account(name: str) -> None:
    data = _read()
    data["hidden"] = [h for h in data.get("hidden", []) if h != name]
    _write(data)


def remove(account: AccountConfig) -> None:
    """Delete a managed account, or hide a config-based one."""
    if account.managed:
        delete_account(account.name)
    else:
        hide_account(account.name)
