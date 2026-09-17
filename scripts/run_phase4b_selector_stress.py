"""Phase 4B: stress-test the Phase 4 horizon selector against null selection.

The stress test preserves the exact Phase 4 OOS signal identities and split
structure. It destroys the relationship between training-selected horizon and
OOS outcome by assigning a random candidate horizon within each walk-forward
split/side/time-bucket cell. No validation outcomes are used to choose the
random horizon. A fixed seed makes the null reproducible.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

HORIZONS = ("2session", "3session", "5session", "10session")
SEED = 20260918
N_SIMULATIONS = 5000
BLOCKS = 10


def daily_mean(df: pd.DataFrame, value_col: str = "return_R") -> float:
    d = df.groupby("signal_day", as_index=False)[value_col].mean()
    return float(d[value_col].mean())


def block_bootstrap_mean(diff: np.ndarray, rng: np.random.Generator, n_boot: int = 5000) -> tuple[float, float]:
    if len(diff) < 2:
        return np.nan, np.nan
    n_blocks = int(np.ceil(len(diff) / BLOCKS))
    blocks = [diff[i : i + BLOCKS] for i in range(0, len(diff), BLOCKS)]
    means = np.empty(n_boot)
    for i in range(n_boot):
        sample = np.concatenate([blocks[j] for j in rng.integers(0, len(blocks), size=n_blocks)])[: len(diff)]
        means[i] = sample.mean()
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


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

    selected = pd.read_csv(a.selected, parse_dates=["signal_time", "signal_date", "entry_session", "target_session"])
    events = pd.read_csv(a.events, parse_dates=["signal_time", "signal_date", "entry_session", "target_session"])
    selections = pd.read_csv(a.selections, parse_dates=["train_start", "train_end", "purge_start", "validation_start", "validation_end"])
    selected["signal_day"] = selected.signal_date.dt.normalize()
    events["signal_day"] = events.signal_date.dt.normalize()

    keys = selected[["split", "signal_time", "side", "entry_bucket"]].drop_duplicates()
    assert len(keys) == len(selected), "Selected OOS contains duplicate signal identities"
    base = events.merge(keys, on=["signal_time", "side", "entry_bucket"], how="inner", suffixes=("", "_key"))
    assert len(base) == len(keys) * len(HORIZONS), "Each selected signal must have all four horizon outcomes"

    chosen = selected[["split", "signal_time", "side", "entry_bucket", "horizon", "return_R", "signal_day"]].copy()
    actual = chosen.rename(columns={"horizon": "selected_horizon", "return_R": "selected_R"})
    actual_for_mean = actual.rename(columns={"selected_R": "return_R"})
    actual_mean = daily_mean(actual_for_mean)

    fixed_rows = []
    for h in HORIZONS:
        q = base[base.horizon == h].copy()
        fixed_rows.append((h, q))

    rng = np.random.default_rng(SEED)
    sim_means = np.empty(a.simulations)
    sim_diffs = np.empty(a.simulations)
    cells = selections[["split", "side", "entry_bucket"]].drop_duplicates().sort_values(["split", "side", "entry_bucket"])
    for i in range(a.simulations):
        assignments = cells.copy()
        assignments["null_horizon"] = rng.choice(HORIZONS, size=len(assignments), replace=True)
        q = base.merge(assignments, on=["split", "side", "entry_bucket"], how="inner")
        q = q[q.horizon == q.null_horizon]
        sim_means[i] = daily_mean(q)
        sim_diffs[i] = actual_mean - sim_means[i]

    null_mean = float(sim_means.mean())
    null_sd = float(sim_means.std(ddof=1))
    null_q025, null_q975 = np.quantile(sim_means, [0.025, 0.975])
    empirical_p = float((np.abs(sim_means - null_mean) >= abs(actual_mean - null_mean)).mean())

    null_summary = pd.DataFrame([{
        "actual_selected_mean_R": actual_mean,
        "null_mean_R": null_mean,
        "null_sd_R": null_sd,
        "null_q025_R": null_q025,
        "null_q975_R": null_q975,
        "actual_minus_null_R": actual_mean - null_mean,
        "empirical_two_sided_p": empirical_p,
        "simulations": a.simulations,
        "seed": SEED,
    }])
    null_summary.to_csv(out / "phase4b_random_horizon_null.csv", index=False)
    pd.DataFrame({"simulation": np.arange(a.simulations), "null_mean_R": sim_means, "selected_minus_null_R": sim_diffs}).to_csv(out / "phase4b_null_distribution.csv", index=False)

    paired_rows = []
    for h, q in fixed_rows:
        fixed = q.groupby("signal_day", as_index=False)["return_R"].mean().rename(columns={"return_R": "fixed_R"})
        sel = actual.groupby("signal_day", as_index=False)["selected_R"].mean()
        m = sel.merge(fixed, on="signal_day", how="inner")
        diff = (m.selected_R - m.fixed_R).to_numpy()
        ci_lo, ci_hi = block_bootstrap_mean(diff, rng)
        paired_rows.append({
            "comparison": f"SELECTED_vs_{h}",
            "signal_days": len(m),
            "mean_difference_R": float(diff.mean()),
            "median_difference_R": float(np.median(diff)),
            "win_day_rate": float((diff > 0).mean()),
            "block_bootstrap_ci95_low": ci_lo,
            "block_bootstrap_ci95_high": ci_hi,
        })
    pd.DataFrame(paired_rows).to_csv(out / "phase4b_paired_bootstrap.csv", index=False)

    concentration = selections.groupby("selected_horizon").size().reindex(HORIZONS, fill_value=0).reset_index(name="selection_cells")
    concentration["fraction"] = concentration.selection_cells / concentration.selection_cells.sum()
    concentration.to_csv(out / "phase4b_selection_concentration.csv", index=False)

    print("=== PHASE 4B RANDOM-HORIZON NULL ===")
    print(null_summary.to_string(index=False))
    print("\n=== PHASE 4B PAIRED BLOCK-BOOTSTRAP ===")
    print(pd.DataFrame(paired_rows).to_string(index=False))
    print("\n=== SELECTION CONCENTRATION ===")
    print(concentration.to_string(index=False))


if __name__ == "__main__":
    main()
