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
| 1B | Conditional intraday edge by CPR regime, signal type, direction, time, year | IN PROGRESS | Conditional distributions + uncertainty reviewed |
| 1C | Intraday multi-horizon outcomes (1/3/6/12 bars, EOD), MFE/MAE | NEXT | Determine whether any conditional edge persists beyond one bar |
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

## Current step: Phase 1B

The current analysis uses the pre-specified CPR width definitions already in the strategy: narrow < 0.50 ATR, neutral 0.50–1.00 ATR, and wide > 1.00 ATR. It separates narrow breakout and wide reversal signals, long/short direction, entry-time buckets, and yearly stability. The purpose is descriptive/diagnostic, not threshold optimization.

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
