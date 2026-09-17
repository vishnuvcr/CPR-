"""Phase 2A: cost-free BTST/overnight characterization of CPR signals.

Discovery-only diagnostic. Signal generation is unchanged and bias-safe; no
threshold, horizon, or subgroup is optimized from the observed outcomes.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from cpr_lab.strategies import StrategyConfig, intraday_directional_signals

NARROW_X = 0.50
WIDE_Y = 1.00


def pvalue_mean(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    if len(x) < 2 or np.std(x, ddof=1) == 0:
        return 1.0 if len(x) and x.mean() == 0 else 0.0 if len(x) else float("nan")
    try:
        from scipy.stats import t
        return float(2 * t.sf(abs(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))), len(x) - 1))
    except ImportError:
        return float("nan")


def summarize(z: pd.DataFrame, group: str, horizon: str) -> dict[str, object]:
    r = z["return_R"]
    return {
        "group": group,
        "horizon": horizon,
        "signals": len(z),
        "mean_R": r.mean(),
        "median_R": r.median(),
        "win_rate": (r > 0).mean(),
        "mean_MFE_R": z.mfe_R.mean(),
        "mean_MAE_R": z.mae_R.mean(),
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
    daily = bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    x = add_intraday_daily_features(bars, daily_reference_features(daily))
    signals = intraday_directional_signals(
        x, StrategyConfig(narrow_x=NARROW_X, wide_y=WIDE_Y, atr_stop=1.0, target_r=2.0, exit_time="15:15")
    )

    # Session metadata from the canonical intraday series.
    session_dates = pd.Series(x.index.date, index=x.index)
    sessions = pd.Index(sorted(session_dates.unique()))
    next_session = {sessions[i]: sessions[i + 1] for i in range(len(sessions) - 1)}

    rows: list[dict[str, object]] = []
    for i in range(len(x) - 1):
        ts = x.index[i]
        side = "LONG" if bool(signals.loc[ts, "long_entry"]) else "SHORT" if bool(signals.loc[ts, "short_entry"]) else None
        atr = x.iloc[i].get("D_ATR20")
        width = x.iloc[i].get("D_CPR_width_ATR_ratio")
        if side is None or pd.isna(atr) or float(atr) <= 0 or pd.isna(width):
            continue

        d = ts.date()
        nd = next_session.get(d)
        if nd is None:
            continue
        next_rows = x.loc[session_dates == nd]
        if next_rows.empty:
            continue

        direction = 1 if side == "LONG" else -1
        regime, bucket = classify(ts, float(width))
        entry = float(x.iloc[i + 1].open) if i + 1 < len(x) and x.index[i + 1].date() == d else float(x.loc[session_dates == d].iloc[-1].close)
        same_day_close = float(x.loc[session_dates == d].iloc[-1].close)
        next_open = float(next_rows.iloc[0].open)
        next_close = float(next_rows.iloc[-1].close)
        next_high = float(next_rows.high.max())
        next_low = float(next_rows.low.min())
        atr_f = float(atr)

        # BTST is explicitly defined as source-session close to next-session open.
        overnight_pnl = direction * (next_open - same_day_close)
        # Next-day holding starts at next-session open and exits at next-session close.
        nextday_pnl = direction * (next_close - next_open)
        future = next_rows
        mfe = direction * ((future.high.max() if direction == 1 else future.low.min()) - next_open)
        mae = direction * ((future.low.min() if direction == 1 else future.high.max()) - next_open)
        rows.append({
            "signal_time": ts,
            "signal_date": d,
            "next_session": nd,
            "year": ts.year,
            "side": side,
            "regime": regime,
            "entry_bucket": bucket,
            "width_ratio": float(width),
            "source_close": same_day_close,
            "next_open": next_open,
            "next_close": next_close,
            "next_high": next_high,
            "next_low": next_low,
            "overnight_return_pct": 100 * overnight_pnl / same_day_close,
            "overnight_R": overnight_pnl / atr_f,
            "nextday_return_pct": 100 * nextday_pnl / next_open,
            "return_R": nextday_pnl / atr_f,
            "mfe_R": mfe / atr_f,
            "mae_R": mae / atr_f,
        })

    events = pd.DataFrame(rows)
    if events.empty:
        raise SystemExit("No valid BTST signals")
    events.to_csv(out / "btst_events.csv", index=False)

    summaries = []
    for horizon, col in (("overnight", "overnight_R"), ("nextday", "return_R")):
        z0 = events.rename(columns={col: "return_R"})
        summaries.append(summarize(z0, "ALL", horizon))
        for side in ("LONG", "SHORT"):
            q = z0[z0.side == side]
            if len(q): summaries.append(summarize(q, side, horizon))
        for regime in ("narrow", "neutral", "wide"):
            q = z0[z0.regime == regime]
            if len(q): summaries.append(summarize(q, f"regime={regime}", horizon))
        for bucket in ("09:15-10:00", "10:01-12:00", "12:01-14:00", "14:01+"):
            q = z0[z0.entry_bucket == bucket]
            if len(q): summaries.append(summarize(q, f"entry={bucket}", horizon))

    metrics = pd.DataFrame(summaries)
    metrics.to_csv(out / "btst_metrics.csv", index=False)

    yearly = []
    for (year, horizon), z in events.assign(_dummy=1).groupby(["year", "_dummy"]):
        for h, col in (("overnight", "overnight_R"), ("nextday", "return_R")):
            zz = z.rename(columns={col: "return_R"})
            yearly.append(summarize(zz, f"year={year}", h))
    yearly_df = pd.DataFrame(yearly)
    yearly_df.to_csv(out / "btst_yearly_metrics.csv", index=False)

    print("=== BTST ALL / DIRECTION ===")
    print(metrics[metrics.group.isin(["ALL", "LONG", "SHORT"])].to_string(index=False))
    print("\n=== BTST YEARLY ===")
    print(yearly_df.to_string(index=False))


if __name__ == "__main__":
    main()
