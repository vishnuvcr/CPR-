# CPR Research Master Ledger / Continuity File

**Purpose:** This is the canonical continuity record for the CPR (Central Pivot Range) research project.  
**Read-first rule:** Before starting, modifying, interpreting, or advancing any research phase, read this file from the current branch and reconcile the proposed action against the latest state recorded here.

> **Persistence rule:** Every completed phase, workflow run, artifact, error/fix, methodological decision, interpretation, branch/commit, and chat-derived research decision must be recorded here or linked from here.  
> **Rationale preservation:** The ledger preserves concise decision rationales and evidence summaries. It does not reproduce private chain-of-thought.

---

## 0. Canonical project identity

- Repository: `vishnuvcr/CPR-`
- Project: **CPR v1.0 — Scientific Multi-Dimensional Testing**
- Research domain: CPR / Camarilla / Virgin CPR / multi-timeframe NIFTY research
- Primary objective: discover reproducible, bias-controlled CPR-conditioned market contexts and determine whether any validated context can support a robust trading/strategy-selection framework.
- The earlier idea of proving that “CPR works universally” has been superseded by a conditional/context-dependent research objective.
- The 30–40% monthly return objective is a scenario to quantify, not a target to optimize toward.

### Non-negotiable scientific rules

1. Chronological OOS evaluation comes before deployment claims.
2. No threshold/horizon/candidate selection from the untouched 2026 holdout.
3. No look-ahead from incomplete source periods.
4. Independent hypotheses are separated from conditional selection and strategy selection.
5. Report uncertainty, sample size, temporal stability and economic friction, not just average returns.
6. Multiple-testing context must be acknowledged; BH/FDR or other pre-specified correction is used where appropriate.
7. Do not turn an attractive cell into a trading rule merely because it is numerically large.
8. Costs/execution realism must be tested before paper/live promotion.
9. Generic ML remains gated until interpretable conditional structure earns the right to be modeled.
10. No deployment promotion without a prospective/paper-trading gate.

---

## 1. Current state at the time this ledger was created

**Date:** 2026-09-19 (Asia/Kolkata)

**Current phase:** **9H — Economic / Strategy-Conditional Validation (next phase)**

**Current status:** Phase 9G COMPLETE; consensus layer not promoted. Phase 9H branch is being prepared.

Latest active branch:
`cpr-v1.0-phase9g-frontier-consensus-validation`

Latest active Phase 9G workflow:
- Run #4 (successful): **35456904514**
- Commit: `aee98cf17f8f5d141cdd8d5f6f014505fc890944`
- Artifact ID: **10588955161**
- Artifact digest: `sha256:59f975772c315f0a7d698e92ec135c406b515995878a760c04b60a9281be7d84`
- Prior Run #3 failure corrected: NumPy array incorrectly treated as pandas Series in `assign_frontier_regime()`.
- URL: https://github.com/vishnuvcr/CPR-/actions/runs/35390742248

The latest 9G run was started after correcting a shell-quoting failure in the Phase 7 dataset download step. At the point of this ledger update, the run status is still being monitored; **no 9G scientific conclusion is recorded yet**.

### Read-before-next-step rule

Before any Phase 9G result interpretation or Phase 10/next-phase creation:
1. Read this ledger.
2. Inspect the latest Phase 9G workflow status.
3. If successful, inspect the uploaded artifacts themselves.
4. Check that the artifact provenance matches the frozen Phase 5A frontier SHA.
5. Only then decide whether the next phase is justified.

---

## 2. Frozen research lineage

### Phase 5A
**Question:** Which interpretable CPR-conditioned contexts show favorable sensitivity/specificity and conditional expectancy under TRAIN-only regime discovery?

- Frozen candidate frontier size: **39 candidates**
- Frontier SHA256:
  `601a72f5e64204aee7ff0bb77347d57b0e2b59871b8bc30011282c2dc02c28b2`
- Method: shallow deterministic decision-tree regime discovery, chronological TRAIN / VALIDATION / TEST, sensitivity/specificity Pareto screening.
- Important rule: the frontier is frozen; later phases do not refit it on Phase 7 or 2026.

