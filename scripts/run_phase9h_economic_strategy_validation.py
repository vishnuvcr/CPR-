"""Phase 9H: frozen-regime economic and strategy-conditional validation.

No consensus selection. No threshold fitting. No 2026 selection.

The script evaluates four pre-specified execution families over named frozen
Phase 5A frontier regimes:
  * FIXED_HORIZON
  * ATR_STOP_1R_TARGET_1R
  * ATR_STOP_1R_TARGET_2R
  * ATR_STOP_1R_BREAKEVEN

Results are event-level economic sensitivity on a normalized INR 100,000
notional using the NIFTY50 index path. Because the source is an index, this is
explicitly a futures-proxy economic analysis, not proof of executable futures
performance. Options are intentionally deferred until historical option-chain
data pass independent QA.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

from cpr_lab.data_quality import load_ohlcv_csv
from run_phase9g_frontier_consensus_validation import make_events, frozen_trees, assign_frontier_regime

FRONTIER_SHA256 = "601a72f5e64204aee7ff0bb77347d57b0e2b59871b8bc30011282c2dc02c28b2"
NOTIONAL = 100_000.0
STRATEGIES = (
    "FIXED_HORIZON",
    "ATR_STOP_1R_TARGET_1R",
    "ATR_STOP_1R_TARGET_2R",
    "ATR_STOP_1R_BREAKEVEN",
)
SCENARIOS = {
    "PAYTM_BASE20_5BPS": {"brokerage": 20.0, "slippage": 0.0005},
    "PAYTM_ALT10_5BPS": {"brokerage": 10.0, "slippage": 0.0005},
    "PAYTM_BASE20_10BPS": {"brokerage": 20.0, "slippage": 0.0010},
    "PAYTM_ALT10_10BPS": {"brokerage": 10.0, "slippage": 0.0010},
}
GST = 0.18
SEBI_RATE = 0.000001
FUTURES_EXCHANGE_RATE = 0.0000183
FUTURES_STT_PRE_2026 = 0.0002
FUTURES_STT_POST_2026 = 0.0005
FUTURES_STAMP_RATE = 0.00002

def bootstrap_ci(x: np.ndarray, reps: int = 2000, seed: int = 20260919):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(reps, len(x)))
    vals = x[idx].mean(axis=1)
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))

def cost_roundtrip(entry_value, exit_value, scenario, trade_day):
    cfg = SCENARIOS[scenario]
    turnover = abs(entry_value) + abs(exit_value)
    exchange = turnover * FUTURES_EXCHANGE_RATE
    sebi = turnover * SEBI_RATE
    stt_rate = FUTURES_STT_PRE_2026 if pd.Timestamp(trade_day) < pd.Timestamp("2026-04-01") else FUTURES_STT_POST_2026
    stt = abs(exit_value) * stt_rate
    stamp = abs(entry_value) * FUTURES_STAMP_RATE
    brokerage = 2.0 * cfg["brokerage"]
    gst = GST * (brokerage + exchange + sebi)
    return brokerage + exchange + sebi + gst + stt + stamp

def apply_entry_slippage(raw_price, side, slip):
    return raw_price * (1.0 + (slip if side == "LONG" else -slip))

def apply_exit_slippage(raw_price, side, slip):
    # exiting a long is a sell; exiting a short is a buy
    return raw_price * (1.0 - (slip if side == "LONG" else -slip))

def event_end_index(asset, horizon, bars_index, signal_idx, session_pos, session_end):
    entry_idx = signal_idx + 1
    if entry_idx >= len(bars_index):
        return None, None
    entry_day = bars_index[entry_idx].normalize()
    if horizon.endswith("bar"):
        h = int(horizon.replace("bar",""))
        end = entry_idx + h - 1
        if end >= len(bars_index) or bars_index[end].normalize() != entry_day:
            return None, None
        return entry_idx, end
    if horizon == "EOD":
        return entry_idx, session_end.get(entry_day)
    if horizon.endswith("session"):
        h = int(horizon.replace("session",""))
        if entry_day not in session_pos:
            return None, None
        target_pos = session_pos[entry_day] + h - 1
        days = sorted(session_end)
        if target_pos >= len(days):
            return None, None
        target_day = days[target_pos]
        return entry_idx, session_end[target_day]
    raise ValueError(f"Unknown horizon: {horizon}")

def simulate_event(bars, row, signal_idx, strategy, scenario, session_pos, session_end):
    bars_index = bars.index
    entry_idx, end_idx = event_end_index(
        row.asset, row.horizon, bars_index, signal_idx, session_pos, session_end
    )
    if entry_idx is None or end_idx is None or end_idx < entry_idx:
        return None

    atr = float(bars.iloc[signal_idx].get("D_ATR20", np.nan))
    if not np.isfinite(atr) or atr <= 0:
        return None
    side = row.side
    raw_entry = float(bars.iloc[entry_idx].open)
    slip = SCENARIOS[scenario]["slippage"]
    entry = apply_entry_slippage(raw_entry, side, slip)
    qty = NOTIONAL / entry
    risk_value = qty * atr

    strategy_path = strategy
    exit_raw = float(bars.iloc[end_idx].close)
    exit_reason = "native_horizon"

    if strategy_path != "FIXED_HORIZON":
        if strategy_path == "ATR_STOP_1R_TARGET_1R":
            stop_dist, target_dist = atr, atr
        elif strategy_path == "ATR_STOP_1R_TARGET_2R":
            stop_dist, target_dist = atr, 2.0 * atr
        elif strategy_path == "ATR_STOP_1R_BREAKEVEN":
            stop_dist, target_dist = atr, np.inf
        else:
            raise ValueError(strategy_path)

        stop = entry - stop_dist if side == "LONG" else entry + stop_dist
        target = entry + target_dist if side == "LONG" else entry - target_dist if np.isfinite(target_dist) else np.inf
        breakeven_armed = False

        for j in range(entry_idx, end_idx + 1):
            b = bars.iloc[j]
            bo, bh, bl = float(b.open), float(b.high), float(b.low)

            # Gap through stop is handled at the bar open.
            if side == "LONG" and bo <= stop:
                exit_raw, exit_reason = bo, "gap_stop"
                break
            if side == "SHORT" and bo >= stop:
                exit_raw, exit_reason = bo, "gap_stop"
                break

            # Conservative intrabar order: stop first, then target.
            if side == "LONG" and bl <= stop:
                exit_raw, exit_reason = stop, "stop"
                break
            if side == "SHORT" and bh >= stop:
                exit_raw, exit_reason = stop, "stop"
                break

            if np.isfinite(target_dist):
                if side == "LONG" and bh >= target:
                    exit_raw, exit_reason = target, "target"
                    break
                if side == "SHORT" and bl <= target:
                    exit_raw, exit_reason = target, "target"
                    break

            if strategy_path == "ATR_STOP_1R_BREAKEVEN" and not breakeven_armed:
                # Arm the break-even stop for the NEXT bar only. This avoids
                # using same-bar high/low sequencing ambiguities.
                moved = (bh >= entry + atr) if side == "LONG" else (bl <= entry - atr)
                if moved:
                    breakeven_armed = True
                    stop = entry

    exit = apply_exit_slippage(exit_raw, side, slip)
    pnl = qty * ((exit - entry) if side == "LONG" else (entry - exit))
    day = bars_index[signal_idx].normalize()
    costs = cost_roundtrip(abs(qty * entry), abs(qty * exit), scenario, day)
    net_pnl = pnl - costs
    gross_r = pnl / risk_value
    net_r = net_pnl / risk_value

    return {
        "signal_time": row.signal_time,
        "signal_day": row.signal_day,
        "asset": row.asset,
        "horizon": row.horizon,
        "side": row.side,
        "regime": row.regime,
        "regime_leaf": row.regime_leaf,
        "strategy": strategy,
        "scenario": scenario,
        "entry_time": bars_index[entry_idx],
        "exit_time": bars_index[end_idx],
        "entry_price": entry,
        "exit_price": exit,
        "atr20": atr,
        "risk_value": risk_value,
        "gross_pnl": pnl,
        "costs_inr": costs,
        "net_pnl": net_pnl,
        "gross_R": gross_r,
        "net_R": net_r,
        "exit_reason": exit_reason,
    }

def prepare_dataset(name, path, reference_bars, frontier):
    bars = load_ohlcv_csv(path)
    events = make_events(bars)
    trees = frozen_trees(reference_bars)
    parts = []
    for asset, ev in events.items():
        if ev.empty:
            continue
        z = assign_frontier_regime(ev, trees, frontier)
        if z.empty:
            continue
        parts.append(z)
    if not parts:
        raise ValueError(f"{name}: no events in named frozen frontier leaves")
    return bars, pd.concat(parts, ignore_index=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--p7", required=True)
    ap.add_argument("--p8", required=True)
    ap.add_argument("--frontier", required=True)
    ap.add_argument("--output-dir", required=True)
    a = ap.parse_args()

    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256(Path(a.frontier).read_bytes()).hexdigest()
    if digest != FRONTIER_SHA256:
        raise ValueError(f"Frozen frontier hash mismatch: {digest}")
    frontier = pd.read_csv(a.frontier)
    if len(frontier) != 39:
        raise ValueError(f"Expected 39 frozen candidates, found {len(frontier)}")

    reference = load_ohlcv_csv(a.reference)
    datasets = {}
    for name, path in [("PHASE7_INDEPENDENT", a.p7), ("PHASE8_UNTOUCHED_2026", a.p8)]:
        datasets[name] = prepare_dataset(name, path, reference, frontier)

    rows = []
    for dataset, (bars, events) in datasets.items():
        session_days = sorted(pd.Index(bars.index.normalize()).unique())
        session_end = {d: int(np.flatnonzero(bars.index.normalize() == d)[-1]) for d in session_days}
        session_pos = {d: i for i, d in enumerate(session_days)}
        pos_map = {ts: i for i, ts in enumerate(bars.index)}

        for row in events.itertuples(index=False):
            sig = pos_map.get(row.signal_time)
            if sig is None:
                continue
            for strategy in STRATEGIES:
                for scenario in SCENARIOS:
                    result = simulate_event(
                        bars, row, sig, strategy, scenario, session_pos, session_end
                    )
                    if result:
                        result["dataset"] = dataset
                        rows.append(result)

    trades = pd.DataFrame(rows)
    if trades.empty:
        raise ValueError("Phase 9H generated no strategy observations")
    if set(trades.dataset.unique()) != {"PHASE7_INDEPENDENT", "PHASE8_UNTOUCHED_2026"}:
        raise ValueError("Dataset labels are not exactly Phase 7 and untouched 2026")

    trades.to_csv(out / "phase9h_strategy_population.csv", index=False)

    cell_rows = []
    for keys, q in trades.groupby(["dataset","strategy","scenario","asset","horizon","side","regime"]):
        dataset,strategy,scenario,asset,horizon,side,regime = keys
        lo, hi = bootstrap_ci(q.net_R.to_numpy(float))
        wlo, whi = bootstrap_ci((q.net_R > 0).to_numpy(float))
        cell_rows.append({
            "dataset":dataset,"strategy":strategy,"scenario":scenario,
            "asset":asset,"horizon":horizon,"side":side,"regime":regime,
            "n":len(q),
            "mean_net_R":q.net_R.mean(),
            "mean_net_R_ci95_low":lo,
            "mean_net_R_ci95_high":hi,
            "median_net_R":q.net_R.median(),
            "win_rate":(q.net_R > 0).mean(),
            "win_rate_ci95_low":wlo,
            "win_rate_ci95_high":whi,
            "mean_gross_R":q.gross_R.mean(),
            "mean_cost_R":(q.costs_inr / q.risk_value).mean(),
            "total_net_pnl":q.net_pnl.sum(),
        })
    cells = pd.DataFrame(cell_rows)
    cells.to_csv(out / "phase9h_strategy_cells.csv", index=False)

    summary = []
    for keys, q in trades.groupby(["dataset","strategy","scenario","asset","horizon","side"]):
        dataset,strategy,scenario,asset,horizon,side = keys
        lo, hi = bootstrap_ci(q.net_R.to_numpy(float))
        summary.append({
            "dataset":dataset,"strategy":strategy,"scenario":scenario,
            "asset":asset,"horizon":horizon,"side":side,"n":len(q),
            "mean_net_R":q.net_R.mean(),"mean_net_R_ci95_low":lo,"mean_net_R_ci95_high":hi,
            "median_net_R":q.net_R.median(),"win_rate":(q.net_R > 0).mean(),
            "mean_gross_R":q.gross_R.mean(),"mean_cost_R":(q.costs_inr/q.risk_value).mean(),
            "total_net_pnl":q.net_pnl.sum(),
        })
    pd.DataFrame(summary).to_csv(out / "phase9h_strategy_summary.csv", index=False)

    yearly = []
    t2 = trades.copy()
    t2["year"] = pd.to_datetime(t2.signal_day).dt.year
    for keys, q in t2.groupby(["dataset","year","strategy","scenario","asset","horizon","side"]):
        dataset,year,strategy,scenario,asset,horizon,side = keys
        yearly.append({
            "dataset":dataset,"year":int(year),"strategy":strategy,"scenario":scenario,
            "asset":asset,"horizon":horizon,"side":side,"n":len(q),
            "mean_net_R":q.net_R.mean(),"win_rate":(q.net_R > 0).mean(),
            "mean_cost_R":(q.costs_inr/q.risk_value).mean(),
        })
    pd.DataFrame(yearly).to_csv(out / "phase9h_yearly_stability.csv", index=False)

    # Strategy-selection is deliberately disabled. This table is a complete
    # family-level comparison for later pre-specified policy design.
    provenance = pd.DataFrame([{
        "protocol":"Phase 9H economic / strategy-conditional validation",
        "frontier_sha256":digest,
        "frontier_count":len(frontier),
        "regime_population":"named frozen frontier leaves only",
        "consensus_role":"metadata only; excluded from selection",
        "strategy_families":"FIXED_HORIZON;ATR_STOP_1R_TARGET_1R;ATR_STOP_1R_TARGET_2R;ATR_STOP_1R_BREAKEVEN",
        "cost_scenarios":";".join(SCENARIOS),
        "notional_inr":NOTIONAL,
        "instrument_boundary":"NIFTY50 index path used as normalized futures-proxy economic analysis; not executable futures proof",
        "phase7_role":"independent evaluation / fixed-library development context",
        "phase8_role":"untouched forward evaluation",
        "selection_from_2026":"NO",
        "threshold_refitting":"NONE",
        "candidate_selection":"NONE",
        "strategy_selection":"NONE",
        "options_included":"NO; historical option-chain QA is a separate gated task",
    }])
    provenance.to_csv(out / "phase9h_provenance.csv", index=False)

    print("=== PHASE 9H COMPLETE ===")
    print("Trade-family rows:", len(trades))
    print("Cell rows:", len(cells))
    print("Datasets:", trades.groupby("dataset").size().to_dict())
    print("Strategies:", trades.groupby("strategy").size().to_dict())
    print("Scenarios:", trades.groupby("scenario").size().to_dict())

if __name__ == "__main__":
    main()
