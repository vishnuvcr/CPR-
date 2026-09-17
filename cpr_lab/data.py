"""Data-contract and survivorship-aware universe utilities."""
from __future__ import annotations

import pandas as pd


REQUIRED_OHLCV = {"timestamp", "symbol", "open", "high", "low", "close", "volume"}


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_OHLCV - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    x = df.copy()
    x["timestamp"] = pd.to_datetime(x["timestamp"], utc=False)
    for c in ["open", "high", "low", "close", "volume"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["timestamp", "symbol", "open", "high", "low", "close"])
    return x.sort_values(["symbol", "timestamp"])


def apply_constituent_history(prices: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    """Restrict observations to symbols that were actually constituents at that date.

    Membership schema: `effective_date,symbol,universe,effective_end`.
    effective_end is exclusive when supplied.
    """
    required = {"effective_date", "symbol", "universe"}
    missing = required - set(membership.columns)
    if missing:
        raise ValueError(f"Missing membership columns: {sorted(missing)}")
    p = prices.copy()
    p["date"] = pd.to_datetime(p["timestamp"]).dt.normalize()
    m = membership.copy()
    m["effective_date"] = pd.to_datetime(m["effective_date"]).dt.normalize()
    if "effective_end" in m:
        m["effective_end"] = pd.to_datetime(m["effective_end"]).dt.normalize()
        eligible = (
            p.merge(m[["symbol", "universe", "effective_date", "effective_end"]], on="symbol", how="inner")
            .query("date >= effective_date and (effective_end.isna() or date < effective_end)")
        )
    else:
        # Without explicit end dates, use the latest membership record effective on or before each observation.
        m = m.sort_values(["symbol", "effective_date"])
        eligible = pd.merge_asof(
            p.sort_values(["symbol", "date"]),
            m.sort_values(["symbol", "effective_date"]),
            left_on="date", right_on="effective_date", by="symbol", direction="backward",
        )
    return eligible


def constituent_data_check(membership: pd.DataFrame) -> dict[str, int]:
    """Simple integrity diagnostics for historical constituent lists."""
    m = membership.copy()
    m["effective_date"] = pd.to_datetime(m["effective_date"])
    duplicates = int(m.duplicated(["symbol", "universe", "effective_date"]).sum())
    missing_symbol = int(m["symbol"].isna().sum())
    return {"duplicate_membership_rows": duplicates, "missing_symbol_rows": missing_symbol}