### Phase 5B
**Status:** COMPLETE — frozen candidate validation.

### Phase 6
**Status:** COMPLETE — robustness diagnostics.

### Phase 7
**Status:** COMPLETE — independent replication.

### Phase 8
**Status:** COMPLETE — untouched 2026 forward holdout.

### Phase 9A
**Status:** COMPLETE — shadow decision engine.

### Phase 9B
**Status:** COMPLETE — fixed consensus taxonomy.

### Phase 9C
**Status:** COMPLETE — consensus OOS returns.

### Phase 9D
**Status:** COMPLETE — sensitivity/specificity classification analysis.

### Phase 9E
**Status:** COMPLETE — incremental-information + consensus robustness.

### Phase 9F
**Status:** COMPLETE — regime × consensus interaction, including all frozen tree leaves.

### Phase 9G
**Status:** COMPLETE — frontier-only consensus validation found no replicated incremental consensus information; consensus is not promoted into the economic decision engine.

---

## 3. Earlier phase history and decisions

### Phase 0 — data integrity / reproducibility
**Status:** COMPLETE.

Purpose:
- canonical data validation
- provenance
- reproducibility smoke tests
- bias-safe feature construction
- historical membership/survivorship controls

Decision:
- Continue only after data/provenance smoke checks passed.

### Phase 1A — unconditional intraday CPR edge
**Status:** COMPLETE.

Key result:
- ~4,281 signals characterized.
- Unconditional next-bar mean outcome was approximately zero / not statistically significant.

Decision:
- A universal unconditional intraday CPR edge was not established.

### Phase 1B — conditional intraday decomposition
**Status:** COMPLETE.

Important audit:
- Initial width classification put all generated signals in the narrow bucket; fixed 0.50/1.00 ATR thresholds did not create useful neutral/wide signal samples.
- Additional width coverage/decile diagnostics were added rather than optimizing thresholds.

Decision:
- Do not manufacture a regime by threshold searching simply to get balanced groups.

### Phase 1C — multi-horizon intraday outcomes
**Status:** COMPLETE.

Horizons:
- 1 bar
- 3 bars
- 6 bars
- 12 bars
- EOD

Decision:
- No statistically reliable aggregate intraday edge.
- Phase 1D stop/target lifecycle optimization deferred rather than forcing optimization without a justified edge.

### Phase 2A — BTST
**Status:** COMPLETE — low sample / no stable separation.

Critical correction:
- Original implementation risked using a full source-session close for earlier intraday BTST events.
- BTST logic was corrected to use only the final fully completed source-session bar and next-session open.
- Corrected characterization produced only **31 valid end-of-session events**.

Decision:
- BTST executable lifecycle/cost optimization deferred.
- Advance to swing characterization.

### Phase 3A — swing horizons
**Status:** COMPLETE.

Horizons:
- 2 sessions
- 3 sessions
- 5 sessions
- 10 sessions

Observation:
- Aggregate results did not establish a stable overall effect.
- LONG/SHORT separation became more pronounced at longer horizons.

Critical dependence correction:
- Overlapping observations made IID reasoning inappropriate.
- Dependence-aware stability analysis was added.

Decision:
- Longer-horizon directional structure was worth conditional-selector research, but not direct strategy promotion.

### Phase 3A directional stability
**Status:** COMPLETE.

Important result:
- Holm-adjusted clustering / fixed-block analysis supported longer-horizon directional separation.
- 2015–2019 vs 2020–2024 showed material regime dependence.

Decision:
- Advance to conditional cross-horizon selection rather than claiming a universal swing rule.

---

## 4. Phase 4 selector lineage

### Phase 4 — cross-horizon conditional selector
**Status:** COMPLETE — no statistically reliable selector advantage established.

Design:
- identical signal population for selected vs fixed-horizon comparison
- chronological OOS evaluation
- no look-ahead selection

Result:
- Selected point estimate was positive.
- Paired OOS differences were not statistically significant.

Decision:
- Do NOT promote selector.
- Gate ML.

### Phase 4B — selector null/stability stress test
**Status:** COMPLETE.

