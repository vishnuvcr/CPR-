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

## 2026-09-19 — Phase 9H rerun attempt after Run #2 fix

- Workflow run ID: 35458024849 (rerun of failed job)
- Classification: **execution/reproducibility issue; not a scientific result**
- Observed: the rerun executed the original failing revision, so it repeated the pre-fix timezone error even though the corrected file had already been committed separately.
- Cause: GitHub Actions job rerun reused the original run revision rather than the newer corrective commit.
- Correction: hardened the timezone-normalization implementation and created a new commit `6f1c403dda9046e3787de0fc599bba4d3d53b56c`; the push trigger on the phase branch will execute the corrected revision.
- Scientific hypothesis changed: **NO**.
- 2026 selection: **NO**.

## 2026-09-19 — Phase 9H fallback Run 1 failure

- Workflow run ID: 35459099070
- Classification: **implementation error; not a scientific result**
- Failure: `SyntaxError: unexpected character after line continuation character`
- Cause: the corrective timezone block was accidentally written with literal `\\n` escape text into the Python source instead of real line breaks.
- Correction: replaced the malformed block with valid Python statements; corrected commit `553f52e41b837290ae73ad309705edecbae1e977`.
- Scientific hypothesis changed: **NO**.
- 2026 selection: **NO**.
- Follow-up: rerun the fallback workflow against the corrected current Phase 9H branch and inspect artifacts.

## 2026-09-19 — Phase 9H successful completion

- Corrected fallback workflow 35459389390 completed successfully.
- The earlier Run #1 ATR feature bug, stale-revision rerun issue, and malformed source patch are closed as implementation errors.
- Artifact 10589707833 was generated and inspected.
- No scientific errors were identified in the final successful run.


## 2026-09-20 — Phase 9I initiation

- Branch: `cpr-v1.0-phase9i-prospective-validation`
- Classification: **phase initialization; no scientific result**
- Fixed candidate: LEAF_4 / SHORT / 10-session / ATR 1R stop + 2R target.
- Fresh holdout cutoff: 2026-09-17 15:30 Asia/Kolkata.
- Important readiness rule: a run with insufficient post-cutoff data is recorded as `INSUFFICIENT_NEW_HOLDOUT`, not as a negative trading result.
- Candidate/refit policy changed: **NO**.
- 2026 re-selection: **NO**.


## 2026-09-20 — Phase 9I pre-run API correction

- Classification: **implementation error detected during pre-run validation; not a scientific result**
- Failure: Phase 9I script initially called `frozen_trees(reference, frontier)`, but the verified Phase 9G helper signature is `frozen_trees(reference_bars)`.
- Cause: the new Phase 9I wrapper incorrectly assumed the helper accepted the frontier as a second positional argument.
- Correction: changed the call to `frozen_trees(reference)` and retained the separate frozen-frontier hash/count assertion before regime assignment.
- Corrective commit: `a24991d5c7934fdcc7bf3baad08628a66868c241`.
- Scientific hypothesis changed: **NO**.
- Candidate parameters changed: **NO**.
- Holdout policy changed: **NO**.
- 2026 selection/refitting: **NO**.
- Status: **CLOSED before first scientific Phase 9I run**.
