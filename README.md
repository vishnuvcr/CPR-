# CPR v1.0: Scientific Multi-Dimensional Testing

Research workspace for Central Pivot Range (CPR), Camarilla, Virgin CPR (VCPR), and multi-timeframe trading hypothesis testing across NIFTY 50/100/500.

## Branch

Git branch:

`cpr-v1.0-scientific-multi-dimensional-testing`

Requested display title:

`CPR v1.0: Scientific Multi-Dimensional Testing`

The colon cannot appear in a Git ref, so the executable branch uses the Git-safe slug above.

## What is implemented

- Classical CPR and Camarilla calculations.
- ATR-normalized CPR width and narrow/neutral/wide regime classification.
- Bias-safe prior-day, prior-week and prior-month projection.
- Intraday narrow-breakout and wide-rejection signals.
- CPR/Camarilla R3/S3 confluence reversal hypothesis.
- Online Virgin CPR first-touch state machine.
- BTST end-of-session model that avoids deriving next-day CPR from an unfinished session.
- Hourly swing logic synchronized to prior weekly CPR.
- Option-chain selection, Black-Scholes Greeks and short-vol structure definition.
- Configurable slippage, brokerage, GST, STT, stamp duty, SEBI fee and exchange charges.
- Event-driven single-position execution engine with next-open execution and conservative stop/target bar resolution.
- Walk-forward optimizer with 252-trading-day train / 63-trading-day test / 63-day step defaults.
- Historical constituent membership contract for survivorship-bias control.
- Statistical tear sheet and 10,000-path Monte Carlo/Kelly risk tools.
- GitHub Actions unit-test workflow.

## Repository layout

```text
cpr_lab/
  indicators.py   # CPR, Camarilla, ATR, higher-timeframe projections
  strategies.py   # intraday, VCPR, BTST, swing and option signals
  costs.py        # configurable India-market friction model
  options.py      # Greeks and option-chain helpers
  engine.py       # event-driven execution and risk-based sizing
  walk_forward.py # WFO folds and parameter selection
  data.py         # OHLCV contract and historical membership filter
  metrics.py      # tear-sheet metrics
  risk.py         # Monte Carlo, Kelly, target-return math

docs/
  MASTER_BLUEPRINT.md
  DATA_AND_SURVIVORSHIP.md
  TEAR_SHEET.md
  REALITY_CHECK.md

configs/default.yaml
scripts/run_wfo.py
scripts/run_monte_carlo.py
tests/
.github/workflows/tests.yml
```

## Research protocol

Do not run a single full-sample optimization and call it validation. The intended order is:

1. Validate raw data and historical membership.
2. Generate only prior-period features.
3. Run independent hypothesis backtests with realistic costs.
4. Perform rolling WFO.
5. Freeze the final parameter policy.
6. Evaluate on the untouched final holdout.
7. Run Monte Carlo under multiple sizing policies.
8. Only then evaluate whether leverage changes the return distribution acceptably.

## Important boundary

The 30–40% monthly objective is a scenario to quantify, not a presumed property of CPR. The repository is designed to falsify the hypothesis when the edge disappears after costs, bias controls, or out-of-sample testing.

## Continuity / read-first rule

**Before any new research step, read `docs/CPR_RESEARCH_LEDGER.md` first.** It is the canonical cross-chat project state and records phase status, workflow IDs, artifacts, errors/fixes, methodological decisions, and the current next-step gate. Do not reconstruct the research state from memory when the ledger is available.


## Latest research status

**Phase 9H complete.** Economic/strategy validation found no deployable trading strategy yet. A frozen research candidate for prospective validation is **LEAF_4 / SHORT / 10-session swing / ATR 1R stop + 2R target**. Its Phase-7 independent bootstrap interval still includes zero, so it is not promoted to paper/live trading. See `docs/CPR_PHASE9H_RESULT.md` and `docs/CPR_CONTINUITY_CHECKPOINT.md`.
