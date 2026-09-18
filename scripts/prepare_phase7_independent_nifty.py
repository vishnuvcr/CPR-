"""Prepare the independent NIFTY50 index parquet source for Phase 7 replication."""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
import pandas as pd

SOURCE_COMMIT="0cf3c94ecc5cfd87cc1823c17f3b2cf63d80f8e9"
SOURCE_PATH="NIFTY50-INDEX.parquet"
SOURCE_URL=f"https://raw.githubusercontent.com/ganeshbiyer/Nse_Historical_Data/{SOURCE_COMMIT}/{SOURCE_PATH}"
REPLICATION_START="2024-04-01"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    a=ap.parse_args()
    raw=pd.read_parquet(a.input)
    required={"Date","Open","High","Low","Close","Volume"}
    missing=required-set(raw.columns)
    if missing: raise ValueError(f"Missing source columns: {sorted(missing)}")
    ts=pd.to_datetime(raw["Date"],errors="raise")
    if ts.dt.tz is None: ts=ts.dt.tz_localize("Asia/Kolkata")
    else: ts=ts.dt.tz_convert("Asia/Kolkata")
    x=pd.DataFrame({
        "open":pd.to_numeric(raw["Open"],errors="raise").to_numpy(),
        "high":pd.to_numeric(raw["High"],errors="raise").to_numpy(),
        "low":pd.to_numeric(raw["Low"],errors="raise").to_numpy(),
        "close":pd.to_numeric(raw["Close"],errors="raise").to_numpy(),
        "volume":pd.to_numeric(raw["Volume"],errors="coerce").fillna(0).to_numpy(),
    },index=ts)
    dups=int(x.index.duplicated().sum())
    print(f"source_duplicate_timestamps={dups}")
    if dups: raise ValueError(f"Duplicate timestamps in independent source: {dups}")
    x=x.sort_index().between_time("09:15","15:29")
    bad=((x.high<x.low)|(x.open>x.high)|(x.open<x.low)|(x.close>x.high)|(x.close<x.low)|x[["open","high","low","close"]].isna().any(axis=1))
    print(f"source_invalid_or_missing_ohlc={int(bad.sum())}")
    if bad.any():
        # Do not repair/fill malformed source observations. Exclude them and
        # retain the count in provenance so the independent source remains auditable.
        x=x.loc[~bad].copy()
    bucket=x.index.floor("5min")
    bars_all=x.groupby(bucket,sort=True).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),volume=("volume","sum"))
    counts=x.close.groupby(bucket,sort=True).count()
    keep=counts.eq(5)
    bars=bars_all.loc[keep].copy()
    bars.index.name="timestamp"
    if bars.empty: raise ValueError("No complete 5-minute bars")
    start=pd.Timestamp(REPLICATION_START,tz="Asia/Kolkata")
    bars=bars[bars.index>=start]
    if bars.empty: raise ValueError("No bars after replication start")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    bars.to_csv(a.output,index_label="timestamp")
    audit=pd.DataFrame({"source_minute_count":counts,"retained":keep},index=counts.index)
    audit.index.name="timestamp"; audit.to_csv(a.output.with_suffix(".source_counts.csv"))
    sha=hashlib.sha256(a.input.read_bytes()).hexdigest()
    prov=a.output.with_suffix(".provenance.txt")
    prov.write_text("\n".join([
        "PHASE 7 INDEPENDENT REPLICATION DATASET",
        f"source_url={SOURCE_URL}",
        f"source_commit={SOURCE_COMMIT}",
        f"source_file={SOURCE_PATH}",
        f"source_file_sha256={sha}",
        "instrument=NIFTY50 index",
        "source_frequency=1-minute",
        "derived_frequency=5-minute",
        "session=09:15-15:30 Asia/Kolkata",
        f"replication_start={REPLICATION_START}",
        f"source_rows={len(raw)}",
        f"source_sessions={x.index.normalize().nunique()}",
        f"source_invalid_or_missing_ohlc_excluded={int(bad.sum())}",
        f"source_start={x.index.min()}",
        f"source_end={x.index.max()}",
        f"five_minute_bins_before_filter={len(bars_all)}",
        f"complete_5_minute_bins_before_date_cut={int(keep.sum())}",
        f"replication_5m_rows={len(bars)}",
        f"replication_start_actual={bars.index.min()}",
        f"replication_end_actual={bars.index.max()}",
        "note=Independent public dataset; not exchange-authoritative and not used for Phase 5A rule fitting.",
    ]),encoding="utf-8")
    print(prov.read_text())

if __name__=="__main__": main()
