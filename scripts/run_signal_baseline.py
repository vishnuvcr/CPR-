"""Run a cost-free, point/R-normalized CPR signal baseline on canonical 5-minute data.

This is deliberately separated from tradable execution. It measures the statistical
behaviour of the CPR hypotheses without brokerage, STT, slippage, leverage or lot-size
effects. Signals are still generated from information available at the time of the bar.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.features import add_intraday_daily_features, daily_reference_features
from cpr_lab.strategy import StrategyConfig, generate_signals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    bars = load_ohlcv_csv(args.input)
    daily = bars.resample("1D").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna(subset=["open", "high", "low", "close"])
    daily = daily_reference_features(daily)
    intraday = add_intraday_daily_features(bars, daily)

    cfg = StrategyConfig(
        narrow_x=0.50,
        wide_y=1.00,
        atr_stop=1.0,
        target_r=2.0,
        exit_time="15:15",
    )
    signals = generate_signals(intraday, cfg)

    # Signal-only forward outcome: enter at next bar OPEN and measure the maximum
    # favourable/adverse excursion and close-to-close outcome in ATR-normalized units.
    x = intraday.copy()
    x["long_entry"] = signals["long_entry"].astype(bool)
    x["short_entry"] = signals["short_entry"].astype(bool)
    x["next_open"] = x["open"].shift(-1)
    x["next_high"] = x["high"].shift(-1)
    x["next_low"] = x["low"].shift(-1)
    x["next_close"] = x["close"].shift(-1)
    x["D_ATR20"] = x["D_ATR20"].replace(0, pd.NA)

    rows = []
    for ts, r in x.iterrows():
        side = "LONG" if bool(r["long_entry"]) else "SHORT" if bool(r["short_entry"]) else None
        if side is None or pd.isna(r["next_open"]) or pd.isna(r["D_ATR20"]):
            continue
        entry = float(r["next_open"])
        atr = float(r["D_ATR20"])
        direction = 1.0 if side == "LONG" else -1.0
        favourable = direction * (float(r["next_high"]) - entry) if side == "LONG" else direction * (entry - float(r["next_low"]))
        adverse = direction * (float(r["next_low"]) - entry) if side == "LONG" else direction * (entry - float(r["next_high"]))
        close_pnl = direction * (float(r["next_close"]) - entry)
        rows.append({
            "signal_time": ts,
            "entry_time": x.index[x.index.get_loc(ts) + 1],
            "side": side,
            "entry_price": entry,
            "next_close_pnl_points": close_pnl,
            "next_close_return_pct": 100.0 * close_pnl / entry,
            "mfe_points": favourable,
            "mae_points": adverse,
            "close_pnl_r": close_pnl / atr,
            "mfe_r": favourable / atr,
            "mae_r": adverse / atr,
            "D_ATR20": atr,
        })

    events = pd.DataFrame(rows)
    if events.empty:
        raise SystemExit("No CPR signals were generated; refusing to create a misleading baseline.")

    events.to_csv(out / "signal_events.csv", index=False)
    signals.to_csv(out / "signals.csv")

    def summarize(df: pd.DataFrame, label: str) -> dict:
        pnl = df["close_pnl_r"]
        return {
            "group": label,
            "signals": int(len(df)),
            "long_signals": int((df["side"] == "LONG").sum()),
            "short_signals": int((df["side"] == "SHORT").sum()),
            "mean_close_R": float(pnl.mean()),
            "median_close_R": float(pnl.median()),
            "win_rate_close": float((pnl > 0).mean()),
            "mean_MFE_R": float(df["mfe_r"].mean()),
            "median_MFE_R": float(df["mfe_r"].median()),
            "mean_MAE_R": float(df["mae_r"].mean()),
            "median_MAE_R": float(df["mae_r"].median()),
            "p25_close_R": float(pnl.quantile(0.25)),
            "p75_close_R": float(pnl.quantile(0.75)),
        }

    summaries = [summarize(events, "ALL")]
    for side in ("LONG", "SHORT"):
        part = events[events["side"] == side]
        if not part.empty:
            summaries.append(summarize(part, side))

    # CPR width/regime dimensions are taken directly from the signal-generation frame.
    meta_cols = [c for c in ["cpr_width", "D_ATR20", "inside_day", "narrow_cpr", "wide_cpr"] if c in x.columns]
    if meta_cols:
        enriched = events.merge(x[meta_cols], left_on="signal_time", right_index=True, how="left")
        if "narrow_cpr" in enriched:
            part = enriched[enriched["narrow_cpr"].fillna(False)]
            if len(part):
                summaries.append(summarize(part, "NARROW_CPR"))
        if "wide_cpr" in enriched:
            part = enriched[enriched["wide_cpr"].fillna(False)]
            if len(part):
                summaries.append(summarize(part, "WIDE_CPR"))

    pd.DataFrame(summaries).to_csv(out / "signal_metrics.csv", index=False)
    print(f"signals={len(events)}")
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__ == "__main__":
    main()
