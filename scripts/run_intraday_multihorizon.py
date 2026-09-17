"""Phase 1C: cost-free multi-horizon outcomes for CPR signals."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from cpr_lab.strategies import StrategyConfig, intraday_directional_signals

HORIZONS = (1, 3, 6, 12)
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
    signals = intraday_directional_signals(x, StrategyConfig(narrow_x=NARROW_X, wide_y=WIDE_Y, atr_stop=1.0, target_r=2.0, exit_time="15:15"))

    rows: list[dict[str, object]] = []
    for i in range(len(x)):
        if i + max(HORIZONS) >= len(x):
            break
        ts = x.index[i]
        side = "LONG" if bool(signals.loc[ts, "long_entry"]) else "SHORT" if bool(signals.loc[ts, "short_entry"]) else None
        atr = x.iloc[i].get("D_ATR20")
        width = x.iloc[i].get("D_CPR_width_ATR_ratio")
        if side is None or pd.isna(atr) or float(atr) <= 0 or pd.isna(width):
            continue
        entry_i = i + 1
        entry = float(x.iloc[entry_i].open)
        direction = 1 if side == "LONG" else -1
        regime = "narrow" if float(width) < NARROW_X else "wide" if float(width) > WIDE_Y else "neutral"
        bucket = "09:15-10:00" if ts.hour*60+ts.minute <= 600 else "10:01-12:00" if ts.hour*60+ts.minute <= 720 else "12:01-14:00" if ts.hour*60+ts.minute <= 840 else "14:01+"
        base = {"signal_time":ts, "entry_time":x.index[entry_i], "date":ts.date(), "year":ts.year, "side":side, "regime":regime, "entry_bucket":bucket, "width_ratio":float(width), "entry_price":entry, "ATR":float(atr)}
        for h in HORIZONS:
            j = entry_i + h - 1
            if j >= len(x):
                continue
            close = float(x.iloc[j].close)
            future = x.iloc[entry_i:j+1]
            pnl = direction * (close-entry)
            mfe = direction * ((future.high.max() if direction == 1 else future.low.min()) - entry)
            mae = direction * ((future.low.min() if direction == 1 else future.high.max()) - entry)
            row = dict(base)
            row.update({"horizon_bars":h, "horizon":f"{h}bar", "exit_time":x.index[j], "return_points":pnl, "return_pct":100*pnl/entry, "return_R":pnl/float(atr), "mfe_R":mfe/float(atr), "mae_R":mae/float(atr)})
            rows.append(row)

        # EOD is measured from next-bar open through the final bar of the same session.
        day_rows = x.loc[x.index.date == ts.date()]
        day_rows = day_rows.loc[day_rows.index >= x.index[entry_i]]
        if not day_rows.empty:
            close = float(day_rows.iloc[-1].close)
            pnl = direction * (close-entry)
            mfe = direction * ((day_rows.high.max() if direction == 1 else day_rows.low.min()) - entry)
            mae = direction * ((day_rows.low.min() if direction == 1 else day_rows.high.max()) - entry)
            row = dict(base)
            row.update({"horizon_bars":len(day_rows), "horizon":"EOD", "exit_time":day_rows.index[-1], "return_points":pnl, "return_pct":100*pnl/entry, "return_R":pnl/float(atr), "mfe_R":mfe/float(atr), "mae_R":mae/float(atr)})
            rows.append(row)

    events = pd.DataFrame(rows)
    if events.empty:
        raise SystemExit("No valid CPR signals")
    events.to_csv(out / "multihorizon_events.csv", index=False)

    summaries = []
    for h, z in events.groupby("horizon", sort=False):
        summaries.append(summarize(z, "ALL", h))
        for side in ("LONG", "SHORT"):
            q = z[z.side == side]
            if len(q): summaries.append(summarize(q, side, h))
        for regime in ("narrow", "neutral", "wide"):
            q = z[z.regime == regime]
            if len(q): summaries.append(summarize(q, f"regime={regime}", h))
        for bucket in ("09:15-10:00","10:01-12:00","12:01-14:00","14:01+"):
            q = z[z.entry_bucket == bucket]
            if len(q): summaries.append(summarize(q, f"entry={bucket}", h))
    pd.DataFrame(summaries).to_csv(out / "multihorizon_metrics.csv", index=False)

    yearly = []
    for (year,h), z in events.groupby(["year","horizon"], sort=True):
        yearly.append(summarize(z, f"year={year}", h))
    pd.DataFrame(yearly).to_csv(out / "multihorizon_yearly_metrics.csv", index=False)

    print("=== MULTI-HORIZON ALL / DIRECTION ===")
    print(pd.DataFrame(summaries)[pd.DataFrame(summaries).group.isin(["ALL","LONG","SHORT"])].to_string(index=False))
    print("\n=== YEARLY MULTI-HORIZON ===")
    print(pd.DataFrame(yearly).to_string(index=False))


if __name__ == "__main__":
    main()
