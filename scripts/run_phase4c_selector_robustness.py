"""Phase 4C: robustness/placebo tests for the leakage-safe CPR horizon selector.

Tests whether the Phase 4 selector's OOS result depends on chronological
alignment between each walk-forward split and the horizon chosen from its
training data. The primary placebo permutes selected horizons across splits
within each direction/time bucket, preserving observed selection frequency
but destroying temporal alignment. A lagged-selection diagnostic uses the
previous split's choice as a deliberately stale selector.

No thresholds, horizons, or features are optimized here.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HORIZONS = ("2session", "3session", "5session", "10session")
SEED = 20260918
N_SIMULATIONS = 5000


def daily_mean(df: pd.DataFrame, value_col: str) -> float:
    d = df.groupby("signal_day", as_index=False)[value_col].mean()
    return float(d[value_col].mean()) if len(d) else np.nan


def load_inputs(selected_path: str, events_path: str, selections_path: str):
    selected = pd.read_csv(selected_path, parse_dates=["signal_time", "signal_date", "entry_session", "target_session"])
    events = pd.read_csv(events_path, parse_dates=["signal_time", "signal_date", "entry_session", "target_session"])
    selections = pd.read_csv(selections_path, parse_dates=["train_start", "train_end", "purge_start", "validation_start", "validation_end"])
    selected["signal_day"] = selected.signal_date.dt.normalize()
    events["signal_day"] = events.signal_date.dt.normalize()
    return selected, events, selections


def validate(selected: pd.DataFrame, events: pd.DataFrame, selections: pd.DataFrame) -> None:
    key_cols = ["split", "signal_time", "side", "entry_bucket"]
    keys = selected[key_cols].drop_duplicates()
    assert len(keys) == len(selected), "Selected OOS contains duplicate signal identities"
    assert set(selected.horizon) <= set(HORIZONS)
    assert set(selections.selected_horizon) <= set(HORIZONS)
    assert selections.split.nunique() >= 2, "Need at least two walk-forward splits for temporal placebo"
    base = events.merge(keys, on=["signal_time", "side", "entry_bucket"], how="inner")
    assert len(base) == len(keys) * len(HORIZONS), "Each selected signal must have all candidate horizon outcomes"


def outcome_for_mapping(selected: pd.DataFrame, events: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    q = selected[["split", "signal_time", "side", "entry_bucket", "signal_day"]].merge(
        mapping, on=["split", "side", "entry_bucket"], how="inner"
    )
    q = q.merge(
        events[["signal_time", "side", "entry_bucket", "horizon", "return_R"]],
        left_on=["signal_time", "side", "entry_bucket", "mapped_horizon"],
        right_on=["signal_time", "side", "entry_bucket", "horizon"],
        how="inner",
    )
    assert len(q) == len(selected), "Mapping must resolve one outcome per selected signal"
    return q.rename(columns={"return_R": "mapped_R"})


def actual_mapping(selections: pd.DataFrame) -> pd.DataFrame:
    return selections[["split", "side", "entry_bucket", "selected_horizon"]].rename(
        columns={"selected_horizon": "mapped_horizon"}
    )


def split_summary(selected: pd.DataFrame) -> pd.DataFrame:
    d = selected.groupby(["split", "signal_day"], as_index=False).return_R.mean()
    return d.groupby("split", as_index=False).agg(signal_days=("signal_day", "nunique"), mean_R=("return_R", "mean"))


def fixed_horizon_summary(selected: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    # Do not merge signal_day from selected because events already carries its
    # own signal_day; retaining both would create signal_day_x/signal_day_y.
    keys = selected[["signal_time", "side", "entry_bucket"]].drop_duplicates()
    base = events.merge(keys, on=["signal_time", "side", "entry_bucket"], how="inner")
    rows = []
    for h in HORIZONS:
        q = base[base.horizon == h]
        rows.append({"horizon": h, "mean_R": daily_mean(q, "return_R"), "signals": len(q), "signal_days": q.signal_day.nunique()})
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--selected", required=True)
    p.add_argument("--events", required=True)
    p.add_argument("--selections", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--simulations", type=int, default=N_SIMULATIONS)
    a = p.parse_args()

    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    selected, events, selections = load_inputs(a.selected, a.events, a.selections)
    validate(selected, events, selections)

    actual = outcome_for_mapping(selected, events, actual_mapping(selections))
    actual_mean = daily_mean(actual, "mapped_R")

    ss = split_summary(selected)
    ss["actual_selected"] = True
    ss.to_csv(out / "phase4c_split_stability.csv", index=False)

    fixed = fixed_horizon_summary(selected, events)
    fixed.to_csv(out / "phase4c_fixed_horizon_reference.csv", index=False)

    # Primary temporal placebo: permute the chosen horizon across walk-forward
    # splits independently within each side/bucket cell. This preserves the
    # observed horizon counts in every cell while destroying temporal alignment.
    cells = selections[["split", "side", "entry_bucket", "selected_horizon"]].copy()
    rng = np.random.default_rng(SEED)
    placebo_means = np.empty(a.simulations)
    for i in range(a.simulations):
        rows = []
        for (side, bucket), g in cells.groupby(["side", "entry_bucket"], sort=True):
            g = g.sort_values("split").reset_index(drop=True)
            horizons = g.selected_horizon.to_numpy(copy=True)
            rng.shuffle(horizons)
            x = g[["split", "side", "entry_bucket"]].copy()
            x["mapped_horizon"] = horizons
            rows.append(x)
        mapping = pd.concat(rows, ignore_index=True)
        q = outcome_for_mapping(selected, events, mapping)
        placebo_means[i] = daily_mean(q, "mapped_R")

    placebo_mean = float(placebo_means.mean())
    placebo_sd = float(placebo_means.std(ddof=1))
    q025, q975 = np.quantile(placebo_means, [0.025, 0.975])
    empirical_p = float((np.abs(placebo_means - placebo_mean) >= abs(actual_mean - placebo_mean)).mean())
    placebo_summary = pd.DataFrame([{
        "actual_selected_mean_R": actual_mean,
        "temporal_placebo_mean_R": placebo_mean,
        "temporal_placebo_sd_R": placebo_sd,
        "placebo_q025_R": q025,
        "placebo_q975_R": q975,
        "actual_minus_placebo_R": actual_mean - placebo_mean,
        "empirical_two_sided_p": empirical_p,
        "simulations": a.simulations,
        "seed": SEED,
        "placebo_definition": "permute selected horizon across walk-forward splits within side/entry_bucket",
    }])
    placebo_summary.to_csv(out / "phase4c_temporal_placebo.csv", index=False)
    pd.DataFrame({"simulation": np.arange(a.simulations), "placebo_mean_R": placebo_means}).to_csv(out / "phase4c_temporal_placebo_distribution.csv", index=False)

    stale = cells.sort_values(["side", "entry_bucket", "split"]).copy()
    stale["mapped_horizon"] = stale.groupby(["side", "entry_bucket"]).selected_horizon.shift(1)
    stale = stale.dropna(subset=["mapped_horizon"])
    stale_selected = selected[selected.split.isin(stale.split)]
    stale_q = outcome_for_mapping(stale_selected, events, stale[["split", "side", "entry_bucket", "mapped_horizon"]])
    stale_mean = daily_mean(stale_q, "mapped_R")
    pd.DataFrame([{
        "actual_selected_mean_R": actual_mean,
        "lagged_selection_mean_R": stale_mean,
        "difference_R": actual_mean - stale_mean,
        "lagged_signals": len(stale_q),
        "lagged_signal_days": stale_q.signal_day.nunique(),
    }]).to_csv(out / "phase4c_lagged_selection.csv", index=False)

    g = actual.groupby(["side", "entry_bucket"], as_index=False).agg(
        signals=("mapped_R", "size"), mean_R=("mapped_R", "mean"),
        median_R=("mapped_R", "median"), win_rate=("mapped_R", lambda x: float((x > 0).mean()))
    )
    g.to_csv(out / "phase4c_direction_bucket.csv", index=False)

    print("=== PHASE 4C TEMPORAL PLACEBO ===")
    print(placebo_summary.to_string(index=False))
    print("\n=== PHASE 4C SPLIT STABILITY ===")
    print(ss.to_string(index=False))
    print("\n=== PHASE 4C FIXED-HORIZON REFERENCE ===")
    print(fixed.to_string(index=False))
    print("\n=== PHASE 4C LAGGED SELECTION ===")
    print(pd.read_csv(out / "phase4c_lagged_selection.csv").to_string(index=False))
    print("\n=== PHASE 4C DIRECTION / TIME BUCKET ===")
    print(g.to_string(index=False))


if __name__ == "__main__":
    main()
