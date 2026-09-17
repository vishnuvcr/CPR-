"""Monte Carlo, Kelly sizing, drawdown and return-target mathematics."""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class MonteCarloSummary:
    median_terminal: float
    p05_terminal: float
    p95_terminal: float
    probability_50pct_drawdown: float
    probability_ruin: float
    median_max_drawdown: float
    p95_max_drawdown: float


def max_drawdown(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd = equity / peak - 1.0
    return float(dd.min())


def bootstrap_paths(
    trade_returns: np.ndarray,
    paths: int = 10_000,
    trades: int | None = None,
    initial_equity: float = 100_000.0,
    risk_fraction: float = 0.01,
    seed: int = 42,
    block_size: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap strategy outcomes.

    `trade_returns` are unlevered per-trade fractional returns. `risk_fraction` scales
    the return stream. block_size > 1 provides a simple dependence-preserving block
    bootstrap rather than assuming IID outcomes.
    """
    r = np.asarray(trade_returns, dtype=float)
    r = r[np.isfinite(r)]
    if r.size == 0:
        raise ValueError("trade_returns is empty")
    rng = np.random.default_rng(seed)
    if trades is None:
        trades = int(r.size)

    equity = np.empty((paths, trades + 1), dtype=float)
    equity[:, 0] = initial_equity
    for p in range(paths):
        sampled = []
        while len(sampled) < trades:
            if block_size <= 1:
                sampled.extend(r[rng.integers(0, len(r), size=1)])
            else:
                if len(r) < block_size:
                    raise ValueError("block_size exceeds number of observations")
                start = int(rng.integers(0, len(r) - block_size + 1))
                sampled.extend(r[start : start + block_size])
        sampled = np.asarray(sampled[:trades])
        equity[p, 1:] = initial_equity * np.cumprod(1.0 + risk_fraction * sampled)
    return equity, np.asarray([max_drawdown(x) for x in equity])


def monte_carlo_summary(equity: np.ndarray, drawdowns: np.ndarray, ruin_level: float = 0.0) -> MonteCarloSummary:
    terminal = equity[:, -1]
    floor = equity[:, 0] * 0.50
    return MonteCarloSummary(
        median_terminal=float(np.median(terminal)),
        p05_terminal=float(np.quantile(terminal, 0.05)),
        p95_terminal=float(np.quantile(terminal, 0.95)),
        probability_50pct_drawdown=float(np.mean(np.min(equity, axis=1) <= floor)),
        probability_ruin=float(np.mean(np.min(equity, axis=1) <= ruin_level)),
        median_max_drawdown=float(np.median(drawdowns)),
        p95_max_drawdown=float(np.quantile(drawdowns, 0.05)),
    )


def empirical_kelly_fraction(trade_returns: np.ndarray, upper: float = 5.0, points: int = 20_001) -> float:
    """Numerically maximize expected log growth over a safe grid."""
    r = np.asarray(trade_returns, dtype=float)
    r = r[np.isfinite(r)]
    min_r = float(r.min())
    max_safe = upper if min_r >= 0 else min(upper, -0.999999 / min_r)
    grid = np.linspace(0.0, max_safe, points)
    vals = np.full_like(grid, -np.inf)
    for i, f in enumerate(grid):
        base = 1.0 + f * r
        if np.all(base > 0):
            vals[i] = np.mean(np.log(base))
    return float(grid[int(np.argmax(vals))])


def binary_kelly(win_probability: float, win_loss_ratio: float) -> float:
    """Kelly fraction for a binary win/loss model with unit loss."""
    p = float(win_probability)
    b = float(win_loss_ratio)
    if not 0 < p < 1 or b <= 0:
        raise ValueError("p must be in (0,1) and b > 0")
    return p - (1.0 - p) / b


def required_per_trade_risk(
    win_probability: float,
    avg_win_multiple: float,
    avg_loss_multiple: float,
    trades_per_week: int,
    target_weekly_return: float = 0.10,
) -> float:
    """Solve constant risk-per-trade needed to hit a weekly target in expectation.

    Uses the geometric expected wealth approximation under independent binary outcomes:
    E[wealth multiplier per trade] = p(1+f*w) + (1-p)(1-f*l).
    The returned f solves the weekly multiplier target; it is a mathematical scenario,
    not a recommendation.
    """
    p, w, l, n, target = map(float, [win_probability, avg_win_multiple, avg_loss_multiple, trades_per_week, target_weekly_return])
    if not (0 < p < 1 and w > 0 and l > 0 and n > 0 and target > -1):
        raise ValueError("Invalid model parameters")
    desired = (1.0 + target) ** (1.0 / n)

    def weekly_factor(f: float) -> float:
        return (p * (1.0 + f * w) + (1.0 - p) * (1.0 - f * l)) - desired

    lo, hi = 0.0, min(0.99 / l, 10.0)
    if weekly_factor(hi) < 0:
        return math.nan
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if weekly_factor(mid) >= 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)
