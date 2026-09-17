"""Phase 3A stability diagnostics for CPR swing horizons.

Pre-specified robustness checks only. This script does not optimize thresholds,
horizons, direction rules, or entry timing. It addresses dependence from the
many overlapping signal events by repeating the directional analysis at three
levels: signal-event, equal-weight signal-day clusters, and fixed 10-session
time blocks. It also reports fixed chronological subperiods and year-wise sign
consistency, with Holm correction across the eight LONG/SHORT x horizon tests.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t

HORIZONS = ("2session", "3session", "5session", "10session")
SIDES = ("LONG", "SHORT")
SUBPERIODS = (("2015-2019", 2015, 2019), ("2020-2024", 2020, 2024))


def t_summary(values: pd.Series) -> dict[str, float]:
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    n = len(x)
    if n < 2:
        return {"n_units": n, "mean_R": float(np.mean(x)) if n else np.nan,
                "median_R": float(np.median(x)) if n else np.nan,
                "ci95_low": np.nan, "ci95_high": np.nan, "p_value": np.nan}
    mean = float(x.mean())
    se = float(x.std(ddof=1) / np.sqrt(n))
    p = float(2 * t.sf(abs(mean / se), n - 1)) if se else (1.0 if mean == 0 else 0.0)
    crit = float(t.ppf(0.975, n - 1))
    return {"n_units": n, "mean_R": mean, "median_R": float(np.median(x)),
            "ci95_low": mean - crit * se, "ci95_high": mean + crit * se,
            "p_value": p}


def holm_adjust(pairs: list[tuple[int, float]]) -> dict[int, float]:
    ordered = sorted(pairs, key=lambda q: q[1])
    out: dict[int, float] = {}
    running = 0.0
    m = len(ordered)
    for rank, (idx, p) in enumerate(ordered, 1):
        adj = min(1.0, (m - rank + 1) * p)
        running = max(running, adj)
        out[idx] = running
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Phase 3A swing_events.csv")
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    e = pd.read_csv(a.input, parse_dates=["signal_time", "signal_date", "entry_session"])
    e["signal_day"] = e["signal_date"].dt.date
    e["year"] = e["signal_date"].dt.year

    # Primary directional stability: equal weight to each signal day rather than
    # allowing days with many intraday signals to dominate the result.
    primary_rows: list[dict[str, object]] = []
    raw_rows: list[dict[str, object]] = []
    block_rows: list[dict[str, object]] = []
    for h in HORIZONS:
        for side in SIDES:
            z = e[(e.horizon == h) & (e.side == side)].copy()
            raw = t_summary(z.return_R)
            raw_rows.append({"horizon": h, "side": side, **raw})

            daily = z.groupby("signal_day", as_index=False).return_R.mean()
            ds = t_summary(daily.return_R)
            primary_rows.append({"horizon": h, "side": side, "method": "signal_day_cluster",
                                 **ds})

            # Fixed 10-session blocks. The block size is chosen ex ante to match
            # the longest tested horizon and is not selected from profitability.
            entry_days = pd.Index(sorted(pd.to_datetime(e.entry_session).dt.date.unique()))
            day_pos = {d: i for i, d in enumerate(entry_days)}
            z["block10"] = z.entry_session.map(lambda d: day_pos.get(pd.Timestamp(d).date(), -1) // 10)
            blocks = z[z.block10 >= 0].groupby("block10", as_index=False).return_R.mean()
            bs = t_summary(blocks.return_R)
            block_rows.append({"horizon": h, "side": side, "method": "10_session_block",
                               **bs})

    primary = pd.DataFrame(primary_rows)
    adj = holm_adjust([(i, float(p)) for i, p in enumerate(primary.p_value) if np.isfinite(p)])
    primary["holm_p_value"] = [adj.get(i, np.nan) for i in range(len(primary))]
    primary.to_csv(out / "swing_stability_direction.csv", index=False)
    pd.DataFrame(raw_rows).to_csv(out / "swing_stability_event_level.csv", index=False)
    pd.DataFrame(block_rows).to_csv(out / "swing_stability_10session_blocks.csv", index=False)

    sub_rows: list[dict[str, object]] = []
    for label, y0, y1 in SUBPERIODS:
        for h in HORIZONS:
            for side in SIDES:
                z = e[(e.year >= y0) & (e.year <= y1) & (e.horizon == h) & (e.side == side)]
                daily = z.groupby("signal_day", as_index=False).return_R.mean()
                s = t_summary(daily.return_R)
                sub_rows.append({"subperiod": label, "horizon": h, "side": side,
                                 "raw_events": len(z), **s})
    pd.DataFrame(sub_rows).to_csv(out / "swing_stability_subperiods.csv", index=False)

    year_rows: list[dict[str, object]] = []
    for (year, h, side), z in e.groupby(["year", "horizon", "side"]):
        s = t_summary(z.groupby("signal_day").return_R.mean())
        year_rows.append({"year": int(year), "horizon": h, "side": side, **s})
    yearly = pd.DataFrame(year_rows)
    yearly.to_csv(out / "swing_stability_yearly.csv", index=False)

    consistency: list[dict[str, object]] = []
    for h in HORIZONS:
        for side in SIDES:
            q = yearly[(yearly.horizon == h) & (yearly.side == side)]
            consistency.append({
                "horizon": h,
                "side": side,
                "years": len(q),
                "positive_years": int((q.mean_R > 0).sum()),
                "negative_years": int((q.mean_R < 0).sum()),
                "zero_years": int((q.mean_R == 0).sum()),
                "positive_year_fraction": float((q.mean_R > 0).mean()) if len(q) else np.nan,
            })
    pd.DataFrame(consistency).to_csv(out / "swing_stability_year_sign_consistency.csv", index=False)

    print("=== DIRECTIONAL STABILITY: EQUAL-WEIGHT SIGNAL DAYS ===")
    print(primary.to_string(index=False))
    print("\n=== FIXED 10-SESSION BLOCKS ===")
    print(pd.DataFrame(block_rows).to_string(index=False))
    print("\n=== CHRONOLOGICAL SUBPERIODS ===")
    print(pd.DataFrame(sub_rows).to_string(index=False))
    print("\n=== YEAR SIGN CONSISTENCY ===")
    print(pd.DataFrame(consistency).to_string(index=False))


if __name__ == "__main__":
    main()
