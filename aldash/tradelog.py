"""Trade log: fetch filled orders and FIFO-match them into round-trip trades.

Alpaca doesn't hand you "realized PnL per trade" directly, so we reconstruct it:
pull closed/filled orders, then walk them in time order matching position-reducing
fills against opposite open lots (first-in-first-out). Each completed match becomes
a round-trip with entry, exit, qty, realized PnL, return %, and holding period.

Handles longs, shorts, and position flips.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class Fill:
    account: str
    symbol: str
    side: str          # "buy" / "sell"
    qty: float
    price: float
    time: datetime
    order_type: str
    order_id: str


@dataclass
class RoundTrip:
    account: str
    symbol: str
    direction: str     # "long" / "short"
    qty: float
    entry_price: float
    exit_price: float
    opened_at: datetime
    closed_at: datetime
    pnl: float
    return_pct: float

    @property
    def holding(self) -> str:
        secs = max((self.closed_at - self.opened_at).total_seconds(), 0)
        d, rem = divmod(int(secs), 86400)
        h, rem = divmod(rem, 3600)
        m, _ = divmod(rem, 60)
        if d:
            return f"{d}d {h}h"
        if h:
            return f"{h}h {m}m"
        return f"{m}m"


def fetch_filled_orders(client, days: int = 90, max_pages: int = 10) -> List[Fill]:
    """Pull filled orders for the last `days`, paginating backwards."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    fills: List[Fill] = []
    until: Optional[datetime] = None
    account_name = client.cfg.name

    for _ in range(max_pages):
        req = GetOrdersRequest(
            status=QueryOrderStatus.CLOSED,
            limit=500,
            after=cutoff,
            until=until,
            nested=False,
        )
        batch = client.trading.get_orders(filter=req)
        if not batch:
            break

        for o in batch:
            filled_qty = _f(getattr(o, "filled_qty", 0))
            filled_at = getattr(o, "filled_at", None)
            avg_price = _f(getattr(o, "filled_avg_price", 0))
            if filled_qty <= 0 or filled_at is None or avg_price <= 0:
                continue
            fills.append(
                Fill(
                    account=account_name,
                    symbol=str(getattr(o, "symbol", "")).upper(),
                    side=str(getattr(o, "side", "")).split(".")[-1].lower(),
                    qty=filled_qty,
                    price=avg_price,
                    time=filled_at,
                    order_type=str(getattr(o, "order_type", getattr(o, "type", ""))).split(".")[-1],
                    order_id=str(getattr(o, "id", "")),
                )
            )

        if len(batch) < 500:
            break
        # Page back: next page ends just before the oldest order we just saw.
        oldest = min((getattr(o, "submitted_at", None) or getattr(o, "created_at", None))
                     for o in batch)
        if oldest is None or oldest <= cutoff:
            break
        until = oldest

    fills.sort(key=lambda f: f.time)
    return fills


def fifo_round_trips(fills: List[Fill]) -> List[RoundTrip]:
    """Match fills FIFO into closed round-trip trades with realized PnL."""
    trips: List[RoundTrip] = []
    # one lot deque per (account, symbol); lots are (dir, qty, price, time)
    books: dict[tuple, deque] = {}

    for f in fills:
        key = (f.account, f.symbol)
        book = books.setdefault(key, deque())
        qty = f.qty

        # A buy closes existing shorts; a sell closes existing longs.
        closing_dir = "short" if f.side == "buy" else "long"

        while qty > 1e-9 and book and book[0][0] == closing_dir:
            ldir, lqty, lprice, ltime = book[0]
            matched = min(qty, lqty)
            if closing_dir == "long":      # selling to close a long
                pnl = (f.price - lprice) * matched
            else:                          # buying to close a short
                pnl = (lprice - f.price) * matched
            cost = lprice * matched
            trips.append(
                RoundTrip(
                    account=f.account,
                    symbol=f.symbol,
                    direction=ldir,
                    qty=matched,
                    entry_price=lprice,
                    exit_price=f.price,
                    opened_at=ltime,
                    closed_at=f.time,
                    pnl=pnl,
                    return_pct=(pnl / cost * 100.0) if cost else 0.0,
                )
            )
            qty -= matched
            if matched >= lqty - 1e-9:
                book.popleft()
            else:
                book[0] = (ldir, lqty - matched, lprice, ltime)

        # Whatever remains opens a new lot in the fill's own direction.
        if qty > 1e-9:
            open_dir = "long" if f.side == "buy" else "short"
            book.append((open_dir, qty, f.price, f.time))

    trips.sort(key=lambda t: t.closed_at, reverse=True)
    return trips


def summarize(trips: List[RoundTrip]) -> dict:
    if not trips:
        return {"n": 0, "pnl": 0.0, "win_rate": 0.0, "avg_win": 0.0,
                "avg_loss": 0.0, "profit_factor": 0.0, "best": 0.0, "worst": 0.0}
    wins = [t.pnl for t in trips if t.pnl > 0]
    losses = [t.pnl for t in trips if t.pnl < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "n": len(trips),
        "pnl": sum(t.pnl for t in trips),
        "win_rate": len(wins) / len(trips) * 100.0,
        "avg_win": (gross_win / len(wins)) if wins else 0.0,
        "avg_loss": (-gross_loss / len(losses)) if losses else 0.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss else float("inf"),
        "best": max(t.pnl for t in trips),
        "worst": min(t.pnl for t in trips),
    }
