"""Phase 9 frozen CPR shadow decision engine.

Generates signals from the frozen Phase 5A frontier without using future
outcomes for signal generation. Default output is SHADOW / NOT FOR LIVE
EXECUTION. Historical outcomes can be attached explicitly for replay analysis.
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path
import numpy as np
import pandas as pd

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from run_cpr_regime_discovery import build_intraday_events, build_swing_events, make_context

PAT = re.compile(r"^([A-Za-z0-9_]+)\s*(<=|>)\s*(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$")


def parse_rule(rule: str):
    if rule == "ALL":
        return []
    out = []
    for condition in rule.split(" AND "):
        m = PAT.match(condition.strip())
        if not m:
            raise ValueError(f"Cannot parse frozen rule: {condition}")
        out.append((m.group(1), m.group(2), float(m.group(3))))
    return out


def matches(context_row: pd.Series, rule: str) -> bool:
    for col, op, value in parse_rule(rule):
        x = float(context_row[col])
        if not np.isfinite(x):
            return False
        if op == "<=" and not x <= value:
            return False
        if op == ">" and not x > value:
            return False
    return True


def build_shadow_signals(bars: pd.DataFrame, frontier: pd.DataFrame) -> pd.DataFrame:
    daily = bars.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    x = add_intraday_daily_features(bars, daily_reference_features(daily))
    context = make_context(bars).reindex(x.index)
    intraday_events = build_intraday_events(x, context)
    swing_events = build_swing_events(x, context)
    event_sets = {"intraday": intraday_events, "swing": swing_events}
    rows = []
    for asset, event_frame in event_sets.items():
        if event_frame.empty:
            continue
        for i in range(len(x) - 1):
            ts = x.index[i]
            event_at_ts = event_frame[event_frame.signal_time == ts]
            if event_at_ts.empty or context.iloc[i].isna().any():
                continue
            side = str(event_at_ts.iloc[0].side)
            entry_i = i + 1
            if x.index[entry_i].date() != ts.date():
                continue
            entry_price = float(x.iloc[entry_i].open)
            compatible = frontier[(frontier.asset == asset) & (frontier.side == side)]
            for cid, candidate in compatible.reset_index(drop=True).iterrows():
                if matches(context.iloc[i], candidate.rule):
                    rows.append({
                        "signal_time": ts, "signal_day": ts.normalize(),
                        "candidate_id": int(candidate.candidate_id) if "candidate_id" in candidate else int(cid),
                        "asset": candidate.asset, "horizon": candidate.horizon, "side": side,
                        "frozen_rule": candidate.rule, "entry_convention": "next_bar_open",
                        "signal_close": float(x.iloc[i].close), "next_bar_open": entry_price,
                        "atr_at_signal": float(x.iloc[i].D_ATR20),
                        "event_return_R_available": float(event_at_ts[event_at_ts.side == side].iloc[0].return_R),
                        "cpr_width_atr": float(context.iloc[i]["cpr_width_atr"]),
                        "atr_pct": float(context.iloc[i]["atr_pct"]),
                        "gap_atr": float(context.iloc[i]["gap_atr"]),
                        "intraday_move_atr": float(context.iloc[i]["intraday_move_atr"]),
                        "prior_day_return_atr": float(context.iloc[i]["prior_day_return_atr"]),
                        "phase6_status": "FROZEN_DIAGNOSTIC_ONLY", "phase7_status": "FROZEN_REPLICATION_ONLY",
                        "actionable": False, "mode": "SHADOW",
                    })
    return pd.DataFrame(rows)

def attach_historical_outcomes(shadow: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if shadow.empty:
        shadow["realized_return_R"] = pd.Series(dtype=float)
        return shadow
    sessions = pd.Index(sorted(bars.index.normalize().unique()))
    session_end = {d: int(np.flatnonzero(bars.index.normalize() == d)[-1]) for d in sessions}
    pos = {d: i for i, d in enumerate(sessions)}
    returns = []
    for _, r in shadow.iterrows():
        ts = pd.Timestamp(r.signal_time)
        loc = bars.index.get_indexer([ts])[0]
        entry_i = loc + 1
        if entry_i >= len(bars):
            returns.append(np.nan)
            continue
        entry_day = bars.index[entry_i].normalize()
        if entry_day not in pos:
            returns.append(np.nan)
            continue
        if r.horizon.endswith("bar"):
            h = int(r.horizon[:-3])
            j = entry_i + h - 1
            same_day = bars.index[j].normalize() == entry_day if j < len(bars) else False
            if j >= len(bars) or not same_day:
                returns.append(np.nan)
                continue
        elif r.horizon == "EOD":
            j = session_end[entry_day]
        else:
            h = int(r.horizon[:-7])
            target = pos[entry_day] + h - 1
            if target >= len(sessions):
                returns.append(np.nan)
                continue
            j = session_end[sessions[target]]
        entry = float(bars.iloc[entry_i].open)
        close = float(bars.iloc[j].close)
        direction = 1 if r.side == "LONG" else -1
        atr = float(r.atr_at_signal)
        returns.append(direction * (close - entry) / atr if atr > 0 else np.nan)
    shadow = shadow.copy()
    shadow["realized_return_R"] = returns
    return shadow


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--frontier", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--attach-historical-outcomes", action="store_true")
    a = ap.parse_args()

    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frontier = pd.read_csv(a.frontier).reset_index(drop=True)
    if len(frontier) != 39:
        raise ValueError(f"Expected exactly 39 frozen candidates, found {len(frontier)}")
    # Candidate identity is the immutable row position in the verified frozen frontier.
    # Do not inherit any non-unique IDs that may be present in the source CSV.
    frontier["candidate_id"] = np.arange(len(frontier), dtype=int)

    bars = load_ohlcv_csv(a.input)
    shadow = build_shadow_signals(bars, frontier)
    if a.attach_historical_outcomes:
        shadow = attach_historical_outcomes(shadow, bars)

    shadow.to_csv(out / "phase9_shadow_signals.csv", index=False)

    if shadow.empty:
        daily = pd.DataFrame(columns=["signal_day", "signals", "candidate_count", "long_candidates", "short_candidates", "conflict"])
        candidates = pd.DataFrame(columns=["candidate_id", "signals"])
    else:
        daily = shadow.groupby("signal_day").agg(
            signals=("candidate_id", "size"),
            candidate_count=("candidate_id", "nunique"),
            long_candidates=("side", lambda s: int((s == "LONG").sum())),
            short_candidates=("side", lambda s: int((s == "SHORT").sum())),
        ).reset_index()
        daily["conflict"] = (daily.long_candidates > 0) & (daily.short_candidates > 0)
        candidates = shadow.groupby(["candidate_id", "asset", "horizon", "side"]).size().reset_index(name="signals")

    daily.to_csv(out / "phase9_daily_signal_summary.csv", index=False)
    candidates.to_csv(out / "phase9_candidate_activation.csv", index=False)

    provenance = pd.DataFrame([{
        "candidate_count": len(frontier),
        "mode": "SHADOW",
        "actionable_default": False,
        "future_outcomes_used_for_signal_generation": False,
        "historical_outcomes_attached": bool(a.attach_historical_outcomes),
        "method": "Frozen Phase 5A rules; no fitting, threshold adjustment, ranking or selection.",
    }])
    provenance.to_csv(out / "phase9_provenance.csv", index=False)

    print("=== PHASE 9 SHADOW DECISION ENGINE ===")
    print(f"Frozen candidates: {len(frontier)}")
    print(f"Shadow signals: {len(shadow)}")
    if not shadow.empty:
        print(f"Signal days: {shadow.signal_day.nunique()}")
        print(f"Long candidate matches: {(shadow.side == 'LONG').sum()}")
        print(f"Short candidate matches: {(shadow.side == 'SHORT').sum()}")
        print(f"Conflicting days: {int(daily.conflict.sum())}")
    print("Actionable: FALSE (shadow mode)")


if __name__ == "__main__":
    main()
