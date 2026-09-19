"""Prepare a fresh, immutable-commit NIFTY50 1-minute source into canonical 5-minute bars."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

SESSION_START = "09:15"
SESSION_END = "15:29"


def prepare(input_path: Path, output_path: Path, source_commit: str, start: str = "2026-01-01") -> None:
    raw = pd.read_parquet(input_path)
    required = {"Date", "Open", "High", "Low", "Close", "Volume"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Missing source columns: {sorted(missing)}")

    ts = pd.to_datetime(raw["Date"], errors="raise")
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize("Asia/Kolkata")
    else:
        ts = ts.dt.tz_convert("Asia/Kolkata")

    x = pd.DataFrame(
        {
            "open": pd.to_numeric(raw["Open"], errors="raise").to_numpy(),
            "high": pd.to_numeric(raw["High"], errors="raise").to_numpy(),
            "low": pd.to_numeric(raw["Low"], errors="raise").to_numpy(),
            "close": pd.to_numeric(raw["Close"], errors="raise").to_numpy(),
            "volume": pd.to_numeric(raw["Volume"], errors="coerce").fillna(0).to_numpy(),
        },
        index=ts,
    )

    duplicate_rows = int(x.index.duplicated().sum())
    dup = x[x.index.duplicated(keep=False)]
    conflicting_groups = 0
    if not dup.empty:
        nunique = dup.groupby(level=0)[["open", "high", "low", "close", "volume"]].nunique()
        conflicting_groups = int((nunique.max(axis=1) > 1).sum())
        if conflicting_groups:
            conflict_idx = nunique.index[nunique.max(axis=1) > 1]
            x = x.loc[~x.index.isin(conflict_idx)].copy()

    before_dedup = len(x)
    x = x[~x.index.duplicated(keep="first")].sort_index()
    exact_duplicate_rows_excluded = before_dedup - len(x)

    x = x.between_time(SESSION_START, SESSION_END)
    if x.empty:
        raise ValueError("No observations remain after session filtering")

    bad = (
        (x.high < x.low)
        | (x.open > x.high)
        | (x.open < x.low)
        | (x.close > x.high)
        | (x.close < x.low)
        | x[["open", "high", "low", "close"]].isna().any(axis=1)
    )
    bad_n = int(bad.sum())
    x = x.loc[~bad].copy()

    bucket = x.index.floor("5min")
    bars_all = x.groupby(bucket, sort=True).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    counts = x.close.groupby(bucket, sort=True).count()
    keep = counts.eq(5)
    bars = bars_all.loc[keep].copy()
    bars.index.name = "timestamp"

    bars = bars[bars.index >= pd.Timestamp(start, tz="Asia/Kolkata")]
    if bars.empty:
        raise ValueError(f"No complete 5-minute bars after {start}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(output_path, index_label="timestamp")

    input_sha = hashlib.sha256(input_path.read_bytes()).hexdigest()
    provenance = output_path.with_suffix(".provenance.txt")
    provenance.write_text(
        "\n".join(
            [
                "PHASE 9I FRESH CHRONOLOGICAL DATASET",
                f"source_commit={source_commit}",
                "source_path=NIFTY50-INDEX.parquet",
                f"source_file_sha256={input_sha}",
                "instrument=NIFTY50 index",
                "source_frequency=1-minute",
                "derived_frequency=5-minute",
                "session=09:15-15:30 Asia/Kolkata",
                f"start_filter={start}",
                f"source_rows={len(raw)}",
                f"duplicate_timestamp_rows_detected={duplicate_rows}",
                f"conflicting_duplicate_timestamp_groups={conflicting_groups}",
                f"exact_duplicate_rows_excluded={exact_duplicate_rows_excluded}",
                f"invalid_or_missing_ohlc_rows_excluded={bad_n}",
                f"output_rows={len(bars)}",
                f"output_start={bars.index.min()}",
                f"output_end={bars.index.max()}",
            ]
        ),
        encoding="utf-8",
    )

    print(provenance.read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--start", default="2026-01-01")
    args = parser.parse_args()
    prepare(args.input, args.output, args.source_commit, args.start)
