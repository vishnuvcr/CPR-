# Data protocol: NIFTY 50 / 100 / 500

## Historical membership is mandatory

Do not backtest historical returns using only the current constituent list. That creates survivorship bias because names that later left an index are omitted from earlier periods.

The required universe file is:

```text
effective_date,symbol,universe,effective_end
2015-01-01,ABC,NIFTY500,2017-03-31
2017-04-01,DEF,NIFTY500,
```

`effective_end` is exclusive. When an official constituent-history source supplies separate snapshots rather than intervals, convert each snapshot into effective-date intervals before running the backtest.

## Recommended dataset layers

1. **Reference index membership:** date-effective NIFTY50/100/500 constituent snapshots.
2. **Security OHLCV:** adjusted corporate-action-aware bars for each symbol, including delisted names where historical data exists.
3. **Index OHLCV:** NIFTY 50/100/500 index data for regime context.
4. **Options chains:** timestamped quotes with bid/ask, strike, expiry, IV if available, volume, OI, and contract multiplier.
5. **Trading calendar:** NSE sessions, holidays, special sessions, and expiry calendars.

## Symbol normalization

Map corporate-action/security-master changes into a stable internal identifier. Do not silently concatenate two unrelated companies simply because the ticker was reused.

## Missing-data policy

- Missing OHLC bars are logged and do not become synthetic flat bars unless the provider explicitly identifies them as non-trading sessions.
- Do not forward-fill price data across a missing trading session.
- Options quote staleness must be measured; stale quotes should be filtered rather than treated as executable fills.
- A symbol lacking sufficient warm-up history is excluded only until it becomes eligible, not removed for the entire sample.

## NIFTY 50/100/500 testing matrix

Run each hypothesis under:

- index universe;
- equal-weight per eligible symbol;
- volatility-scaled per symbol;
- portfolio-level risk cap.

Report both pooled statistics and per-universe distributions so that a result driven by a small subset of names is visible.

## Options-specific data requirements

At minimum:

```text
timestamp,underlying,expiry,strike,option_type,bid,ask,last,volume,open_interest,iv
```

For realistic execution, the fill model must use ask for a buy and bid for a sell, with a configurable additional impact component. Mid-price execution is a sensitivity case, not the base case.
