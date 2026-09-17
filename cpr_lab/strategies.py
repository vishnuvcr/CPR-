"""Signal engines for CPR hypothesis testing."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .indicators import regime, strict_inside


@dataclass(frozen=True)
class StrategyConfig:
    narrow_x: float = 0.50
    wide_y: float = 1.00
    atr_stop: float = 1.0
    target_r: float = 2.0
    reject_bars: int = 1
    exit_time: str = "15:15"


def _cross_above(s: pd.Series, level: pd.Series) -> pd.Series:
    return (s > level) & (s.shift(1) <= level.shift(1))


def _cross_below(s: pd.Series, level: pd.Series) -> pd.Series:
    return (s < level) & (s.shift(1) >= level.shift(1))


def intraday_directional_signals(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    x = df.copy()
    required = ["open", "high", "low", "close", "D_CPR_width_ATR_ratio", "D_R1", "D_S1", "D_PDH", "D_PDL", "D_P"]
    missing = [c for c in required if c not in x]
    if missing:
        raise ValueError(f"Missing strategy columns: {missing}")
    x["regime"] = regime(x["D_CPR_width_ATR_ratio"], cfg.narrow_x, cfg.wide_y)
    x["upper_trigger"] = x[["D_R1", "D_PDH"]].max(axis=1)
    x["lower_trigger"] = x[["D_S1", "D_PDL"]].min(axis=1)
    x["narrow_long"] = (x.regime == "narrow") & _cross_above(x.close, x.upper_trigger)
    x["narrow_short"] = (x.regime == "narrow") & _cross_below(x.close, x.lower_trigger)
    x["wide_short"] = (x.regime == "wide") & (x.high >= x.upper_trigger) & (x.close < x.upper_trigger)
    x["wide_long"] = (x.regime == "wide") & (x.low <= x.lower_trigger) & (x.close > x.lower_trigger)
    x["long_entry"] = x["narrow_long"] | x["wide_long"]
    x["short_entry"] = x["narrow_short"] | x["wide_short"]
    x["exit_time"] = x.index.strftime("%H:%M") == cfg.exit_time
    return x


def confluence_reversal_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Camarilla R3/S3 strictly inside prior-day CPR, with rejection."""
    x = df.copy()
    needed = ["high", "low", "close", "D_CPR_low", "D_CPR_high", "D_R3", "D_S3"]
    missing = [c for c in needed if c not in x]
    if missing:
        raise ValueError(f"Missing confluence columns: {missing}")
    r3_inside = strict_inside(x.D_R3, x.D_CPR_low, x.D_CPR_high)
    s3_inside = strict_inside(x.D_S3, x.D_CPR_low, x.D_CPR_high)
    x["r3_inside_cpr"] = r3_inside
    x["s3_inside_cpr"] = s3_inside
    x["r3_reject_short"] = r3_inside & (x.high >= x.D_R3) & (x.close < x.D_R3)
    x["s3_reject_long"] = s3_inside & (x.low <= x.D_S3) & (x.close > x.D_S3)
    x["short_entry"] = x.r3_reject_short
    x["long_entry"] = x.s3_reject_long
    return x


class VirginCPRTracker:
    """Online first-touch state machine for verified virgin CPR zones."""
    def __init__(self) -> None:
        self.active: list[dict[str, object]] = []

    def add_zone(self, source_day: pd.Timestamp, lower: float, upper: float) -> None:
        self.active.append({"source_day": pd.Timestamp(source_day), "lower": float(min(lower, upper)), "upper": float(max(lower, upper))})

    def update_bar(self, ts: pd.Timestamp, low: float, high: float) -> list[dict[str, object]]:
        hits, still_active = [], []
        for zone in self.active:
            touched = float(high) >= float(zone["lower"]) and float(low) <= float(zone["upper"])
            if touched:
                hits.append({**zone, "touch_time": ts})
            else:
                still_active.append(zone)
        self.active = still_active
        return hits


