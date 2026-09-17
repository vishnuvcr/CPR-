"""Run the pre-optimization CPR baseline on real 5-minute OHLCV data."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from cpr_lab.costs import CostModel
from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.engine import BacktestConfig, simulate_single_position
from cpr_lab.indicators import daily_reference_features, add_intraday_daily_features
from cpr_lab.metrics import trade_metrics
from cpr_lab.strategies import StrategyConfig, intraday_directional_signals


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", default="results/baseline")
    p.add_argument("--initial-capital", type=float, default=100_000.0)
    p.add_argument("--risk-per-trade", type=float, default=0.01)
    p.add_argument("--max-leverage", type=float, default=2.0)
    args = p.parse_args()

    bars = load_ohlcv_csv(args.input)
    daily = bars.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    features = daily_reference_features(daily)
    x = add_intraday_daily_features(bars, features)
    signals = intraday_directional_signals(x, StrategyConfig(narrow_x=0.50, wide_y=1.00, atr_stop=1.0, target_r=2.0, exit_time="15:15"))

    config = BacktestConfig(initial_capital=args.initial_capital, risk_per_trade=args.risk_per_trade, max_leverage=args.max_leverage, asset="cash_intraday")
    costs = CostModel()
    trades, equity = simulate_single_position(signals, atr_stop=1.0, target_r=2.0, config=config, costs=costs)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    signals.to_csv(out / "signals.csv")
    trades.to_csv(out / "trades.csv", index=False)
    equity.to_csv(out / "equity.csv")

    returns = trades["return_on_risk"] if not trades.empty else pd.Series(dtype=float)
    metrics = trade_metrics(returns, equity["equity"] if not equity.empty else None)
    pd.DataFrame([metrics]).to_csv(out / "metrics.csv", index=False)
    print(pd.Series(metrics).to_string())
    print(f"Trades: {len(trades)}")
    print(f"Output: {out.resolve()}")


if __name__ == "__main__":
    main()
