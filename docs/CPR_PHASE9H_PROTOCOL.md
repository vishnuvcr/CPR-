# Phase 9H Protocol — Economic / Strategy-Conditional Validation

## Objective

Determine whether the frozen, named CPR regimes from the Phase 5A frontier retain economically meaningful performance when translated into multiple pre-specified execution/strategy families with realistic friction.

Phase 9H does NOT optimize a strategy on the untouched 2026 holdout. It does not use consensus count as a decision variable because Phase 9G did not establish replicated incremental consensus information.

## Primary research question

Within frozen named CPR regimes, side and native horizon, how does net performance change across fixed strategy/execution policies after slippage, brokerage, statutory charges and conservative execution?

## Frozen inputs

- Phase 5A frontier: 39 candidates.
- Frontier SHA256: 601a72f5e64204aee7ff0bb77347d57b0e2b59871b8bc30011282c2dc02c28b2
- Phase 7: independent replication dataset.
- Phase 8: untouched 2026 forward dataset.
- Consensus: descriptive metadata only; excluded from strategy selection.

## Strategy families

All families use the frozen event side and frozen regime membership. No strategy-specific threshold is fitted.

1. FIXED_HORIZON
   - Entry: next available bar open after the frozen signal.
   - Exit: native frontier horizon close.
   - Stop/target: none.
   - Purpose: benchmark for implementation effects.

2. ATR_STOP_1R_TARGET_1R
   - Entry: next bar open.
   - Initial stop: 1.0 x signal-time ATR20.
   - Target: +1.0R.
   - If neither is touched, exit at native horizon close.
   - Conservative gap handling.

3. ATR_STOP_1R_TARGET_2R
   - Entry: next bar open.
   - Initial stop: 1.0 x ATR20.
   - Target: +2.0R.
   - If neither is touched, exit at native horizon close.
   - Conservative gap handling.

4. ATR_STOP_1R_BREAKEVEN
   - Entry: next bar open.
   - Initial stop: 1.0 x ATR20.
   - Once price reaches +1.0R, stop moves to entry.
   - Exit at native horizon close if not stopped.
   - Conservative gap handling.

The first implementation will retain all four families simultaneously. No family is selected from 2026.

## Cost scenarios

### Base friction
- Slippage: 5 bps per side.
- Paytm Money brokerage parameter: ₹20 per executed order as the research base, based on Paytm Money's published flat-₹20 pricing update effective 15 Jan 2025.
- Alternative brokerage sensitivity: ₹10 per executed F&O order because Paytm Money's current F&O FAQ currently displays ₹10 per unique F&O order. The conflicting published materials are therefore retained as a sensitivity scenario rather than silently choosing one.
- GST: 18% on brokerage + exchange/SEBI charges.
- SEBI turnover fee: 0.0001% of turnover.
- Statutory/exchange rates are instrument-specific and date-aware.

### Stress friction
- Slippage: 10 bps per side.
- Brokerage: ₹20/order.
- Same statutory rates.

### Important tradability boundary
The historical source is the NIFTY50 index, not a directly tradable futures contract. Phase 9H therefore reports a normalized economic sensitivity per ₹100,000 notional and labels it as an index-proxy economic analysis. It is not treated as proof of executable NIFTY futures/options performance.

Actual futures/options contract validation remains downstream and requires instrument-specific historical contract data, lot sizes, quotes and expiry handling.

## Return normalization

For comparability:
- Notional = ₹100,000.
- Signal-time risk unit = notional x ATR20 / entry_price.
- Gross P&L is calculated from actual path prices.
- Net P&L subtracts explicit brokerage, exchange, SEBI, STT, stamp duty, GST and adverse slippage.
- Net_R = net P&L / signal-time one-ATR risk unit.
- Fixed-horizon benchmark uses the same ATR risk denominator even though it has no stop.

## Execution assumptions

- Signals are generated only from information available at the signal timestamp.
- Entry is next available bar open.
- A stop/target gap through at the next bar open exits at that open.
- If stop and target are both touched in the same bar, stop is assumed first.
- No perfect mid-price fills.
- Strategy results are reported before any portfolio-level leverage selection.

## Statistical reporting

For every dataset x strategy x asset x horizon x side x regime cell:
- n
- win rate
- mean net_R
- median net_R
- total net P&L
- mean gross_R
- mean costs_R
- transaction count
- bootstrap 95% CI for mean net_R
- bootstrap 95% CI for win rate
- drawdown of the sequential trade/equity path for descriptive context

The phase is primarily descriptive/economic. It does not select a winner.

## Chronological rule

- Phase 7 is the independent evaluation/development context for this fixed strategy library.
- Phase 8 (2026) remains a forward untouched evaluation.
- No 2026 statistic may determine which strategy family, regime, side or horizon is selected.

## Strategy selection gate

No single strategy is promoted from Phase 9H based on one cell.

A later strategy-selection phase must require:
1. Phase 7 evidence across sufficient sample size.
2. Replication on untouched 2026.
3. Net performance after base and stress friction.
4. Stability across chronological subperiods.
5. No dependence on a tiny sample cell.
6. Explicit treatment of multiple testing and selection.

## Current broker/cost references

Paytm Money:
- Current F&O FAQ: https://www.paytmmoney.com/stocks/customer/fno-faq/onboarding-and-kyc/account-segment-activation/how-to-activate-fo-from-mobile-app-web
- Pricing calculator: https://www.paytmmoney.com/stocks/brokerage-calculator
- Paytm Money pricing update describing flat ₹20 brokerage from 15 Jan 2025: https://www.paytmmoney.com/blog/all-new-paytm-money-updates-revisions-and-more/

NSE:
- STT rates effective 1 Apr 2026: https://www.nseindia.com/static/products-services/equity-derivatives-securities-transaction-tax
- SEBI turnover fee / stamp duty / STT reference: https://www.nseindia.com/static/invest/first-time-investor-sebi-turnover-fees-stt-other-levies
- NSE transaction charge circular dated 27 Feb 2026: https://nsearchives.nseindia.com/content/circulars/FA73061.pdf

## Exit criterion

Phase 9H exits only after:
- all fixed strategy families are evaluated on both datasets,
- artifact provenance is verified,
- friction is explicitly broken out,
- no 2026 selection has occurred,
- and the results are stored in the repository and ledger.

Only then may a subsequent phase define a frozen economic strategy policy.
