"""Account configuration loading.

Credentials are read from .streamlit/secrets.toml first (kept for backward
compatibility), and fall back to environment variables (ALDASH_ACCOUNT_*) so
the app can run in CI / containers / on hosts like Render.

secrets.toml format:

    [[accounts]]
    name = "Main (Live)"
    api_key = "..."
    api_secret = "..."
    paper = false
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import List

# Load a local .env file (if present) so credentials can live there.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

_SECRETS_PATH = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"


def read_secrets() -> dict:
    """Parse .streamlit/secrets.toml directly (no Streamlit dependency)."""
    try:
        return tomllib.loads(_SECRETS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


@dataclass(frozen=True)
class AccountConfig:
    name: str
    api_key: str
    api_secret: str
    paper: bool
    managed: bool = False  # True = added via dashboard (stored in accounts.json)

    @property
    def env_label(self) -> str:
        return "PAPER" if self.paper else "LIVE"


def _from_secrets() -> List[AccountConfig]:
    raw = read_secrets().get("accounts", None)
    if not raw:
        return []

    accounts: List[AccountConfig] = []
    for entry in raw:
        accounts.append(
            AccountConfig(
                name=str(entry.get("name", "Account")),
                api_key=str(entry["api_key"]),
                api_secret=str(entry["api_secret"]),
                paper=bool(entry.get("paper", True)),
            )
        )
    return accounts


def _from_env() -> List[AccountConfig]:
    """Fallback: ALDASH_ACCOUNT_<i>_KEY / _SECRET / _NAME / _PAPER.

    We scan a fixed range and *skip* empty slots rather than stopping at the
    first gap, so removing one account (e.g. deleting only ACCOUNT_2_*) doesn't
    silently drop every higher-numbered account after it.
    """
    accounts: List[AccountConfig] = []
    for i in range(1, 51):
        key = os.getenv(f"ALDASH_ACCOUNT_{i}_KEY")
        secret = os.getenv(f"ALDASH_ACCOUNT_{i}_SECRET")
        if not key or not secret:
            continue
        accounts.append(
            AccountConfig(
                name=os.getenv(f"ALDASH_ACCOUNT_{i}_NAME", f"Account {i}"),
                api_key=key,
                api_secret=secret,
                paper=os.getenv(f"ALDASH_ACCOUNT_{i}_PAPER", "true").lower() != "false",
            )
        )
    return accounts


def _is_configured(a: AccountConfig) -> bool:
    """True only for accounts with real (non-placeholder) credentials."""
    return bool(
        a.api_key
        and not a.api_key.startswith("YOUR_")
        and a.api_secret
        and not a.api_secret.startswith("YOUR_")
    )


def load_accounts() -> List[AccountConfig]:
    """Return all accounts: config-based (.env / secrets) + dashboard-managed.

    We filter placeholders *within* each config source so a leftover template
    secrets.toml (all YOUR_… keys) doesn't shadow a real .env, and vice-versa.
    Dashboard-added accounts (accounts.json) are merged on top; on a name clash
    the config-based account wins.
    """
    config: List[AccountConfig] = []
    for source in (_from_secrets, _from_env):
        configured = [a for a in source() if _is_configured(a)]
        if configured:
            config = configured
            break

    # Lazy import avoids a circular dependency (store imports AccountConfig).
    from .store import hidden_names, load_stored_accounts

    hidden = hidden_names()
    config = [a for a in config if a.name not in hidden]
    names = {a.name for a in config}
    managed = [
        a for a in load_stored_accounts()
        if a.name not in names and a.name not in hidden
    ]
    return config + managed
