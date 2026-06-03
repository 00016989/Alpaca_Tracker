"""Consolidate raw Alpaca positions + open orders into one row per ticker.

Alpaca returns a bracket as three separate things: the entry (now your filled
position) plus a take-profit leg (a limit order) and a stop-loss leg (a stop
order). This module stitches them back together so the UI can show, on one line:

    ticker | side | qty | avg entry | current | SL | TP | market value | PnL

`worth` = position market value (what the holding is currently worth).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _enum_str(value) -> str:
    """Normalize an Alpaca enum/value to its bare lowercase name.

    Alpaca enums stringify as 'OrderSide.SELL' / 'PositionSide.LONG'; we want
    'sell' / 'long'. Plain strings pass through unchanged.
    """
    return str(value).split(".")[-1].lower()


@dataclass
class ConsolidatedPosition:
    account: str
    symbol: str
    side: str               # "long" / "short"
    qty: float
    avg_entry: float
    current_price: float
    market_value: float     # the "worth" of the holding
    unrealized_pl: float    # floating PnL ($)
    unrealized_plpc: float  # floating PnL (%)
    stop_loss: Optional[float]    # SL price from the stop leg, if any
    take_profit: Optional[float]  # TP price from the limit leg, if any
    sl_order_id: Optional[str]
    tp_order_id: Optional[str]

    def _pl_at(self, price: Optional[float]) -> Optional[float]:
        """Dollar P/L if the position were closed at `price`.

        qty is signed (negative for shorts), so (price - entry) * qty gives the
        correct sign for both longs and shorts.
        """
        if price is None:
            return None
        return (price - self.avg_entry) * self.qty

    @property
    def sl_amount(self) -> Optional[float]:
        """How much you LOSE (usually negative) if the stop-loss hits."""
        return self._pl_at(self.stop_loss)

    @property
    def tp_amount(self) -> Optional[float]:
        """How much you GAIN if the take-profit hits."""
        return self._pl_at(self.take_profit)

    @property
    def risk_reward(self) -> Optional[float]:
        """Reward-to-risk ratio (|TP gain| / |SL loss|), if both exist."""
        sl, tp = self.sl_amount, self.tp_amount
        if sl is None or tp is None or sl == 0:
            return None
        return abs(tp) / abs(sl)


def _classify_order(order):
    """Return ('tp'|'sl'|None, price) for an exit leg order."""
    otype = str(getattr(order, "order_type", getattr(order, "type", ""))).lower()
    stop_price = getattr(order, "stop_price", None)
    limit_price = getattr(order, "limit_price", None)
    trail = getattr(order, "trail_price", None) or getattr(order, "trail_percent", None)

    if "stop" in otype or stop_price is not None or trail is not None:
        price = _f(stop_price) if stop_price is not None else None
        return "sl", price
    if "limit" in otype or limit_price is not None:
        return "tp", _f(limit_price) if limit_price is not None else None
    return None, None


def _exit_legs_for_symbol(symbol: str, position_side: str, orders) -> dict:
    """Find the SL/TP exit orders matching an open position.

    Exit orders sit on the opposite side of the position (sell to close a long).
    """
    close_side = "sell" if position_side == "long" else "buy"
    result = {"sl": None, "tp": None, "sl_id": None, "tp_id": None}

    # Flatten any nested bracket legs so children are considered too.
    flat = []
    for o in orders:
        flat.append(o)
        for leg in (getattr(o, "legs", None) or []):
            flat.append(leg)

    for o in flat:
        if str(getattr(o, "symbol", "")).upper() != symbol.upper():
            continue
        if _enum_str(getattr(o, "side", "")) != close_side:
            continue
        kind, price = _classify_order(o)
        if kind == "sl" and result["sl"] is None:
            result["sl"] = price
            result["sl_id"] = str(getattr(o, "id", "")) or None
        elif kind == "tp" and result["tp"] is None:
            result["tp"] = price
            result["tp_id"] = str(getattr(o, "id", "")) or None
    return result


def consolidate(account_name: str, positions, open_orders) -> List[ConsolidatedPosition]:
    rows: List[ConsolidatedPosition] = []
    for p in positions:
        side = _enum_str(getattr(p, "side", "long"))
        symbol = str(getattr(p, "symbol", "")).upper()
        legs = _exit_legs_for_symbol(symbol, side, open_orders)
        rows.append(
            ConsolidatedPosition(
                account=account_name,
                symbol=symbol,
                side=side,
                qty=_f(getattr(p, "qty", 0)),
                avg_entry=_f(getattr(p, "avg_entry_price", 0)),
                current_price=_f(getattr(p, "current_price", 0)),
                market_value=_f(getattr(p, "market_value", 0)),
                unrealized_pl=_f(getattr(p, "unrealized_pl", 0)),
                unrealized_plpc=_f(getattr(p, "unrealized_plpc", 0)) * 100.0,
                stop_loss=legs["sl"],
                take_profit=legs["tp"],
                sl_order_id=legs["sl_id"],
                tp_order_id=legs["tp_id"],
            )
        )
    rows.sort(key=lambda r: abs(r.market_value), reverse=True)
    return rows
