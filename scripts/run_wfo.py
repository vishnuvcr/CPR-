#!/usr/bin/env python3
"""Run chronological walk-forward optimization on OHLCV data."""
from __future__ import annotations

import argparse
import pandas as pd

from cpr_lab.walk_forward import grid, optimize_wfo
from cpr_lab.indicators import daily_reference_features, add_intraday_daily_features
from cpr_lab.strategies import StrategyConfig, intraday_directional_signals
from cpr_lab.engine import simulate_single_position, BacktestConfig
from cpr_lab.metrics import trade_metrics


def evaluate(data: pd.DataFrame, params: dict) -> float:
    cfg = StrategyConfig(narrow_x=params["narrow_x"], wide_y=params["wide_y"])
    signals = intraday_directional_signals(data, cfg)
    trades, _ = simulate_single_position(
        signals,
        atr_stop=params.get("atr_stop", 1.0),
        target_r=params.get("target_r", 2.0),
        config=BacktestConfig(risk_per_trade=0.01),
    )
    if trades.empty:
        return -1e9
    m = trade_metrics(trades["return_on_risk"])
    return float(m.get("expectancy", -1e9))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Parquet/CSV OHLCV file with timestamp index")
    ap.add_argument("--format", choices=["csv", "parquet"], default="csv")
    ap.add_argument("--output", default="results/wfo_folds.csv")
    ap.add_argument("--fast", action="store_true", help="Small grid for CI smoke testing")
    args = ap.parse_args()

    df = pd.read_parquet(args.input) if args.format == "parquet" else pd.read_csv(args.input, parse_dates=["timestamp"], index_col="timestamp")
    daily = df.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
    features = daily_reference_features(daily)
    bars = add_intraday_daily_features(df, features)

    if args.fast:
        parameter_space = {
            "narrow_x": [0.30, 0.60],
            "wide_y": [1.00, 1.50],
            "atr_stop": [1.0],
            "target_r": [1.5, 2.0],
        }
    else:
        parameter_space = {
            "narrow_x": [0.20, 0.30, 0.40, 0.50, 0.60, 0.75],
            "wide_y": [0.75, 1.00, 1.25, 1.50, 1.75],
            "atr_stop": [0.75, 1.0, 1.5],
            "target_r": [1.0, 1.5, 2.0, 3.0],
        }

    fold_df, stitched = optimize_wfo(
        bars,
        grid(parameter_space),
        evaluate,
        train_periods=252,
        test_periods=63,
        step=63,
        fold_index=daily.index,
    )
    fold_df.to_csv(args.output, index=False)
    stitched_path = args.output.replace(".csv", "_stitched.csv")
    stitched.to_csv(stitched_path)
    print(fold_df)
    print(f"WFO folds: {len(fold_df)}")
    print(f"Stitched test bars: {len(stitched):,}")


if __name__ == "__main__":
    main()
