"""Simple password gate for the dashboard.

Set a password via the `ALDASH_PASSWORD` env var (or `.env`), or `app_password`
in Streamlit secrets. If none is set, the app runs unprotected (fine for local
use, NOT for a public deployment).

Comparison is constant-time to avoid timing attacks.
"""
from __future__ import annotations

import hmac
import os

import streamlit as st

from aldash.ui import logo_svg


def _expected_password() -> str | None:
    try:
        pw = st.secrets.get("app_password", None)
    except Exception:
        pw = None
    return pw or os.getenv("ALDASH_PASSWORD")


def require_login() -> None:
    """Block the app with a login form until the correct password is entered.

    Call this once, early in the script. Does nothing if no password is set.
    """
    expected = _expected_password()

    # No password configured -> unprotected (local dev convenience).
    if not expected:
        st.session_state["_unprotected"] = True
        return

    if st.session_state.get("auth_ok"):
        return

    # ---- render centered login ----
    st.markdown(
        '<div style="max-width:400px;margin:11vh auto 0 auto;text-align:center;">'
        '<div style="display:inline-flex;align-items:center;gap:12px;font-size:31px;'
        'font-weight:800;color:#e7ecf3;letter-spacing:-.6px;">'
        f'{logo_svg(40, "login")}'
        '<span>AL<span style="color:#10b981;">Dash</span></span></div>'
        '<div style="color:#9aa6b6;font-size:13.5px;margin:10px 0 22px 0;">'
        'Enter your password to access your trading dashboard.</div></div>',
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.form("login_form"):
            pw = st.text_input("Password", type="password", label_visibility="collapsed",
                               placeholder="🔒  Password")
            submitted = st.form_submit_button("Sign in", width="stretch", type="primary")
        if submitted:
            if hmac.compare_digest(str(pw), str(expected)):
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    st.stop()


def logout_button() -> None:
    """Render a logout control in the sidebar (only if a password is in use)."""
    if st.session_state.get("_unprotected"):
        st.sidebar.caption("⚠️ No password set — app is unprotected.")
        return
    if st.sidebar.button(":material/logout: Log out", width="stretch"):
        st.session_state["auth_ok"] = False
        st.rerun()
