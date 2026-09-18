import pandas as pd

from scripts.run_intraday_multihorizon import same_session_horizon_position


def test_horizon_cannot_cross_trading_session():
    idx = pd.DatetimeIndex([
        "2024-01-02 15:10:00+05:30",
        "2024-01-02 15:15:00+05:30",
        "2024-01-03 09:15:00+05:30",
        "2024-01-03 09:20:00+05:30",
    ])
    # Entry at the second bar: 1-bar is valid; 2-bar would enter the next session.
    assert same_session_horizon_position(idx, 1, 1) == 1
    assert same_session_horizon_position(idx, 1, 2) is None


def test_horizon_stays_inside_session():
    idx = pd.DatetimeIndex([
        "2024-01-03 09:15:00+05:30",
        "2024-01-03 09:20:00+05:30",
        "2024-01-03 09:25:00+05:30",
        "2024-01-03 09:30:00+05:30",
    ])
    assert same_session_horizon_position(idx, 0, 3) == 2
    assert same_session_horizon_position(idx, 0, 5) is None
