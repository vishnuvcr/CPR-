import numpy as np
import pandas as pd
import pytest

from cpr_lab.data_quality import validate_ohlcv


def _frame():
    idx = pd.date_range("2026-01-01 09:15", periods=3, freq="5min")
    return pd.DataFrame({
        "open": [100, 101, 102],
        "high": [102, 103, 104],
        "low": [99, 100, 101],
        "close": [101, 102, 103],
        "volume": [1000, 1100, 1200],
    }, index=idx)


def test_valid_ohlcv_passes():
    report = validate_ohlcv(_frame())
    assert report.passed


def test_invalid_ohlc_fails():
    x = _frame()
    x.loc[x.index[1], "high"] = 99
    report = validate_ohlcv(x)
    assert not report.passed
    assert report.invalid_ohlc == 1