Protocol:
- 5,000 reproducible random-horizon null simulations
- exact Phase 4 OOS signal identities preserved
- dependence-aware paired block bootstrap
- concentration diagnostics

Key result:
- Selected mean approximately **+0.190 R/day**
- Random-horizon null approximately **+0.125 R/day**
- Empirical two-sided p approximately **0.162**
- All paired 95% block-bootstrap intervals crossed zero.

Decision:
- Selector incremental value not validated.
- ML remained gated.

### Phase 4C — selector temporal placebo / stale-selection / robustness
**Status:** COMPLETE.

Key results:
- Actual selected mean: **+0.190 R/day**
- Temporal-placebo mean: **+0.222 R/day**
- Placebo SD: ~**0.0275 R**
- 2.5–97.5% placebo interval: approximately **+0.167 to +0.272 R**
- Empirical two-sided placebo p: **0.264**
- Chronological split means: **+0.012, +0.448, +0.109 R/day**
- Lagged selector: **+0.291 R/day**
- Fixed-horizon references: roughly **+0.111 to +0.131 R/day**

Decision:
- No evidence of incremental selector value robust to temporal placebo/stale-selection stress.
- Generic ML selector development remains gated.

---

## 5. Phase 5A–8 cross-phase persistence

Canonical source:
`docs/CPR_CROSS_PHASE_PERSISTENCE.md`

Frozen candidate rules evaluated: **39**.

Cross-phase diagnostic highlights:
- Phase 5B positive mean-R count: 18/39
- Phase 6 positive mean-R count: 18/39
- Phase 7 independent replication: 11/39 with positive 95% CI-excluding-zero effect
- Phase 8 2026 YTD: 23/39 positive by mean

Important stability facts:
- **0** candidates passed the strict Phase 6 robustness diagnostic.
- **4/11** Phase 7 positive-CI candidates remained positive in the 2026 holdout.
- **0** frozen candidates were positive in all three 2026 windows with at least 5 signals per window.
- Cross-phase mean-R relationships were weak/inconsistent; the persistence report explicitly concludes that a single universal CPR candidate should not be promoted.

Key implication:
- CPR appears more plausibly **context-dependent** than universally effective.
- The decision-engine research therefore moved toward regime/context discovery rather than single-rule optimization.

---

## 6. Phase 9A–9D consensus lineage

### 9A — shadow engine
A deterministic frozen decision/shadow infrastructure was introduced so downstream testing could operate on fixed states rather than ad hoc analysis.

### 9B — consensus taxonomy
Fixed taxonomy:
- NO_SIGNAL
- CONFLICT
- SINGLE_LONG
- MULTIPLE_LONG_2_3
- MULTIPLE_LONG_4_PLUS
- SINGLE_SHORT
- MULTIPLE_SHORT_2_3
- MULTIPLE_SHORT_4_PLUS

No downstream phase is allowed to change this taxonomy based on 2026.

### 9C — consensus OOS returns
Purpose:
- describe OOS returns conditional on fixed consensus states.

### 9D — sensitivity/specificity
For each native horizon/side event:
- Positive prediction = matching-side CPR consensus state
- Negative prediction = NO_SIGNAL + CONFLICT + opposite-side state
- Positive outcome = realized return > 0

#### Phase 7 independent replication — strongest descriptive J cells
- 3-session LONG: sensitivity ~48.2%, specificity ~64.6%, Youden J ~0.128
- 12-bar LONG: sensitivity ~29.8%, specificity ~81.1%, J ~0.109
- 6-bar LONG: sensitivity ~28.9%, specificity ~80.5%, J ~0.094
- 2-session LONG: sensitivity ~46.6%, specificity ~62.6%, J ~0.091

#### Untouched 2026
- 2-session LONG: sensitivity ~46.2%, specificity ~75.6%, J ~0.217
- 3-session LONG: sensitivity ~41.5%, specificity ~72.1%, J ~0.136
- 10-session SHORT: sensitivity 0%, specificity 100% — technically high specificity but essentially no positive detection.

