#!/usr/bin/env python3
"""Run 10,000-path risk simulation from a trade-return CSV.

Usage:
  python scripts/run_monte_carlo.py --input results/trades.csv --column return_on_risk --risk 0.01
"""
from __future__ import annotations

import argparse
import pandas as pd

from cpr_lab.risk import bootstrap_paths, monte_carlo_summary, empirical_kelly_fraction


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--column", default="return_on_risk")
    ap.add_argument("--risk", type=float, default=0.01)
    ap.add_argument("--paths", type=int, default=10_000)
    ap.add_argument("--trades", type=int, default=None)
    ap.add_argument("--block-size", type=int, default=5)
    args = ap.parse_args()

    r = pd.read_csv(args.input)[args.column].dropna().to_numpy(dtype=float)
    kelly = empirical_kelly_fraction(r)
    eq, dd = bootstrap_paths(r, paths=args.paths, trades=args.trades, risk_fraction=args.risk, block_size=args.block_size)
    summary = monte_carlo_summary(eq, dd)
    print("Empirical Kelly:", kelly)
    print(summary)


if __name__ == "__main__":
    main()
