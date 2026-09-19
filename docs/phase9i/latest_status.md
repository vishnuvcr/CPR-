# Phase 9I Latest Run

- Workflow run: **35467969660**
- Workflow artifact: **10592206097**
- Artifact digest: `sha256:d21c78a63788286f1ad7c3524316bcfdb44e6b37eea8aa8d589daf6c70a19739`
- Git SHA: `191268535f328bd792a77f3e64f23f2b6e218b49`
- Source commit: `e8f19f3f53ca6fac0b116e83508e814e568dca54`
- Source SHA256: `8861e062df4d1aa861120c2b1613f8b50e0de7d99fd89625066077e224a5aa5f`
- Status: **INSUFFICIENT_NEW_HOLDOUT**
- Fresh data end: **2026-09-17 15:25 Asia/Kolkata**
- Completed event trades: **0**
- Completed non-overlap portfolio trades: **0**
- Pending signals: **0**

The fresh source still ends before the hard holdout cutoff of 2026-09-17 15:30 Asia/Kolkata. This is a **data-readiness state**, not a positive or negative strategy result.

The candidate remains frozen: **LEAF_4 / SHORT / 10-session / ATR 1R stop + 2R target**. No refitting or re-selection was performed.

The first run's repository-persistence failure was an execution/concurrency issue only: the workflow attempted to push from an older checkout after the branch had advanced. The workflow has been hardened to reset to the latest remote branch before persisting state.
