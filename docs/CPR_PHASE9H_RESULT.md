# Phase 9H Result — Economic / Strategy-Conditional Validation

**Run:** 35459389390  
**Artifact:** 10589707833  
**Artifact SHA-256:** `fcb6264d34f385309adce2e08d51ffaf198b0d957993457044ba376a1e162108`  
**Frontier:** 39 frozen Phase-5A named leaves  
**2026 selection:** NO

## Question

Do the frozen CPR frontier contexts retain economically meaningful performance after realistic transaction costs across multiple pre-specified strategy families?

## Result

Phase 9H generated 576 strategy × cost × context cells across independent Phase-7 evaluation and untouched 2026 forward evaluation.

The broad result is **not sufficient to promote a trading strategy to live/paper deployment yet**.

One conditional configuration is scientifically interesting:

- Frozen regime leaf: **LEAF_4**
- Side: **SHORT**
- Horizon: **10-session swing**
- Strategy: **ATR stop 1R / target 2R**
- Cost scenario: **Paytm-style ₹10/order + 5 bps/side**
- Phase 7 independent evaluation: n=222, mean net R = **+0.173**, win rate **45.95%**, bootstrap 95% CI **[-0.066, +0.398]**
- Untouched 2026 evaluation: n=28, mean net R = **+0.843**, win rate **71.43%**, bootstrap 95% CI **[+0.351, +1.321]**

The same candidate at the full frontier level is weaker in Phase 7 because LEAF_7 is strongly negative there. Across all frozen leaves, the same strategy/cost/horizon/side has Phase-7 mean net R **+0.021** but 95% CI **[-0.194,+0.233]**, while 2026 is **+0.820** with CI **[+0.429,+1.218]**.

Therefore the 2026 result is a **replication signal worth prospective testing**, not a validated edge. The independent historical interval includes zero, so the evidence does not establish a stable positive expectancy.

## What was tested

Strategy families:
1. Fixed horizon
2. ATR 1R stop / 1R target
3. ATR 1R stop / 2R target
4. ATR 1R stop / breakeven after +1R

Cost scenarios:
- ₹20/order + 5 bps/side
- ₹10/order + 5 bps/side
- ₹20/order + 10 bps/side
- ₹10/order + 10 bps/side

The analysis used a normalized ₹100,000 notional and treated NIFTY50 index paths as a **futures-proxy economic analysis**, not executable futures proof.

## Decision

**Do not declare a live trading strategy from Phase 9H.**

The most useful research candidate for the next controlled gate is:

> **LEAF_4 / SHORT / 10-session swing / ATR 1R stop + 2R target**

It should be evaluated prospectively or in a newly frozen chronological holdout before any paper/live use.

## Important interpretation

This result does not prove CPR is ineffective. It shows that, under the frozen frontier and specified execution-cost assumptions, the evidence is heterogeneous: one named regime/strategy combination is promising in untouched 2026, but its independent historical uncertainty is still too wide to establish a robust edge.

No parameter was selected from 2026. No 2026 result was used to refit the regime tree, horizon, threshold, or strategy.

## Exit criterion

Phase 9H is complete. The project has reached a **usable research conclusion**: a concrete, frozen candidate exists for prospective validation, but there is not yet sufficient evidence to call it a deployable trading strategy.
