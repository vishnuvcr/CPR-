# Phase 9I Run Log

This is the persistent, factual execution log for the prospective validation phase. It intentionally records run state, data provenance, errors/fixes, and results rather than private chain-of-thought.

## 2026-09-20 — Phase 9I initialized

- Branch: `cpr-v1.0-phase9i-prospective-validation`
- Frozen candidate: LEAF_4 / SHORT / 10-session / ATR 1R stop + 2R target
- Fresh-holdout cutoff: 2026-09-17 15:30 Asia/Kolkata
- 2026 selection/refitting: NO
- Expected behavior before sufficient new data: status may be `INSUFFICIENT_NEW_HOLDOUT`
- Workflow: `.github/workflows/cpr-phase9i-prospective-validation.yml`


## 2026-09-20 — Pre-run validation correction

- Found before first scientific run: incorrect call signature to the frozen tree-construction helper.
- Corrected in commit `a24991d5c7934fdcc7bf3baad08628a66868c241`.
- No data, candidate, cutoff, cost or statistical rule changed.
- First scientific workflow run remains pending.
