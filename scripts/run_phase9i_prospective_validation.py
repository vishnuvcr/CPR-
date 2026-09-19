"""Phase 9I — prospective chronological validation of the frozen Phase 9H candidate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from run_phase9g_frontier_consensus_validation import make_events, frozen_trees, assign_frontier_regime
from run_phase9h_economic_strategy_validation import (
    FRONTIER_SHA256,
    NOTIONAL,
    SCENARIOS,
    bootstrap_ci,
    event_end_index,
    simulate_event,
)

CANDIDATE = {
    "regime_leaf": "LEAF_4",
    "side": "SHORT",
    "horizon": "10session",
    "strategy": "ATR_STOP_1R_TARGET_2R",
}
CUTOFF = pd.Timestamp("2026-09-17 15:30:00", tz="Asia/Kolkata")
BOOTSTRAP_REPS = 5000
EVENT_BOOTSTRAP_SEED = 20260920
PORTFOLIO_BOOTSTRAP_SEED = 20260921
MIN_MATURE_TRADES = 30
MATURE_CALENDAR_DAYS = 90


def _cluster_bootstrap_mean_ci(q: pd.DataFrame, value_col: str, reps: int, seed: int):
    groups = [g[value_col].to_numpy(dtype=float) for _, g in q.groupby("signal_day", sort=True)]
    groups = [g[np.isfinite(g)] for g in groups if np.isfinite(g).any()]
    if len(groups) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    vals = np.empty(reps, dtype=float)
    for k in range(reps):
        picked = rng.integers(0, len(groups), size=len(groups))
        sample = np.concatenate([groups[i] for i in picked])
        vals[k] = sample.mean()
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def _moving_block_bootstrap_mean_ci(x: np.ndarray, block: int, reps: int, seed: int):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < max(2, block):
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    n = len(x)
    vals = np.empty(reps, dtype=float)
    starts_max = n if n > block else 1
    for k in range(reps):
        chunks = []
        while sum(len(v) for v in chunks) < n:
            start = int(rng.integers(0, starts_max))
            idx = [(start + j) % n for j in range(block)]
            chunks.append(x[idx])
        sample = np.concatenate(chunks)[:n]
        vals[k] = sample.mean()
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def _max_drawdown(values: pd.Series) -> float:
    eq = values.cumsum().to_numpy(dtype=float)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return float(np.min(eq - peak)) if len(eq) else 0.0


def _clean_num(v):
    return None if v is None or not np.isfinite(float(v)) else float(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--fresh", required=True)
    ap.add_argument("--frontier", required=True)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--source-sha256", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    frontier_sha = __import__("hashlib").sha256(Path(args.frontier).read_bytes()).hexdigest()
    if frontier_sha != FRONTIER_SHA256:
        raise ValueError(f"Frozen frontier hash mismatch: {frontier_sha}")

    frontier = pd.read_csv(args.frontier)
    if len(frontier) != 39:
        raise ValueError(f"Expected 39 frozen frontier candidates, found {len(frontier)}")

    reference = load_ohlcv_csv(args.reference)
    fresh = load_ohlcv_csv(args.fresh)

    daily = fresh.resample("1D").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    featured = add_intraday_daily_features(fresh, daily_reference_features(daily))
    if "D_ATR20" not in featured.columns:
        raise ValueError("Phase 9I fresh bars missing D_ATR20")

    events = make_events(fresh)
    trees = frozen_trees(reference)
    parts = []
    for asset, ev in events.items():
        if ev.empty:
            continue
        z = assign_frontier_regime(ev, trees, frontier)
        if z.empty:
            continue
        parts.append(z)

    if not parts:
        raise ValueError("No frontier events generated from the fresh dataset")

    events_df = pd.concat(parts, ignore_index=True)
    events_df["signal_time"] = pd.to_datetime(events_df["signal_time"])
    events_df = events_df[
        (events_df["signal_time"] > CUTOFF)
        & (events_df["regime_leaf"] == CANDIDATE["regime_leaf"])
        & (events_df["side"] == CANDIDATE["side"])
        & (events_df["horizon"] == CANDIDATE["horizon"])
    ].copy()

    if events_df.empty:
        completed = pd.DataFrame()
        pending = pd.DataFrame(
            columns=["event_id", "signal_time", "signal_day", "asset", "horizon", "side", "regime_leaf", "status"]
        )
        latest_data_ts = fresh.index.max()
        state = {
            "status": "INSUFFICIENT_NEW_HOLDOUT",
            "completed_event_trades": 0,
            "completed_portfolio_trades": 0,
            "pending_signals": 0,
            "fresh_data_end": str(latest_data_ts),
            "cutoff": str(CUTOFF),
            "maturity_rule": {"min_trades": MIN_MATURE_TRADES, "calendar_days": MATURE_CALENDAR_DAYS},
        }
        pd.DataFrame([{
            "dataset":"PHASE9I_FRESH_HOLDOUT",
            "status":state["status"],
            "source_commit":args.source_commit,
            "source_sha256":args.source_sha256,
            "cutoff":CUTOFF.isoformat(),
            **CANDIDATE,
        }]).to_csv(out / "phase9i_provenance.csv", index=False)
        for name, frame in [
            ("phase9i_completed_event_trades.csv", completed),
            ("phase9i_pending_signals.csv", pending),
            ("phase9i_event_summary.csv", pd.DataFrame()),
            ("phase9i_portfolio_trades.csv", pd.DataFrame()),
            ("phase9i_portfolio_summary.csv", pd.DataFrame()),
        ]:
            frame.to_csv(out / name, index=False)
        (out / "phase9i_run_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(json.dumps(state, indent=2))
        return

    session_days = sorted(pd.Index(fresh.index.normalize()).unique())
    session_end = {d: int(np.flatnonzero(fresh.index.normalize() == d)[-1]) for d in session_days}
    session_pos = {d: i for i, d in enumerate(session_days)}
    pos_map = {ts: i for i, ts in enumerate(fresh.index)}

    rows = []
    pending_rows = []
    for row in events_df.itertuples(index=False):
        sig = pos_map.get(row.signal_time)
        if sig is None:
            continue
        eid = f"{row.asset}|{row.signal_time}|{row.horizon}|{row.side}|{row.regime_leaf}"
        any_complete = False
        first_sim = None
        for scenario in SCENARIOS:
            simulated = simulate_event(
                featured, row, sig, CANDIDATE["strategy"], scenario, session_pos, session_end
            )
            if simulated is not None:
                simulated["event_id"] = eid
                simulated["dataset"] = "PHASE9I_FRESH_HOLDOUT"
                rows.append(simulated)
                any_complete = True
                first_sim = simulated
        if not any_complete:
            pending_rows.append(
                {
                    "event_id": eid,
                    "signal_time": row.signal_time,
                    "signal_day": row.signal_day,
                    "asset": row.asset,
                    "horizon": row.horizon,
                    "side": row.side,
                    "regime_leaf": row.regime_leaf,
                    "status": "PENDING_10_SESSION_EXIT",
                }
            )

    trades = pd.DataFrame(rows)
    pending = pd.DataFrame(pending_rows)

    if trades.empty:
        state = {
            "status": "INSUFFICIENT_NEW_HOLDOUT",
            "completed_event_trades": 0,
            "completed_portfolio_trades": 0,
            "pending_signals": int(len(pending)),
            "fresh_data_end": str(fresh.index.max()),
            "cutoff": str(CUTOFF),
            "maturity_rule": {"min_trades": MIN_MATURE_TRADES, "calendar_days": MATURE_CALENDAR_DAYS},
        }
        trades.to_csv(out / "phase9i_completed_event_trades.csv", index=False)
        pending.to_csv(out / "phase9i_pending_signals.csv", index=False)
        for name in ["phase9i_event_summary.csv","phase9i_portfolio_trades.csv","phase9i_portfolio_summary.csv"]:
            pd.DataFrame().to_csv(out / name, index=False)
        (out / "phase9i_run_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        pd.DataFrame([{
            "dataset":"PHASE9I_FRESH_HOLDOUT",
            "status":state["status"],
            "source_commit":args.source_commit,
            "source_sha256":args.source_sha256,
            "cutoff":CUTOFF.isoformat(),
            "fresh_data_end":str(fresh.index.max()),
            **CANDIDATE,
        }]).to_csv(out / "phase9i_provenance.csv", index=False)
        print(json.dumps(state, indent=2))
        return

    summary_rows = []
    for scenario, q in trades.groupby("scenario"):
        lo, hi = _cluster_bootstrap_mean_ci(q, "net_R", BOOTSTRAP_REPS, EVENT_BOOTSTRAP_SEED)
        win_lo, win_hi = _cluster_bootstrap_mean_ci(
            q.assign(win=q["net_R"] > 0), "win", BOOTSTRAP_REPS, EVENT_BOOTSTRAP_SEED + 1
        )
        summary_rows.append(
            {
                "dataset":"PHASE9I_FRESH_HOLDOUT",
                "scenario":scenario,
                "n_events":int(len(q)),
                "mean_net_R":float(q.net_R.mean()),
                "mean_net_R_ci95_low":lo,
                "mean_net_R_ci95_high":hi,
                "median_net_R":float(q.net_R.median()),
                "win_rate":float((q.net_R > 0).mean()),
                "win_rate_ci95_low":win_lo,
                "win_rate_ci95_high":win_hi,
                "total_net_pnl":float(q.net_pnl.sum()),
                "mean_cost_inr":float(q.costs_inr.mean()),
                "mean_cost_R":float((q.costs_inr / q.risk_value).mean()),
                "max_drawdown_inr_event_sequence":_max_drawdown(q.sort_values("entry_time").net_pnl),
            }
        )
    pd.DataFrame(summary_rows).to_csv(out / "phase9i_event_summary.csv", index=False)

    # Deterministic no-pyramiding portfolio diagnostic: chronological earliest
    # eligible entry while flat. Selection is fixed by timestamp, not outcome.
    base = trades[trades.scenario == "PAYTM_BASE20_5BPS"].sort_values("entry_time")
    chosen_ids = []
    last_exit = None
    for eid, q in base.groupby("event_id", sort=False):
        first = q.iloc[0]
        if last_exit is None or first.entry_time > last_exit:
            chosen_ids.append(eid)
            last_exit = first.exit_time

    portfolio = trades[trades.event_id.isin(chosen_ids)].copy()
    p_rows = []
    for scenario, q in portfolio.groupby("scenario"):
        q = q.sort_values("entry_time")
        lo, hi = _moving_block_bootstrap_mean_ci(
            q.net_R.to_numpy(float), block=min(5, max(2, len(q))), reps=BOOTSTRAP_REPS, seed=PORTFOLIO_BOOTSTRAP_SEED
        )
        p_rows.append(
            {
                "dataset":"PHASE9I_FRESH_HOLDOUT",
                "scenario":scenario,
                "n_trades":int(len(q)),
                "mean_net_R":float(q.net_R.mean()),
                "mean_net_R_ci95_low":lo,
                "mean_net_R_ci95_high":hi,
                "median_net_R":float(q.net_R.median()),
                "win_rate":float((q.net_R > 0).mean()),
                "total_net_pnl":float(q.net_pnl.sum()),
                "mean_cost_inr":float(q.costs_inr.mean()),
                "mean_cost_R":float((q.costs_inr / q.risk_value).mean()),
                "max_drawdown_inr":_max_drawdown(q.net_pnl),
            }
        )
    portfolio.to_csv(out / "phase9i_portfolio_trades.csv", index=False)
    pd.DataFrame(p_rows).to_csv(out / "phase9i_portfolio_summary.csv", index=False)
    pending.to_csv(out / "phase9i_pending_signals.csv", index=False)

    state = {
        "status": (
            "MATURE_FOR_PHASE9I_REVIEW"
            if len(chosen_ids) >= MIN_MATURE_TRADES
            else "PROSPECTIVE_HOLDOUT_ACTIVE"
        ),
        "completed_event_trades": int(trades["event_id"].nunique()),
        "completed_portfolio_trades": int(len(chosen_ids)),
        "pending_signals": int(len(pending)),
        "fresh_data_end": str(fresh.index.max()),
        "cutoff": str(CUTOFF),
        "maturity_rule": {"min_trades": MIN_MATURE_TRADES, "calendar_days": MATURE_CALENDAR_DAYS},
        "candidate": CANDIDATE,
    }
    (out / "phase9i_run_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    pd.DataFrame([{
        "dataset":"PHASE9I_FRESH_HOLDOUT",
        "status":state["status"],
        "source_commit":args.source_commit,
        "source_sha256":args.source_sha256,
        "cutoff":CUTOFF.isoformat(),
        "fresh_data_end":str(fresh.index.max()),
        "reference_frontier_sha256":frontier_sha,
        "frontier_count":len(frontier),
        "event_bootstrap_reps":BOOTSTRAP_REPS,
        "event_bootstrap_seed":EVENT_BOOTSTRAP_SEED,
        "portfolio_bootstrap_seed":PORTFOLIO_BOOTSTRAP_SEED,
        "maturity_min_trades":MIN_MATURE_TRADES,
        "maturity_calendar_days":MATURE_CALENDAR_DAYS,
        **CANDIDATE,
    }]).to_csv(out / "phase9i_provenance.csv", index=False)

    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
