"""Signal engines for CPR hypothesis testing.

These functions emit event columns; execution, fill rules, costs and sizing stay outside
signal generation so hypotheses remain independently testable.
"""
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
    """Narrow-CPR breakout + wide-CPR rejection signals.

    Required columns are OHLC plus D_* prior-day levels from indicators.py.
    """
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

    # A touch without rejection is not enough; close must return back inside the trigger.
    x["wide_short"] = (
        (x.regime == "wide")
        & (x.high >= x.upper_trigger)
        & (x.close < x.upper_trigger)
    )
    x["wide_long"] = (
        (x.regime == "wide")
        & (x.low <= x.lower_trigger)
        & (x.close > x.lower_trigger)
    )

    x["long_entry"] = x["narrow_long"] | x["wide_long"]
    x["short_entry"] = x["narrow_short"] | x["wide_short"]
    x["exit_time"] = x.index.strftime("%H:%M") == cfg.exit_time
    return x


def confluence_reversal_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Camarilla R3/S3 strictly inside prior-day CPR, with first-touch rejection."""
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
    """Online VCPR state machine.

    Add a zone only after its source session has completed. The first execution bar
    intersecting the zone emits a touch event and retires it from the active list.
    """

    def __init__(self) -> None:
        self.active: list[dict[str, object]] = []

    def add_zone(self, source_day: pd.Timestamp, lower: float, upper: float) -> None:
        self.active.append({
            "source_day": pd.Timestamp(source_day),
            "lower": float(min(lower, upper)),
            "upper": float(max(lower, upper)),
        })

    def update_bar(self, ts: pd.Timestamp, low: float, high: float) -> list[dict[str, object]]:
        hits = []
        still_active = []
        for zone in self.active:
            touched = float(high) >= float(zone["lower"]) and float(low) <= float(zone["upper"])
            if touched:
                hits.append({**zone, "touch_time": ts})
            else:
                still_active.append(zone)
        self.active = still_active
        return hits


def vcp_r_first_touch_events(intraday: pd.DataFrame, prior_daily_cpr: pd.DataFrame) -> pd.DataFrame:
    """Generate first-touch events for prior CPR zones using an online state machine."""
    x = intraday.copy().sort_index()
    d = prior_daily_cpr.copy().sort_index()
    out = []
    tracker = VirginCPRTracker()
    last_day = None
    for ts, row in x.iterrows():
        day = pd.Timestamp(ts).normalize()
        if day != last_day:
            last_day = day
            if day in d.index:
                z = d.loc[day]
                if pd.notna(z.get("CPR_low")) and pd.notna(z.get("CPR_high")):
                    tracker.add_zone(day, float(z.CPR_low), float(z.CPR_high))
        hits = tracker.update_bar(ts, float(row.low), float(row.high))
        for h in hits:
            out.append({
                "timestamp": ts,
                "source_day": h["source_day"],
                "zone_low": h["lower"],
                "zone_high": h["upper"],
            })
    return pd.DataFrame(out).set_index("timestamp") if out else pd.DataFrame(
        columns=["source_day", "zone_low", "zone_high"], index=pd.DatetimeIndex([], name=x.index.name)
    )


def btst_signals(daily: pd.DataFrame, near_atr: float = 0.30) -> pd.DataFrame:
    """BTST using completed-session information only.

    The next session CPR is computed from the completed current session, so the entry
    is modeled at the official session close / last executable close. A 15:25 proxy
    is intentionally not used unless the vendor defines it as the completed close.
    """
    x = daily.copy().sort_index()
    for c in ["high", "low", "close", "CPR_width_ATR_ratio"]:
        if c not in x:
            raise ValueError(f"Missing {c}")

    # Today's completed H/L/C defines tomorrow's CPR.
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
    """Attach directional option selection flags to a CPR signal table.

    The actual strike is chosen by the option-chain selector, not by the CPR signaler.
    """
    x = df.copy()
    x["option_bias"] = np.select([x.get("narrow_long", False), x.get("narrow_short", False)], ["CALL", "PUT"], default="NONE")
    return x