Decision:
- Multi-session LONG contexts deserved further investigation.
- No particular horizon/cell was declared validated because many combinations had been examined.

---

## 7. Phase 9E — incremental information

**Workflow:** CPR Phase 9E Consensus Incremental Information  
**Result:** COMPLETE ✅  
**Run time:** ~3m41s  
**Branch:** `cpr-v1.0-phase9e-incremental-information`

Question:
> Does multiple same-side CPR agreement add information beyond ordinary CPR directional activation?

Protocol:
- Baseline = >=1 frozen matching-side candidate.
- Strict = >=2 frozen matching-side candidates.
- SINGLE vs MULTIPLE compared only within baseline-positive events.
- Bootstrap 95% CIs.
- Fisher exact two-sided tests.
- BH/FDR correction.
- Year-by-year stability.
- 2026 untouched.

Important findings:
- Consensus count was **not monotonic** as a confidence score.
- Several Phase 7 swing cells showed SINGLE > MULTIPLE, while 2026 showed reversals in the same areas.
- Therefore “more agreement = stronger signal” was not supported as a general rule.

Decision:
- Do NOT implement simple consensus-count scaling.
- Do NOT implement blanket >=2-consensus gating.
- Investigate **regime × consensus interaction**.

---

## 8. Phase 9F — regime × consensus interaction

Branch:
`cpr-v1.0-phase9f-regime-consensus-interaction`

Successful workflow:
- Run ID **35389425578**
- Final successful commit:
  `66f45b6fb8d4dc3116b35e4029cfbd94ab12e374`
- Artifact ID: **10565821111**
- Population: **8,890**
- Interaction tests: **14**
- Uploaded CSV files: 5

The 9F workflow contained and corrected multiple implementation errors during development:
1. missing `outcome_positive`
2. Series/record access bug in consensus labeling
3. missing `asset` column

These were implementation fixes, not research-hypothesis changes.

### 9F result

The analysis showed some apparently material regime × consensus interactions, but some of the strongest historical-looking effects occurred in `OTHER_FROZEN_TREE_LEAF`, a heterogeneous bucket containing tree leaves outside the named frozen Pareto frontier.

Examples from the 9F successful run:
- Phase 7, swing 10-session LONG, OTHER_FROZEN_TREE_LEAF:
  - SINGLE n=17, win rate ~88.2%
  - MULTIPLE n=68, win rate ~42.6%
  - delta ~−45.6 percentage points
  - Fisher p ~0.000849
  - FDR q ~0.00747
  - mean-R delta ~−1.1349 R
  - bootstrap CI approximately [−2.007, −0.286] R
- Phase 7, swing 5-session LONG, OTHER:
  - delta win rate ~−42.1 pp
  - p ~0.00107
  - FDR q ~0.00747
  - mean-R delta ~−0.509 R
- Untouched 2026, swing 5-session LONG, OTHER:
  - delta win rate ~+26.3 pp
  - mean-R delta ~+1.021 R

Thus the historical interactions can **reverse sign in untouched 2026**, demonstrating context dependence and/or regime instability.

Decision:
- Do not use `OTHER_FROZEN_TREE_LEAF` to justify a deployable rule.
- Tighten to **named frozen frontier leaves only**.
- Add stratified inference rather than relying only on cell-by-cell p-values.

---

## 9. Phase 9G — frozen frontier-only validation

**Purpose:** Remove the heterogeneous `OTHER_FROZEN_TREE_LEAF` population and test whether consensus adds information inside actual named frozen Phase 5A frontier regimes.

Branch:
`cpr-v1.0-phase9g-frontier-consensus-validation`

Workflow:
**CPR Phase 9G Frozen Frontier Consensus Validation**

Current run:
- Run #3
- Run ID: **35390742248**
- Current commit:
  `e0f44cf8d6eabda496195fcf0753a009084119ca`
- URL:
  https://github.com/vishnuvcr/CPR-/actions/runs/35390742248

