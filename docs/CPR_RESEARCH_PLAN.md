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
| 4 | Cross-horizon conditional selector | IN PROGRESS | Predefined walk-forward selector evaluated against fixed-horizon baselines without leakage |
| 5 | ML model as regime/horizon selector | PLANNED | Walk-forward validation beats appropriate non-ML baselines after costs |
| 6 | Robustness: subperiods, volatility regimes, direction, perturbation, Monte Carlo | PLANNED | Edge survives reasonable robustness tests |
| 7 | Final walk-forward / untouched holdout | PLANNED | No material degradation on unseen data |
| 8 | Paper-trading signal pipeline | PLANNED | Reproducible live signal generation with explicit execution rules |

## Current step: Phase 4 — Cross-horizon conditional selector

Phase 3A stability analysis completed successfully on the pinned reference dataset. Equal-weight signal-day clustering and fixed 10-session blocks showed that the longer-horizon directional separation is not explained solely by treating every intraday event as independent. However, the chronological 2015–2019 versus 2020–2024 comparison showed material regime dependence: the LONG effect changes substantially over time, while the SHORT effect is also horizon- and period-dependent. The aggregate directional pattern is therefore hypothesis-generating rather than a stationary executable edge.

The stability work used eight pre-specified LONG/SHORT-by-horizon tests with Holm correction, fixed 10-session blocks, equal-weight signal-day clusters, two chronological subperiods, and year-wise sign consistency. The primary equal-weight signal-day analysis produced Holm-adjusted significance for 3-session LONG, 5-session LONG, 10-session LONG and 10-session SHORT. The fixed-block analysis also showed strong negative 10-session SHORT behavior. These findings are not sufficient for promotion because the chronological subperiod results do not reproduce a uniform effect across time.

Phase 4 therefore tests whether a pre-specified walk-forward horizon selector can adapt to changing conditions without using future outcomes. The first selector is intentionally simple and non-ML: fixed-horizon baselines (always 2/3/5/10 sessions) are compared with a rolling historical selector using only information available before each validation block. Candidate conditioning variables are fixed in advance as signal direction and entry-time bucket. No width threshold or other feature will be tuned from validation profitability. Selection occurs only inside chronological training windows, followed by untouched forward validation blocks.

No Phase 3B executable strategy is promoted until Phase 4 demonstrates that a selector can improve on fixed-horizon baselines out of sample and the resulting hypothesis survives realistic transaction-cost analysis.

## Decision gates

- If BTST characterization shows no meaningful and stable separation: proceed to swing characterization.
- If a BTST effect appears: test its stability across years/subperiods before designing an executable BTST strategy.
- Any promising swing directional pattern must survive dependence-aware stability, chronological out-of-sample testing, and realistic costs.
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
- 2026-09-18: Phase 2A rerun completed successfully after fixing the summary outcome-column collision. Artifact validation and timing-integrity checks passed. The corrected characterization produced 31 valid end-of-session events; aggregate overnight and next-session outcomes did not show stable separation, and yearly sample sizes were too small for a stability claim. Phase 2B is therefore deferred and Phase 3A swing-horizon characterization is advanced.
- 2026-09-18: Phase 3A swing characterization completed successfully. Aggregate 2/3/5/10-session outcomes did not show a statistically reliable overall effect, while LONG/SHORT results became increasingly separated at 5–10 sessions. Because the raw event series contains overlapping observations, a dependence-aware stability analysis was added before any executable swing strategy is considered.
- 2026-09-18: Phase 3A directional stability completed successfully. Holm-adjusted signal-day clustering and fixed 10-session block analyses supported longer-horizon directional separation, but 2015–2019 versus 2020–2024 results demonstrated material regime dependence. Phase 3B is therefore deferred and Phase 4 cross-horizon conditional selection is advanced.
