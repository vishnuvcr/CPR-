"""Run a cost-free, point/R-normalized CPR signal baseline on canonical 5-minute data."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.features import add_intraday_daily_features, daily_reference_features
from cpr_lab.strategy import StrategyConfig, generate_signals


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True)

    bars = load_ohlcv_csv(a.input)
    daily = bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    intraday = add_intraday_daily_features(bars, daily_reference_features(daily))
    cfg = StrategyConfig(narrow_x=0.50, wide_y=1.00, atr_stop=1.0, target_r=2.0, exit_time="15:15")
    sig = generate_signals(intraday, cfg)
    x = intraday.copy()
    x["long_entry"] = sig["long_entry"].astype(bool)
    x["short_entry"] = sig["short_entry"].astype(bool)
    rows = []
    for i, (ts, r) in enumerate(x.iloc[:-1].iterrows()):
        side = "LONG" if bool(r["long_entry"]) else "SHORT" if bool(r["short_entry"]) else None
        if side is None or pd.isna(r.get("D_ATR20")) or float(r.get("D_ATR20", 0)) <= 0:
            continue
        n = x.iloc[i + 1]
        entry, atr = float(n["open"]), float(r["D_ATR20"])
        direction = 1.0 if side == "LONG" else -1.0
        close_pnl = direction * (float(n["close"]) - entry)
        mfe = direction * (float(n["high"]) - entry) if side == "LONG" else direction * (entry - float(n["low"]))
        mae = direction * (float(n["low"]) - entry) if side == "LONG" else direction * (entry - float(n["high"]))
        rows.append({"signal_time":ts,"entry_time":x.index[i+1],"side":side,"entry_price":entry,
                     "next_close_pnl_points":close_pnl,"next_close_return_pct":100*close_pnl/entry,
                     "mfe_points":mfe,"mae_points":mae,"close_pnl_r":close_pnl/atr,
                     "mfe_r":mfe/atr,"mae_r":mae/atr,"D_ATR20":atr})
    events = pd.DataFrame(rows)
    if events.empty:
        raise SystemExit("No CPR signals generated")
    events.to_csv(out/"signal_events.csv", index=False)
    sig.to_csv(out/"signals.csv")

    def summary(df, group):
        r = df.close_pnl_r
        return {"group":group,"signals":len(df),"long_signals":int((df.side=="LONG").sum()),"short_signals":int((df.side=="SHORT").sum()),
                "mean_close_R":r.mean(),"median_close_R":r.median(),"win_rate_close":(r>0).mean(),
                "mean_MFE_R":df.mfe_r.mean(),"median_MFE_R":df.mfe_r.median(),"mean_MAE_R":df.mae_r.mean(),"median_MAE_R":df.mae_r.median(),
                "p25_close_R":r.quantile(.25),"p75_close_R":r.quantile(.75)}
    result = [summary(events,"ALL")]
    for side in ("LONG","SHORT"):
        z=events[events.side==side]
        if len(z): result.append(summary(z,side))
    pd.DataFrame(result).to_csv(out/"signal_metrics.csv", index=False)
    print(pd.DataFrame(result).to_string(index=False))

if __name__ == "__main__":
    main()
