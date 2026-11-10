# Experiment log

Every configuration tried, in order, with what changed, why, and its result. Only the training (returns realized up to
2014-12-26) and the validation (2014-12-29 to 2018-12-28) are used to compare attempts. The Out-of-Sample period
(from 2018-12-31) is opened **once**, after the last attempt, and is reported whatever the result.

Common to all attempts: AAPL, MSFT, AMZN, GOOG, weekly, execution at the next open, equal weight 1/N, no leverage,
10 bps per trade, risk-free 2%, long / flat only. Benchmarks on the same weeks (buy and hold, no costs):

| Benchmark | Training Sharpe | Training max DD | Validation Sharpe | Validation max DD |
|---|---|---|---|---|
| Equal weight, 4 stocks | 0.86 | -53.8% | 1.00 | -25.7% |
| SPY | 0.32 | -55.2% | 0.28 | -17.7% |

## Attempt 1: one genome, chosen on the validation

- **Setup**: ensemble of 4 indicators (trend, momentum, short-term return, volatility), 9 genes. Genetic algorithm (DEAP),
  population 60, 30 generations, 5 seeds; fitness = training Sharpe net of costs. The 5 best genomes of each run (19 distinct)
  go to the validation; the one with the best validation Sharpe is kept.
- **Control**: random search with the same number of backtests (7,394) and the same selection.
- **Outputs**: `data/ga/attempt_1/` (candidates of both methods), written by the version of `03_optimize_ga.py` used for
  this attempt, since replaced by the one of Attempt 2.
- **Result**

| | Training Sharpe | Validation Sharpe | Validation max DD | Validation time long |
|---|---|---|---|---|
| Genetic algorithm, chosen genome | 1.11 | 1.07 | -21.2% | 95% |
| Random search, chosen genome | 1.11 | 1.54 | -15.7% | 81% |

- **Findings**
  - The genetic algorithm does not beat the random search: mean validation Sharpe of the candidates 0.96 (GA) vs 0.98 (random).
  - The 5 runs find very different genomes with similar training Sharpe (1.11 to 1.24), e.g. momentum weight +0.53 in one run,
    -0.72 in another: the parameters are not identified by the data.
  - Consistent in all 5 runs: negative weight of the volatility indicator (exit when short-term volatility jumps) and positive
    weight of the short-term return.
  - Choosing 1 of 19 candidates on the validation uses the validation to select, not only to evaluate.
- **Decision**: replace the single genome with a vote of the runs, decided for robustness (instability across seeds),
  before seeing its result.

## Attempt 2: vote of the 5 runs

- **Change**: the best genome of each run **on the training** is a member; long when at least 3 of the 5 members are long.
  The validation is used only to evaluate the vote, not to choose among genomes.
- **Control**: random search split in 5 batches of 1,478 backtests (the budget of one run), best genome of each batch on the
  training, same vote.
- **Result**

| | Training Sharpe | Training max DD | Validation Sharpe | Validation max DD | Validation time long |
|---|---|---|---|---|---|
| Genetic algorithm, vote | 1.25 | -21.0% | 0.93 | -20.8% | 87% |
| Random search, vote | 1.36 | -23.4% | 1.49 | -11.4% | 76% |

- **Findings**
  - The vote of the genetic algorithm is worse on the validation than the equal weight buy and hold (0.93 vs 1.00), with a
    smaller drawdown (-20.8% vs -25.7%). On the training it is much better (1.25 vs 0.86, max DD -21% vs -54%): most of the
    gain comes from being out of the market in 2008.
  - Training Sharpe 1.25 -> validation 0.93 for the GA; the members of the random search lose less. With a single random seed
    this can be luck: it is not a reason to switch to the random search, which would be chosen by looking at the validation.
  - The optimization does not find better parameters than random draws: on these 4 stocks almost every "mostly long" rule
    works, the fitness landscape is flat.

## Final strategy, frozen on 2026-10-01

Attempt 2 (vote of the 5 runs of the genetic algorithm) is the final strategy, with the settings in `config.yaml` and the
members in `data/ga/best.yaml`. No diagnostic of the random search was run before. The Out-of-Sample period is opened now,
once, by `05_evaluate_strategy.py`; nothing is changed after.

## Out-of-Sample result (opened once, 2026-10-01)

