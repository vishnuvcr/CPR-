"""Phase 4: leakage-safe cross-horizon selector for CPR swing signals.

Discovery-to-validation bridge. Horizons are fixed at 2/3/5/10 sessions. For
each signal, a selector trained only on prior, non-overlapping observations
chooses one horizon for the next validation period. The training window uses
signal-day-clustered returns and is purged by the maximum 10-session horizon
before validation. No thresholds or horizons are optimized; the selector only
chooses among the four pre-specified horizons.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HORIZONS = ("2session", "3session", "5session", "10session")
MAX_HORIZON = 10
TRAIN_SESSIONS = 756  # approximately three trading years; fixed ex ante
VALIDATION_SESSIONS = 252  # approximately one trading year


def load_events(path: str) -> pd.DataFrame:
    e = pd.read_csv(path, parse_dates=["signal_time", "signal_date", "entry_session", "target_session"])
    e["signal_day"] = e.signal_date.dt.normalize()
    e["entry_day"] = e.entry_session.dt.normalize()
    return e.sort_values(["signal_day", "signal_time", "horizon"]).reset_index(drop=True)


def choose_horizon(train: pd.DataFrame, side: str) -> tuple[str, pd.DataFrame]:
    """Choose the highest mean daily-cluster R using only purged training data."""
    z = train[train.side == side]
    rows = []
    for h in HORIZONS:
        q = z[z.horizon == h]
        daily = q.groupby("signal_day", as_index=False).return_R.mean()
        mean = float(daily.return_R.mean()) if len(daily) else np.nan
        rows.append({"side": side, "horizon": h, "training_days": len(daily), "training_mean_R": mean})
    scores = pd.DataFrame(rows)
    valid = scores.dropna(subset=["training_mean_R"])
    if valid.empty:
        return HORIZONS[0], scores
    # Deterministic tie-break: shorter horizon first.
    order = {h: i for i, h in enumerate(HORIZONS)}
    selected = valid.sort_values(["training_mean_R"], ascending=False, kind="mergesort")
    best_value = selected.iloc[0].training_mean_R
    tied = valid[np.isclose(valid.training_mean_R, best_value, rtol=0, atol=1e-12)]
    chosen = sorted(tied.horizon.tolist(), key=lambda h: order[h])[0]
    return chosen, scores


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Phase 3A swing_events.csv")
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    e = load_events(a.input)
    sessions = pd.Index(sorted(e.entry_day.dropna().unique()))
    if len(sessions) < TRAIN_SESSIONS + VALIDATION_SESSIONS + MAX_HORIZON:
        raise SystemExit("Insufficient sessions for the fixed walk-forward design")
    pos = {d: i for i, d in enumerate(sessions)}

    selections: list[dict[str, object]] = []
    oos_rows: list[pd.DataFrame] = []
    split_id = 0
    train_end = TRAIN_SESSIONS - 1
    while train_end + MAX_HORIZON + VALIDATION_SESSIONS < len(sessions):
        purge_start = train_end + 1
        validation_start = purge_start + MAX_HORIZON
        validation_end = min(validation_start + VALIDATION_SESSIONS - 1, len(sessions) - 1)
        train_start = max(0, train_end - TRAIN_SESSIONS + 1)
        train_days = set(sessions[train_start : train_end + 1])
        validation_days = set(sessions[validation_start : validation_end + 1])
        train = e[e.entry_day.isin(train_days)]
        validation = e[e.entry_day.isin(validation_days)]
        split_id += 1

        chosen_by_side: dict[str, str] = {}
        for side in ("LONG", "SHORT"):
            chosen, scores = choose_horizon(train, side)
            chosen_by_side[side] = chosen
            selections.append({
                "split": split_id,
                "train_start": sessions[train_start],
                "train_end": sessions[train_end],
                "purge_start": sessions[purge_start],
                "validation_start": sessions[validation_start],
                "validation_end": sessions[validation_end],
                "side": side,
                "selected_horizon": chosen,
                "training_days": int(scores.training_days.sum()),
                "training_scores": "|".join(f"{r.horizon}:{r.training_mean_R:.8f}" for r in scores.itertuples()),
            })

        # One horizon is selected for every signal in the validation period.
        # Keep the complete fixed-horizon benchmark rows for the same OOS period.
        v = validation.copy()
        v["selected"] = v.apply(lambda r: r.horizon == chosen_by_side.get(r.side), axis=1)
        selected = v[v.selected].copy()
        selected["split"] = split_id
        oos_rows.append(selected)

        train_end = validation_end

    if not oos_rows:
        raise SystemExit("No walk-forward validation splits generated")
    oos = pd.concat(oos_rows, ignore_index=True)
    selections_df = pd.DataFrame(selections)
    selections_df.to_csv(out / "cross_horizon_selections.csv", index=False)
    oos.to_csv(out / "cross_horizon_selected_events.csv", index=False)

    # OOS comparison: selected horizon versus each fixed horizon, using equal
    # weight per signal day so repeated signals on one day do not dominate.
    rows: list[dict[str, object]] = []
    for label, q in [("SELECTED", oos)]:
        daily = q.groupby("signal_day", as_index=False).return_R.mean()
        rows.append({"strategy": label, "signals": len(q), "signal_days": len(daily),
                     "mean_R": daily.return_R.mean(), "median_R": daily.return_R.median(),
                     "win_day_rate": (daily.return_R > 0).mean()})
    for h in HORIZONS:
        q = e[e.entry_day.isin(set(oos.entry_day)) & (e.horizon == h)].copy()
        # Only use the exact OOS split membership, not all events in those dates.
        q = q[q.entry_day.isin(set(oos.entry_day))]
        daily = q.groupby("signal_day", as_index=False).return_R.mean()
        rows.append({"strategy": h, "signals": len(q), "signal_days": len(daily),
                     "mean_R": daily.return_R.mean(), "median_R": daily.return_R.median(),
                     "win_day_rate": (daily.return_R > 0).mean()})
    pd.DataFrame(rows).to_csv(out / "cross_horizon_oos_comparison.csv", index=False)

    # Yearly OOS selected results for stability inspection.
    yearly_rows = []
    for year, q in oos.assign(year=oos.signal_date.dt.year).groupby("year"):
        daily = q.groupby("signal_day", as_index=False).return_R.mean()
        yearly_rows.append({"year": int(year), "signals": len(q), "signal_days": len(daily),
                            "mean_R": daily.return_R.mean(), "median_R": daily.return_R.median(),
                            "win_day_rate": (daily.return_R > 0).mean()})
    pd.DataFrame(yearly_rows).to_csv(out / "cross_horizon_oos_yearly.csv", index=False)

    print("=== WALK-FORWARD HORIZON SELECTIONS ===")
    print(selections_df.to_string(index=False))
    print("\n=== OOS COMPARISON ===")
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n=== SELECTED OOS YEARLY ===")
    print(pd.DataFrame(yearly_rows).to_string(index=False))


if __name__ == "__main__":
    main()
