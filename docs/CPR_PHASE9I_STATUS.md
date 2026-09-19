# Phase 9I Status

**Phase:** 9I — Prospective Chronological Validation  
**Branch:** `cpr-v1.0-phase9i-prospective-validation`  
**Candidate:** LEAF_4 / SHORT / 10-session swing / ATR 1R stop + 2R target

## State at initiation

Phase 9I has been initialized from the verified Phase 9H state.

The candidate is frozen. The fresh holdout begins strictly after the Phase 8 pinned-source cutoff of 17-Sep-2026 15:30 Asia/Kolkata.

The upstream 2026 source currently available to the project is updated by immutable source commits. The workflow resolves the latest commit on each scheduled/manual execution, caches the source by commit SHA, and never changes the candidate from the incoming data.

A newly started holdout may initially contain zero completed 10-session trades. That is an expected readiness state, not a strategy failure. The workflow remains active and re-checks on the next market-data update.

## Decision state

- Live trading: **NOT AUTHORIZED**
- Paper trading: **NOT AUTHORIZED from Phase 9I initiation alone**
- Candidate refitting: **FORBIDDEN**
- 2026 re-selection: **FORBIDDEN**
- Next gate: sufficiently mature fresh chronological evidence

The canonical ledger and continuity checkpoint are updated at phase initiation; subsequent run-by-run factual state is retained in `docs/phase9i/run_log.md`.
