# CPR Error Log

## 2026-09-19 — Phase 9G Run #3

- Workflow: CPR Phase 9G Frozen Frontier Consensus Validation
- Run ID: 35390742248
- Commit: e0f44cf8d6eabda496195fcf0753a009084119ca
- Classification: **implementation error; not a scientific result**
- Failure point: `scripts/run_phase9g_frontier_consensus_validation.py`, `assign_frontier_regime()`
- Error:
  `AttributeError: 'numpy.ndarray' object has no attribute 'isin'`
- Cause: `DecisionTreeClassifier.apply()` returns a NumPy array, but the code attempted to call pandas `.isin()` on it.
- Correction: use NumPy membership testing (`np.isin`) while preserving row order.
- Scientific hypothesis changed: **NO**
- Data/holdout policy changed: **NO**
- 2026 used for selection: **NO**
- Follow-up: patch the script, add an invariant/unit-level check, rerun Phase 9G, then inspect artifacts before advancing.
