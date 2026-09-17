"""Small event-driven execution engine for hypothesis-level backtests."""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from .costs import CostModel


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    risk_per_trade: float = 0.01
    execution: str = "next_open"
    asset: str = "cash_intraday"
    max_leverage: float = 2.0


def simulate_single_position(
    bars: pd.DataFrame,
    long_col: str = "long_entry",
    short_col: str = "short_entry",
    atr_col: str = "D_ATR20",
    atr_stop: float = 1.0,
    target_r: float = 2.0,
    config: BacktestConfig = BacktestConfig(),
    costs: CostModel = CostModel(),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Single-position long/short simulator.

    Signals are evaluated on bar close and, by default, executed at the next bar open.
    If stop and target are both touched in one bar, the stop is assumed to execute first
    (conservative bar-resolution rule). Once account equity reaches zero, the account is
    treated as liquidated and no new positions are opened; this prevents negative-equity
    risk sizing from creating artificial position-size explosions.
    """
    x = bars.copy().sort_index()
    equity = config.initial_capital
    position = None
    entry_price = stop = target = None
    entry_ts = None
    qty = 0.0
    trades = []
    equity_curve = []
    liquidated = False

    for i, (ts, row) in enumerate(x.iterrows()):
        mtm = equity
        if position is not None:
            direction = 1 if position == "LONG" else -1
            mtm = equity + qty * direction * (float(row.close) - float(entry_price))
        equity_curve.append((ts, mtm))

        if position is not None:
            direction = 1 if position == "LONG" else -1
            exit_reason = None
            exit_price = None
            if direction == 1 and float(row.open) <= stop:
                exit_price, exit_reason = float(row.open), "gap_stop"
            elif direction == -1 and float(row.open) >= stop:
                exit_price, exit_reason = float(row.open), "gap_stop"
            elif direction == 1 and float(row.low) <= stop:
                exit_price, exit_reason = stop, "stop"
            elif direction == -1 and float(row.high) >= stop:
                exit_price, exit_reason = stop, "stop"
            elif direction == 1 and float(row.high) >= target:
                exit_price, exit_reason = target, "target"
            elif direction == -1 and float(row.low) <= target:
                exit_price, exit_reason = target, "target"
            elif row.get("exit_time", False):
                exit_price, exit_reason = float(row.close), "time_exit"

            if exit_price is not None:
                fill = costs.fill_price(exit_price, "sell" if direction == 1 else "buy", asset=config.asset)
                gross = qty * direction * (fill - float(entry_price))
                buy_value = abs(qty * (entry_price if direction == 1 else fill))
                sell_value = abs(qty * (fill if direction == 1 else entry_price))
                fee = costs.transaction_cost(buy_value, sell_value, asset=config.asset, orders=2)
                net = gross - fee
                equity += net
                if equity <= 0:
                    equity = 0.0
                    liquidated = True
                # Replace the pre-exit mark-to-market value with realized account equity.
                equity_curve[-1] = (ts, equity)

                trades.append({
                    "entry_time": entry_ts,
                    "exit_time": ts,
                    "side": position,
                    "entry_price": entry_price,
                    "exit_price": fill,
                    "qty": qty,
                    "gross_pnl": gross,
                    "costs": fee,
                    "net_pnl": net,
                    "return_on_risk": net / max(abs(qty * (entry_price - stop)), 1e-12),
                    "exit_reason": exit_reason,
                    "account_liquidated": liquidated,
                })
                position = None
                entry_price = stop = target = entry_ts = None
                qty = 0.0
                if liquidated:
                    break
                continue

        if position is None and not liquidated and equity > 0 and i + 1 < len(x):
            next_row = x.iloc[i + 1]
            next_ts = x.index[i + 1]
            side = "LONG" if bool(row.get(long_col, False)) else "SHORT" if bool(row.get(short_col, False)) else None
            if side is not None:
                price_raw = float(next_row.open)
                direction = 1 if side == "LONG" else -1
                fill = costs.fill_price(price_raw, "buy" if direction == 1 else "sell", asset=config.asset)
                atr = float(row.get(atr_col, 0.0) or 0.0)
                if atr <= 0:
                    continue
                risk_distance = atr_stop * atr
                stop_price = fill - risk_distance if direction == 1 else fill + risk_distance
                target_price = fill + target_r * risk_distance if direction == 1 else fill - target_r * risk_distance
                capital_at_risk = equity * config.risk_per_trade
                q = capital_at_risk / risk_distance
                max_qty = (equity * config.max_leverage) / max(abs(fill), 1e-12)
                q = min(q, max_qty)
                if q <= 0:
                    continue
                position = side
                entry_price, stop, target, entry_ts, qty = fill, stop_price, target_price, next_ts, q

    if position is not None and not liquidated:
        ts = x.index[-1]
        price_raw = float(x.iloc[-1].close)
        direction = 1 if position == "LONG" else -1
        fill = costs.fill_price(price_raw, "sell" if direction == 1 else "buy", asset=config.asset)
        gross = qty * direction * (fill - float(entry_price))
        buy_value = abs(qty * (entry_price if direction == 1 else fill))
        sell_value = abs(qty * (fill if direction == 1 else entry_price))
        fee = costs.transaction_cost(buy_value, sell_value, asset=config.asset, orders=2)
        net = gross - fee
        equity += net
        if equity <= 0:
            equity = 0.0
            liquidated = True
        equity_curve[-1] = (ts, equity)
        trades.append({
            "entry_time": entry_ts, "exit_time": ts, "side": position,
            "entry_price": entry_price, "exit_price": fill, "qty": qty,
            "gross_pnl": gross, "costs": fee, "net_pnl": net,
            "return_on_risk": net / max(abs(qty * (entry_price - stop)), 1e-12),
            "exit_reason": "end_of_test",
            "account_liquidated": liquidated,
        })

    trade_df = pd.DataFrame(trades)
    eq = pd.DataFrame(equity_curve, columns=["timestamp", "equity"]).drop_duplicates("timestamp").set_index("timestamp")
    return trade_df, eq
