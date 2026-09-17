# CPR v1.0 — Scientific Multi-Dimensional Testing

## Research objective

Test Central Pivot Range (CPR), Camarilla, Virgin CPR (VCPR), and multi-timeframe alignment as falsifiable trading hypotheses across NIFTY 50/100/500 universes and four execution styles: intraday, BTST, swing, and options.

The research standard is **out-of-sample evidence first**. The 30–40% monthly objective is a target scenario to quantify, not an assumption to optimize toward.

## 1. Mathematical definitions

### 1.1 Classic CPR
For completed session t:

- `P_t = (H_t + L_t + C_t) / 3`
- `BC_t = (H_t + L_t) / 2`
- `TC_t = 2*P_t - BC_t`
- `CPR_low_t = min(BC_t, TC_t)`
- `CPR_high_t = max(BC_t, TC_t)`
- `CPR_width_t = CPR_high_t - CPR_low_t`

The CPR used during session t+1 must be the CPR computed from session t only.

### 1.2 Volatility normalization
Use a 20-session Wilder ATR on daily OHLC:

`ATR20_t = WilderATR_20(H, L, C)`

For a day whose CPR is based on t-1:

`width_ratio_t = CPR_width_(t-1) / ATR20_(t-1)`

The primary research axis is the **dimensionless width/ATR ratio** rather than an arbitrary price-point width.

Initial hypothesis grid (not a conclusion):

- Narrow candidate: `width_ratio < X`, with `X ∈ {0.20, 0.30, 0.40, 0.50, 0.60, 0.75}`
- Wide candidate: `width_ratio > Y`, with `Y ∈ {0.75, 1.00, 1.25, 1.50, 1.75}`
- The research engine allows a neutral band `X <= width_ratio <= Y` where neither regime is traded.

`X` and `Y` are tuned **inside each WFO training window only**. No parameter is selected from the final test period.

### 1.3 Camarilla
For completed session t, with `R = H_t - L_t`:

- `R1 = C_t + R*1.1/12`
- `R2 = C_t + R*1.1/6`
- `R3 = C_t + R*1.1/4`
- `R4 = C_t + R*1.1/2`
- `S1 = C_t - R*1.1/12`
- `S2 = C_t - R*1.1/6`
- `S3 = C_t - R*1.1/4`
- `S4 = C_t - R*1.1/2`

The CPR/Camarilla levels used on t+1 are calculated solely from t.

### 1.4 Confluence reversal
A confluence event exists on the trading session if either:

- `CPR_low < R3 < CPR_high`, or
- `CPR_low < S3 < CPR_high`.

The containment is **strict**; equality at a boundary is not counted.

Entry hypotheses:

- R3-inside-CPR: short when price tests the zone and closes back below the local trigger level.
- S3-inside-CPR: long when price tests the zone and closes back above the local trigger level.

A more conservative implementation can require rejection over two consecutive bars. The primary engine keeps this as a parameter.

### 1.5 Virgin CPR
A prior CPR zone is considered virgin at the start of the next trading session if the next session's price never intersects `[CPR_low, CPR_high]`.

For intraday live state, each previous-session CPR is stored as an active zone until the first bar whose interval `[Low, High]` intersects the zone. On first intersection:

- the zone becomes `touched=True`;
- a VCPR first-touch event is emitted;
- subsequent bars do not emit another first-touch event for that zone.

For historical testing, only the information available before the bar may be used. Future-day knowledge must never be used to decide whether a zone was virgin at the time of entry.

### 1.6 Multi-timeframe synchronization

**Intraday:** 5-minute bars + daily CPR/Camarilla/PDH/PDL.

**Swing/BTST:**
- hourly bars + weekly CPR, or
- daily bars + monthly CPR.

A higher-timeframe level becomes available only after the higher-timeframe reference period has closed.

## 2. Exact strategy hypotheses

### H1 — Narrow CPR directional expansion
Regime: `width_ratio < X`.

Long trigger:

`Close_t > max(R1_t, PDH_t)` and previous close `<= max(R1, PDH)`.

Short trigger:

`Close_t < min(S1_t, PDL_t)` and previous close `>= min(S1, PDL)`.

Optional confirmation filters to test independently:

- first 60-minute opening range break;
- relative volume z-score;
- higher-timeframe directional alignment;
- distance from VWAP.

Exit variants:

- fixed clock exit 15:15;
- ATR stop + fixed R multiple target;
- trailing stop after 1R.

### H2 — Wide CPR mean reversion
Regime: `width_ratio > Y`.

Short trigger:

`High_t >= max(R1_t, PDH_t)` and `Close_t < max(R1, PDH)`.

Long trigger:

`Low_t <= min(S1_t, PDL_t)` and `Close_t > min(S1, PDL)`.

Primary exit: CPR midpoint `P`. Alternate exit: opposite edge of CPR or time exit.

The engine avoids treating a simple touch as a fill; entry requires a rejection condition to reduce false positives caused by bar-level ambiguity.

### H3 — CPR + Camarilla confluence reversal
Trade only when R3 or S3 lies strictly inside CPR.

A trade requires first touch followed by rejection; no trade is generated from a pre-touch condition alone.

### H4 — Virgin CPR magnet
Trade the first touch of an active prior CPR zone.

Two variants:

- `magnet`: mean-revert toward CPR midpoint;
- `break`: fade only if rejection occurs; otherwise treat clean traversal as a regime failure.

