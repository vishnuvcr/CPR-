# Theoretical target-risk scenario (not a CPR backtest)

This file records the 10,000-path synthetic stress test used during initialization.

Assumptions:

- Win probability: 55%
- Average win: +1.5R
- Average loss: -1R
- 100 trades in the horizon
- Independent Bernoulli outcomes
- Starting equity: 1.0x
- No costs, gap jumps, volatility clustering or regime shifts

| Risk per trade | Median terminal equity | P05 | P95 | Median max DD | Worst-tail max DD (5th percentile) | P(DD >= 50%) |
|---:|---:|---:|---:|---:|---:|---:|
| 0.5% | 1.2037x | 1.0893x | 1.3301x | -2.96% | -5.14% | 0.0% |
| 1.0% | 1.4428x | 1.1819x | 1.7614x | -5.85% | -10.07% | 0.0% |
| 2.0% | 2.0475x | 1.3751x | 3.0487x | -11.42% | -19.29% | 0.0% |
| 3.0% | 2.8584x | 1.5753x | 5.1866x | -16.70% | -27.98% | 0.0% |

## Target-equivalent weekly returns

Using 4.345 weeks/month:

- 30% monthly -> 6.22% weekly equivalent.
- 40% monthly -> 8.05% weekly equivalent.
- 10% weekly -> about 52.9% monthly equivalent.

Under the same synthetic 55% / +1.5R / -1R / 5-trades-per-week assumptions, solving for the risk-per-trade that produces the target geometric weekly factor gives approximately:

- 10% weekly -> 5.13% risk per trade.
- 30% monthly -> 3.24% risk per trade.
- 40% monthly -> 4.16% risk per trade.

Binary Kelly under those assumptions is 25% per trade. That number is included only as the mathematical full-Kelly reference; it is not a live-trading sizing recommendation.

The empirical Monte Carlo runner in `scripts/run_monte_carlo.py` must replace these synthetic assumptions once real CPR trade returns are available.
