"""Validation contracts for real-market CPR research datasets."""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


REQUIRED_OHLCV = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class DataQualityReport:
    rows: int
    start: pd.Timestamp
    end: pd.Timestamp
    duplicate_timestamps: int
    non_monotonic: bool
    missing_ohlcv: int
    invalid_ohlc: int
    non_positive_prices: int
    negative_volume: int

    @property
    def passed(self) -> bool:
        return (
            self.rows > 0
            and self.duplicate_timestamps == 0
            and not self.non_monotonic
            and self.missing_ohlcv == 0
            and self.invalid_ohlc == 0
            and self.non_positive_prices == 0
            and self.negative_volume == 0
        )


def validate_ohlcv(df: pd.DataFrame) -> DataQualityReport:
    """Validate a normalized OHLCV frame before it enters research."""
    missing = set(REQUIRED_OHLCV) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("OHLCV index must be a DatetimeIndex")

    numeric = df.loc[:, REQUIRED_OHLCV].apply(pd.to_numeric, errors="coerce")
    invalid_ohlc = int(((numeric.high < numeric.low) | (numeric.open > numeric.high) | (numeric.open < numeric.low) | (numeric.close > numeric.high) | (numeric.close < numeric.low)).sum())
    missing_ohlcv = int(numeric.isna().any(axis=1).sum())
    non_positive = int((numeric[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())
    negative_volume = int((numeric.volume < 0).sum())

    return DataQualityReport(
        rows=len(df),
        start=df.index.min() if len(df) else pd.NaT,
        end=df.index.max() if len(df) else pd.NaT,
        duplicate_timestamps=int(df.index.duplicated().sum()),
        non_monotonic=not df.index.is_monotonic_increasing,
        missing_ohlcv=missing_ohlcv,
        invalid_ohlc=invalid_ohlc,
        non_positive_prices=non_positive,
        negative_volume=negative_volume,
    )


def load_ohlcv_csv(path: str, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Load and normalize a research CSV; no resampling or silent repair is performed."""
    x = pd.read_csv(path)
    if timestamp_col not in x.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_col}")
    x[timestamp_col] = pd.to_datetime(x[timestamp_col], errors="raise")
    x = x.set_index(timestamp_col).sort_index()
    report = validate_ohlcv(x)
    if not report.passed:
        raise ValueError(f"Data quality failed: {report}")
    return x
