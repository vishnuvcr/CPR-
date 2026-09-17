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
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(x) < 2:
        return float("nan")
    sd = x.std(ddof=1)
    if sd == 0:
        return 0.0 if x.mean() != 0 else 1.0
    try:
        from scipy.stats import t as student_t  # type: ignore
        statistic = x.mean() / (sd / np.sqrt(len(x)))
        return float(2.0 * student_t.sf(abs(statistic), len(x) - 1))
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
    daily_features = daily_reference_features(daily)
    x = add_intraday_daily_features(bars, daily_features)
    config = StrategyConfig(narrow_x=NARROW_X, wide_y=WIDE_Y, atr_stop=1.0, target_r=2.0, exit_time="15:15")
    signals = intraday_directional_signals(x, config)

    rows = []
    for i, (ts, r) in enumerate(x.iloc[:-1].iterrows()):
        side = "LONG" if bool(signals.loc[ts, "long_entry"]) else "SHORT" if bool(signals.loc[ts, "short_entry"]) else None
        atr = r.get("D_ATR20")
        width_ratio = r.get("D_CPR_width_ATR_ratio")
        if side is None or pd.isna(atr) or float(atr) <= 0 or pd.isna(width_ratio):
            continue

        nxt = x.iloc[i + 1]
        entry = float(nxt.open)
        atr = float(atr)
        width_ratio = float(width_ratio)
        direction = 1 if side == "LONG" else -1
        close_pnl = direction * (float(nxt.close) - entry)
        mfe = float(nxt.high) - entry if direction == 1 else entry - float(nxt.low)
        mae = float(nxt.low) - entry if direction == 1 else entry - float(nxt.high)
        regime = "narrow" if width_ratio < NARROW_X else "wide" if width_ratio > WIDE_Y else "neutral"
        signal_type = "narrow_breakout" if regime == "narrow" else "wide_reversal" if regime == "wide" else "neutral_signal"
        entry_minutes = ts.hour * 60 + ts.minute
        entry_bucket = "09:15-10:00" if entry_minutes <= 600 else "10:01-12:00" if entry_minutes <= 720 else "12:01-14:00" if entry_minutes <= 840 else "14:01+"
        rows.append({
            "signal_time": ts,
            "entry_time": x.index[i + 1],
            "date": ts.date(),
            "year": ts.year,
            "hour": ts.hour,
            "side": side,
            "signal_type": signal_type,
            "cpr_regime": regime,
            "entry_bucket": entry_bucket,
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
        })

    events = pd.DataFrame(rows)
    if events.empty:
        raise SystemExit("No CPR signals generated")

    events.to_csv(out / "signal_events.csv", index=False)
    signals.to_csv(out / "signals.csv")

    base_metrics = [summarize(events, "ALL")]
    base_metrics.extend(summarize(events[events.side == side], side) for side in ("LONG", "SHORT") if (events.side == side).any())
    pd.DataFrame(base_metrics).to_csv(out / "signal_metrics.csv", index=False)

    groupings = [
        ("cpr_regime", ["narrow", "neutral", "wide"]),
        ("signal_type", ["narrow_breakout", "neutral_signal", "wide_reversal"]),
        ("side", ["LONG", "SHORT"]),
        ("entry_bucket", ["09:15-10:00", "10:01-12:00", "12:01-14:00", "14:01+"]),
    ]
    conditional = []
    for column, levels in groupings:
        for level in levels:
            z = events[events[column] == level]
            if len(z):
                conditional.append(summarize(z, f"{column}={level}"))

    yearly = [summarize(z, f"year={year}") for year, z in events.groupby("year")]
    pd.DataFrame(conditional).to_csv(out / "conditional_metrics.csv", index=False)
    pd.DataFrame(yearly).to_csv(out / "yearly_metrics.csv", index=False)

    print("=== ALL / DIRECTION ===")
    print(pd.DataFrame(base_metrics).to_string(index=False))
    print("\n=== CPR REGIME / SIGNAL TYPE / ENTRY TIME ===")
    print(pd.DataFrame(conditional).to_string(index=False))
    print("\n=== YEARLY STABILITY ===")
    print(pd.DataFrame(yearly).to_string(index=False))


if __name__ == "__main__":
    main()
