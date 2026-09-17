"""Cost-free, point/R-normalized CPR signal baseline and conditional diagnostics."""
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


def _pvalue_mean(values: pd.Series) -> float:
    """Two-sided one-sample t-test against zero, without scipy dependency."""
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(x) < 2:
        return float("nan")
    sd = x.std(ddof=1)
    if sd == 0:
        return 0.0 if x.mean() != 0 else 1.0
    try:
        from scipy.stats import t as student_t  # type: ignore
        return float(2.0 * student_t.sf(abs(x.mean() / (sd / np.sqrt(len(x)))), len(x) - 1))
    except ImportError:
        return float("nan")


def summarize(z: pd.DataFrame, group: str) -> dict[str, object]:
    r = z["close_pnl_r"]
    return {
        "group": group,
        "signals": len(z),
        "long_signals": int((z.side == "LONG").sum()),
        "short_signals": int((z.side == "SHORT").sum()),
        "mean_close_R": r.mean(),
        "median_close_R": r.median(),
        "win_rate_close": (r > 0).mean(),
        "mean_MFE_R": z.mfe_r.mean(),
        "median_MFE_R": z.mfe_r.median(),
        "mean_MAE_R": z.mae_r.mean(),
        "median_MAE_R": z.mae_r.median(),
        "p25_close_R": r.quantile(0.25),
        "p75_close_R": r.quantile(0.75),
        "p_value_mean_R": _pvalue_mean(r),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()

    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    bars = load_ohlcv_csv(a.input)
    daily = bars.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    daily["day_return"] = daily.close.pct_change()
    daily["day_range_atr"] = (daily.high - daily.low) / daily_reference_features(daily)["D_ATR20"].reindex(daily.index)
    daily_features = daily_reference_features(daily)
    x = add_intraday_daily_features(bars, daily_features)
    config = StrategyConfig(narrow_x=NARROW_X, wide_y=WIDE_Y, atr_stop=1.0, target_r=2.0, exit_time="15:15")
    signals = intraday_directional_signals(x, config)

    rows = []
    for i, (ts, r) in enumerate(x.iloc[:-1].iterrows()):
        side = "LONG" if bool(signals.loc[ts, "long_entry"]) else "SHORT" if bool(signals.loc[ts, "short_entry"]) else None
        atr = r.get("D_ATR20")
        if side is None or pd.isna(atr) or float(atr) <= 0:
            continue
        nxt = x.iloc[i + 1]
        entry = float(nxt.open)
        atr = float(atr)
        direction = 1 if side == "LONG" else -1
        close_pnl = direction * (float(nxt.close) - entry)
        mfe = float(nxt.high) - entry if direction == 1 else entry - float(nxt.low)
        mae = float(nxt.low) - entry if direction == 1 else entry - float(nxt.high)
        width_ratio = float(r.get("D_CPR_width_ATR_ratio")) if pd.notna(r.get("D_CPR_width_ATR_ratio")) else np.nan
        regime = "narrow" if width_ratio < NARROW_X else "wide" if width_ratio > WIDE_Y else "neutral"
        signal_type = "narrow_breakout" if regime == "narrow" else "wide_reversal" if regime == "wide" else "neutral_signal"
        day = pd.Timestamp(ts).normalize()
        day_close = float(r.close)
        day_open = float(x.loc[day].open) if day in x.index.normalize() else np.nan
        intraday_direction = "up" if day_close >= day_open else "down"
        rows.append({
            "signal_time": ts,
            "entry_time": x.index[i + 1],
            "date": pd.Timestamp(ts).date(),
            "hour": ts.hour,
            "side": side,
            "signal_type": signal_type,
            "cpr_regime": regime,
            "width_ratio": width_ratio,
            "entry_price": entry,
            "next_close_pnl_points": close_pnl,
            "next_close_return_pct": 100.0 * close_pnl / entry,
            "mfe_points": mfe,
            "mae_points": mae,
            "close_pnl_r": close_pnl / atr,
            "mfe_r": mfe / atr,
            "mae_r": mae / atr,
            "D_ATR20": atr,
            "prior_day_return_pct": 100.0 * float(r.get("D_Close", np.nan)) / float(r.get("D_Close", np.nan)) - 100.0,
        })

    events = pd.DataFrame(rows)
    if events.empty:
        raise SystemExit("No CPR signals generated")

    # Regime-independent descriptive outputs.
    events.to_csv(out / "signal_events.csv", index=False)
    signals.to_csv(out / "signals.csv")

    metrics = [summarize(events, "ALL")]
    metrics.extend(summarize(events[events.side == side], side) for side in ("LONG", "SHORT") if (events.side == side).any())
    pd.DataFrame(metrics).to_csv(out / "signal_metrics.csv", index=False)

    groupings = [
        ("cpr_regime", ["narrow", "neutral", "wide"]),
        ("signal_type", ["narrow_breakout", "neutral_signal", "wide_reversal"]),
        ("side", ["LONG", "SHORT"]),
    ]
    conditional = []
    for column, levels in groupings:
        for level in levels:
            z = events[events[column] == level]
            if len(z):
                conditional.append(summarize(z, f"{column}={level}"))

    # Entry-time buckets are descriptive only; no threshold selection is performed.
    events["entry_bucket"] = pd.cut(events["hour"], bins=[-1, 10, 12, 14, 24], labels=["09:15-10:00", "10:01-12:00", "12:01-14:00", "14:01+"])
    for level in events.entry_bucket.dropna().unique():
        z = events[events.entry_bucket == level]
        conditional.append(summarize(z, f"entry_bucket={level}"))

    # Calendar-year stability is retained as an audit diagnostic, not an optimization target.
    events["year"] = pd.to_datetime(events.date).dt.year
    yearly = []
    for year, z in events.groupby("year"):
        yearly.append(summarize(z, f"year={year}"))

    pd.DataFrame(conditional).to_csv(out / "conditional_metrics.csv", index=False)
    pd.DataFrame(yearly).to_csv(out / "yearly_metrics.csv", index=False)

    print("=== ALL / DIRECTION ===")
    print(pd.DataFrame(metrics).to_string(index=False))
    print("\n=== CPR REGIME / SIGNAL TYPE / ENTRY TIME ===")
    print(pd.DataFrame(conditional).to_string(index=False))
    print("\n=== YEARLY STABILITY ===")
    print(pd.DataFrame(yearly).to_string(index=False))


if __name__ == "__main__":
    main()
