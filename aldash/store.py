"""JSON-backed store for accounts added through the dashboard.

Kept separate from .env / Streamlit secrets so the UI can add/remove accounts at
runtime. The file (accounts.json) holds API secrets, so it is git-ignored.

Note: on Streamlit Community Cloud the filesystem is ephemeral — accounts added
here persist until the app reboots/redeploys. For permanent accounts, add them to
Streamlit secrets instead.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .config import AccountConfig

STORE_PATH = Path(__file__).resolve().parent.parent / "accounts.json"


def load_stored_accounts() -> List[AccountConfig]:
    if not STORE_PATH.exists():
        return []
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    out: List[AccountConfig] = []
    for e in data:
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


def _write(accounts: List[AccountConfig]) -> None:
    data = [
        {"name": a.name, "api_key": a.api_key, "api_secret": a.api_secret, "paper": a.paper}
        for a in accounts
    ]
    STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_account(name: str, api_key: str, api_secret: str, paper: bool) -> None:
    """Add (or replace by name) a dashboard-managed account."""
    accounts = [a for a in load_stored_accounts() if a.name != name]
    accounts.append(AccountConfig(name=name, api_key=api_key, api_secret=api_secret,
                                  paper=paper, managed=True))
    _write(accounts)


def delete_account(name: str) -> None:
    """Remove a dashboard-managed account by name."""
    _write([a for a in load_stored_accounts() if a.name != name])
