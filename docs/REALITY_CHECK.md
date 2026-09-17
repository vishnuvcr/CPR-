# CPR v1.0 — Harsh Reality Check

## 1. The target is a sizing problem only after an edge is proven

A 30–40% monthly return corresponds to roughly 6.22–8.05% compounded weekly over 4.345 weeks/month. A 10% weekly target compounds to roughly 52.9% over that same month-length approximation.

To illustrate the sizing pressure, assume **only as a theoretical scenario**:

- win probability = 55%;
- average winner = +1.5R;
- average loser = -1R;
- 5 trades/week;
- independent binary outcomes;
- no correlation, no regime shifts, no gap losses beyond the modeled R.

Under those assumptions:

- full binary Kelly = `25%` of capital per trade;
- expected-geometric sizing for 10% weekly target ≈ `5.13%` risk per trade;
- expected-geometric sizing for 30% monthly target ≈ `3.24%` risk per trade;
- expected-geometric sizing for 40% monthly target ≈ `4.16%` risk per trade.

These are mathematical scenarios, not recommended live-risk levels. Real market dependence, slippage, gaps and parameter uncertainty push the safe sizing requirement downward.

## 2. Illustrative Monte Carlo — 10,000 paths

The following is a **synthetic stress test**, not a historical CPR result. It uses 100 trades, 55% win probability, +1.5R wins and -1R losses.

| Risk per trade | Median terminal equity | P05 terminal | P95 terminal | Median max DD | P95 max DD (worse tail) |
|---:|---:|---:|---:|---:|---:|
| 0.5% | 1.204x | 1.089x | 1.330x | -2.96% | -5.14% |
| 1.0% | 1.443x | 1.182x | 1.761x | -5.85% | -10.07% |
| 2.0% | 2.047x | 1.375x | 3.049x | -11.42% | -19.29% |
| 3.0% | 2.858x | 1.575x | 5.187x | -16.70% | -27.98% |

No path in this simple 100-trade synthetic experiment crossed a 50% drawdown at these sizes. This **does not** establish low real-world risk; the simulation deliberately omits gap jumps, serial correlation, volatility clustering, changing win/loss distributions, and liquidity failure.

## 3. Where CPR is most likely to fail

### Gap risk
A prior-day CPR is static while the market can gap directly through R1/S1, PDH/PDL or an untested VCPR. A next-open fill can be far beyond a model stop, making realized loss several times the nominal risk.

### Regime instability
“Narrow CPR = trend” and “wide CPR = range” are conditional hypotheses, not laws. Strong overnight information can turn a mathematically narrow day into a two-sided reversal session; very wide ranges can still produce directional expansion.

### False breakout clusters
A breakout rule can be repeatedly whipsawed near PDH/PDL/R1/S1. This is particularly costly when the trend filter is absent and the market oscillates around the trigger.

### VCPR over-interpretation
Virgin CPRs can behave as magnets, but the fact that a level is untouched does not establish a causal reversal. The first touch may instead be a high-momentum continuation through the zone.

### Options theta and IV effects
For long options, being correct on direction can still produce a loss if the move arrives too late or implied volatility contracts. For short options, theta can be outweighed by gamma/vega losses during a large move. Expiry proximity can make P&L highly nonlinear.

### Short-vol tail risk
A short straddle/strangle can show many small winners and a few catastrophic losses. Profit factor and win rate can therefore look attractive while risk-adjusted survival is poor. Defined-risk structures should be tested alongside naked versions.

### Transaction costs
For options, exchange charges, STT and bid/ask spread are not small details. Since NSE's current option STT is charged on option premium sold and rose to 0.15% from 1 April 2026, high-turnover short-option systems are particularly sensitive to turnover and execution quality.

### Parameter instability
Optimizing X/Y, stop size, target R, confirmation windows and MTF filters simultaneously creates a large search surface. The primary defense is WFO plus an untouched final holdout and a requirement for parameter-neighborhood stability.

## 4. Scientific conclusion rule

A 30–40% monthly CAGR observed in-sample is not sufficient evidence of a CPR edge. The strategy must demonstrate positive and reasonably stable out-of-sample expectancy after friction, survive realistic gap handling, and maintain acceptable drawdown under Monte Carlo stress.

The first scientific question is therefore:

> Does CPR add statistically significant, economically tradable edge after costs and bias controls?

Only after that answer is established should leverage be explored.
