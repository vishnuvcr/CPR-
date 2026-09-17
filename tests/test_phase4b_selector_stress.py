import numpy as np
import pandas as pd
from scripts.run_phase4b_selector_stress import daily_mean, block_bootstrap_mean, HORIZONS


def test_daily_mean_equal_weights_days():
    df = pd.DataFrame({
        "signal_day": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-02"]),
        "return_R": [1.0, 1.0, -1.0],
    })
    assert daily_mean(df) == 0.0


def test_horizons_are_fixed_predeclared_candidates():
    assert HORIZONS == ("2session", "3session", "5session", "10session")


def test_block_bootstrap_is_reproducible_and_finite():
    x = np.arange(30, dtype=float) / 100.0
    a = block_bootstrap_mean(x, np.random.default_rng(7), n_boot=100)
    b = block_bootstrap_mean(x, np.random.default_rng(7), n_boot=100)
    assert a == b
    assert np.isfinite(a).all()
