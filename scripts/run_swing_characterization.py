"""Phase 3A: cost-free swing-horizon characterization of CPR signals.

Discovery-only diagnostic. The unchanged CPR directional signal is evaluated
at a completed source bar and executed at the following bar open. Outcomes
are measured to the close of the 2nd, 3rd, 5th and 10th subsequent trading
sessions. No threshold, horizon, stop, target, or subgroup is optimized from
observed profitability.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from cpr_lab.strategies import StrategyConfig, intraday_directional_signals

HORIZONS = (2, 3, 5, 10)
NARROW_X = 0.50
WIDE_Y = 1.00


def pvalue_mean(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    if len(x) < 2:
        return float("nan")
    sd = x.std(ddof=1)
    if sd == 0:
        return 1.0 if x.mean() == 0 else 0.0
    try:
        from scipy.stats import t
        statistic = x.mean() / (sd / np.sqrt(len(x)))
        return float(2 * t.sf(abs(statistic), len(x) - 1))
    except ImportError:
        return float("nan")


def summarize(z: pd.DataFrame, group: str, horizon: str) -> dict[str, object]:
    r = pd.to_numeric(z["return_R"], errors="coerce").dropna()
    return {
        "group": group,
        "horizon": horizon,
        "signals": len(r),
        "mean_R": r.mean(),
        "median_R": r.median(),
        "win_rate": (r > 0).mean(),
        "mean_MFE_R": pd.to_numeric(z.loc[r.index, "mfe_R"], errors="coerce").mean(),
        "mean_MAE_R": pd.to_numeric(z.loc[r.index, "mae_R"], errors="coerce").mean(),
        "p25_R": r.quantile(.25),
        "p75_R": r.quantile(.75),
        "p_value_mean_R": pvalue_mean(r),
    }


def classify(ts: pd.Timestamp, width: float) -> tuple[str, str]:
    regime = "narrow" if width < NARROW_X else "wide" if width > WIDE_Y else "neutral"
    mins = ts.hour * 60 + ts.minute
    bucket = "09:15-10:00" if mins <= 600 else "10:01-12:00" if mins <= 720 else "12:01-14:00" if mins <= 840 else "14:01+"
    return regime, bucket


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    bars = load_ohlcv_csv(a.input)
    daily = bars.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    x = add_intraday_daily_features(bars, daily_reference_features(daily))
    signals = intraday_directional_signals(
        x,
        StrategyConfig(narrow_x=NARROW_X, wide_y=WIDE_Y, atr_stop=1.0, target_r=2.0, exit_time="15:15"),
    )

    session_dates = pd.Series(x.index.date, index=x.index)
    sessions = pd.Index(sorted(session_dates.unique()))
    session_rows = {d: np.flatnonzero((session_dates == d).to_numpy()) for d in sessions}
    session_pos = {d: i for i, d in enumerate(sessions)}

    rows: list[dict[str, object]] = []
    for i in range(len(x) - 1):
        ts = x.index[i]
        side = "LONG" if bool(signals.loc[ts, "long_entry"]) else "SHORT" if bool(signals.loc[ts, "short_entry"]) else None
        atr = x.iloc[i].get("D_ATR20")
        width = x.iloc[i].get("D_CPR_width_ATR_ratio")
        if side is None or pd.isna(atr) or float(atr) <= 0 or pd.isna(width):
            continue

        entry_i = i + 1
        entry_ts = x.index[entry_i]
        entry_date = entry_ts.date()
        if entry_date not in session_pos:
            continue
        entry_session_idx = session_pos[entry_date]
        direction = 1 if side == "LONG" else -1
        regime, bucket = classify(ts, float(width))
        entry = float(x.iloc[entry_i].open)
        atr_f = float(atr)

        for h in HORIZONS:
            target_idx = entry_session_idx + h - 1
            if target_idx >= len(sessions):
                continue
            target_date = sessions[target_idx]
            start_i = entry_i
            end_i = int(session_rows[target_date][-1])
            if end_i < start_i:
                continue
            future = x.iloc[start_i:end_i + 1]
            exit_close = float(future.iloc[-1].close)
            pnl = direction * (exit_close - entry)
            mfe = direction * ((future.high.max() if direction == 1 else future.low.min()) - entry)
            mae = direction * ((future.low.min() if direction == 1 else future.high.max()) - entry)
            rows.append({
                "signal_time": ts,
                "entry_time": entry_ts,
                "signal_date": ts.date(),
                "entry_session": entry_date,
                "target_session": target_date,
                "year": ts.year,
                "side": side,
                "regime": regime,
                "entry_bucket": bucket,
                "width_ratio": float(width),
                "entry_price": entry,
                "exit_time": future.index[-1],
                "exit_close": exit_close,
                "horizon_sessions": h,
                "horizon": f"{h}session",
                "return_points": pnl,
                "return_pct": 100 * pnl / entry,
                "return_R": pnl / atr_f,
                "mfe_R": mfe / atr_f,
                "mae_R": mae / atr_f,
            })

    events = pd.DataFrame(rows)
    if events.empty:
        raise SystemExit("No valid CPR swing signals")
    events.to_csv(out / "swing_events.csv", index=False)

    summaries: list[dict[str, object]] = []
    for h, z in events.groupby("horizon", sort=False):
        summaries.append(summarize(z, "ALL", h))
        for side in ("LONG", "SHORT"):
            q = z[z.side == side]
            if len(q):
                summaries.append(summarize(q, side, h))
        for regime in ("narrow", "neutral", "wide"):
            q = z[z.regime == regime]
            if len(q):
                summaries.append(summarize(q, f"regime={regime}", h))
        for bucket in ("09:15-10:00", "10:01-12:00", "12:01-14:00", "14:01+"):
            q = z[z.entry_bucket == bucket]
            if len(q):
                summaries.append(summarize(q, f"entry={bucket}", h))
    metrics = pd.DataFrame(summaries)
    metrics.to_csv(out / "swing_metrics.csv", index=False)

    yearly: list[dict[str, object]] = []
    for (year, h), z in events.groupby(["year", "horizon"], sort=True):
        yearly.append(summarize(z, f"year={year}", h))
    pd.DataFrame(yearly).to_csv(out / "swing_yearly_metrics.csv", index=False)

    print("=== SWING ALL / DIRECTION ===")
    print(metrics[metrics.group.isin(["ALL", "LONG", "SHORT"])].to_string(index=False))
    print("\n=== SWING YEARLY ===")
    print(pd.DataFrame(yearly).to_string(index=False))


if __name__ == "__main__":
    main()
