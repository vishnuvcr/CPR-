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

    x = pd.DataFrame(
        {
            "open": pd.to_numeric(raw["Open"], errors="raise"),
            "high": pd.to_numeric(raw["High"], errors="raise"),
            "low": pd.to_numeric(raw["Low"], errors="raise"),
            "close": pd.to_numeric(raw["Close"], errors="raise"),
        },
        index=ts,
    ).sort_index()

    # Regular NSE cash session. We do not fabricate missing source minutes.
    x = x.between_time("09:15", "15:29")
    x["volume"] = 0.0  # NIFTY spot index has no traded volume.

    # Anchor 5-minute bins to the NSE session start. Preserve every bin that has
    # source observations; no OHLC values are forward-filled or invented.
    rule = "5min"
    kwargs = {"origin": "start_day", "offset": "15min", "label": "left", "closed": "left"}
    bars = x.resample(rule, **kwargs).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    counts = x["close"].resample(rule, **kwargs).count().reindex(bars.index)

    # Keep a machine-readable completeness audit alongside the canonical data.
    audit = pd.DataFrame({"source_minute_count": counts.astype("int64")}, index=bars.index)
    audit.index.name = "timestamp"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(output_path, index_label="timestamp")
    audit.to_csv(output_path.with_suffix(".source_counts.csv"))

    complete_fraction = float((counts == 5).mean()) if len(counts) else 0.0
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
        f"five_minute_bins={len(bars)}\n"
        f"complete_5_minute_bins={int((counts == 5).sum())}\n"
        f"complete_5_minute_fraction={complete_fraction:.6f}\n"
        f"minimum_source_minutes_per_bin={int(counts.min()) if len(counts) else 0}\n"
        f"maximum_source_minutes_per_bin={int(counts.max()) if len(counts) else 0}\n"
        "note=Reference dataset only; independently validate against exchange/vendor data before publication.\n"
        "note=5-minute bars are retained when source observations exist; incomplete-bin statistics are audited separately and are not repaired.\n",
        encoding="utf-8",
    )
    print(f"source_rows={len(raw)}")
    print(f"five_minute_rows={len(bars)}")
    print(f"complete_5_minute_fraction={complete_fraction:.6f}")
    print(f"min_source_minutes_per_bin={int(counts.min()) if len(counts) else 0}")
    print(f"max_source_minutes_per_bin={int(counts.max()) if len(counts) else 0}")
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
