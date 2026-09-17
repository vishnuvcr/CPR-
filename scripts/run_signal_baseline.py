"""Cost-free, point/R-normalized CPR signal baseline."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from cpr_lab.strategies import StrategyConfig, intraday_directional_signals


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()

    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    bars = load_ohlcv_csv(a.input)
    daily = (
        bars.resample("1D")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )
    x = add_intraday_daily_features(bars, daily_reference_features(daily))
    config = StrategyConfig(
        narrow_x=0.50,
        wide_y=1.00,
        atr_stop=1.0,
        target_r=2.0,
        exit_time="15:15",
    )
    signals = intraday_directional_signals(x, config)

    rows = []
    for i, (ts, r) in enumerate(x.iloc[:-1].iterrows()):
        side = (
            "LONG" if bool(signals.loc[ts, "long_entry"])
            else "SHORT" if bool(signals.loc[ts, "short_entry"])
            else None
        )
        atr = r.get("D_ATR20")
        if side is None or pd.isna(atr) or float(atr) <= 0:
            continue

        nxt = x.iloc[i + 1]
        entry = float(nxt.open)
        atr = float(atr)
        direction = 1 if side == "LONG" else -1
        close_pnl = direction * (float(nxt.close) - entry)
        mfe = (
            float(nxt.high) - entry
            if direction == 1
            else entry - float(nxt.low)
        )
        mae = (
            float(nxt.low) - entry
            if direction == 1
            else entry - float(nxt.high)
        )

        rows.append(
            {
                "signal_time": ts,
                "entry_time": x.index[i + 1],
                "side": side,
                "entry_price": entry,
                "next_close_pnl_points": close_pnl,
                "next_close_return_pct": 100.0 * close_pnl / entry,
                "mfe_points": mfe,
                "mae_points": mae,
                "close_pnl_r": close_pnl / atr,
                "mfe_r": mfe / atr,
                "mae_r": mae / atr,
                "D_ATR20": atr,
            }
        )

    events = pd.DataFrame(rows)
    if events.empty:
        raise SystemExit("No CPR signals generated")

    events.to_csv(out / "signal_events.csv", index=False)
    signals.to_csv(out / "signals.csv")

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
        }

    metrics = [summarize(events, "ALL")]
    metrics.extend(
        summarize(events[events.side == side], side)
        for side in ("LONG", "SHORT")
        if (events.side == side).any()
    )
    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(out / "signal_metrics.csv", index=False)
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
