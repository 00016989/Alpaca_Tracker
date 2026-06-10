"""Account configuration loading.

Credentials are read from Streamlit secrets (.streamlit/secrets.toml) first, and
fall back to environment variables so the app can also run in CI / containers.

secrets.toml format:

    [[accounts]]
    name = "Main (Live)"
    api_key = "..."
    api_secret = "..."
    paper = false
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

# Load a local .env file (if present) so credentials can live there.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


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


def _from_streamlit() -> List[AccountConfig]:
    try:
        import streamlit as st
    except ImportError:
        return []

    try:
        raw = st.secrets.get("accounts", None)
    except Exception:
        # st.secrets raises if no secrets file exists at all
        return []

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
    """Fallback: ALDASH_ACCOUNT_1_KEY / _SECRET / _NAME / _PAPER, incrementing index."""
    accounts: List[AccountConfig] = []
    i = 1
    while True:
        key = os.getenv(f"ALDASH_ACCOUNT_{i}_KEY")
        secret = os.getenv(f"ALDASH_ACCOUNT_{i}_SECRET")
        if not key or not secret:
            break
        accounts.append(
            AccountConfig(
                name=os.getenv(f"ALDASH_ACCOUNT_{i}_NAME", f"Account {i}"),
                api_key=key,
                api_secret=secret,
                paper=os.getenv(f"ALDASH_ACCOUNT_{i}_PAPER", "true").lower() != "false",
            )
        )
        i += 1
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
    for source in (_from_streamlit, _from_env):
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
