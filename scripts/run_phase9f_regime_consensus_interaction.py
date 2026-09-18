"""Phase 9F: frozen regime x consensus interaction study.

Purpose
-------
Test whether the fixed Phase 9B consensus taxonomy behaves differently across
the already-discovered/frozen Phase 5A regime leaves.

Strict OOS rules
----------------
* Phase 5A frontier is recreated from the reference/training data only.
* The Phase 5A tree structure is reconstructed deterministically from the same
  frozen reference data and never refit on Phase 7 or 2026.
* Phase 7 is independent replication; 2026 is an untouched forward evaluation.
* No regime, horizon, side, consensus state, or strategy is selected using 2026.
* All eligible regime x consensus cells are reported; no "winner" is chosen.

The central estimand is the incremental effect of MULTIPLE (>=2 same-side
frozen candidates) versus SINGLE (exactly 1) within each frozen regime leaf.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from sklearn.tree import DecisionTreeClassifier

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from cpr_lab.strategies import StrategyConfig, intraday_directional_signals
from run_cpr_regime_discovery import (
    FEATURES, MIN_LEAF, MAX_DEPTH, SEED, make_context,
    build_intraday_events, build_swing_events, split_label,
)
from run_phase9_shadow_engine import matches

FRONTIER_SHA256 = "601a72f5e64204aee7ff0bb77347d57b0e2b59871b8bc30011282c2dc02c28b2"
LONG_STATES = {"SINGLE_LONG", "MULTIPLE_LONG_2_3", "MULTIPLE_LONG_4_PLUS"}
SHORT_STATES = {"SINGLE_SHORT", "MULTIPLE_SHORT_2_3", "MULTIPLE_SHORT_4_PLUS"}
MULTI_LONG = {"MULTIPLE_LONG_2_3", "MULTIPLE_LONG_4_PLUS"}
MULTI_SHORT = {"MULTIPLE_SHORT_2_3", "MULTIPLE_SHORT_4_PLUS"}

def state(long_n: int, short_n: int) -> str:
    if long_n == 0 and short_n == 0:
        return "NO_SIGNAL"
    if long_n and short_n:
        return "CONFLICT"
    n = max(long_n, short_n)
    side = "LONG" if long_n else "SHORT"
    if n == 1:
        return f"SINGLE_{side}"
    if n <= 3:
        return f"MULTIPLE_{side}_2_3"
    return f"MULTIPLE_{side}_4_PLUS"

def bootstrap_diff(a: np.ndarray, b: np.ndarray, reps: int = 4000, seed: int = SEED):
    a = np.asarray(a, float); b = np.asarray(b, float)
    a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for i in range(reps):
        vals[i] = rng.choice(a, len(a), replace=True).mean() - rng.choice(b, len(b), replace=True).mean()
    return float(np.quantile(vals, .025)), float(np.quantile(vals, .975))

def bootstrap_mean(x: np.ndarray, reps: int = 4000, seed: int = SEED):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for i in range(reps):
        vals[i] = rng.choice(x, len(x), replace=True).mean()
    return float(np.quantile(vals, .025)), float(np.quantile(vals, .975))

def bh(p):
    p = np.asarray(p, float)
    out = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    pv = p[ok]
    if not len(pv):
        return out
    order = np.argsort(pv)
    ranked = pv[order]
    q = np.minimum.accumulate((ranked * len(pv) / np.arange(1, len(pv)+1))[::-1])[::-1]
    tmp = np.empty(len(pv)); tmp[order] = np.minimum(q, 1.0)
    out[ok] = tmp
    return out

def make_events(bars):
    daily = bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    x = add_intraday_daily_features(bars, daily_reference_features(daily))
    ctx = make_context(bars).reindex(x.index)
    return {
        "intraday": build_intraday_events(x, ctx),
        "swing": build_swing_events(x, ctx),
    }

def build_frozen_trees(reference_bars, frontier):
    """Rebuild exactly the deterministic Phase 5A trees from reference data."""
    events = make_events(reference_bars)
    trees = {}
    for asset, ev in events.items():
        if ev.empty:
            continue
        ev = ev.copy()
        ev["split"] = ev.signal_day.map(split_label)
        horizons = sorted(ev.horizon.dropna().unique())
        for horizon in horizons:
            for side in ("LONG", "SHORT"):
                z = ev[(ev.horizon == horizon) & (ev.side == side)].dropna(subset=FEATURES + ["return_R"]).copy()
                tr = z[z.split == "TRAIN"]
                if len(tr) < MAX_DEPTH * MIN_LEAF * 2:
                    continue
                tree = DecisionTreeClassifier(
                    max_depth=MAX_DEPTH, min_samples_leaf=MIN_LEAF,
                    random_state=SEED, criterion="gini"
                )
                tree.fit(tr[FEATURES], (tr.return_R > 0).astype(int))
                trees[(asset, horizon, side)] = tree
    return trees

def assign_regimes(events, trees, frontier):
    frontier_keys = {}
    for (asset, horizon, side), g in frontier.groupby(["asset","horizon","side"]):
        frontier_keys[(asset,horizon,side)] = set(g.leaf.astype(int))
    out = []
    for asset, ev in events.items():
        if ev.empty:
            continue
        for (horizon, side), q in ev.groupby(["horizon","side"]):
            key = (asset, horizon, side)
            q = q.copy()
            tree = trees.get(key)
            allowed = frontier_keys.get(key, set())
            if tree is None:
                q["regime_leaf"] = np.nan
                q["regime"] = "NO_FROZEN_TREE"
            else:
                leaves = tree.apply(q[FEATURES])
                q["regime_leaf"] = leaves.astype(int)
                q["regime"] = [
                    f"LEAF_{int(v)}" if int(v) in allowed else "OTHER_FROZEN_TREE_LEAF"
                    for v in leaves
                ]
            out.append(q)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()

def add_consensus(events, frontier):
    rows = []
    for dataset, ev in events.items():
        if ev.empty:
            continue
        for ts, g in ev.groupby("signal_time"):
            # Same frozen context is shared by all horizons generated by the signal.
            c = g.iloc[0]
            activated = [
                cand for _, cand in frontier.iterrows()
                if cand.asset == c.asset and matches(c, cand.rule)
            ]
            ln = sum(cand.side == "LONG" for cand in activated)
            sn = sum(cand.side == "SHORT" for cand in activated)
            st = state(ln, sn)
            gg = g.copy()
            gg["long_n"] = ln; gg["short_n"] = sn; gg["consensus_state"] = st
            gg["outcome_positive"] = gg["return_R"] > 0
            gg["dataset"] = dataset
            rows.append(gg)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--p7", required=True)
    ap.add_argument("--p8", required=True)
    ap.add_argument("--frontier", required=True)
    ap.add_argument("--output-dir", required=True)
    a = ap.parse_args()
    out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True)

    frontier_path = Path(a.frontier)
    digest = hashlib.sha256(frontier_path.read_bytes()).hexdigest()
    if digest != FRONTIER_SHA256:
        raise ValueError(f"Frozen frontier hash mismatch: {digest}")

    frontier = pd.read_csv(frontier_path)
    if len(frontier) != 39:
        raise ValueError(f"Expected 39 frozen candidates, found {len(frontier)}")

    ref = load_ohlcv_csv(a.reference)
    trees = build_frozen_trees(ref, frontier)

    datasets = {}
    for name, path in [("PHASE7_INDEPENDENT", a.p7), ("PHASE8_UNTOUCHED_2026", a.p8)]:
        ev = make_events(load_ohlcv_csv(path))
        pop = add_consensus(ev, frontier)
        pop = assign_regimes({"all": pop}, trees, frontier) if False else pop
        # assign_regimes expects per-asset events; preserve asset labels explicitly.
        per_asset = {}
        for asset, q in pop.groupby("asset"):
            per_asset[asset] = q.copy()
        # Trees are keyed by asset and horizon/side; assign directly.
        reg_parts = []
        for asset, q in per_asset.items():
            for (horizon, side), z in q.groupby(["horizon","side"]):
                z = z.copy()
                tree = trees.get((asset, horizon, side))
                allowed = set(frontier[
                    (frontier.asset == asset) &
                    (frontier.horizon == horizon) &
                    (frontier.side == side)
                ].leaf.astype(int))
                if tree is None:
                    z["regime_leaf"] = np.nan
                    z["regime"] = "NO_FROZEN_TREE"
                else:
                    leaves = tree.apply(z[FEATURES])
                    z["regime_leaf"] = leaves.astype(int)
                    z["regime"] = [
                        f"LEAF_{int(v)}" if int(v) in allowed else "OTHER_FROZEN_TREE_LEAF"
                        for v in leaves
                    ]
                reg_parts.append(z)
        datasets[name] = pd.concat(reg_parts, ignore_index=True)

    d = pd.concat(datasets.values(), ignore_index=True)
    d.to_csv(out / "phase9f_population.csv", index=False)

    # State-conditioned cells, retained without selecting winners.
    cells = []
    for (dataset, asset, horizon, side, regime, st), q in d.groupby(
        ["dataset","asset","horizon","side","regime","consensus_state"]
    ):
        lo, hi = bootstrap_mean(q.outcome_positive.to_numpy(float))
        rlo, rhi = bootstrap_mean(q.return_R.to_numpy(float))
        cells.append({
            "dataset": dataset, "asset": asset, "horizon": horizon, "side": side,
            "regime": regime, "consensus_state": st, "n": len(q),
            "win_rate": q.outcome_positive.mean(),
            "win_rate_ci95_low": lo, "win_rate_ci95_high": hi,
            "mean_R": q.return_R.mean(),
            "mean_R_ci95_low": rlo, "mean_R_ci95_high": rhi,
        })
    pd.DataFrame(cells).to_csv(out / "phase9f_regime_consensus_cells.csv", index=False)

    # Primary incremental test: MULTIPLE vs SINGLE within each frozen regime.
    tests = []
    for (dataset, asset, horizon, side, regime), q in d.groupby(
        ["dataset","asset","horizon","side","regime"]
    ):
        single_name = "SINGLE_LONG" if side == "LONG" else "SINGLE_SHORT"
        multi_names = MULTI_LONG if side == "LONG" else MULTI_SHORT
        single = q[q.consensus_state == single_name]
        multi = q[q.consensus_state.isin(multi_names)]
        if len(single) < 5 or len(multi) < 5:
            continue
        a1 = int(single.outcome_positive.sum()); b1 = len(single) - a1
        a2 = int(multi.outcome_positive.sum()); b2 = len(multi) - a2
        _, p = fisher_exact([[a1,b1],[a2,b2]], alternative="two-sided")
        dw = float(multi.outcome_positive.mean() - single.outcome_positive.mean())
        dwlo, dwhi = bootstrap_diff(
            multi.outcome_positive.to_numpy(float),
            single.outcome_positive.to_numpy(float)
        )
        dr = float(multi.return_R.mean() - single.return_R.mean())
        drlo, drhi = bootstrap_diff(
            multi.return_R.to_numpy(float),
            single.return_R.to_numpy(float)
        )
        tests.append({
            "dataset": dataset, "asset": asset, "horizon": horizon, "side": side,
            "regime": regime, "single_n": len(single), "multiple_n": len(multi),
            "single_win_rate": single.outcome_positive.mean(),
            "multiple_win_rate": multi.outcome_positive.mean(),
            "delta_win_rate_multiple_minus_single": dw,
            "delta_win_rate_ci95_low": dwlo, "delta_win_rate_ci95_high": dwhi,
            "single_mean_R": single.return_R.mean(),
            "multiple_mean_R": multi.return_R.mean(),
            "delta_mean_R_multiple_minus_single": dr,
            "delta_mean_R_ci95_low": drlo, "delta_mean_R_ci95_high": drhi,
            "fisher_p": float(p),
        })
    tests_df = pd.DataFrame(tests)
    if not tests_df.empty:
        tests_df["fdr_q"] = bh(tests_df.fisher_p.to_numpy())
    tests_df.to_csv(out / "phase9f_interaction_tests.csv", index=False)

    # Temporal stability: report every year with enough observations; do not select.
    yearly = []
    for (dataset, year, asset, horizon, side, regime), q in d.assign(
        year=pd.to_datetime(d.signal_day).dt.year
    ).groupby(["dataset","year","asset","horizon","side","regime"]):
        for st_name, z in q.groupby("consensus_state"):
            if len(z) < 5:
                continue
            yearly.append({
                "dataset": dataset, "year": int(year), "asset": asset,
                "horizon": horizon, "side": side, "regime": regime,
                "consensus_state": st_name, "n": len(z),
                "win_rate": z.outcome_positive.mean(),
                "mean_R": z.return_R.mean(),
            })
    pd.DataFrame(yearly).to_csv(out / "phase9f_yearly_stability.csv", index=False)

    pd.DataFrame([{
        "protocol": "Phase 9F frozen regime x consensus interaction",
        "frozen_frontier_sha256": digest,
        "frozen_candidate_count": len(frontier),
        "regime_definition": "Phase 5A deterministic tree leaves reconstructed from reference TRAIN only; only frozen Pareto leaves are named, all others retained as OTHER",
        "consensus_definition": "Fixed Phase 9B taxonomy from frozen candidate activations",
        "primary_estimand": "MULTIPLE (>=2 same-side candidates) minus SINGLE (1 same-side candidate) within each frozen regime",
        "minimum_group_n_for_interaction_test": 5,
        "inference": "two-sided Fisher exact; bootstrap 95% CIs; BH FDR q-values",
        "phase7_role": "independent replication",
        "phase8_role": "untouched 2026 forward evaluation",
        "threshold_refitting": "NONE on Phase 7 or 2026",
        "candidate_selection": "NONE on Phase 7 or 2026",
        "strategy_selection": "NONE",
    }]).to_csv(out / "phase9f_provenance.csv", index=False)

    print("=== PHASE 9F COMPLETE ===")
    print("Population:", len(d))
    print("Interaction tests:", len(tests_df))
    if not tests_df.empty:
        print(tests_df.to_string(index=False))
    print("\nCell counts by dataset:")
    print(d.groupby(["dataset","regime","consensus_state"]).size().to_string())

if __name__ == "__main__":
    main()