Returns realized from 2018-12-31 to 2026-09-21, 404 weeks; strategies net of 10 bps per trade.

| | Annual return | Volatility | Sharpe | Max DD | Beta to SPY | Time long |
|---|---|---|---|---|---|---|
| Genetic algorithm, vote | 18.6% | 18.4% | 0.91 | -34.5% | 0.62 | 82% |
| Equal weight, 4 stocks | 28.2% | 25.0% | 1.05 | -36.9% | 1.12 | 100% |
| SPY | 17.9% | 18.2% | 0.88 | -31.8% | 1.00 | 100% |

- Against SPY, the declared benchmark: Sharpe 0.91 vs 0.88, a difference too small to be meaningful; max drawdown worse
  (-34.5% vs -31.8%).
- Against the buy and hold of the same stocks: lower Sharpe (0.91 vs 1.05) and much lower return, slightly smaller drawdown.
- Sudden crash (Covid, 2020): flat from the week of 2020-02-28 to early April, as designed (volatility filter).
- Slow bear market (2022): long only 45% of the weeks, yet -29.5% vs -31.5% for the equal weight: out after the falls, back in
  on the rebounds. The volatility filter protects from sudden crashes, not from slow declines.
- The gain of the training period came mostly from 2008 (-2% vs -42% for the equal weight): the period the genetic algorithm
  was fitted on. It does not repeat Out-of-Sample.

## Tests after the Out-of-Sample, decided on 2026-11-03 before downloading their data

The strategy stays frozen (`config.yaml`, `data/ga/best.yaml`): these tests only evaluate it, are reported whatever their
result, and change nothing. Their data are downloaded by `06_download_extra_data.py` (settings in `extra` of `config.yaml`).

1. **Transfer test.** The frozen strategy (the same 5 members and vote, no new optimization) trades the ETFs of the AI
   supply chain with 10+ years of prices: SOXX (semiconductors), IGV (software), XLK (technology), XLU (utilities, power for
   data centers), XLE (oil and gas), NLR (nuclear and uranium), URA (uranium). Equal weight, same execution and costs.
   Benchmark: equal weight buy and hold of the same ETFs; SPY as market reference. Same In-Sample / Out-of-Sample dates as
   the main strategy, each ETF from its first signal. The parameters never saw these ETFs. Question: does the timing work
   beyond the 4 stocks it was fitted on? Limit: the ETFs are chosen in 2026 for their link with AI, a theme known to have
   done well from 2023: only the difference with their own buy and hold is meaningful.
2. **Short histories, secondary.** The same test on QTUM (quantum computing), BOTZ (robotics and AI), SRVR (data centers),
   from their first signal. Less than 10 years: reported, not used for conclusions.
3. **Peer benchmarks.** AIEQ (equities selected by AI), DBMF (managed futures, trend following), AQMIX (AQR managed futures
   fund), bought and held, compared with the main strategy on the common Out-of-Sample weeks. Their returns are net of their
   fees; ours only of 10 bps per trade.
4. **Market regimes.** Each week is classified by the FRED value at the close of the signal week (latest vintage): stress if
   VIXCLS > 25; inverted curve if T10Y3M < 0; recession if USREC = 1; rate hikes if DFF is more than 0.25 points above
   26 weeks before; credit stress if BAA10Y is above its median over the evaluated weeks; high inflation if CPIAUCSL is more
   than 3% above 12 months before. Recessions and inflation are known only later: the classification describes the results,
   it is never usable as a signal. For each regime: weeks, annualized return, volatility and Sharpe ratio of the strategy and
   of the equal weight. The sample holds only two recessions (2008-2009, 2020).
5. **Risk-free rate.** Sharpe ratios recomputed with DTB3 (3-month T-bill) instead of the constant 2%.

## Change of plan, decided on 2026-11-08 before running any of the tests above

The strategy on AAPL, MSFT, AMZN, GOOG becomes the **pilot**: its two attempts and its Out-of-Sample result stay as
reported above. Its main lessons: the universe was chosen with hindsight (survivorship bias), and the genetic algorithm
did not beat random parameters. The **final strategy** is a long/short strategy on semiconductors, on a universe without
survivorship bias (the members of the SOX index at each date, from Bloomberg, delisted companies included).

Tests 1 to 3 above (ETFs and quantitative funds) are dropped before being run, with their data; tests 4 (market regimes)
and 5 (T-bill risk-free rate) apply to the final strategy.

