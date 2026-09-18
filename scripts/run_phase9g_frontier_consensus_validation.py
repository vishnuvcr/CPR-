"""Phase 9G: frozen frontier-regime-only consensus validation.

Purpose
-------
The successful Phase 9F analysis found some dataset-specific interaction
signals, but several arose inside heterogeneous OTHER_FROZEN_TREE_LEAF
observations. Phase 9G repeats the interaction analysis using ONLY the named
frozen Phase 5A Pareto frontier leaves.

No threshold refitting, candidate selection, horizon selection, regime
selection, or strategy selection is performed.

Primary comparison:
  MULTIPLE (>=2 matching-side frozen candidates) vs SINGLE (1 matching-side)
  within each named frozen frontier regime.

For each dataset we report:
  * regime-stratified cell effects;
  * Fisher exact p-values + BH FDR;
  * bootstrap CIs for win-rate and mean-R differences;
  * a Cochran-Mantel-Haenszel (CMH) association test stratified by frontier
    regime for each native horizon/side;
  * year-by-year stability;
  * direct Phase 7 vs untouched-2026 effect-size replication table.

2026 remains a forward validation set. No statistic from 2026 is used to choose
a regime, horizon, side, or rule.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from statsmodels.stats.contingency_tables import StratifiedTable
from sklearn.tree import DecisionTreeClassifier

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from run_cpr_regime_discovery import (
    FEATURES, MIN_LEAF, MAX_DEPTH, SEED, make_context,
    build_intraday_events, build_swing_events, split_label,
)
from run_phase9_shadow_engine import matches

FRONTIER_SHA256 = "601a72f5e64204aee7ff0bb77347d57b0e2b59871b8bc30011282c2dc02c28b2"
MULTI_LONG = {"MULTIPLE_LONG_2_3", "MULTIPLE_LONG_4_PLUS"}
MULTI_SHORT = {"MULTIPLE_SHORT_2_3", "MULTIPLE_SHORT_4_PLUS"}

def consensus_state(long_n: int, short_n: int) -> str:
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

def bootstrap_diff(a, b, reps=4000, seed=SEED):
    a = np.asarray(a, float); b = np.asarray(b, float)
    a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for i in range(reps):
        vals[i] = rng.choice(a, len(a), replace=True).mean() - rng.choice(b, len(b), replace=True).mean()
    return float(np.quantile(vals, .025)), float(np.quantile(vals, .975))

def bootstrap_mean(x, reps=4000, seed=SEED):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan, np.nan
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
    order = np.argsort(pv); ranked = pv[order]
    q = np.minimum.accumulate((ranked * len(pv) / np.arange(1, len(pv)+1))[::-1])[::-1]
    tmp = np.empty(len(pv)); tmp[order] = np.minimum(q, 1.0)
    out[ok] = tmp
    return out

def make_events(bars):
    daily = bars.resample("1D").agg({
        "open":"first","high":"max","low":"min","close":"last","volume":"sum"
    }).dropna()
    x = add_intraday_daily_features(bars, daily_reference_features(daily))
    ctx = make_context(bars).reindex(x.index)
    intr = build_intraday_events(x, ctx)
    swing = build_swing_events(x, ctx)
    if not intr.empty:
        intr["asset"] = "intraday"
    if not swing.empty:
        swing["asset"] = "swing"
    return {"intraday": intr, "swing": swing}

def frozen_trees(reference_bars):
    events = make_events(reference_bars)
    trees = {}
    for asset, ev in events.items():
        if ev.empty:
            continue
        ev = ev.copy()
        ev["split"] = ev.signal_day.map(split_label)
        for horizon in sorted(ev.horizon.dropna().unique()):
            for side in ("LONG","SHORT"):
                z = ev[(ev.horizon == horizon) & (ev.side == side)].dropna(subset=FEATURES+["return_R"])
                tr = z[z.split == "TRAIN"]
                if len(tr) < MAX_DEPTH * MIN_LEAF * 2:
                    continue
                tree = DecisionTreeClassifier(
                    max_depth=MAX_DEPTH, min_samples_leaf=MIN_LEAF,
                    random_state=SEED, criterion="gini"
                )
                tree.fit(tr[FEATURES], (tr.return_R > 0).astype(int))
                trees[(asset,horizon,side)] = tree
    return trees

def add_consensus(events, frontier, dataset_label):
    records = frontier.to_dict("records")
    parts = []
    for asset, ev in events.items():
        if ev.empty:
            continue
        candidate_records = [r for r in records if r["asset"] == asset]
        for ts, g in ev.groupby("signal_time"):
            c = g.iloc[0]
            activated = [r for r in candidate_records if matches(c, r["rule"])]
            ln = sum(r["side"] == "LONG" for r in activated)
            sn = sum(r["side"] == "SHORT" for r in activated)
            st = consensus_state(ln, sn)
            z = g.copy()
            z["long_n"] = ln
            z["short_n"] = sn
            z["consensus_state"] = st
            z["outcome_positive"] = z["return_R"] > 0
            z["dataset"] = dataset_label
            parts.append(z)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

def assign_frontier_regime(pop, trees, frontier):
    parts = []
    for (asset,horizon,side), q in pop.groupby(["asset","horizon","side"]):
        q = q.copy()
        tree = trees.get((asset,horizon,side))
        allowed = set(frontier[
            (frontier.asset == asset) &
            (frontier.horizon == horizon) &
            (frontier.side == side)
        ].leaf.astype(int))
        if tree is None:
            continue
        leaves = tree.apply(q[FEATURES]).astype(int)
        q["regime_leaf"] = leaves
        q = q[leaves.isin(allowed)].copy()
        q["regime"] = [f"LEAF_{int(v)}" for v in q.regime_leaf]
        if not q.empty:
            parts.append(q)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--p7", required=True)
    ap.add_argument("--p8", required=True)
    ap.add_argument("--frontier", required=True)
    ap.add_argument("--output-dir", required=True)
    a = ap.parse_args()
    out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256(Path(a.frontier).read_bytes()).hexdigest()
    if digest != FRONTIER_SHA256:
        raise ValueError(f"Frozen frontier hash mismatch: {digest}")
    frontier = pd.read_csv(a.frontier)
    if len(frontier) != 39:
        raise ValueError(f"Expected 39 frozen candidates, found {len(frontier)}")

    trees = frozen_trees(load_ohlcv_csv(a.reference))
    datasets = {}
    for name, path in [
        ("PHASE7_INDEPENDENT", a.p7),
        ("PHASE8_UNTOUCHED_2026", a.p8),
    ]:
        pop = add_consensus(make_events(load_ohlcv_csv(path)), frontier, name)
        if pop.empty:
            raise ValueError(f"{name}: empty population after consensus construction")
        pop = assign_frontier_regime(pop, trees, frontier)
        if pop.empty:
            raise ValueError(f"{name}: no events mapped to named frozen frontier leaves")
        datasets[name] = pop

    d = pd.concat(datasets.values(), ignore_index=True)
    expected = {"PHASE7_INDEPENDENT","PHASE8_UNTOUCHED_2026"}
    if set(d.dataset.unique()) != expected:
        raise ValueError(f"Dataset labels corrupted: {sorted(d.dataset.unique())}")
    d.to_csv(out/"phase9g_population_frontier_only.csv", index=False)

    cell_rows = []
    test_rows = []
    for (dataset,asset,horizon,side,regime), q in d.groupby(
        ["dataset","asset","horizon","side","regime"]
    ):
        single_name = "SINGLE_LONG" if side == "LONG" else "SINGLE_SHORT"
        multi_names = MULTI_LONG if side == "LONG" else MULTI_SHORT
        single = q[q.consensus_state == single_name]
        multi = q[q.consensus_state.isin(multi_names)]

        for st, z in q.groupby("consensus_state"):
            lo, hi = bootstrap_mean(z.outcome_positive.to_numpy(float))
            rlo, rhi = bootstrap_mean(z.return_R.to_numpy(float))
            cell_rows.append({
                "dataset":dataset,"asset":asset,"horizon":horizon,"side":side,
                "regime":regime,"consensus_state":st,"n":len(z),
                "win_rate":z.outcome_positive.mean(),
                "win_rate_ci95_low":lo,"win_rate_ci95_high":hi,
                "mean_R":z.return_R.mean(),
                "mean_R_ci95_low":rlo,"mean_R_ci95_high":rhi,
            })

        if len(single) >= 5 and len(multi) >= 5:
            a1 = int(single.outcome_positive.sum()); b1 = len(single)-a1
            a2 = int(multi.outcome_positive.sum()); b2 = len(multi)-a2
            _, p = fisher_exact([[a2,b2],[a1,b1]], alternative="two-sided")
            dw = float(multi.outcome_positive.mean()-single.outcome_positive.mean())
            dwlo,dwhi = bootstrap_diff(multi.outcome_positive, single.outcome_positive)
            dr = float(multi.return_R.mean()-single.return_R.mean())
            drlo,drhi = bootstrap_diff(multi.return_R, single.return_R)
            test_rows.append({
                "dataset":dataset,"asset":asset,"horizon":horizon,"side":side,"regime":regime,
                "single_n":len(single),"multiple_n":len(multi),
                "single_win_rate":single.outcome_positive.mean(),
                "multiple_win_rate":multi.outcome_positive.mean(),
                "delta_win_rate":dw,"delta_win_rate_ci95_low":dwlo,"delta_win_rate_ci95_high":dwhi,
                "single_mean_R":single.return_R.mean(),
                "multiple_mean_R":multi.return_R.mean(),
                "delta_mean_R":dr,"delta_mean_R_ci95_low":drlo,"delta_mean_R_ci95_high":drhi,
                "fisher_p":float(p),
            })

    cells = pd.DataFrame(cell_rows)
    tests = pd.DataFrame(test_rows)
    if not tests.empty:
        tests["fdr_q"] = bh(tests.fisher_p.to_numpy())
    tests.to_csv(out/"phase9g_frontier_interaction_tests.csv", index=False)
    cells.to_csv(out/"phase9g_frontier_cells.csv", index=False)

    # Stratified CMH tests: consensus count (MULTIPLE vs SINGLE) vs outcome,
    # conditioning on named frontier regime. One test per dataset x native
    # horizon x side. No result is used for rule selection.
    cmh_rows = []
    eligible = d.copy()
    eligible["consensus_binary"] = np.where(
        eligible.consensus_state.isin(MULTI_LONG | MULTI_SHORT), "MULTIPLE",
        np.where(
            eligible.consensus_state.isin({"SINGLE_LONG","SINGLE_SHORT"}), "SINGLE", None
        )
    )
    eligible = eligible[eligible.consensus_binary.notna()].copy()
    for (dataset,asset,horizon,side), q in eligible.groupby(
        ["dataset","asset","horizon","side"]
    ):
        tables = []
        strata = []
        for regime, z in q.groupby("regime"):
            multi = z[z.consensus_binary == "MULTIPLE"]
            single = z[z.consensus_binary == "SINGLE"]
            if len(multi) < 2 or len(single) < 2:
                continue
            # 2x2: rows = MULTIPLE, SINGLE; columns = positive, non-positive.
            tables.append([
                [int(multi.outcome_positive.sum()), int((~multi.outcome_positive).sum())],
                [int(single.outcome_positive.sum()), int((~single.outcome_positive).sum())],
            ])
            strata.append(regime)
        if len(tables) >= 1:
            arr = np.stack(tables, axis=2)
            st = StratifiedTable(arr)
            test = st.test_null_odds()
            cmh_rows.append({
                "dataset":dataset,"asset":asset,"horizon":horizon,"side":side,
                "strata_used":len(strata),"strata":";".join(strata),
                "cmh_odds_ratio":float(st.oddsratio_pooled),
                "cmh_p":float(test.pvalue),
                "n":int(len(q)),
            })

    cmh = pd.DataFrame(cmh_rows)
    if not cmh.empty:
        cmh["fdr_q"] = bh(cmh.cmh_p.to_numpy())
    cmh.to_csv(out/"phase9g_cmh_by_dataset.csv", index=False)

    # Direct forward replication table: paired descriptive comparison of the
    # same named frontier regime/horizon/side cells between P7 and 2026.
    rep = tests.pivot_table(
        index=["asset","horizon","side","regime"],
        columns="dataset",
        values=["delta_win_rate","delta_mean_R","fisher_p","fdr_q","single_n","multiple_n"],
        aggfunc="first"
    ).reset_index()
    if not rep.empty:
        rep.columns = [
            "_".join(str(x) for x in c if str(x) != "") if isinstance(c, tuple) else str(c)
            for c in rep.columns
        ]
        if "delta_win_rate_PHASE7_INDEPENDENT" in rep.columns and "delta_win_rate_PHASE8_UNTOUCHED_2026" in rep.columns:
            rep["delta_win_rate_same_sign"] = (
                np.sign(rep["delta_win_rate_PHASE7_INDEPENDENT"]) ==
                np.sign(rep["delta_win_rate_PHASE8_UNTOUCHED_2026"])
            )
        if "delta_mean_R_PHASE7_INDEPENDENT" in rep.columns and "delta_mean_R_PHASE8_UNTOUCHED_2026" in rep.columns:
            rep["delta_mean_R_same_sign"] = (
                np.sign(rep["delta_mean_R_PHASE7_INDEPENDENT"]) ==
                np.sign(rep["delta_mean_R_PHASE8_UNTOUCHED_2026"])
            )
    rep.to_csv(out/"phase9g_forward_replication.csv", index=False)

    yearly = []
    for (dataset,year,asset,horizon,side,regime,st), q in d.assign(
        year=pd.to_datetime(d.signal_day).dt.year
    ).groupby(["dataset","year","asset","horizon","side","regime","consensus_state"]):
        if len(q) < 5:
            continue
        yearly.append({
            "dataset":dataset,"year":int(year),"asset":asset,"horizon":horizon,
            "side":side,"regime":regime,"consensus_state":st,
            "n":len(q),"win_rate":q.outcome_positive.mean(),"mean_R":q.return_R.mean()
        })
    pd.DataFrame(yearly).to_csv(out/"phase9g_yearly_stability.csv", index=False)

    pd.DataFrame([{
        "protocol":"Phase 9G named frozen frontier-regime-only consensus validation",
        "frozen_frontier_sha256":digest,
        "frozen_candidate_count":len(frontier),
        "regime_population":"ONLY named Pareto frontier leaves; all OTHER tree leaves excluded",
        "primary_estimand":"MULTIPLE (>=2 matching-side) minus SINGLE (1 matching-side) within each named frozen regime",
        "statistics":"Fisher exact + BH FDR; bootstrap 95% CIs; CMH tests stratified by named regime",
        "replication":"Phase 7 independent vs untouched 2026 reported side-by-side; no 2026 selection",
        "threshold_refitting":"NONE",
        "candidate_selection":"NONE",
        "strategy_selection":"NONE",
    }]).to_csv(out/"phase9g_provenance.csv", index=False)

    print("=== PHASE 9G COMPLETE ===")
    print("Frontier-only population:", len(d))
    print("Interaction cells/tests:", len(tests))
    print(tests.to_string(index=False) if not tests.empty else "No eligible frontier interaction tests")
    print("\nCMH:")
    print(cmh.to_string(index=False) if not cmh.empty else "No eligible CMH strata")
    print("\nReplication:")
    print(rep.to_string(index=False) if not rep.empty else "No paired cells")

if __name__ == "__main__":
    main()
