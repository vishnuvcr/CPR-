"""Phase 9B: pre-defined CPR context consensus analysis.

This script never fits or optimizes consensus thresholds. It labels historical
shadow signal timestamps using a fixed, pre-registered state taxonomy and then
describes subsequent candidate outcomes within compatible horizons.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def state(long_n: int, short_n: int) -> str:
    if long_n == 0 and short_n == 0:
        return "NO_SIGNAL"
    if long_n > 0 and short_n > 0:
        return "CONFLICT"
    n = max(long_n, short_n)
    side = "LONG" if long_n else "SHORT"
    if n == 1:
        return f"SINGLE_{side}"
    if n <= 3:
        return f"MULTIPLE_{side}_2_3"
    return f"MULTIPLE_{side}_4_PLUS"


def bootstrap_mean_ci(values: np.ndarray, reps: int = 2000, seed: int = 20260918):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    means = np.mean(x[rng.integers(0, len(x), size=(reps, len(x)))], axis=1)
    return float(np.quantile(means, .025)), float(np.quantile(means, .975))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    d = pd.read_csv(args.signals)
    required = {"signal_time", "signal_day", "candidate_id", "asset", "horizon", "side"}
    missing = required - set(d.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    d["signal_time"] = pd.to_datetime(d["signal_time"])
    d["signal_day"] = pd.to_datetime(d["signal_day"])

    day = d.groupby(["signal_time", "signal_day"], as_index=False).agg(
        long_n=("side", lambda s: int((s == "LONG").sum())),
        short_n=("side", lambda s: int((s == "SHORT").sum())),
        candidate_n=("candidate_id", "nunique"),
    )
    day["net_consensus"] = day.long_n - day.short_n
    day["state"] = [state(a, b) for a, b in zip(day.long_n, day.short_n)]
    day["horizon_breadth"] = d.groupby(["signal_time", "signal_day"]).horizon.nunique().to_numpy()
    day["asset_breadth"] = d.groupby(["signal_time", "signal_day"]).asset.nunique().to_numpy()
    day.to_csv(out / "phase9b_consensus_states.csv", index=False)

    x = d.merge(day[["signal_time", "signal_day", "state", "net_consensus", "horizon_breadth", "asset_breadth"]],
                on=["signal_time", "signal_day"], how="left")
    if "realized_return_R" not in x.columns:
        raise ValueError("Signals must contain realized_return_R; run shadow replay with historical outcomes attached.")
    x["realized_return_R"] = pd.to_numeric(x.realized_return_R, errors="coerce")

    # Candidate outcomes are retained at their native horizon; no cross-horizon
    # return is averaged into a single artificial trading result.
    by = x.groupby(["state", "asset", "horizon", "side"], as_index=False).agg(
        observations=("realized_return_R", lambda s: int(s.notna().sum())),
        mean_R=("realized_return_R", "mean"),
        median_R=("realized_return_R", "median"),
        positive_fraction=("realized_return_R", lambda s: float((s > 0).mean())),
        mean_consensus=("net_consensus", "mean"),
    )
    cis = []
    for _, r in by.iterrows():
        vals = x.loc[
            (x.state == r.state) & (x.asset == r.asset) &
            (x.horizon == r.horizon) & (x.side == r.side),
            "realized_return_R"
        ].dropna().to_numpy()
        lo, hi = bootstrap_mean_ci(vals)
        cis.append((lo, hi))
    by["mean_R_ci95_low"] = [z[0] for z in cis]
    by["mean_R_ci95_high"] = [z[1] for z in cis]
    by.to_csv(out / "phase9b_consensus_outcomes.csv", index=False)

    conflict = x.groupby(["signal_time", "signal_day"]).agg(
        state=("state", "first"),
        long_n=("side", lambda s: int((s == "LONG").sum())),
        short_n=("side", lambda s: int((s == "SHORT").sum())),
        candidates=("candidate_id", "nunique"),
    ).reset_index()
    conflict["conflict"] = conflict.long_n.gt(0) & conflict.short_n.gt(0)
    conflict.to_csv(out / "phase9b_conflict_summary.csv", index=False)

    prov = pd.DataFrame([{
        "taxonomy": "NO_SIGNAL; SINGLE_SIDE; MULTIPLE_SIDE_2_3; MULTIPLE_SIDE_4_PLUS; CONFLICT",
        "threshold_fitting": "NONE",
        "outcome_based_selection": "NONE",
        "cross_horizon_return_pooling": "NONE",
        "purpose": "Descriptive consensus-state analysis of frozen shadow signals.",
    }])
    prov.to_csv(out / "phase9b_provenance.csv", index=False)

    print("=== PHASE 9B CONSENSUS ===")
    print(f"Signal timestamps: {len(day)}")
    print(f"States: {day.state.value_counts().to_dict()}")
    print(by.to_string(index=False))


if __name__ == "__main__":
    main()