## Final strategy: design, written on 2026-11-08 before computing any of its results

Only the training period is used to choose; the validation period only evaluates; the Out-of-Sample period is opened
once, after this design is frozen. Items marked *to confirm* are decided by the group before the first run on the
point-in-time universe.

| Item | Choice |
|---|---|
| Hypothesis | Inside one cyclical industry, the dispersion between winners and losers is large (still-listed companies earned a median 10.6% a year, those that left 5.8%): ranking the companies on price-based features and holding the best against the worst earns a return that does not depend on the direction of the sector |
| Universe | Each week, the companies in the SOX index at the latest year-end composition (`membership.csv`), with a close and every feature; delisted companies sold at their last price |
| Features | Seven, with the prices up to the Friday close (`src/features.py`): return of 4 weeks, momentum 52-4 weeks, trend 26 weeks, distance from the 52-week high, volatility 26 weeks, volatility ratio 10/52 weeks, beta 52 weeks; winsorized at 1%/99% and z-scored across the universe of each week (*to confirm*: size and liquidity left out) |
| Score and signal | Score = weighted average of the z-scores, weights in [-1, 1]; +1 for the top 20% of the scores, -1 for the bottom 20%, 0 otherwise (*to confirm*: 20%); no position with fewer than 10 companies |
| Position sizing | Half of the capital on the longs, half on the shorts, equally within each side: dollar neutral, gross exposure 100%, no leverage |
| Execution | As the pilot: signal after the Friday close, executed at the next open, held to the following open |
| Costs | 10 bps on the capital traded; 0.5% a year on the short side for borrowing the shares (*to confirm*) |
| Optimization | Genetic algorithm (same settings as the pilot, 5 seeds), 7 genes = the weights; fitness = Sharpe ratio on the training period, net of costs. Final weights = average of the 5 members (normalized). Control: random search with the same budget, reported, never chosen |
| Periods | Training: returns realized up to 2014-12-26 (from the first week with 52 weeks of features, 2001); validation: 2014-12-29 to 2018-12-28; Out-of-Sample: from 2018-12-31 |
| Risk-free | The returns are already in excess of cash (collateral interest not counted): Sharpe ratio with a risk-free rate of 0 |
| Benchmarks | Cash (zero) for a dollar-neutral strategy; equal weight, long only, of the same universe; SPY |
| Evaluation | All the metrics of `docs/metrics.md`; for the market-neutral bonus: Out-of-Sample beta and correlation to SPY, average return in the weeks SPY falls; block bootstrap of the Out-of-Sample Sharpe ratio; tests 4 and 5 above |

## Development run, 2026-11-08: provisional universe, training period only

`12_optimize_longshort.py` run on every company with a price (the point-in-time composition is not downloaded yet, so
the universe holds future members: development only). Only training results were computed and looked at; nothing of the
validation or Out-of-Sample periods.

| | Training Sharpe (risk-free 0, net of costs) |
|---|---|
| Genetic algorithm, 5 members | 1.13 to 1.33 |
| Genetic algorithm, average weights (the strategy) | 1.13 |
| Random search, 5 members / average | 0.89 to 1.10 / 0.88 |

Findings:
- Unlike the pilot, the members agree on the sign of five weights: momentum 52-4 (+0.72 to +0.99), volatility 26 weeks
  (+0.82 to +1.00), return of 4 weeks (+0.17 to +0.74), trend 26 weeks (-0.29 to -0.66), distance from the 52-week high
  (-0.29 to -0.90). The volatility ratio and the beta are not identified.
- Not market neutral: long the most volatile companies and short the calmest gives a beta of 0.24 to SPY (correlation
  0.32) and an average loss of 0.25% in the weeks SPY falls. Dollar neutral is not beta neutral.
- The training return leans on a few years: 2001 (+49%), 2002 (+36%) and 2009 (+79%, the rebound of the companies hit
  hardest); 2008, 2011 and 2014 are negative.
- Turnover: the capital is traded about 15 times a year, 1.5% a year of costs at 10 bps.

Same development run with the sides sized to a zero 52-week beta (option `sizing: beta`), training only:

