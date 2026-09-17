import numpy as np
import pandas as pd

from cpr_lab.indicators import camarilla_levels, cpr_levels, daily_reference_features, regime, strict_inside


def test_cpr_classic():
    x = cpr_levels(110, 100, 105)
    assert x.pivot == 105
    assert x.bc == 105
    assert x.tc == 105
    assert x.width == 0


def test_camarilla_r3_s3():
    x = camarilla_levels(110, 100, 105)
    assert np.isclose(x["R3"], 107.75)
    assert np.isclose(x["S3"], 102.25)


def test_regime_and_strict_inside():
    ratio = pd.Series([0.2, 0.8, 1.2])
    r = regime(ratio, 0.5, 1.0)
    assert list(r) == ["narrow", "neutral", "wide"]
    assert bool(strict_inside(pd.Series([5.0]), pd.Series([4.0]), pd.Series([6.0])).iloc[0])
    assert not bool(strict_inside(pd.Series([6.0]), pd.Series([4.0]), pd.Series([6.0])).iloc[0])


def test_daily_features_are_shifted():
    idx = pd.bdate_range("2026-01-01", periods=30)
    daily = pd.DataFrame({
        "open": np.arange(100, 130),
        "high": np.arange(102, 132),
        "low": np.arange(98, 128),
        "close": np.arange(101, 131),
    }, index=idx)
    f = daily_reference_features(daily)
    assert pd.isna(f.iloc[0]["D_P"])
    assert np.isclose(f.iloc[1]["D_P"], (102 + 98 + 101) / 3)
