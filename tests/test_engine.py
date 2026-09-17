import pandas as pd

from cpr_lab.costs import CostModel
from cpr_lab.engine import BacktestConfig, simulate_single_position


def test_liquidated_account_cannot_open_new_positions():
    idx = pd.date_range("2024-01-02 09:15", periods=5, freq="5min")
    bars = pd.DataFrame(
        {
            "open": [100.0, 100.0, 90.0, 90.0, 90.0],
            "high": [100.0, 101.0, 90.0, 90.0, 90.0],
            "low": [100.0, 99.0, 90.0, 90.0, 90.0],
            "close": [100.0, 100.0, 90.0, 90.0, 90.0],
            "volume": [0.0] * 5,
            "D_ATR20": [1.0] * 5,
            "long_entry": [True, False, True, False, False],
            "short_entry": [False] * 5,
            "exit_time": [False, True, False, False, False],
        },
        index=idx,
    )

    costs = CostModel(
        slippage_rate=0.0,
        brokerage_per_order=100.0,
        gst_rate=0.0,
        sebi_turnover_rate=0.0,
        cash_exchange_rate=0.0,
        cash_intraday_stt_rate=0.0,
        cash_intraday_stamp_rate=0.0,
    )
    trades, equity = simulate_single_position(
        bars,
        config=BacktestConfig(initial_capital=100.0, risk_per_trade=0.01, max_leverage=2.0),
        costs=costs,
    )

    assert len(trades) == 1
    assert bool(trades.iloc[0]["account_liquidated"])
    assert float(equity["equity"].iloc[-1]) == 0.0
    assert trades.iloc[0]["exit_time"] == idx[1]
