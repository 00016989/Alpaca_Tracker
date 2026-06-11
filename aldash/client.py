"""Thin wrapper around alpaca-py for a single account.

Keeps trading + news clients together and exposes the handful of operations the
dashboard needs. All methods raise on error so the UI can surface the message.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import (
    OrderClass,
    OrderSide,
    QueryOrderStatus,
    TimeInForce,
)
from alpaca.trading.requests import (
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)

from .config import AccountConfig

# News lives in the data API; import lazily-friendly but at module top is fine.
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest

# Order statuses that mean the order is still live (can still fill/cancel).
# Notably includes "held" — where a bracket's stop-loss leg waits.
_ACTIVE_ORDER_STATUSES = {
    "new", "held", "accepted", "pending_new", "accepted_for_bidding",
    "partially_filled", "calculated", "pending_replace",
}


def _is_active_order(order) -> bool:
    status = str(getattr(order, "status", "")).split(".")[-1].lower()
    return status in _ACTIVE_ORDER_STATUSES


class AccountClient:
    """Wraps one Alpaca account (trading + news)."""

    def __init__(self, cfg: AccountConfig):
        self.cfg = cfg
        self.trading = TradingClient(
            cfg.api_key, cfg.api_secret, paper=cfg.paper
        )
        # News uses the same keys; works for both live and paper.
        self.news = NewsClient(cfg.api_key, cfg.api_secret)

    # ---- reads -----------------------------------------------------------
    def get_account(self):
        return self.trading.get_account()

    def get_positions(self) -> list:
        return self.trading.get_all_positions()

    def get_open_orders(self) -> list:
        """Return all *active* orders, including bracket legs parked in HELD.

        A bracket's stop-loss leg sits in `held` status until the take-profit
        leg triggers/cancels, and Alpaca's `status=OPEN` filter excludes `held`.
        So we pull `status=ALL` (nested), flatten parents + legs, de-dupe by id,
        and keep only orders that are still live.
        """
        req = GetOrdersRequest(status=QueryOrderStatus.ALL, nested=True, limit=500)
        raw = self.trading.get_orders(filter=req)

        flat: dict[str, object] = {}
        for o in raw:
            flat[str(getattr(o, "id", id(o)))] = o
            for leg in (getattr(o, "legs", None) or []):
                flat[str(getattr(leg, "id", id(leg)))] = leg

        return [o for o in flat.values() if _is_active_order(o)]

    def get_recent_orders(self, limit: int = 50) -> list:
        req = GetOrdersRequest(status=QueryOrderStatus.ALL, nested=True, limit=limit)
        return self.trading.get_orders(filter=req)

    def get_equity_series(self, period: str = "1D", timeframe: str = "5Min") -> List[float]:
        """Intraday equity points for a sparkline (empty list on any failure)."""
        try:
            from alpaca.trading.requests import GetPortfolioHistoryRequest
            req = GetPortfolioHistoryRequest(
                period=period, timeframe=timeframe,
                intraday_reporting="market_hours", pnl_reset="per_day",
            )
            ph = self.trading.get_portfolio_history(history_filter=req)
            raw = getattr(ph, "equity", None) or []
            return [float(x) for x in raw if x is not None]
        except Exception:
            return []

    def get_news(self, symbols: Optional[List[str]] = None, limit: int = 20) -> list:
        start = datetime.now(timezone.utc) - timedelta(days=5)
        req = NewsRequest(
            symbols=",".join(symbols) if symbols else None,
            start=start,
            limit=limit,
            include_content=False,
        )
        news_set = self.news.get_news(req)
        # NewsSet exposes .data["news"]; fall back defensively across versions.
        data = getattr(news_set, "data", None)
        if isinstance(data, dict):
            return data.get("news", [])
        return getattr(news_set, "news", []) or []

    # ---- writes ----------------------------------------------------------
    def submit_bracket(
        self,
        symbol: str,
        qty: float,
        side: str,
        take_profit: Optional[float],
        stop_loss: Optional[float],
        limit_price: Optional[float] = None,
        time_in_force: str = "day",
    ):
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif = TimeInForce(time_in_force.lower())

        tp = TakeProfitRequest(limit_price=round(float(take_profit), 2)) if take_profit else None
        sl = StopLossRequest(stop_price=round(float(stop_loss), 2)) if stop_loss else None

        # Bracket requires both legs; if only one is given, send a simple order.
        order_class = OrderClass.BRACKET if (tp and sl) else (
            OrderClass.OTO if (tp or sl) else OrderClass.SIMPLE
        )

        common = dict(
            symbol=symbol.upper(),
            qty=float(qty),
            side=order_side,
            time_in_force=tif,
            order_class=order_class,
            take_profit=tp,
            stop_loss=sl,
        )

        if limit_price:
            order = LimitOrderRequest(limit_price=round(float(limit_price), 2), **common)
        else:
            order = MarketOrderRequest(**common)

        return self.trading.submit_order(order_data=order)

    def cancel_order(self, order_id: str):
        return self.trading.cancel_order_by_id(order_id)

    def cancel_all_orders(self):
        return self.trading.cancel_orders()

    def close_position(self, symbol: str):
        return self.trading.close_position(symbol)


def build_clients(accounts: List[AccountConfig]) -> "list[AccountClient]":
    return [AccountClient(a) for a in accounts]
