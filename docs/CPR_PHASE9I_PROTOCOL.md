# Phase 9I Protocol — Prospective Chronological Validation

## Purpose

Test the frozen Phase 9H research candidate on a genuinely new chronological holdout that was not available when the Phase 9H candidate was documented.

This phase is a **validation gate, not an optimization phase**.

## Frozen candidate

The candidate is fixed before evaluating new observations:

- Frontier: Phase 5A frozen frontier, 39 candidates.
- Frontier SHA256: `601a72f5e64204aee7ff0bb77347d57b0e2b59871b8bc30011282c2dc02c28b2`
- Regime leaf: `LEAF_4`
- Side: SHORT
- Horizon: 10-session swing
- Strategy: ATR(20) stop = 1R; target = 2R
- Entry: next available bar open after the frozen signal.
- Exit: first conservative stop/target event; otherwise close of the 10th trading session after entry.
- Same-bar ambiguity: stop is evaluated before target.
- Gap-through barrier: exit at bar open.
- No pyramiding in the deployment-like portfolio diagnostic; while a candidate trade is open, later candidate signals are skipped.

No threshold, tree, horizon, side, regime definition or strategy parameter is changed using Phase 9I data.

## Chronological boundary

Phase 8 used the pinned 2026 source ending on 17-Sep-2026. Phase 9I therefore treats:

`2026-09-17 15:30 Asia/Kolkata`

as the hard cutoff. Only signals strictly after that cutoff are eligible.

A signal generated after the cutoff may remain **pending** until enough new trading sessions exist to complete the 10-session horizon.

## Data policy

1. The Phase 5A reference dataset and frozen frontier remain immutable.
2. A fresh Phase 9I source snapshot is resolved from the upstream 2026 NIFTY50 dataset by immutable commit SHA.
3. The resolved source commit and input SHA256 are recorded every run.
4. Source data are cached by commit SHA in GitHub Actions.
5. No future data are backfilled into earlier signal calculations.
6. The NIFTY50 index path remains a futures-proxy economic analysis, not proof of executable futures/options fills.

## Friction scenarios

The same four pre-registered Phase 9H cost scenarios are retained:

- `PAYTM_BASE20_5BPS`
- `PAYTM_ALT10_5BPS`
- `PAYTM_BASE20_10BPS`
- `PAYTM_ALT10_10BPS`

No cost scenario is chosen because it looks best after seeing Phase 9I outcomes.

## Statistical analysis

Primary descriptive outputs:

- completed event count
- completed non-overlapping portfolio trade count
- mean net R
- median net R
- win rate
- cumulative net P&L
- maximum drawdown
- mean cost in INR and R
- chronological block summaries

Uncertainty:

- Event-level mean-R 95% CI: cluster bootstrap by signal day, preserving within-day dependence.
- Portfolio mean-R 95% CI: moving-block bootstrap over chronological trade order.
- Bootstrap seed is fixed and stored in provenance.

Because the strategy is frozen, multiple-testing correction is not used to manufacture significance after the fact. The relevant inference is whether the **pre-registered candidate** survives a fresh holdout with economically positive performance and acceptable uncertainty.

## Evidence maturation rule

Phase 9I remains an active prospective gate until at least one of these conditions is reached:

1. 30 completed non-overlapping candidate trades, or
2. 90 calendar days after the frozen cutoff with sufficient completed observations.

A run with no completed new trades is a **data-readiness state**, not a negative strategy result.

## Promotion boundary

Phase 9I does not by itself authorize live deployment.

The candidate can only move to a later paper-trading/implementation gate after the fresh holdout is sufficiently mature and the full results remain economically credible under the pre-registered base and stress friction cases.

## Outputs

Each run must produce:

- `phase9i_provenance.csv`
- `phase9i_completed_event_trades.csv`
- `phase9i_pending_signals.csv`
- `phase9i_event_summary.csv`
- `phase9i_portfolio_trades.csv`
- `phase9i_portfolio_summary.csv`
- `phase9i_run_state.json`

The workflow also publishes a human-readable status page under `docs/phase9i/` and appends a factual run record to the Phase 9I run log.

## Recovery rule

If a chat or workflow stops, read in this order before continuing:

1. `docs/CPR_CONTINUITY_CHECKPOINT.md`
2. `docs/CPR_RESEARCH_LEDGER.md`
3. `docs/CPR_ERROR_LOG.md`
4. `docs/CPR_PHASE9I_PROTOCOL.md`
5. `docs/phase9i/run_log.md`

Never refit or redefine the candidate because a prospective run is inconvenient, sparse or negative.
