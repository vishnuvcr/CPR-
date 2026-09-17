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
| 1C | Intraday multi-horizon outcomes (1/3/6/12 bars, EOD), MFE/MAE | COMPLETE — NO STABLE INTRADAY EDGE ESTABLISHED | Pre-specified horizons characterized without evidence of a statistically reliable overall effect |
| 1D | Intraday event/trade lifecycle with stops, targets and time exits, excluding costs | DEFERRED | Revisit only if later evidence provides a justified intraday hypothesis |
| 2A | BTST signal characterization | IN PROGRESS — LOOK-AHEAD CORRECTION APPLIED | Bias-safe end-of-session signal; close-to-next-open and next-day OHLC distributions by CPR regime |
| 2B | BTST executable lifecycle and realistic costs | PLANNED | Out-of-sample cost-aware results |
| 3A | Swing horizons (2/3/5/10 sessions) | PLANNED | Horizon-dependent CPR effect characterized |
| 3B | Swing executable lifecycle and costs | PLANNED | Out-of-sample cost-aware results |
| 4 | Cross-horizon conditional selector | PLANNED | Predefined features select horizon without leakage |
| 5 | ML model as regime/horizon selector | PLANNED | Walk-forward validation beats appropriate baselines after costs |
| 6 | Robustness: subperiods, volatility regimes, direction, perturbation, Monte Carlo | PLANNED | Edge survives reasonable robustness tests |
| 7 | Final walk-forward / untouched holdout | PLANNED | No material degradation on unseen data |
| 8 | Paper-trading signal pipeline | PLANNED | Reproducible live signal generation with explicit execution rules |

## Current step: Phase 2A — BTST signal characterization

Phase 1C tested the unchanged bias-safe CPR directional signal from next-bar open across 1, 3, 6 and 12 five-minute bars plus same-session EOD. The aggregate results did not establish a statistically reliable intraday effect, so the research now tests whether the information content is expressed across the session boundary instead.

Phase 2A measures two pre-specified quantities without costs: (1) source-session close to next-session open, representing the overnight/BTST gap; and (2) next-session open to next-session close, representing a one-session hold. Next-session high/low are used for MFE/MAE. BTST eligibility is restricted to the final completed bar of each source session, so the signal cannot use the later same-day close. The next session open is the executable entry. Results are reported by direction, fixed CPR regime, signal-time bucket, and year. No width bin, holding rule, stop, target, or threshold is selected from historical profitability.

## Decision gates

- If BTST characterization shows no meaningful and stable separation: proceed to swing characterization.
- If a BTST effect appears: test its stability across years/subperiods before designing an executable BTST strategy.
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
- 2026-09-17: Phase 1C multi-horizon diagnostic implementation and CI workflow added.
- 2026-09-17: Phase 1C completed successfully on the pinned reference dataset; aggregate 1/3/6/12-bar and EOD outcomes did not establish a statistically reliable intraday effect. Phase 1D was therefore deferred rather than forcing stop/target optimization.
- 2026-09-18: Phase 2A BTST characterization implementation and CI workflow added.
- 2026-09-18: BTST workflow initially failed during canonicalization because an unsupported --source-counts-output argument was passed; the workflow was corrected.
- 2026-09-18: BTST characterization was audited for temporal leakage. The original implementation used the full source-session close for intraday signals generated before that close. BTST logic was corrected to use only the final completed source-session bar and the next-session open as the executable entry. CI now explicitly validates one end-of-session event per source day and final-bar timing.