| Training | Dollar neutral (logged design) | Beta neutral |
|---|---|---|
| Sharpe (average weights) | 1.13 | 0.84 |
| Annual return | 14.9% | 10.3% |
| Beta / correlation to SPY | 0.24 / 0.32 | 0.17 / 0.24 |
| Average week when SPY falls / rises | -0.25% / +0.72% | -0.18% / +0.52% |
| 2008 | -8% | -20% |

The beta neutral sizing does not make the strategy market neutral (the trailing beta of the most volatile companies is
unstable) and lowers the Sharpe ratio: the design keeps the dollar neutral sizing.

## Overnight and daytime features, decided on 2026-11-09 before any validation or Out-of-Sample result

Following Lou, Polk and Skouras (2019), "A tug of war: overnight versus intraday expected returns" (Journal of
Financial Economics), each daily return is split into its overnight part (previous close to open) and its daytime part
(open to close). Check on the training period only (2001-2014, provisional universe): long the 20% highest, short the
20% lowest of each feature, return of the next week from Monday open to the following Monday open, before costs.

| Feature | Overnight part | Daytime part | Total (what we earn) | t of the total |
|---|---|---|---|---|
| Momentum 52-4 weeks | -7.4% (t -3.5) | +2.3% (t 0.8) | -5.1% | -1.5 |
| Return of 4 weeks | -14.3% (t -7.3) | +13.7% (t 4.6) | -0.6% | -0.2 |
| Momentum 52-4, overnight part only | +24.0% (t 12.4) | -16.8% (t -6.6) | +7.2% | 2.5 |
| Momentum 52-4, daytime part only | -20.4% (t -10.0) | +14.5% (t 4.9) | -5.9% | -1.9 |
| Return of 4 weeks, overnight part only | +22.2% (t 12.0) | -19.2% (t -7.9) | +3.0% | 1.1 |
| Return of 4 weeks, daytime part only | -26.6% (t -13.6) | +23.7% (t 8.3) | -2.9% | -1.0 |

Findings:
- The tug of war is strong in semiconductors: companies that rose overnight keep rising overnight and fall in the day,
  and the other way round. The two parts mostly cancel; we hold from open to open, so we earn only the total.
- On the total, only the overnight part of momentum is significant (+7.2% a year, t 2.5); the usual momentum loses.
- Past daytime gains reverse a little, past overnight gains continue a little: the usual one-month reversal mixes two
  opposite effects.

Decision: the momentum 52-4 and the 4-week return of the design are replaced by their overnight and daytime parts
(9 features, `longshort.features` in `config.yaml`). Every part uses only the days up to the Friday close (the weekend
overnight belongs to the next week). Data check: the opens of Bloomberg exist on every day with a close; overnight plus
daytime equals the close-to-close return exactly (`10_clean_bloomberg.py`).

Development run with the 9 features (provisional universe, training only):

| Training Sharpe (risk-free 0, net of costs) | 7 features | 9 features (overnight / daytime split) |
|---|---|---|
| Genetic algorithm, 5 members | 1.13 to 1.33 | 0.86 to 1.06 |
| Genetic algorithm, average weights | 1.13 | 0.92 |
| Random search, average weights | 0.88 | 0.71 |

With 9 features the members agree only on volatility (positive in all 5) and distance from the 52-week high (negative in
all 5); the overnight part of momentum is positive in 4 of 5; the daytime parts and the 4-week parts change sign. More
features did not help: with the same budget the search is noisier and the average of the members dilutes them. The
feature set is decided by the group before the run on the point-in-time universe.

## Final design frozen on 2026-11-10, before the run on the point-in-time universe

Decided by the group, with only training results of the provisional universe seen:
- Features (7): return of 4 weeks, **overnight part of the 52-4 week momentum** (it replaces the momentum: on the
  training period it is the only part of momentum with a significant return, and the usual momentum loses), trend 26
  weeks, distance from the 52-week high, volatility 26 weeks, volatility ratio 10/52 weeks, beta 52 weeks.
- Long the top 20%, short the bottom 20%, half of the capital on each side (dollar neutral), 10 bps per trade, 0.5% a year
  to borrow the shares sold short: confirmed.
- The market-neutral bonus is not pursued: on the training period the strategy has a beta of about 0.2 to SPY, and
  neither the dollar nor the beta neutral sizing removes it. The beta, the correlation and the weeks when SPY falls are
  reported as limits.
- Everything else as in the design of 2026-11-08. Nothing changes after the validation and Out-of-Sample results.
