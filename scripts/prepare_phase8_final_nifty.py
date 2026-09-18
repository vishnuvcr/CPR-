"""Prepare the 2026 NIFTY50 source for the final untouched forward holdout."""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
import pandas as pd

SOURCE_COMMIT="e8f19f3f53ca6fac0b116e83508e814e568dca54"
SOURCE_PATH="NIFTY50-INDEX.parquet"
SOURCE_URL=f"https://raw.githubusercontent.com/ganeshbiyer/Nse_Historical_Data_2026/{SOURCE_COMMIT}/{SOURCE_PATH}"
START="2026-01-01"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True,type=Path); ap.add_argument("--output",required=True,type=Path)
    a=ap.parse_args()
    raw=pd.read_parquet(a.input)
    req={"Date","Open","High","Low","Close","Volume"}
    miss=req-set(raw.columns)
    if miss: raise ValueError(f"Missing source columns: {sorted(miss)}")
    ts=pd.to_datetime(raw["Date"],errors="raise")
    ts=ts.dt.tz_localize("Asia/Kolkata") if ts.dt.tz is None else ts.dt.tz_convert("Asia/Kolkata")
    x=pd.DataFrame({
        "open":pd.to_numeric(raw["Open"],errors="raise").to_numpy(),
        "high":pd.to_numeric(raw["High"],errors="raise").to_numpy(),
        "low":pd.to_numeric(raw["Low"],errors="raise").to_numpy(),
        "close":pd.to_numeric(raw["Close"],errors="raise").to_numpy(),
        "volume":pd.to_numeric(raw["Volume"],errors="coerce").fillna(0).to_numpy(),
    },index=ts)
    dups=int(x.index.duplicated().sum())
    dup=x[x.index.duplicated(keep=False)]
    conflict_groups=0
    if not dup.empty:
        n=dup.groupby(level=0)[["open","high","low","close","volume"]].nunique()
        conflict_groups=int((n.max(axis=1)>1).sum())
        if conflict_groups:
            idx=n.index[n.max(axis=1)>1]
            x=x.loc[~x.index.isin(idx)].copy()
    before=len(x); x=x[~x.index.duplicated(keep="first")].sort_index()
    exact_excluded=before-len(x)
    x=x.between_time("09:15","15:29")
    bad=((x.high<x.low)|(x.open>x.high)|(x.open<x.low)|(x.close>x.high)|(x.close<x.low)|x[["open","high","low","close"]].isna().any(axis=1))
    bad_n=int(bad.sum()); x=x.loc[~bad].copy()
    bucket=x.index.floor("5min")
    bars_all=x.groupby(bucket,sort=True).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),volume=("volume","sum"))
    counts=x.close.groupby(bucket,sort=True).count()
    keep=counts.eq(5); bars=bars_all.loc[keep].copy()
    bars.index.name="timestamp"
    start=pd.Timestamp(START,tz="Asia/Kolkata"); bars=bars[bars.index>=start]
    if bars.empty: raise ValueError("No complete 5-minute bars after 2026-01-01")
    a.output.parent.mkdir(parents=True,exist_ok=True); bars.to_csv(a.output,index_label="timestamp")
    counts.rename("source_minute_count").to_frame().assign(retained=keep).to_csv(a.output.with_suffix(".source_counts.csv"))
    sha=hashlib.sha256(a.input.read_bytes()).hexdigest()
    prov=a.output.with_suffix(".provenance.txt")
    prov.write_text("\n".join([
        "PHASE 8 FINAL UNTOUCHED FORWARD HOLDOUT DATASET",
        f"source_url={SOURCE_URL}",f"source_commit={SOURCE_COMMIT}",f"source_file={SOURCE_PATH}",
        f"source_file_sha256={sha}","instrument=NIFTY50 index","source_frequency=1-minute","derived_frequency=5-minute",
        "session=09:15-15:30 Asia/Kolkata",f"holdout_start={START}",f"source_rows={len(raw)}",
        f"source_duplicate_timestamp_rows_detected={dups}",f"source_exact_duplicate_timestamp_rows_excluded={exact_excluded}",
        f"source_conflicting_duplicate_timestamp_groups={conflict_groups}",f"source_invalid_or_missing_ohlc_excluded={bad_n}",
        f"complete_5_minute_bins_before_date_cut={int(keep.sum())}",f"holdout_5m_rows={len(bars)}",
        f"holdout_start_actual={bars.index.min()}",f"holdout_end_actual={bars.index.max()}",
        "note=Untouched 2026 source; frozen Phase 5A candidates are evaluated without refitting or selection."
    ]),encoding="utf-8")
    print(prov.read_text())
if __name__=="__main__": main()
