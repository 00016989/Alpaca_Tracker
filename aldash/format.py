"""Small display-formatting helpers."""
from __future__ import annotations

from typing import Optional


def money(value: Optional[float], dash: str = "—") -> str:
    if value is None:
        return dash
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def pct(value: Optional[float], dash: str = "—") -> str:
    if value is None:
        return dash
    return f"{value:+.2f}%"


def price(value: Optional[float], dash: str = "—") -> str:
    if value is None:
        return dash
    return f"${value:,.2f}"


def arrow(value: float) -> str:
    if value > 0:
        return "🟢"
    if value < 0:
        return "🔴"
    return "⚪"
