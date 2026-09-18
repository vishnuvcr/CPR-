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
| 2A | BTST signal characterization | COMPLETE — LOW SAMPLE / NO STABLE SEPARATION | Bias-safe end-of-session signal characterized; only 31 valid events, with no stable aggregate or year-wise separation |
| 2B | BTST executable lifecycle and realistic costs | DEFERRED | Revisit only if a later, independently justified BTST hypothesis provides sufficient signal density |
| 3A | Swing horizons (2/3/5/10 sessions) | COMPLETE — DIRECTIONAL STABILITY REVIEWED | Horizon-dependent effects characterized and dependence-aware/chronological stability assessed |
| 3B | Swing executable lifecycle and costs | DEFERRED pending selector evidence | A defined swing hypothesis must first survive selector/OOS testing |
| 4 | Cross-horizon conditional selector | COMPLETE — NO STATISTICALLY RELIABLE SELECTOR ADVANTAGE ESTABLISHED | Corrected identical-signal OOS comparison completed; selector point estimate positive but paired comparisons not significant after multiple-testing context |
| 4B | Selector null/stability stress test | COMPLETE — SELECTOR ADVANTAGE NOT VALIDATED | 5,000 random-horizon null simulations, paired block bootstrap, concentration, and reproducibility completed; observed advantage did not reach a strong empirical significance threshold and all paired CIs crossed zero |
| 4C | Selector robustness / temporal placebo / stale-selector tests | COMPLETE — SELECTOR ROBUSTNESS NOT VALIDATED | Temporal placebo, chronological split stability, lagged-selection diagnostic, fixed-horizon reference, and subgroup decomposition completed; no evidence of incremental selector value |
| 5 | ML model as regime/horizon selector | PLANNED — GATED BY 4C | Only proceed if selector survives robustness/placebo testing and has a clearly defined incremental hypothesis |
| 6 | Robustness: subperiods, volatility regimes, direction, perturbation, Monte Carlo | PLANNED | Edge survives reasonable robustness tests |
| 7 | Final walk-forward / untouched holdout | PLANNED | No material degradation on unseen data |
| 8 | Paper-trading signal pipeline | PLANNED | Reproducible live signal generation with explicit execution rules |

## Current step: Phase 4C — Selector robustness / temporal placebo testing

Phase 4B has been completed. The uploaded Phase 4B artifact contained 5,000 reproducible random-horizon simulations, paired block-bootstrap comparisons, and selection-concentration diagnostics. The selected selector mean was above the random-horizon null mean, but the empirical two-sided p-value was approximately 0.162 and all four paired 95% block-bootstrap intervals crossed zero. Therefore the selector's incremental value is not validated and Phase 5 ML remains gated.

Phase 4C tested whether the apparent selector value depends on chronological alignment rather than a generic horizon-selection artifact. The primary temporal placebo permuted the already-selected horizon choices across walk-forward splits within direction/time-bucket cells, preserving observed selection frequencies while destroying their chronological alignment with the corresponding OOS outcomes. Additional outputs provided chronological split stability, a non-optimized lagged-selection diagnostic, fixed-horizon references on the identical signal population, and direction/time-bucket decomposition.

Phase 4C result: the actual selected mean was +0.190 R/day, while the temporal-placebo mean was +0.222 R/day (SD 0.0275 R; 2.5–97.5% placebo interval +0.167 to +0.272 R). The empirical two-sided placebo p-value was 0.264, with the observed selector below the placebo mean by 0.032 R/day. Split means were +0.012 R, +0.448 R, and +0.109 R across the three chronological splits, indicating substantial instability. The non-optimized lagged selector produced +0.291 R/day versus +0.190 R/day for the actual selector. Fixed-horizon references on the identical signal population ranged from +0.111 to +0.131 R/day. These results do not validate incremental selector value; the apparent positive point estimate is not robust to temporal placebo or stale-selection tests.

No thresholds, horizons, or features will be optimized during Phase 4C. The purpose is robustness and falsification, not improvement of the observed result.

## Decision gates

- If BTST characterization shows no meaningful and stable separation: proceed to swing characterization.
- If a BTST effect appears: test its stability across years/subperiods before designing an executable BTST strategy.
- Any promising swing directional pattern must survive dependence-aware stability, chronological out-of-sample testing, and realistic costs.
- A positive backtest alone is not sufficient for promotion; reproducibility and robustness are required.
- A positive selector point estimate is not sufficient for Phase 5; selector value must survive null/stress testing and Phase 4C robustness/placebo analysis.
- Phase 4C did not validate incremental selector value; therefore Phase 5 ML selector development remains gated and must not be started merely to optimize the observed result.

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
- 2026-09-18: Phase 2A rerun completed successfully after fixing the summary outcome-column collision. Artifact validation and timing-integrity checks passed. The corrected characterization produced 31 valid end-of-session events; aggregate overnight and next-session outcomes did not show stable separation, and yearly sample sizes were too small for a stability claim. Phase 2B is therefore deferred and Phase 3A swing-horizon characterization is advanced.
- 2026-09-18: Phase 3A swing characterization completed successfully. Aggregate 2/3/5/10-session outcomes did not show a statistically reliable overall effect, while LONG/SHORT results became increasingly separated at 5–10 sessions. Because the raw event series contains overlapping observations, a dependence-aware stability analysis was added before any executable swing strategy is considered.
- 2026-09-18: Phase 3A directional stability completed successfully. Holm-adjusted signal-day clustering and fixed 10-session block analyses supported longer-horizon directional separation, but 2015–2019 versus 2020–2024 results demonstrated material regime dependence. Phase 3B is therefore deferred and Phase 4 cross-horizon conditional selection is advanced.
- 2026-09-18: Phase 4 corrected identical-signal OOS benchmark completed successfully. SELECTED had a positive point estimate relative to fixed horizons, but paired OOS differences were not statistically significant; Phase 5 ML is gated pending a null/stability stress test.
- 2026-09-18: Phase 4B selector stress-test implementation added. It preserves exact Phase 4 OOS signal identities, uses a reproducible random-horizon null, dependence-aware paired block bootstrap intervals, and selection-concentration diagnostics.
- 2026-09-18: Phase 4B artifact reviewed: selected mean was approximately +0.190 R/day versus random-horizon null approximately +0.125 R/day; empirical two-sided p approximately 0.162; all four paired 95% block-bootstrap intervals crossed zero. Phase 4B therefore does not validate incremental selector value.
- 2026-09-18: Phase 4C selector robustness implementation and CI workflow added. Temporal split-permutation placebo, chronological split stability, lagged-selection diagnostic, fixed-horizon reference, and direction/time-bucket decomposition are now reproducibly generated from the pinned dataset without optimization.

- 2026-09-18: Phase 4C artifact reviewed. Actual selected mean was +0.190 R/day versus temporal-placebo mean +0.222 R/day; empirical two-sided p=0.264. Chronological split means were +0.012, +0.448, and +0.109 R/day; lagged selection was +0.291 R/day. Fixed-horizon references were +0.111, +0.127, +0.131, and +0.128 R/day for 2/3/5/10 sessions. Phase 4C therefore does not validate incremental selector value, and Phase 5 ML remains gated.
