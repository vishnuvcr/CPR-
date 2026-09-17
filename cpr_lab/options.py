"""Option-chain selection, Black-Scholes diagnostics and defined-risk helpers."""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
from scipy.stats import norm


@dataclass(frozen=True)
class OptionQuote:
    symbol: str
    expiry: pd.Timestamp
    strike: float
    option_type: str
    bid: float
    ask: float
    last: float | None = None
    iv: float | None = None
    delta: float | None = None
    volume: float | None = None
    open_interest: float | None = None


def bs_greeks(spot: float, strike: float, time_years: float, rate: float, iv: float, option_type: str) -> dict[str, float]:
    if spot <= 0 or strike <= 0 or time_years <= 0 or iv <= 0:
        raise ValueError("spot, strike, time and iv must be positive")
    cp = option_type.upper()
    sign = 1.0 if cp == "CALL" else -1.0
    d1 = (math.log(spot / strike) + (rate + 0.5 * iv * iv) * time_years) / (iv * math.sqrt(time_years))
    d2 = d1 - iv * math.sqrt(time_years)
    delta = sign * norm.cdf(sign * d1)
    gamma = norm.pdf(d1) / (spot * iv * math.sqrt(time_years))
    theta = -(spot * norm.pdf(d1) * iv / (2 * math.sqrt(time_years))) - sign * rate * strike * math.exp(-rate * time_years) * norm.cdf(sign * d2)
    vega = spot * norm.pdf(d1) * math.sqrt(time_years)
    return {"delta": float(delta), "gamma": float(gamma), "theta": float(theta), "vega": float(vega)}


def choose_atm_or_itm(chain: pd.DataFrame, spot: float, option_type: str, itm_steps: int = 1) -> pd.Series:
    """Choose ATM or one-step ITM using strike ordering; expects one expiry in the input."""
    x = chain.copy()
    cp = option_type.upper()
    x = x[x["option_type"].str.upper() == cp].copy()
    if x.empty:
        raise ValueError("No contracts for option type")
    x = x.sort_values("strike").reset_index(drop=True)
    if cp == "CALL":
        candidates = x[x.strike <= spot]
        row = candidates.iloc[-1] if len(candidates) > itm_steps else x.iloc[0]
        if len(candidates) >= itm_steps:
            row = candidates.iloc[-itm_steps]
    else:
        candidates = x[x.strike >= spot]
        row = candidates.iloc[0] if len(candidates) < itm_steps else candidates.iloc[itm_steps - 1]
    return row


def wide_cpr_short_vol_structure(chain: pd.DataFrame, spot: float, expiry: pd.Timestamp, defined_risk: bool = False, wing_steps: int = 3) -> dict:
    """Describe a short ATM straddle/strangle on a wide-CPR hypothesis.

    For defined_risk=True, returns wings to cap tail loss. The backtest must still
    use actual bid/ask quotes for each leg.
    """
    x = chain[pd.to_datetime(chain["expiry"]) == pd.Timestamp(expiry)].copy()
    if x.empty:
        raise ValueError("Expiry not present")
    calls = x[x.option_type.str.upper() == "CALL"].sort_values("strike").reset_index(drop=True)
    puts = x[x.option_type.str.upper() == "PUT"].sort_values("strike").reset_index(drop=True)
    atm_call = calls.iloc[(calls.strike - spot).abs().argmin()]
    atm_put = puts.iloc[(puts.strike - spot).abs().argmin()]
    legs = [
        {"action": "SELL", "type": "CALL", "strike": float(atm_call.strike)},
        {"action": "SELL", "type": "PUT", "strike": float(atm_put.strike)},
    ]
    if defined_risk:
        ci = int(calls.index[calls.strike == atm_call.strike][0])
        pi = int(puts.index[puts.strike == atm_put.strike][0])
        ci = min(ci + wing_steps, len(calls) - 1)
        pi = max(pi - wing_steps, 0)
        legs.extend([
            {"action": "BUY", "type": "CALL", "strike": float(calls.loc[ci, "strike"])},
            {"action": "BUY", "type": "PUT", "strike": float(puts.loc[pi, "strike"])},
        ])
    return {"expiry": pd.Timestamp(expiry), "structure": "iron_fly_or_wings" if defined_risk else "short_straddle", "legs": legs}
