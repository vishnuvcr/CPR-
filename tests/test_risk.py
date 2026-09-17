import numpy as np

from cpr_lab.risk import binary_kelly, empirical_kelly_fraction, required_per_trade_risk


def test_binary_kelly():
    assert np.isclose(binary_kelly(0.5, 2.0), 0.25)


def test_empirical_kelly_is_nonnegative():
    r = np.array([0.02, 0.03, -0.01, 0.04, -0.02])
    f = empirical_kelly_fraction(r, upper=2.0, points=1001)
    assert f >= 0


def test_target_risk_solver():
    f = required_per_trade_risk(0.55, 1.5, 1.0, 5, 0.10)
    assert np.isfinite(f)
    assert f > 0
