# Statistical tear-sheet specification

Every strategy/universe/timeframe run should emit one row per tested configuration and a detailed trade ledger.

## Core metrics

| Metric | Definition / implementation |
|---|---|
| Total Return | Ending equity / starting equity - 1 |
| CAGR | Annualized compound return |
| Sharpe | Mean return / return std × sqrt(periods) |
| Sortino | Mean return / downside deviation × sqrt(periods) |
| Calmar | CAGR / absolute max drawdown |
| Win Rate | winning trades / total trades |
| Avg Win | mean positive trade return or P&L |
| Avg Loss | mean absolute losing trade return or P&L |
| Payoff Ratio | Avg Win / Avg Loss |
| Expectancy | p(win)×AvgWin − p(loss)×AvgLoss |
| Profit Factor | Gross profit / absolute gross loss |
| Max Drawdown | Minimum peak-to-trough equity decline |
| Max DD Duration | Longest time until prior equity high is recovered |
| Trade Count | Number of completed round trips |
| Turnover | Total notional traded |
| Exposure | Average and maximum gross exposure |
| Leverage | Average and maximum gross exposure / equity |

## Robustness metrics

- Train Sharpe vs test Sharpe degradation.
- Train CAGR vs test CAGR degradation.
- Fraction of WFO folds with positive test expectancy.
- Fraction of WFO folds with Profit Factor > 1.
- Parameter-neighborhood stability: share of nearby parameter sets producing positive test expectancy.
- Performance concentration by year, symbol and regime.
- Worst 1%, 5% and 10% trade outcomes.
- Maximum consecutive losses.
- Monthly return distribution, not only monthly CAGR.

## Risk metrics

- Probability of >=50% drawdown from 10,000 Monte Carlo paths.
- Probability of full ruin when loss support permits it.
- Median / P05 / P95 terminal equity.
- Median / P95 maximum drawdown.
- Kelly fraction and 1/2, 1/4 Kelly stress cases.
- Margin utilization and forced-liquidation threshold where leverage applies.

## Required output files

```text
results/
  trades_<strategy>_<universe>.csv
  equity_<strategy>_<universe>.csv
  wfo_folds_<strategy>_<universe>.csv
  tear_sheet_<strategy>_<universe>.csv
  monte_carlo_<strategy>_<universe>.csv
```
