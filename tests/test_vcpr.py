import numpy as np
import pandas as pd

from cpr_lab.strategies import vcp_r_first_touch_events, virgin_cpr_candidates


def test_virgin_cpr_requires_source_day_to_miss_its_own_zone():
    idx = pd.bdate_range("2026-01-01", periods=2)
    daily = pd.DataFrame({
        "high": [110.0, 120.0],
        "low": [100.0, 115.0],
        "close": [109.0, 119.0],
    }, index=idx)
    candidates = virgin_cpr_candidates(daily)
    # Day 1 CPR is around 104.5-109.5 and its range intersects it, so it is not virgin.
    assert idx[0] not in candidates.index


def test_verified_virgin_cpr_emits_only_first_future_touch():
    idx = pd.bdate_range("2026-01-01", periods=3)
    daily = pd.DataFrame({
        "high": [100.0, 110.0, 120.0],
        "low": [99.0, 109.0, 119.0],
        "close": [99.5, 109.5, 119.5],
    }, index=idx)
    candidates = virgin_cpr_candidates(daily.iloc[:2])
    assert idx[0] in candidates.index

    intraday_idx = pd.to_datetime([
        "2026-01-02 09:15",
        "2026-01-02 09:20",
        "2026-01-03 09:15",
    ])
    intraday = pd.DataFrame({
        "low": [98.0, 99.0, 99.0],
        "high": [98.5, 100.0, 100.5],
    }, index=intraday_idx)
    events = vcp_r_first_touch_events(intraday, candidates)
    assert len(events) == 1
    assert events.index[0] == intraday_idx[1]
