# Phase 9G — Final Result

Status: COMPLETE. No replicated incremental consensus information established.

Workflow: CPR Phase 9G Frozen Frontier Consensus Validation
Run #4: 35456904514
Branch: cpr-v1.0-phase9g-frontier-consensus-validation
Commit: aee98cf17f8f5d141cdd8d5f6f014505fc890944
Artifact ID: 10588955161
Artifact digest: sha256:59f975772c315f0a7d698e92ec135c406b515995878a760c04b60a9281be7d84

Frozen frontier: 39 candidates
Frontier SHA256: 601a72f5e64204aee7ff0bb77347d57b0e2b59871b8bc30011282c2dc02c28b2

Primary question:
Does MULTIPLE (>=2 same-side frozen candidates) add information over SINGLE (1 same-side candidate) inside named frozen Phase 5A frontier leaves?

Result:
Not established. Only three regime-level SINGLE-vs-MULTIPLE comparisons met the minimum sample-size requirement. None survived BH/FDR at q<0.05.

Phase 7 intraday 1-bar LONG LEAF_5:
delta win rate -0.75 percentage points; bootstrap CI [-30.83, +29.82] pp; Fisher p=1.000; FDR q=1.000; delta mean R=-0.0104 with CI [-0.0548,+0.0271].

Phase 7 swing 2-session LONG LEAF_5:
delta win rate +17.64 pp; bootstrap CI [-12.76,+48.03] pp; Fisher p=0.346; FDR q=0.519; delta mean R=-0.00091 with CI [-0.2095,+0.1964].

Untouched 2026 swing 2-session LONG LEAF_6:
delta win rate -45.45 pp; bootstrap CI [-72.73,-18.18] pp; Fisher p=0.102; FDR q=0.307; delta mean R=-0.5309 with CI [-1.4835,+0.4583].

CMH stratified tests produced q-values approximately 0.779 to 0.993; no result survived q<0.05.

Direct forward replication showed no matched named-regime cell with the same sign for both consensus delta-win-rate and delta-mean-R across Phase 7 and untouched 2026.

Scientific decision:
- Do not promote consensus count into the economic decision engine.
- Keep SINGLE/MULTIPLE only as descriptive metadata.
- Primary downstream variables are frozen regime/context, side and horizon.
- 2026 remained untouched and was not used for selection.
- Next phase: 9H Economic / Strategy-Conditional Validation.

Implementation history:
- Run #1: malformed Phase 7 download command.
- Run #2: shell quoting failure.
- Run #3: numpy array incorrectly treated as pandas Series via .isin().
- Run #4: successful after correction.

Interpretation boundary:
This does not prove consensus is useless in all conceivable models. It shows the fixed SINGLE-vs-MULTIPLE layer did not demonstrate replicated incremental information within the named frozen frontier under the pre-specified test, so it is not a validated trading feature at this stage.
