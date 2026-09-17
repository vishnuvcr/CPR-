"""Bias-safe CPR, Camarilla, ATR and higher-timeframe feature builders."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

try:  # optional acceleration/consistency with pandas-ta
    import pandas_ta as pta  # type: ignore
except ImportError:  # pragma: no cover
    pta = None


@dataclass(frozen=True)
class CPRLevels:
    pivot: float
    bc: float
    tc: float
    lower: float
    upper: float
    width: float


def cpr_levels(high: float, low: float, close: float) -> CPRLevels:
    """Return classical CPR levels from one *completed* period."""
    pivot = (high + low + close) / 3.0
    bc = (high + low) / 2.0
    tc = 2.0 * pivot - bc
    lower, upper = min(bc, tc), max(bc, tc)
    return CPRLevels(pivot, bc, tc, lower, upper, upper - lower)


def camarilla_levels(high: float, low: float, close: float) -> dict[str, float]:
    """Classic Camarilla R1-R4/S1-S4 from one completed period."""
    rng = float(high) - float(low)
    k = 1.1 * rng
    return {
        "R1": close + k / 12.0,
        "R2": close + k / 6.0,
        "R3": close + k / 4.0,
        "R4": close + k / 2.0,
        "S1": close - k / 12.0,
        "S2": close - k / 6.0,
        "S3": close - k / 4.0,
        "S4": close - k / 2.0,
    }


def wilder_atr(df: pd.DataFrame, length: int = 20) -> pd.Series:
    """Wilder ATR. Uses pandas-ta when available; otherwise exact RMA formulation."""
    high, low, close = df["high"], df["low"], df["close"]
    if pta is not None:
        result = pta.atr(high=high, low=low, close=close, length=length, mamode="rma")
        if result is not None:
            return result.rename(f"ATR_{length}")
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean().rename(f"ATR_{length}")


def _period_features(ohlc: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    required = {"high", "low", "close"}
    missing = required - set(ohlc.columns)
    if missing:
        raise ValueError(f"Missing OHLC columns: {sorted(missing)}")
    rows = []
    for ts, row in ohlc.iterrows():
        c = cpr_levels(float(row.high), float(row.low), float(row.close))
        cam = camarilla_levels(float(row.high), float(row.low), float(row.close))
        rows.append({
            "timestamp": ts,
            f"{prefix}P": c.pivot,
            f"{prefix}BC": c.bc,
            f"{prefix}TC": c.tc,
            f"{prefix}CPR_low": c.lower,
            f"{prefix}CPR_high": c.upper,
            f"{prefix}CPR_width": c.width,
            **{f"{prefix}{k}": v for k, v in cam.items()},
            f"{prefix}PDH": float(row.high),
            f"{prefix}PDL": float(row.low),
            f"{prefix}Close": float(row.close),
        })
    return pd.DataFrame(rows).set_index("timestamp")


def daily_reference_features(daily_ohlc: pd.DataFrame, atr_length: int = 20) -> pd.DataFrame:
    """Create daily CPR/Camarilla features, then shift by one completed day.

    The returned index is the *trading day on which the values may be used*.
    """
    daily = daily_ohlc.copy().sort_index()
    base = _period_features(daily)
    base[f"ATR{atr_length}"] = wilder_atr(daily, atr_length)
    base["CPR_width_ATR_ratio"] = base["CPR_width"] / base[f"ATR{atr_length}"]
    usable = base.shift(1)
    usable.index.name = daily.index.name
    return usable.add_prefix("D_")


def add_intraday_daily_features(intraday: pd.DataFrame, daily_features: pd.DataFrame) -> pd.DataFrame:
    """Join prior-day features onto intraday bars without forward information leakage."""
    x = intraday.copy().sort_index()
    if not isinstance(x.index, pd.DatetimeIndex):
        raise TypeError("intraday index must be a DatetimeIndex")
    day = x.index.normalize()
    d = daily_features.copy().sort_index()
    d.index = pd.to_datetime(d.index).normalize()
    d = d[~d.index.duplicated(keep="last")]
    aligned = d.reindex(day).set_index(x.index)
    return pd.concat([x, aligned], axis=1)


def weekly_reference_features(daily_ohlc: pd.DataFrame) -> pd.DataFrame:
    """Prior completed week's CPR/Camarilla projected onto each current week."""
    x = daily_ohlc.copy().sort_index()
    weekly = x.resample("W-FRI").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    features = _period_features(weekly).shift(1).add_prefix("W_")
    week_key = x.index.to_period("W-FRI").to_timestamp("W-FRI")
    features.index = features.index.to_period("W-FRI").to_timestamp("W-FRI")
    mapped = features.reindex(week_key)
    mapped.index = x.index
    return mapped


def monthly_reference_features(daily_ohlc: pd.DataFrame) -> pd.DataFrame:
    """Prior completed month's CPR/Camarilla projected onto each current month."""
    x = daily_ohlc.copy().sort_index()
    monthly = x.resample("ME").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    features = _period_features(monthly).shift(1).add_prefix("M_")
    key = x.index.to_period("M").to_timestamp("M")
    features.index = features.index.to_period("M").to_timestamp("M")
    mapped = features.reindex(key)
    mapped.index = x.index
    return mapped


def regime(width_ratio: pd.Series, narrow_x: float, wide_y: float) -> pd.Series:
    """Return narrow/wide/neutral without forcing a trade in the neutral band."""
    out = pd.Series("neutral", index=width_ratio.index, dtype="object")
    out.loc[width_ratio < narrow_x] = "narrow"
    out.loc[width_ratio > wide_y] = "wide"
    return out


def strict_inside(value: pd.Series, lower: pd.Series, upper: pd.Series) -> pd.Series:
    return (value > lower) & (value < upper)
