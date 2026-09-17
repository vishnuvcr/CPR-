# CPR Research Plan

## Objective

Scientifically evaluate whether Central Pivot Range (CPR)-derived signals contain a robust, reproducible trading edge, and determine whether any edge is specific to intraday, BTST, or swing holding horizons.

## Research rules

1. No parameter optimization during discovery.
2. Define hypotheses before inspecting conditional results.
3. Keep signal generation bias-safe: only completed prior periods may generate current-period features.
4. Separate signal edge from transaction costs and execution assumptions.
5. Report effect size, uncertainty, sample size, and stability—not just profitability.
6. Use chronological train/validation/test splits for any later optimization or ML.
7. Preserve a fixed external reference dataset and provenance.
8. Do not promote a strategy to paper trading until realistic-cost and out-of-sample tests pass.

## Roadmap / status

| Phase | Research question | Status | Exit criterion |
|---|---|---|---|
| 0 | Data integrity, provenance, reproducibility | COMPLETE | Canonical data validates; reproducibility smoke passes |
| 1A | Unconditional intraday CPR signal edge | COMPLETE | 4,281 signals characterized; unconditional next-bar edge assessed |
| 1B | Conditional intraday edge by CPR regime, signal type, direction, time, year | COMPLETE — WIDTH DIAGNOSTICS REVIEWED | Width distribution reviewed; fixed-regime comparison not available because generated signals remain narrow |
| 1C | Intraday multi-horizon outcomes (1/3/6/12 bars, EOD), MFE/MAE | IN PROGRESS | Determine whether any conditional edge persists beyond one bar |
| 1D | Intraday event/trade lifecycle with stops, targets and time exits, excluding costs | PLANNED | Compare signal edge with executable trade distributions |
| 2A | BTST signal characterization | PLANNED | Close-to-next-open and next-day OHLC distributions by CPR regime |
| 2B | BTST executable lifecycle and realistic costs | PLANNED | Out-of-sample cost-aware results |
| 3A | Swing horizons (2/3/5/10 sessions) | PLANNED | Horizon-dependent CPR effect characterized |
| 3B | Swing executable lifecycle and costs | PLANNED | Out-of-sample cost-aware results |
| 4 | Cross-horizon conditional selector | PLANNED | Predefined features select horizon without leakage |
| 5 | ML model as regime/horizon selector | PLANNED | Walk-forward validation beats appropriate baselines after costs |
| 6 | Robustness: subperiods, volatility regimes, direction, perturbation, Monte Carlo | PLANNED | Edge survives reasonable robustness tests |
| 7 | Final walk-forward / untouched holdout | PLANNED | No material degradation on unseen data |
| 8 | Paper-trading signal pipeline | PLANNED | Reproducible live signal generation with explicit execution rules |

## Current step: Phase 1C — multi-horizon intraday persistence

Phase 1B is closed as a diagnostic phase. The full daily CPR-width distribution showed that neutral/wide CPR days exist, but the current directional signal definition generates only narrow-regime signals. Exploratory width deciles showed no statistically convincing monotonic relationship with next-bar outcome. The research therefore moves to a pre-specified horizon test rather than optimizing width thresholds.

Phase 1C measures the same bias-safe CPR signal from next-bar open across 1, 3, 6 and 12 five-minute bars, plus same-session EOD. Each horizon is session-bounded so an intraday measurement cannot silently become an overnight/BTST test. Outcomes include R-normalized return, win rate, MFE, MAE, quartiles, p-values, direction, entry-time bucket, regime, and yearly stability.

These horizon measurements are descriptive discovery tests. No horizon, width bin, stop, target, or threshold will be selected because it produces the most favorable historical result.

## Decision gates

- If no conditional separation is found: proceed to BTST and swing characterization rather than forcing an intraday strategy.
- If conditional separation is found: test the effect across additional horizons before any optimization.
- Any promising subgroup must survive chronological out-of-sample testing and realistic costs.
- A positive backtest alone is not sufficient for promotion; reproducibility and robustness are required.

## Change log

- 2026-09-17: Data-quality and reference-data protocol established.
- 2026-09-17: Virgin CPR methodology and tests established.
- 2026-09-17: Fixed-cost intraday baseline completed; results interpreted separately from signal edge because the NIFTY spot/index data and cash-equity cost model are not a clean tradability match.
- 2026-09-17: Phase 1A signal-only baseline completed: 4,281 signals; unconditional next-bar mean close outcome approximately zero and not statistically significant.
- 2026-09-17: Phase 1B conditional decomposition implemented and CI-validated on commit 7332948fe41a34076202279b3fa0591e6c1eda58.
- 2026-09-17: Phase 1B result reviewed: all 4,281 signals were classified as narrow; fixed 0.50/1.00 ATR thresholds did not produce neutral/wide signal groups. Width-coverage and exploratory decile diagnostics added in commit 8226132a6d5e195013f8b67f2a842d8bc4783526.
- 2026-09-17: Width diagnostic completed: daily CPR population contained 2,207 narrow, 44 neutral, and 2 wide days; width-vs-next-bar outcome Spearman rho was approximately -0.010 with p approximately 0.50. No width threshold was optimized.
- 2026-09-17: Phase 1C multi-horizon diagnostic implementation added; horizons are explicitly session-bounded. CI workflow added for reproducible execution.
