# CPR cross-phase persistence synthesis

This report joins already-computed outputs from Phases 5B, 6, 7 and 8. No thresholds are fitted, adjusted, ranked for deployment, or selected here.

## Frozen research pipeline

5A conditional discovery → 5B frozen validation → 6 robustness → 7 independent replication → 8 untouched 2026 holdout.

## Key findings

- Frozen candidate rules evaluated: **39**.
- Positive mean-R counts: Phase 5B test **18/39**, Phase 6 test **18/39**, Phase 7 independent replication **11/39 with a positive 95% CI-excluding-zero effect**, Phase 8 2026 YTD **23/39**.
- Candidates positive by mean in 5B, 6, and 2026 holdout while also passing the Phase 7 positive-CI replication diagnostic: **3**.
- Candidates passing the strict Phase 6 robustness diagnostic (q<0.10, CI>0, ≥75% positive under threshold perturbation and adjacent-horizon checks): **0**.
- Phase 7 positive-CI candidates that remained positive in the 2026 holdout: **4/11**.
- Candidates with the same mean-R sign in all three 2026 windows, with ≥5 signals in each window: **1**; positive in all three windows: **0**.

## Interpretation

1. The frozen CPR effects are not stable enough across time to support a universal CPR rule. The untouched 2026 holdout shows substantial quarter-to-quarter sign changes and/or sparse activation for most previously interesting candidates.
2. The strongest evidence of persistence is concentrated in a small set of Phase-7-replicated candidates, but several have very low 2026 signal counts. They remain observationally interesting rather than validated for deployment.
3. Candidate 20 (intraday EOD LONG) is the clearest 2026 example with a non-trivial sample: **49** YTD signals, mean **+0.118R**, sensitivity **50.8%**, specificity **82.4%**, Youden J **0.332**. However, it was negative in the original Phase-6 test and did not pass the strict robustness diagnostic; its 2026 quarterly mean moved from about **+0.177R / +0.113R** in Q1/Q2 to **−0.056R** in Q3-to-date. This is evidence of context dependence, not a deployment warrant.
4. Candidates 16 (12-bar LONG), 32 (3-session SHORT), and 36 (10-session LONG) are positive in 2026 YTD and in the Phase-7 replication, but their 2026 activation counts are only **7, 6 and 4** respectively. These counts are too small to establish a stable operational edge.
5. Phase 5B and Phase 6 use the same original test period; Phase 6 adds robustness diagnostics but is not an independent dataset. Phase 7 and Phase 8 are the independent/forward checks.
6. The 2026 holdout was not used to modify rules, and no candidate is promoted based on its holdout result.

## Phase-7 replicated candidates entering Phase 8

| Candidate | Horizon | Side | Phase 5B mean R | Phase 7 mean R (95% CI) | Phase 8 YTD mean R | Phase 8 signals | Phase 8 sensitivity | Phase 8 specificity | Phase 8 Youden J |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 36 | 10session | LONG | 0.604 | 0.715 [0.046, 1.857] | 0.184 | 4 | 9.5% | 100.0% | 0.095 |
| 32 | 3session | SHORT | 0.587 | 0.400 [0.320, 0.422] | 0.149 | 6 | 4.8% | 95.4% | 0.001 |
| 20 | EOD | LONG | -0.061 | 0.264 [0.180, 0.329] | 0.118 | 49 | 50.8% | 82.4% | 0.332 |
| 16 | 12bar | LONG | 0.032 | 0.119 [0.053, 0.179] | 0.089 | 7 | 6.9% | 97.0% | 0.039 |
| 2 | 1bar | LONG | 0.002 | 0.007 [0.002, 0.012] | -0.008 | 16 | 8.3% | 88.1% | -0.036 |
| 15 | 6bar | SHORT | -0.024 | 0.051 [0.003, 0.105] | -0.019 | 19 | 15.6% | 85.5% | 0.011 |
| 22 | EOD | SHORT | -0.090 | 0.147 [0.022, 0.328] | -0.071 | 41 | 30.0% | 66.7% | -0.033 |
| 30 | 3session | LONG | 0.043 | 0.781 [0.491, 1.027] | -0.206 | 31 | 24.6% | 82.6% | 0.072 |
| 27 | 2session | SHORT | 0.170 | 0.064 [0.064, 0.064] | -0.401 | 21 | 9.2% | 76.2% | -0.146 |
| 35 | 10session | LONG | 0.105 | 0.629 [0.088, 1.261] | -0.416 | 40 | 38.1% | 77.8% | 0.159 |
| 26 | 2session | LONG | -0.245 | 0.604 [0.545, 0.613] | -0.574 | 31 | 3.1% | 66.3% | -0.306 |

## 2026 window consistency

No frozen candidate was positive in all three 2026 windows with at least five signals in each window. One candidate had the same sign in all three windows under that sample-size rule, but the sign was negative.

## Descriptive cross-phase Spearman correlations

| Metric A | Metric B | Spearman rho | n |
|---|---|---:|---:|
| p5b_mean_R | p7_mean_R | 0.264 | 39 |
| p5b_mean_R | p8_mean_R | -0.041 | 39 |
| p7_mean_R | p8_mean_R | -0.331 | 39 |
| p5b_J | p7_J | 0.463 | 39 |
| p5b_J | p8_J | -0.016 | 39 |
| p7_J | p8_J | -0.060 | 39 |

These correlations are descriptive only; they are not tests of deployment utility.

## Phase 9 implication

The cross-phase evidence does **not** justify promoting a single frozen CPR candidate to an automated live-trading rule. The next stage should preserve the discovered context dependence and explicitly handle no-trade/insufficient-evidence states, followed by paper trading only after realistic transaction-cost and execution checks.

## Provenance

- Phase 5B workflow run: **35322009351** (run #4).
- Phase 6 robustness workflow run: **35333187046** (run #4).
- Phase 7 independent replication workflow run: **35331621044** (run #8).
- Phase 8 untouched forward holdout workflow run: **35334523903** (run #2).
- All 39 candidates originate from the frozen Phase 5A TRAIN Pareto frontier; Phase 8 verifies the frozen frontier SHA before evaluation.
