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

## 2026-09-19 — Phase 9G Run #4 success

- Run ID: 35456904514
- Final commit: aee98cf17f8f5d141cdd8d5f6f014505fc890944
- All workflow stages passed.
- The prior NumPy `.isin()` implementation error was corrected with `np.isin` and row-aligned regime labels.
- Scientific outputs were generated and artifact integrity/provenance checks passed.
- Result: no replicated incremental consensus information inside named frozen frontier leaves.

## 2026-09-19 — Phase 9H Run #1 failure

- Workflow run ID: 35457500756
- Classification: **implementation error; not a scientific result**
- Failure: no strategy observations generated.
- Root cause: the raw OHLCV frame used by the simulator did not contain `D_ATR20`; the event builder computed ATR internally but the simulator was reading ATR from the raw bars, so every event was rejected as invalid ATR.
- Correction: create a featured bar frame with `add_intraday_daily_features(... daily_reference_features(...))` before simulation and use its `D_ATR20`.
- Added invariant: fail early if the featured bar frame lacks `D_ATR20`.
- Scientific hypothesis changed: NO.
- 2026 selection: NO.

## 2026-09-19 — Phase 9H Run #2 failure

- Workflow run ID: 35458024849
- Classification: **implementation error; not a scientific result**
- Failure point: `cost_roundtrip()` in `scripts/run_phase9h_economic_strategy_validation.py`
- Error: `TypeError: Cannot compare tz-naive and tz-aware timestamps`
- Cause: trade dates derived from timezone-aware Asia/Kolkata bar indices were compared directly with a timezone-naive 2026-04-01 cutoff.
- Correction: normalize the trade timestamp to timezone-naive before the date comparison; no price, event, holdout, strategy, or cost rule was changed.
- Scientific hypothesis changed: **NO**.
- 2026 selection: **NO**.
- Follow-up: rerun Phase 9H after the patch and inspect all generated artifacts before interpretation.
