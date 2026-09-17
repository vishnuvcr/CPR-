# CPR v1.0 — Real-Market Data Protocol

## Research order

1. **Index baseline:** NIFTY 50 spot daily + 5-minute OHLCV.
2. **Breadth:** NIFTY 100 and NIFTY 500 constituent-level data using point-in-time membership.
3. **Derivatives:** NIFTY futures and option-chain/contract data with timestamp, expiry, strike, bid/ask or traded OHLC, volume, OI and IV where available.
4. **Only after validation:** WFO, parameter sensitivity, holdout and Monte Carlo.

## Canonical schema

Every market-price file must contain:

```text
timestamp, open, high, low, close, volume
```

Timestamps must be timezone-aware or explicitly documented as Asia/Kolkata. The loader does not silently repair duplicates, invalid OHLC relationships, missing values or negative volume.

## Official sources

- NSE provides historical reports, including CM bhavcopy/common bhavcopy and F&O archives.
- NSE Indices provides historical index data and states that historical NIFTY 50 data is available for research; its historical index page exposes CSV-formatted OHLC data after index/date selection.
- NSE Indices also identifies index constituent data as a subscription data product. Therefore current constituent lists must **not** be substituted for historical membership in the survivorship-bias experiment.

## Point-in-time membership contract

For each index universe create a table:

```text
index_name, constituent, effective_from, effective_to
```

A security is eligible on date `t` iff:

```text
effective_from <= t < effective_to
```

Never use today's NIFTY 50/100/500 constituent list to represent historical universes.

## Corporate actions

Keep a raw/unadjusted price layer and an analysis layer. Document whether each dataset is adjusted for splits, bonuses, rights or dividends. Do not mix adjusted and unadjusted prices within a backtest.

## Intraday session contract

For NSE equity/index research, preserve the source bars exactly. Session boundaries, missing bars and holidays must be recorded in a data manifest. Do not manufacture bars by forward filling prices.

## Options contract contract

Each option record must identify:

- underlying
- timestamp
- expiry
- strike
- call/put
- bid
- ask
- last/traded price
- volume
- open interest
- implied volatility when supplied or reproducibly calculated

A strategy may not use an option price if the historical chain cannot establish that the contract existed and was tradable at that timestamp.

## Required provenance manifest

Every real-data run should record:

- provider/source URL or vendor
- download timestamp
- coverage start/end
- timezone
- adjustment status
- symbol mapping
- missing-bar policy
- constituent-membership source
- options data source
- checksum/hash of raw files

## First empirical experiment

The first run is deliberately **non-optimized**:

- Narrow: CPR-width / ATR20 `< 0.50`
- Wide: CPR-width / ATR20 `> 1.00`
- Neutral: otherwise
- Narrow breakout: close crossing max(R1, PDH) or min(S1, PDL)
- Wide reversal: intrabar touch with close back inside trigger
- Time exit: 15:15 unless the dataset's execution convention explicitly models another close
- Next-bar execution
- No leverage optimization

This baseline is a falsification test. Parameter optimization begins only after the baseline has been measured on the predefined training/test protocol.
