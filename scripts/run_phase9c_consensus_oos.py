"""Phase 9C: frozen consensus taxonomy validation on Phase 7 and Phase 8 data."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd


def stable_seed(key: str, base: int = 20260918) -> int:
    """Return a process-independent 32-bit seed derived from a group key."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return (base + int.from_bytes(digest[:4], "big")) % (2**32)


def bootstrap_ci(x, reps=3000, seed=20260918):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), (reps, len(x)))].mean(axis=1)
    return float(np.quantile(means, .025)), float(np.quantile(means, .975))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p7", required=True)
    ap.add_argument("--p8", required=True)
    ap.add_argument("--output-dir", required=True)
    a = ap.parse_args()
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    frames = []
    for label, path in [("PHASE7_INDEPENDENT", a.p7), ("PHASE8_UNTOUCHED_2026", a.p8)]:
        d = pd.read_csv(path)
        req = {"signal_time", "signal_day", "candidate_id", "asset", "horizon", "side", "realized_return_R"}
        if req - set(d.columns):
            raise ValueError(f"{label} missing {sorted(req - set(d.columns))}")
        d["dataset"] = label
        d["signal_time"] = pd.to_datetime(d.signal_time)
        d["signal_day"] = pd.to_datetime(d.signal_day)
        frames.append(d)

    d = pd.concat(frames, ignore_index=True)

    # Recreate the exact fixed taxonomy from Phase 9B; no threshold is fitted here.
    g = d.groupby(["dataset", "signal_time", "signal_day"], as_index=False).agg(
        long_n=("side", lambda s: int((s == "LONG").sum())),
        short_n=("side", lambda s: int((s == "SHORT").sum())),
    )

    def st(a, b):
        if a == 0 and b == 0:
            return "NO_SIGNAL"
        if a and b:
            return "CONFLICT"
        n = max(a, b)
        side = "LONG" if a else "SHORT"
        return f"SINGLE_{side}" if n == 1 else f"MULTIPLE_{side}_2_3" if n <= 3 else f"MULTIPLE_{side}_4_PLUS"

    g["state"] = [st(a, b) for a, b in zip(g.long_n, g.short_n)]
    d = d.merge(
        g[["dataset", "signal_time", "signal_day", "state"]],
        on=["dataset", "signal_time", "signal_day"],
        how="left",
    )

    rows = []
    for (dataset, state, asset, horizon, side), q in d.groupby(
        ["dataset", "state", "asset", "horizon", "side"]
    ):
        x = q.realized_return_R.dropna().to_numpy()
        key = "|".join([str(dataset), str(state), str(asset), str(horizon), str(side)])
        lo, hi = bootstrap_ci(x, seed=stable_seed(key))
        rows.append(
            dict(
                dataset=dataset,
                state=state,
                asset=asset,
                horizon=horizon,
                side=side,
                observations=len(x),
                mean_R=float(np.mean(x)) if len(x) else np.nan,
                median_R=float(np.median(x)) if len(x) else np.nan,
                positive_fraction=float(np.mean(x > 0)) if len(x) else np.nan,
                mean_R_ci95_low=lo,
                mean_R_ci95_high=hi,
            )
        )

    result = pd.DataFrame(rows)
    result.to_csv(out / "phase9c_consensus_oos_results.csv", index=False)

    counts = g.groupby(["dataset", "state"]).size().reset_index(name="signal_timestamps")
    counts.to_csv(out / "phase9c_consensus_state_counts.csv", index=False)

    wide = result.pivot_table(
        index=["state", "asset", "horizon", "side"],
        columns="dataset",
        values="mean_R",
    )
    if "PHASE7_INDEPENDENT" in wide and "PHASE8_UNTOUCHED_2026" in wide:
        wide = wide.reset_index()
        wide["same_sign"] = np.sign(wide.PHASE7_INDEPENDENT) == np.sign(wide.PHASE8_UNTOUCHED_2026)
        wide.to_csv(out / "phase9c_cross_dataset_sign_consistency.csv", index=False)

    pd.DataFrame(
        [
            {
                "taxonomy": "Fixed Phase 9B taxonomy; no refitting or threshold adjustment.",
                "datasets": "Phase 7 independent replication + Phase 8 untouched 2026 holdout",
                "candidate_selection": "NONE",
                "outcome_based_selection": "NONE",
                "cross_horizon_pooling": "NONE",
                "bootstrap_seed_method": "SHA256-derived process-independent group seed",
            }
        ]
    ).to_csv(out / "phase9c_provenance.csv", index=False)

    print("=== PHASE 9C ===")
    print(counts.to_string(index=False))
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
