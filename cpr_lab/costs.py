"""Configurable India-market friction model.

Rates are date-configurable because broker/exchange/tax schedules can change.
Defaults reflect NSE references available in the research initialization (September 2026).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CostModel:
    slippage_rate: float = 0.0005  # 5 bps per side, user-requested baseline
    brokerage_per_order: float = 20.0
    gst_rate: float = 0.18
    sebi_turnover_rate: float = 0.000001  # 0.0001%
    cash_exchange_rate: float = 0.0000307  # Rs 307/crore/side = 0.00307%
    futures_exchange_rate: float = 0.0000183  # Rs 183/crore/side = 0.00183%
    options_exchange_rate: float = 0.0003553  # Rs 3,553/crore premium/side = 0.03553%
    cash_intraday_stt_rate: float = 0.00025  # seller only
    equity_delivery_stt_rate: float = 0.001  # seller only after delivery
    futures_stt_rate: float = 0.0005  # seller only from Apr 1 2026
    options_stt_rate: float = 0.0015  # seller only from Apr 1 2026, premium basis
    cash_intraday_stamp_rate: float = 0.00003  # buyer only
    futures_stamp_rate: float = 0.00002  # buyer only
    options_stamp_rate: float = 0.00003  # buyer only, premium basis

    def fill_price(self, mid: float, side: str, asset: str = "cash", extra_spread: float = 0.0) -> float:
        """Apply adverse slippage; options can add explicit half-spread."""
        sign = 1.0 if side.lower() == "buy" else -1.0
        impact = self.slippage_rate + extra_spread
        return mid * (1.0 + sign * impact)

    def transaction_cost(
        self,
        buy_value: float,
        sell_value: float,
        asset: str = "cash_intraday",
        orders: int = 2,
    ) -> float:
        """Return all modeled explicit costs for a round trip."""
        turnover = abs(buy_value) + abs(sell_value)
        asset = asset.lower()

        if asset == "options":
            exchange = turnover * self.options_exchange_rate
            stt = abs(sell_value) * self.options_stt_rate
            stamp = abs(buy_value) * self.options_stamp_rate
        elif asset == "futures":
            exchange = turnover * self.futures_exchange_rate
            stt = abs(sell_value) * self.futures_stt_rate
            stamp = abs(buy_value) * self.futures_stamp_rate
        elif asset == "cash_delivery":
            exchange = turnover * self.cash_exchange_rate
            stt = abs(sell_value) * self.equity_delivery_stt_rate
            stamp = abs(buy_value) * self.cash_intraday_stamp_rate
        else:  # cash intraday
            exchange = turnover * self.cash_exchange_rate
            stt = abs(sell_value) * self.cash_intraday_stt_rate
            stamp = abs(buy_value) * self.cash_intraday_stamp_rate

        sebi = turnover * self.sebi_turnover_rate
        brokerage = orders * self.brokerage_per_order
        gst = self.gst_rate * (brokerage + exchange + sebi)
        return brokerage + exchange + sebi + gst + stt + stamp


def option_half_spread(best_bid: float, best_ask: float) -> float:
    """Return half-spread as a decimal of mid, safe for zero/invalid quotes."""
    mid = (best_bid + best_ask) / 2.0
    if mid <= 0 or best_ask < best_bid:
        raise ValueError("Invalid bid/ask")
    return (best_ask - best_bid) / (2.0 * mid)


DEFAULT_EFFECTIVE_DATE = date(2026, 4, 1)