9G methodology:
- Recreate frozen Phase 5A trees from reference TRAIN data.
- Verify frontier SHA.
- Include ONLY named Pareto frontier leaves.
- Exclude all OTHER tree leaves.
- Compare SINGLE vs MULTIPLE within each named frontier regime.
- Fisher exact + BH/FDR.
- Bootstrap 95% CI for win-rate and mean-R differences.
- Cochran–Mantel–Haenszel test stratified by named frontier regime.
- Year-by-year stability.
- Direct Phase 7 vs 2026 descriptive replication table.
- No threshold refitting.
- No candidate selection.
- No strategy selection.
- No use of 2026 for model selection.

### 9G implementation corrections

Run #1/2 failed before scientific evaluation due pipeline issues:
- incorrect Phase 7 URL / shell quoting in the workflow.

Those errors were corrected.
**Do not reinterpret the failed runs as scientific failures.** They were infrastructure failures.

---

## 10. Workflow/run/error register

| Run | Phase | Run ID | Status | Main event |
|---|---|---:|---|---|
| #4 | 5B | 35322009351 | COMPLETE | Frozen candidate validation |
| #4 | 6 | 35333187046 | COMPLETE | Robustness |
| #8 | 7 | 35331621044 | COMPLETE | Independent replication |
| #2 | 8 | 35334523903 | COMPLETE | Untouched 2026 |
| 9D work | 9D | multiple | COMPLETE | classification + reproducibility |
| #1 | 9E | workflow-linked | COMPLETE | incremental consensus |
| #1 | 9F | 35381702731 | FAIL | implementation issue |
| #2 | 9F | 35381732564 | FAIL | missing outcome label / pipeline issue |
| #3 | 9F | 35384718108 | FAIL | missing asset column |
| #4 | 9F | 35388737698 | COMPLETE | regime × consensus |
| #1 | 9G | 35390362965 | FAIL | bad Phase 7 URL |
| #2 | 9G | 35390384998 | FAIL | shell quoting |
| #3 | 9G | 35390742248 | FAIL | NumPy array `.isin` implementation error; no scientific output produced |
| #4 | 9G | 35456904514 | COMPLETE | Frontier-only consensus validation; no replicated incremental information |

Full workflow logs remain available through the corresponding GitHub Actions pages. The ledger records the scientific-relevant conclusions and the reason each implementation failure occurred.

---

## 11. Chat/session continuity record

### User's continuation instruction
The user explicitly asked to continue the CPR research in this chat and not restart the workflow.

### User's requested scientific standard
The user repeatedly instructed:
- complete the phases without unnecessary stopping;
- rectify errors automatically;
- maintain scientific validity;
- avoid bias and silly mistakes;
- do not stop midway except for serious issues;
- do not assume the strategy is only long iron condor;
- test multiple strategy types after regime/direction/horizon discovery.

### Research-direction decision from the conversation
The research direction was intentionally changed from:
> “Does CPR work?”

to:
> “Under what combinations of CPR context/regime, consensus and horizon does CPR provide measurable conditional discrimination?”

This is an important conceptual decision and must not be lost between chats.

### 9D interpretation from the conversation
The 2-session LONG and 3-session LONG cells looked interesting across Phase 7 and 2026, but no one was allowed to call them “validated” merely because their 2026 Youden J was large.

### 9E interpretation from the conversation
Consensus count was found to be context-dependent rather than a simple confidence multiplier.

### 9F interpretation from the conversation
Regime × consensus interaction was promising as a scientific hypothesis but contaminated by heterogeneous `OTHER_FROZEN_TREE_LEAF` observations, motivating 9G.

### Current continuation instruction
The user requested autonomous continuation without stopping midway for ordinary implementation errors. Therefore the workflow should rectify routine errors automatically, log them, rerun, and continue until the next serious research gate. The repository ledger remains the authoritative checkpoint.

---

## 12. Decision register

### D-001 — Universal CPR rule rejected
**Status:** ACTIVE  
Reason: unconditional and broad cross-phase effects are not stable enough.

### D-002 — Generic ML selector gated
**Status:** ACTIVE  
Reason: Phase 4B/4C selector edge did not survive null/stress/placebo validation.

### D-003 — Context-dependent CPR hypothesis retained
**Status:** ACTIVE  
Reason: conditional regime discovery and later consensus analysis suggest heterogeneous effects.