### H5 — BTST
Default implementation uses the last fully completed session close because the next-session CPR is computed from the completed current-session H/L/C. A 15:25 proxy may only be used if the data vendor explicitly defines that bar as the session-close observation; otherwise using a 15:25 bar to infer the final 15:30 H/L/C introduces look-ahead.

Entry candidates:

- close above/below next-session CPR with directional bias;
- closing distance to projected CPR normalized by ATR;
- alignment with the current session's narrow/wide regime.

Exit candidates:

- next-session open;
- first 60 minutes;
- momentum failure stop.

### H6 — Swing
Use 1-hour execution with prior-week CPR, or daily execution with prior-month CPR.

Directional alignment can require the execution timeframe close to be on the same side of the higher-timeframe CPR midpoint as the planned trade.

Trailing stop candidates:

- weekly S1/R1;
- weekly CPR edge;
- ATR multiple.

### H7 — Options
Directional:

- Narrow CPR breakout -> buy ATM or one-step ITM call/put in the breakout direction.
- Selection requires available bid/ask, volume, open interest, IV, delta, and time-to-expiry.

Non-directional:

- Wide CPR -> short ATM straddle or 1-step OTM strangle as a hypothesis.
- A defined-risk version must also be tested because naked short-option tail risk can dominate average returns.

Option fills must use the bid for selling and ask for buying, plus configurable slippage. Mid-price fills are prohibited in the primary realism test.

## 3. Anti-bias architecture

### Look-ahead guard
Every higher-timeframe feature is created on its source timeframe and shifted by one completed source period before it is joined to the execution timeframe.

Examples:

- daily levels -> `shift(1)` before intraday join;
- weekly levels -> prior completed week before hourly join;
- monthly levels -> prior completed month before daily join.

A test should fail if a feature timestamp is later than the trade decision timestamp.

### Survivorship-bias control
The universe must be time-varying. Use a constituent-history file such as:

`date, symbol, universe`

where `universe ∈ {NIFTY50,NIFTY100,NIFTY500}` and each row expresses membership effective from that date.

At each historical date, only symbols that were constituents on that date are eligible. Delisted, merged, suspended, and later-added stocks must remain in the historical sample when data exists.

### Overfitting control
Use rolling WFO:

- train = 252 trading days;
- test = 63 trading days;
- step = 63 trading days.

Parameter selection occurs only inside the training block. The selected parameter set is frozen throughout the corresponding test block.

Recommended robustness gate:

- hold out the last 12 months as a final untouched test set;
- require performance stability across at least three geographically/temporally separated market regimes;
- report parameter neighborhoods, not only the single optimum.

## 4. Friction model

Default configurable assumptions:

- equity/future slippage: 5 bps per side;
- options slippage: half-spread + configurable impact floor;
- brokerage: user-configurable per order;
- GST: 18% on brokerage + exchange transaction charges + SEBI turnover fee;
- STT: instrument- and side-specific;
- stamp duty: buyer-side and instrument-specific;
- exchange transaction fee: configurable by effective date;
- no perfect mid-price option fills in the primary test.

The repository defaults are intentionally explicit rather than hidden inside the strategy.

## 5. Risk and sizing

For an empirical per-trade return distribution `r_i`, the Kelly fraction is estimated numerically as:

`f* = argmax_f mean(log(1 + f*r_i))`

subject to `1 + f*r_i > 0` for every simulated outcome.

Use fractional Kelly for live/paper sizing. The Monte Carlo module reports full Kelly, 1/2 Kelly, 1/4 Kelly, and capped-risk variants.

Risk-of-ruin is defined here as:

`P(min_t Equity_t / Equity_0 <= 0.50)`

for a fixed horizon under bootstrapped trade returns. A separate zero-account bankruptcy probability is also reported for strategies whose simulated loss support permits it.

The 10,000-path Monte Carlo must preserve dependence where possible by block-bootstrap rather than IID-only sampling, with IID shown as a secondary diagnostic.

## 6. Acceptance criteria

A strategy is not considered validated merely because CAGR is high. At minimum report:

- CAGR / annualized return;
- weekly and monthly hit distribution;
- Sharpe, Sortino, Calmar;
- win rate, payoff ratio, expectancy;
- profit factor;
- maximum drawdown and maximum drawdown duration;
- trade count and turnover;
- exposure and leverage;
- tail loss quantiles;
- out-of-sample degradation vs training;
- parameter sensitivity;
- Monte Carlo median, 5th percentile, 95th percentile terminal equity;
- probability of >=50% drawdown;
- probability of ruin under several position-sizing policies.

## 7. Research conclusion standard

The desired 30–40% monthly return is not treated as an optimization objective that can justify arbitrary leverage. The research engine must first determine whether the underlying CPR edge survives costs, regime changes, and out-of-sample validation. Only after that can sizing be evaluated.

A result that hits 40% per month only after extreme leverage, high turnover, or unstable parameter selection is classified as a **fragile high-leverage scenario**, not as evidence that CPR itself delivers 40% monthly alpha.

## Current external cost references

- NSE STT schedule, including changes effective 1 April 2026: https://www.nseindia.com/static/products-services/equity-derivatives-securities-transaction-tax
- NSE/FA/73061 transaction-charge revision effective 1 March 2026: https://nsearchives.nseindia.com/content/circulars/FA73061.pdf
- NSE SEBI/stamp/GST reference: https://www.nseindia.com/static/invest/first-time-investor-sebi-turnover-fees-stt-other-levies
