#!/usr/bin/env python3
"""Generate deterministic synthetic 5-minute OHLCV data for pipeline smoke tests.

This dataset is ONLY for software validation. It must never be used as evidence
of trading performance.
"""
from __future__ import annotations

import argparse
import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=520)
    ap.add_argument("--output", default="data/wfo_smoke.csv")
    args = ap.parse_args()

    # NSE-like session: 09:15 through 15:30, 5-minute bars = 75 bars/day.
    rng = np.random.default_rng(20260917)
    sessions = pd.bdate_range("2024-01-01", periods=args.days)
    stamps = []
    for day in sessions:
        stamps.extend(pd.date_range(day + pd.Timedelta(hours=9, minutes=15), periods=75, freq="5min"))
    idx = pd.DatetimeIndex(stamps)

    n = len(idx)
    shocks = rng.normal(0.0, 0.0007, n)
    drift = 0.00001 * np.sin(np.arange(n) / 200.0)
    close = 22000.0 * np.exp(np.cumsum(shocks + drift))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.normal(0.00045, 0.00015, n))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    volume = rng.integers(100_000, 500_000, n)

    out = pd.DataFrame({"timestamp": idx, "open": open_, "high": high, "low": low, "close": close, "volume": volume})
    out.to_csv(args.output, index=False)
    print(f"Wrote {len(out):,} bars to {args.output}")


if __name__ == "__main__":
    main()