### D-004 — Simple consensus-count confidence score rejected
**Status:** ACTIVE  
Reason: Phase 9E did not show monotonic, replicated improvement from SINGLE to MULTIPLE.

### D-005 — Regime × consensus interaction retained for investigation
**Status:** ACTIVE  
Reason: Phase 9F found some statistically interesting interactions, but several were located outside named frontier leaves and/or reversed in 2026.

### D-006 — Named frontier-only validation required
**Status:** SATISFIED / COMPLETE
Reason: Phase 9G removed heterogeneous OTHER leaves and completed the pre-specified validation.

### D-009 — Phase 9G Run #3 failure classified as implementation-only
**Status:** CLOSED
Reason: Run #4 successfully reproduced the full analysis after the NumPy membership fix.

### D-010 — Consensus not promoted into downstream economic decision engine
**Status:** ACTIVE
Reason: Phase 9G produced no FDR-significant incremental SINGLE-vs-MULTIPLE result and no matched Phase 7-to-2026 sign replication.

### D-007 — 2026 remains untouched
**Status:** LOCKED  
No threshold/horizon/candidate/strategy selection can use 2026.

### D-008 — Paper/live trading remains gated
**Status:** LOCKED  
Need validated signal/context structure + economic friction + execution checks + prospective paper gate.

---

## 13. What has NOT been proven

The project has **not** yet proven:
- that CPR alone has a universal edge;
- that any one frozen candidate is deployable;
- that consensus count improves prediction;
- that a specific horizon is universally superior;
- that any option structure is appropriate for a given regime;
- that ML will improve the research outcome;
- that a 30–40% monthly return is achievable robustly.

These statements must remain explicit in future chats and manuscripts.

---

## 14. Next-phase gate

After 9G completes:

### If 9G shows no replicated incremental information
- consensus layer should be reduced/removed from the decision engine;
- use the independently supported frozen regime/direction information only;
- move to economic/strategy-conditional testing without forcing consensus.

### If 9G shows replicated incremental information
- preserve only the pre-specified, replicated state structure;
- proceed to an economic/strategy-selection study;
- test multiple strategy families conditioned on the same frozen regime/context definitions;
- do not optimize a strategy specifically to fit 2026.

### In either case
Before any ML:
- lock the interpretable decision variables;
- define a new training period distinct from the untouched holdout;
- specify the model family, features, loss, calibration, and rejection/no-trade policy before fitting.

---

## 15. Artifact/provenance principle

Every future phase should store:
- workflow run ID
- commit SHA
- branch
- frozen-data SHA/provenance
- script path
- workflow path
- output artifact name/ID
- key result summary
- decision
- error/fix history
- whether 2026 was read for selection (must be **NO** for all research phases prior to prospective use)

---

## 16. Future-chat operating instruction

**Before doing any new research work in a fresh chat:**
1. Locate this file.
2. Read it completely enough to understand the current phase and decision gates.
3. Inspect the latest referenced workflow/run.
4. Inspect the latest artifact before interpreting results.
5. Continue from the recorded state; do not recreate earlier phases from memory.
6. After the work, update this file before opening the next phase.

If this file conflicts with recollection from a conversation, **the repository evidence wins** unless a newer verified commit/run explicitly supersedes it.

---


## 17. Ledger establishment event

**2026-09-19:** Canonical cross-chat continuity ledger established after the user reported continuity loss between chats. The repository README was updated to require reading this ledger before every new research step. The ledger now records phase lineage, workflow/run IDs, scientific decisions, implementation failures/fixes, current gates, and research-relevant chat decisions. Future updates must be made before advancing to another phase.


## 18. Latest verified execution event

**2026-09-19:** Phase 9G Run #3 was inspected directly. Data preparation and frozen-frontier verification passed; the analysis failed because `DecisionTreeClassifier.apply()` returned a NumPy array and the code called pandas `.isin()`. Error logged in `docs/CPR_ERROR_LOG.md`. Correction is implementation-only; rerun is required before any scientific interpretation.
