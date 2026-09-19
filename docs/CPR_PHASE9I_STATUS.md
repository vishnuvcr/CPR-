# Phase 9I Status

**Phase:** 9I — Prospective Chronological Validation  
**Branch:** `cpr-v1.0-phase9i-prospective-validation`  
**Candidate:** LEAF_4 / SHORT / 10-session swing / ATR 1R stop + 2R target

## State at verified first execution

Phase 9I has been initialized from the verified Phase 9H state and the first two workflow executions have now been checked.

The candidate is frozen. The fresh holdout begins strictly after the Phase 8 pinned-source cutoff of 17-Sep-2026 15:30 Asia/Kolkata.

Verified Run #2:
- Workflow: **35468434477 — SUCCESS**
- Artifact: **10592625047**
- Artifact digest: `sha256:28c25e0aacc1e0a242e3cf281c028609dbdf6ac011d5251f97d5b27e9a662b3e`
- Source commit: `e8f19f3f53ca6fac0b116e83508e814e568dca54`
- Source SHA256: `8861e062df4d1aa861120c2b1613f8b50e0de7d99fd89625066077e224a5aa5f`
- Fresh data end: **2026-09-17 15:25 Asia/Kolkata**
- Completed event trades: **0**
- Completed non-overlap portfolio trades: **0**
- Pending signals: **0**
- State: **INSUFFICIENT_NEW_HOLDOUT**

This is a data-readiness state because the verified fresh source ends before the hard cutoff. It is not evidence for or against the candidate.

The upstream 2026 source is resolved by immutable commit, cached by SHA, and the candidate is never refit or reselected.

## Decision state

- Live trading: **NOT AUTHORIZED**
- Paper trading: **NOT AUTHORIZED from Phase 9I initiation alone**
- Candidate refitting: **FORBIDDEN**
- 2026 re-selection: **FORBIDDEN**
- Next gate: sufficiently mature fresh chronological evidence

The canonical ledger and continuity checkpoint are updated at phase initiation; subsequent run-by-run factual state is retained in `docs/phase9i/run_log.md`.
