# CPR Phase 5B — Frozen Candidate Validation Protocol

## Purpose
Phase 5A discovered interpretable CPR-favorable conditional contexts using TRAIN-only shallow decision trees. Phase 5B does not discover new thresholds. It freezes every TRAIN Pareto leaf and evaluates its stability.

## Inputs
- Phase 5A regime_discovery_intraday_events.csv
- Phase 5A regime_discovery_swing_events.csv
- Phase 5A regime_discovery_train_pareto.csv

The candidate definition is therefore fixed before validation/test outcomes are examined.

## Validation dimensions
For every frozen candidate:
1. TRAIN, VALIDATION and TEST conditional mean R, win rate, sensitivity, specificity and Youden J.
2. 95% block-bootstrap CI for mean R, using signal-day means and block length 10.
3. Day-block bootstrap intervals for sensitivity, specificity and Youden J.
4. Calendar-year stability, including annual signal count, mean R and positive year fraction for years with at least 50 candidate signals.
5. Adjacent-horizon consistency: the same frozen feature condition is applied unchanged to all horizons within the same asset family.

## No-selection rule
Phase 5B produces diagnostics only. It does not choose a winner, tune a threshold, or re-fit a model using validation/test outcomes. Candidate count and exact protocol parameters are recorded in phase5b_provenance.csv.

## Metric definition
As in Phase 5A, a positive event is return_R > 0. Sensitivity and specificity therefore describe how well a conditional subset isolates positive-return events relative to the full event population. They are not live-trading precision/recall.

## Interpretation
A candidate that looks attractive in TEST but is unstable across years, adjacent horizons, or uncertainty intervals is not considered robust. Phase 5B is a gate toward Phase 6 robustness, not the final decision-rule selection stage.

## Reproducibility
Seed: 20260918. Bootstrap replicates: 5000. Reference data source and commit remain pinned to the Phase 5A provenance.
