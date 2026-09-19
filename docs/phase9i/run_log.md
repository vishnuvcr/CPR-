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

## 2026-09-20 — workflow run 35467969660

- Git SHA: `191268535f328bd792a77f3e64f23f2b6e218b49`
- Source commit: `e8f19f3f53ca6fac0b116e83508e814e568dca54`
- Source SHA256: `8861e062df4d1aa861120c2b1613f8b50e0de7d99fd89625066077e224a5aa5f`
- Scientific status: **INSUFFICIENT_NEW_HOLDOUT**
- Completed event trades: 0
- Completed non-overlap portfolio trades: 0
- Repository persistence: failed because the checkout was stale relative to the remote branch; corrected in subsequent workflow revision.

## 2026-09-20 — workflow run 35468434477

- Git SHA: 6246445f9db2a1bf5d11f17894669cfea8f4435f
- Source commit: e8f19f3f53ca6fac0b116e83508e814e568dca54
- Source SHA256: 8861e062df4d1aa861120c2b1613f8b50e0de7d99fd89625066077e224a5aa5f
- Status: **INSUFFICIENT_NEW_HOLDOUT**
- Completed event trades: 0
- Completed non-overlap portfolio trades: 0
- Pending signals: 0

- Artifact: **10592625047**
- Artifact digest: `sha256:28c25e0aacc1e0a242e3cf281c028609dbdf6ac011d5251f97d5b27e9a662b3e`
- Repository persistence: **SUCCESS**
