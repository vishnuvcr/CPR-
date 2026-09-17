"""Convert a pinned public NIFTY 1-minute dataset into canonical 5-minute OHLCV.

This adapter is deliberately marked as REFERENCE data. It is not treated as an
exchange-authoritative dataset. The source repository documents minute NIFTY 50
spot data from 2015-01-09 through 2024-03-27 and has no volume column.
Spot-index volume is therefore represented as zero, with provenance recorded.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

SOURCE_COMMIT = "81800ba10cf47e9c7806b6a40e300ef389187846"
SOURCE_URL = (
    "https://raw.githubusercontent.com/sandeepkapri/Nifty50-Minute-Data/"
    f"{SOURCE_COMMIT}/nifty50_candlestick_data.csv"
)


def prepare(input_path: Path, output_path: Path) -> None:
    raw = pd.read_csv(input_path)
    required = {"Instrument", "Date", "Time", "Open", "High", "Low", "Close"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Missing source columns: {sorted(missing)}")

    ts = pd.to_datetime(
        raw["Date"].astype(str) + " " + raw["Time"].astype(str),
        format="%d-%m-%Y %H:%M:%S",
        errors="raise",
    ).dt.tz_localize("Asia/Kolkata")

    if ts.duplicated().any():
        raise ValueError(f"Duplicate source timestamps: {int(ts.duplicated().sum())}")

    # Convert to NumPy arrays before constructing the datetime-indexed frame.
    # Otherwise pandas aligns the original RangeIndex to the new DatetimeIndex,
    # silently turning every OHLC value into NaN.
    ohlc = {
        "open": pd.to_numeric(raw["Open"], errors="raise").to_numpy(),
        "high": pd.to_numeric(raw["High"], errors="raise").to_numpy(),
        "low": pd.to_numeric(raw["Low"], errors="raise").to_numpy(),
        "close": pd.to_numeric(raw["Close"], errors="raise").to_numpy(),
    }
    x = pd.DataFrame(ohlc, index=ts).sort_index()

    source_missing_ohlc_rows = int(x.isna().any(axis=1).sum())
    if source_missing_ohlc_rows:
        print(f"source_rows_with_missing_ohlc={source_missing_ohlc_rows}")

    # Regular NSE cash session. We do not fabricate missing source minutes.
    x = x.between_time("09:15", "15:29")
    if x.empty:
        raise ValueError("No source observations remain after NSE session filtering")
    x["volume"] = 0.0  # NIFTY spot index has no traded volume.

    # Avoid pandas resample origin/offset behaviour differences across pandas
    # versions. Build the bucket explicitly from each timestamp's 5-minute floor.
    # The session filter above guarantees alignment to 09:15, 09:20, ..., 15:25.
    bucket = x.index.floor("5min")
    bars_all = x.groupby(bucket, sort=True).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    bars_all.index.name = "timestamp"

    source_counts = x["close"].groupby(bucket, sort=True).count().astype("int64")
    source_counts.index.name = "timestamp"

    valid_ohlc = x[["open", "high", "low", "close"]].notna().all(axis=1)
    valid_counts = valid_ohlc.groupby(bucket, sort=True).sum().astype("int64")
    valid_counts.index.name = "timestamp"

    # A canonical 5-minute bar must contain all five source observations and
    # every OHLC value must be present. Incomplete/malformed bins are excluded,
    # never repaired or forward-filled, and are retained in the audit below.
    keep = (source_counts == 5) & (valid_counts == 5)
    bars = bars_all.loc[keep]
    counts = source_counts.loc[bars.index]

    if bars.empty:
        raise ValueError(
            "No complete 5-minute bars remain after excluding incomplete/missing-OHLC bins"
        )
    if bars.isna().any().any():
        raise ValueError("Canonical 5-minute aggregation produced NaN OHLCV values")

    # Machine-readable completeness audit for every source-derived bin.
    audit = pd.DataFrame(
        {
            "source_minute_count": source_counts,
            "valid_ohlc_minute_count": valid_counts,
            "retained": keep,
        },
        index=bars_all.index,
    )
    audit.index.name = "timestamp"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(output_path, index_label="timestamp")
    audit.to_csv(output_path.with_suffix(".source_counts.csv"))

    complete_fraction = float(keep.mean()) if len(keep) else 0.0
    provenance = output_path.with_suffix(".provenance.txt")
    provenance.write_text(
        "REFERENCE DATASET\n"
        f"source_url={SOURCE_URL}\n"
        f"source_commit={SOURCE_COMMIT}\n"
        "instrument=Nifty50 spot index\n"
        "source_frequency=1-minute\n"
        "derived_frequency=5-minute\n"
        "volume=0 because spot index has no traded volume\n"
        "session=09:15-15:30 Asia/Kolkata\n"
        f"source_rows={len(raw)}\n"
        f"source_session_rows={len(x)}\n"
        f"source_rows_with_missing_ohlc={source_missing_ohlc_rows}\n"
        f"five_minute_bins_before_filter={len(bars_all)}\n"
        f"five_minute_bins_retained={len(bars)}\n"
        f"complete_5_minute_bins={int(keep.sum())}\n"
        f"complete_5_minute_fraction={complete_fraction:.6f}\n"
        f"minimum_source_minutes_per_bin={int(source_counts.min()) if len(source_counts) else 0}\n"
        f"maximum_source_minutes_per_bin={int(source_counts.max()) if len(source_counts) else 0}\n"
        "note=Reference dataset only; independently validate against exchange/vendor data before publication.\n"
        "note=Incomplete/missing-OHLC bins are excluded rather than repaired; see .source_counts.csv for the full audit.\n",
        encoding="utf-8",
    )
    print(f"source_rows={len(raw)}")
    print(f"session_source_rows={len(x)}")
    print(f"unique_sessions={x.index.normalize().nunique()}")
    print(f"source_rows_with_missing_ohlc={source_missing_ohlc_rows}")
    print(f"five_minute_bins_before_filter={len(bars_all)}")
    print(f"five_minute_rows_retained={len(bars)}")
    print(f"complete_5_minute_fraction={complete_fraction:.6f}")
    print(f"min_source_minutes_per_bin={int(source_counts.min()) if len(source_counts) else 0}")
    print(f"max_source_minutes_per_bin={int(source_counts.max()) if len(source_counts) else 0}")
    print(f"start={bars.index.min()}")
    print(f"end={bars.index.max()}")
    print(f"output={output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.input, args.output)


if __name__ == "__main__":
    main()
