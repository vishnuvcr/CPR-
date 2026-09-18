# CPR Phase 9 — Shadow Decision Engine

## Purpose

Phase 9 converts the frozen 39-candidate CPR regime frontier into a reproducible **shadow** decision pipeline. It is not yet an executable trading system.

The objective is to observe, prospectively, which frozen contexts activate and what happens afterward without using the 2026 untouched holdout to alter rules or create a new fitted threshold.

## Why shadow mode is required

The cross-phase synthesis found:

- 39 frozen candidates remain under consideration.
- 0 candidates passed the strict Phase 6 robustness diagnostic.
- 11 candidates had a positive effect with a 95% CI excluding zero in the Phase 7 independent replication.
- Only 4 of those 11 were positive in the 2026 YTD holdout.
- No candidate was positive in all three 2026 windows with at least five signals per window.

Therefore Phase 9 must collect prospective evidence without silently promoting a candidate to live trading.

## Frozen inputs

The engine must use the exact Phase 5A TRAIN-Pareto frontier already verified in the research pipeline. No threshold may be changed inside the shadow engine.

For every completed 5-minute bar it will:

1. update the bias-safe daily/intraday context;
2. evaluate all 39 frozen rules whose horizon/side is compatible with the current event;
3. emit every matching candidate rather than selecting a single candidate;
4. record the candidate rule, context variables, signal timestamp, expected horizon, and later realized outcome;
5. record evidence metadata from Phases 6 and 7 as **descriptive tags only**.

## Required output fields

Each shadow signal should contain at least:

- timestamp and trading session;
- candidate_id;
- asset;
- horizon;
- side;
- exact frozen rule;
- matched feature values;
- expected entry convention;
- signal price / next executable price when available;
- outcome horizon;
- realized return_R after the horizon;
- MFE_R and MAE_R when available;
- phase-6 robustness tag;
- phase-7 replication tag;
- 2026 holdout observation tag;
- actionable = false unless a later validated gate explicitly enables it.

## No-trade and ambiguity handling

The engine must explicitly support:

- no candidate matched;
- multiple candidates matched;
- opposing candidates matched;
- insufficient bars to evaluate the requested horizon;
- incomplete session/data quality;
- conflicting candidate evidence.

These states must not be converted automatically into a directional trade.

## Prospective evaluation

The shadow pipeline should accumulate signals prospectively and report:

- activation frequency;
- candidate overlap;
- directional agreement/disagreement;
- realized mean_R and distribution;
- sensitivity, specificity and Youden J;
- drawdown under a clearly labelled hypothetical execution model;
- stability by month/quarter;
- performance after realistic costs only as a separate analysis.

The prospective period must remain untouched until the signal is generated. Future outcomes can only be attached after they occur.

## Promotion gate

A candidate or ensemble may only move from shadow status toward paper trading after a separately documented validation stage establishes:

1. reproducibility outside the original discovery sample;
2. sufficient signal count;
3. uncertainty compatible with the intended use;
4. stability across multiple periods;
5. realistic execution-cost analysis;
6. no unresolved leakage or data-quality issue.

The current research evidence does **not** satisfy that promotion gate for a single candidate.

## Important research rule

The Phase 8 2026 holdout is not to be re-mined to manufacture a new rule. Any future model that uses 2026 observations for fitting must define a new chronological training/validation boundary and reserve a newer untouched holdout.

## Planned Phase 9 outputs

The implementation should produce:

- a machine-readable shadow-signal CSV/Parquet;
- a daily human-readable decision report;
- an overlap/conflict report;
- prospective outcome statistics;
- an immutable provenance file;
- a separate paper-trading eligibility report.

The default state of every emitted signal is **SHADOW / NOT FOR LIVE EXECUTION**.
