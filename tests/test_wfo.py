import pandas as pd

from cpr_lab.walk_forward import make_folds


def test_make_folds_uses_supplied_daily_schedule():
    daily = pd.date_range("2024-01-01", periods=380, freq="B")
    intraday = pd.date_range("2024-01-01 09:15", periods=380 * 75, freq="5min")
    folds = list(make_folds(daily, train_periods=252, test_periods=63, step=63))

    assert len(folds) == 2
    assert (folds[0]["train"][1] - folds[0]["train"][0]).days > 300
    assert folds[0]["test"][0] == daily[252]
    assert len(intraday) > len(daily)