def virgin_cpr_candidates(daily: pd.DataFrame) -> pd.DataFrame:
    """Identify CPRs whose *immediately following session* never touched the zone.

    The source day's own range necessarily contains its CPR. Therefore virgin status
    is determined by the next completed session. A verified zone becomes eligible
    from the session after that validation session.
    """
    required = {"high", "low", "close"}
    if not required.issubset(daily.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(daily.columns))}")
    from .indicators import cpr_levels

    x = daily.sort_index()
    rows = []
    for i in range(len(x) - 1):
        source_day = x.index[i]
        validation_day = x.index[i + 1]
        source = x.iloc[i]
        validation = x.iloc[i + 1]
        c = cpr_levels(float(source.high), float(source.low), float(source.close))
        untouched_next_day = float(validation.high) < c.lower or float(validation.low) > c.upper
        if untouched_next_day:
            rows.append({"source_day": source_day, "validation_day": validation_day, "eligible_from": validation_day, "CPR_low": c.lower, "CPR_high": c.upper})
    return pd.DataFrame(rows).set_index("source_day") if rows else pd.DataFrame(columns=["validation_day", "eligible_from", "CPR_low", "CPR_high"], index=pd.DatetimeIndex([], name=x.index.name))


def vcp_r_first_touch_events(intraday: pd.DataFrame, virgin_zones: pd.DataFrame) -> pd.DataFrame:
    """Generate the first touch strictly after the validation session."""
    x = intraday.copy().sort_index()
    d = virgin_zones.copy().sort_index()
    tracker = VirginCPRTracker()
    out = []
    pending = d.reset_index().sort_values("eligible_from").to_dict("records")
    p = 0
    for ts, row in x.iterrows():
        while p < len(pending) and pd.Timestamp(pending[p]["eligible_from"]).normalize() < pd.Timestamp(ts).normalize():
            z = pending[p]
            tracker.add_zone(pd.Timestamp(z["source_day"]), float(z["CPR_low"]), float(z["CPR_high"]))
            p += 1
        for hit in tracker.update_bar(ts, float(row.low), float(row.high)):
            out.append({"timestamp": ts, "source_day": hit["source_day"], "zone_low": hit["lower"], "zone_high": hit["upper"]})
    return pd.DataFrame(out).set_index("timestamp") if out else pd.DataFrame(columns=["source_day", "zone_low", "zone_high"], index=pd.DatetimeIndex([], name=x.index.name))


def btst_signals(daily: pd.DataFrame, near_atr: float = 0.30) -> pd.DataFrame:
    """BTST using completed-session information only."""
    x = daily.copy().sort_index()
    for c in ["high", "low", "close", "CPR_width_ATR_ratio"]:
        if c not in x:
            raise ValueError(f"Missing {c}")
    next_p = (x.high + x.low + x.close) / 3.0
    next_bc = (x.high + x.low) / 2.0
    next_tc = 2.0 * next_p - next_bc
    next_lo = pd.concat([next_bc, next_tc], axis=1).min(axis=1)
    next_hi = pd.concat([next_bc, next_tc], axis=1).max(axis=1)
    atr = x.get("ATR20", pd.Series(np.nan, index=x.index))
    distance = np.minimum((x.close - next_lo).abs(), (x.close - next_hi).abs())
    x["next_CPR_low"] = next_lo
    x["next_CPR_high"] = next_hi
    x["distance_to_next_CPR"] = distance
    x["near_next_CPR"] = distance <= near_atr * atr
    x["btst_long"] = x.near_next_CPR & (x.close > next_hi)
    x["btst_short"] = x.near_next_CPR & (x.close < next_lo)
    return x


def swing_signals(hourly: pd.DataFrame, weekly_features: pd.DataFrame) -> pd.DataFrame:
    """Hourly execution synchronized to prior completed weekly CPR."""
    x = hourly.copy().sort_index()
    wf = weekly_features.reindex(x.index)
    x = pd.concat([x, wf], axis=1)
    required = ["W_CPR_low", "W_CPR_high", "W_P", "W_R1", "W_S1"]
    missing = [c for c in required if c not in x]
    if missing:
        raise ValueError(f"Missing weekly features: {missing}")
    x["htf_bull"] = x.close > x.W_P
    x["htf_bear"] = x.close < x.W_P
    x["long_entry"] = x.htf_bull & (x.close > x.W_CPR_high) & (x.close.shift(1) <= x.W_CPR_high.shift(1))
    x["short_entry"] = x.htf_bear & (x.close < x.W_CPR_low) & (x.close.shift(1) >= x.W_CPR_low.shift(1))
    x["long_trail"] = x.W_S1
    x["short_trail"] = x.W_R1
    return x


def option_direction(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    long_flag = x["narrow_long"] if "narrow_long" in x else pd.Series(False, index=x.index)
    short_flag = x["narrow_short"] if "narrow_short" in x else pd.Series(False, index=x.index)
    x["option_bias"] = np.select([long_flag, short_flag], ["CALL", "PUT"], default="NONE")
    return x
