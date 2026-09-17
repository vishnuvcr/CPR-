import pandas as pd

from cpr_lab.strategies import vcp_r_first_touch_events, virgin_cpr_candidates


def test_virgin_cpr_is_based_on_the_following_session():
    idx = pd.bdate_range("2026-01-01", periods=4)
    daily = pd.DataFrame({
        "high": [110.0, 120.0, 130.0, 140.0],
        "low": [100.0, 111.0, 121.0, 131.0],
        "close": [109.0, 119.0, 129.0, 139.0],
    }, index=idx)
    candidates = virgin_cpr_candidates(daily)
    assert idx[0] in candidates.index
    assert candidates.loc[idx[0], "validation_day"] == idx[1]
    assert candidates.loc[idx[0], "eligible_from"] == idx[2]


def test_verified_virgin_cpr_emits_only_first_touch_after_validation():
    idx = pd.bdate_range("2026-01-01", periods=4)
    daily = pd.DataFrame({
        "high": [110.0, 120.0, 130.0, 140.0],
        "low": [100.0, 111.0, 121.0, 131.0],
        "close": [109.0, 119.0, 129.0, 139.0],
    }, index=idx)
    candidates = virgin_cpr_candidates(daily)

    # Jan 2 is the validation session and must not trigger the zone.
    # Jan 5 is the first eligible session and touches the Jan 1 CPR zone.
    intraday_idx = pd.to_datetime([
        "2026-01-02 09:15",
        "2026-01-05 09:15",
        "2026-01-05 09:20",
    ])
    intraday = pd.DataFrame({
        "low": [112.0, 106.0, 106.5],
        "high": [113.0, 109.0, 109.5],
    }, index=intraday_idx)
    events = vcp_r_first_touch_events(intraday, candidates)
    assert len(events) == 1
    assert events.index[0] == intraday_idx[1]
