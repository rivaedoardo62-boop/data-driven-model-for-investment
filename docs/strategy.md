# Strategy and data

The complete definition of the trading system: what it bets on, which data it uses, how the weekly signal is computed, how
its parameters were chosen and how it is executed. Formulas of the returns and metrics are in [metrics.md](metrics.md),
every attempt and the results in [experiment_log.md](experiment_log.md).

## Hypothesis

Large US stocks are worth holding most of the time (equity risk premium), but not in every week. The strategy stays long
by default and steps aside (flat) when a stock shows the signs that usually come before further losses:

- **a sharp fall over the last few weeks**: past returns tend to persist (time-series momentum, documented for look-backs
  of 1 to 12 months by Moskowitz, Ooi and Pedersen, 2012). The opposite effect, a short-term reversal, is also documented
  for single stocks: the sign was left to the genetic algorithm, which chose persistence in all 5 runs;
- **a jump in volatility** with respect to the last year: volatility clusters, and periods of high volatility have poor
  risk-adjusted returns (volatility-managed portfolios, Moreira and Muir, 2017);
- **a price below its trend** (moving average).

The strategy never goes short: the signal is +1 (long) or 0 (flat).

What the data said (see [experiment_log.md](experiment_log.md)): across the 5 independent runs of the genetic algorithm
the sign of three indicators is stable (trend +, short-term return +, volatility −), while the sign of the long-horizon
momentum is not (from −0.72 to +0.75): that indicator is not identified by the data.

## Data

| Item | Choice |
|---|---|
| Source | Yahoo Finance through `yfinance`, daily open, high, low, close, volume, **adjusted for splits and dividends** (`auto_adjust=True`) |
| Traded assets | AAPL, MSFT, AMZN, GOOG |
| Market benchmark | SPY (ETF on the S&P 500), bought and held, never traded |
| Daily sample | 2000-01-03 to 2026-09-25 (1,395 weeks) |
| Frequency | Weekly: open of the first trading day and close of the last trading day of each week (Monday to Friday) |
| First signal | Week of 2005-08-19: GOOG is listed on 2004-08-19 and every indicator needs 52 weeks of returns |
| Storage | Downloaded once by `01_download_data.py`, saved in `data/prices/`: the results are reproducible without downloading |
| Validation | `02_validate_data.py`, saved in `data/validation/`: calendar, positive prices, OHLC consistency, gaps, stale prices, zero volume, every split (no false crash), every dividend adjustment, weekly prices rebuilt from the daily ones, outliers. All checks pass; 28 extreme moves are reported and kept (real prices) |
| Alternative data | None, by choice: the hypothesis needs only prices |
| Risk-free rate | 2% per year, constant (about the average 3-month US T-bill rate over the period), used only in the Sharpe ratio |

## Periods

Split by the day each weekly return is realized (see [metrics.md](metrics.md)).

| Period | Use | Weeks of the signals | Returns realized | Weeks | Market regimes |
|---|---|---|---|---|---|
| Training | The genetic algorithm maximizes the Sharpe ratio here | 2005-08-19 to 2014-12-12 | 2005-08-29 to 2014-12-22 | 487 | 2008 financial crisis, 2009-2014 bull market |
| Validation | Only evaluates the final strategy, nothing is chosen | 2014-12-19 to 2018-12-14 | 2014-12-29 to 2018-12-24 | 209 | 2015-2016 correction, 2017 low volatility, end-2018 sell-off |
| Out-of-Sample | Opened once, on 2026-10-01 | 2018-12-21 to 2026-09-11 | 2018-12-31 to 2026-09-21 | 404 | 2020 Covid crash, 2022 bear market, 2023-2025 rally |

Training and validation together are the In-Sample period (696 weeks); the Out-of-Sample period is 37% of the evaluated
weeks.

## Signal

For each stock $i$ and week $t$, computed after the Friday close with the closes up to $C_t$ only.

**1. Four indicators**, each scaled to $[-1, 1]$ with tanh so that their weights are comparable. $\sigma_t$ is the standard
deviation of the last 26 weekly returns; dividing a return over $n$ weeks by $\sigma_t \sqrt{n}$ makes it a z-score.

| Indicator | Formula | Meaning |
|---|---|---|
| Trend($n$) | $\tanh\left(\dfrac{C_t / \text{SMA}_n - 1}{\sigma_t \sqrt{n}}\right)$ | Price above (+) or below (−) its $n$-week moving average |
| Momentum($n$) | $\tanh\left(\dfrac{C_t / C_{t-n} - 1}{\sigma_t \sqrt{n}}\right)$, $n$ from 4 to 52 weeks | Return of the last months |
| Short-term return($n$) | Same formula, $n$ from 1 to 8 weeks | Return of the last weeks (called `reversal` in the code: a negative weight would bet on a reversal, the genetic algorithm always chose a positive one) |
| Volatility($n$) | $\tanh\left(\log \dfrac{\sigma_{n}}{\sigma_{52}}\right)$ | Volatility of the last $n$ weeks with respect to the last year: positive when it jumps |

**2. Five members.** Each member $k$ has its own windows, weights $w$ and threshold $\theta$, and gives a long signal when
its score is above the threshold:

$$\text{score}_{k,t} = \frac{\sum_j w_{k,j} \, x_{j,t}}{\sum_j \lvert w_{k,j} \rvert} \in [-1, 1], \qquad s_{k,t} = \begin{cases} +1 & \text{if } \text{score}_{k,t} > \theta_k \\ 0 & \text{otherwise} \end{cases}$$

The five members, as chosen by the genetic algorithm (`data/ga/best.yaml`), window in weeks and weight:

| Member | Trend | Momentum | Short-term return | Volatility | Threshold $\theta$ |
|---|---|---|---|---|---|
| 1 | 35 w, +0.78 | 29 w, −0.72 | 7 w, +0.76 | 10 w, −0.97 | −0.25 |
| 2 | 5 w, +0.99 | 10 w, +0.75 | 6 w, +0.83 | 15 w, −0.87 | −0.06 |
| 3 | 47 w, +0.41 | 9 w, −0.07 | 2 w, +0.24 | 9 w, −0.42 | +0.01 |
| 4 | 29 w, +0.16 | 47 w, +0.53 | 2 w, +0.23 | 5 w, −0.35 | −0.18 |
| 5 | 45 w, +0.19 | 34 w, −0.53 | 6 w, +0.75 | 21 w, −0.03 | −0.29 |

Four thresholds out of five are negative: a member stays long even with a slightly negative score, and goes flat only when
the indicators are clearly bad.

**3. Vote.** The final signal of stock $i$ in week $t$ is **+1 if at least 3 of the 5 members are long, 0 otherwise**.

**Example**, AAPL at the start of the Covid crash:

| Week (Friday close) | Short-term return of the members | Volatility of the members | Members long | Final signal |
|---|---|---|---|---|
| 2020-02-21 | from −0.62 to +0.75 | from −0.24 to +0.04 | 5 of 5 | +1, long |
| 2020-02-28 | from −1.00 to −0.85 | from +0.10 to +0.53 | 1 of 5 | 0, flat from the open of Monday 2020-03-02 |

The exit was driven mostly by the collapse of the short-term return, with the volatility indicator pushing in the same
direction. All four stocks went flat in the same week and were long again by the week of 2020-04-17.

## Parameters: genetic algorithm

The optimization method required by the project. Each member has 9 parameters (4 windows, 4 weights, 1 threshold), mixed
integer and continuous, and the objective (the Sharpe ratio of a backtest with discrete signals) has no gradient; the grid of
the windows alone has about 440,000 points. A genetic algorithm searches this space with a fixed budget of backtests.

| Setting | Value |
|---|---|
| Library | DEAP |
| Genome | 9 genes in $[0, 1]$, decoded into windows (bounds in `config.yaml`), weights in $[-1, 1]$, threshold in $[-0.5, 0.5]$ |
| Fitness | Sharpe ratio on the **training** period, net of transaction costs |
| Population, generations | 60, 30 |
| Selection, crossover, mutation | Tournament of 3; simulated binary crossover, probability 0.7; polynomial mutation, probability 0.3 |
| Runs | 5, seeds 1 to 5; the best genome of each run on the training is a member |
| Use of the validation | None in the choice: it only evaluates the vote |
| Control | Random search with the same budget (1,478 backtests per member), same vote |

Why a vote: the 5 runs find very different genomes with similar training Sharpe, so a single genome would depend on a
lucky run. The vote keeps only what most runs agree on.

## Execution and portfolio

| Item | Choice |
|---|---|
| Execution | Signal computed after the Friday close of week $t$, executed at the **open of the next trading day** (week $t+1$), held until the open of week $t+2$: return $O_{t+2} / O_{t+1} - 1$. The weekend gap is neither earned nor lost |
| Position sizing | Equal weight: 1/4 of the capital per stock, rebalanced every week; a flat stock leaves its quarter in cash |
| Cash | Earns 0% in the backtest (conservative) |
| Leverage, short selling | None |
| Transaction costs | 10 bps of the capital traded at every change of signal (strategies only, not the benchmarks) |
| Returns | Simple, compounded; equity curves start at 100 in each period |

## Benchmarks

| Benchmark | Why |
|---|---|
| Equal weight buy and hold of AAPL, MSFT, AMZN, GOOG | The fair comparison: same stocks, same weights, always long. The difference measures only the timing of the strategy, not the choice of the stocks |
| SPY buy and hold | The market. It also shows how much of the result comes from the choice of the 4 stocks (see survivorship bias below) |
| SMA rule (long when the close is above its 10-week average) and random signals | Baselines: a simple rule and pure chance |

## Pitfalls

| Pitfall | How it is handled |
|---|---|
| Lookahead bias | Indicators use only rolling windows up to $C_t$, never the whole sample; execution at the next open; In-Sample and Out-of-Sample split by the day each return is realized, so no In-Sample return uses Out-of-Sample prices |
| Overfitting | Parameters fitted on the training only; validation used to evaluate, not to choose; vote of 5 runs instead of the best genome; random search control. The control shows that the genetic algorithm does not beat random draws: the gain over random parameters is not evidence of skill |
| Data snooping | Two attempts, both in [experiment_log.md](experiment_log.md) with their results; the Out-of-Sample period opened once, on 2026-10-01, after the strategy was frozen; nothing changed after |
| Survivorship bias | **Present, not solved.** The 4 stocks were chosen in 2026 among the largest companies of today, which are there because they grew. The equal weight of the 4 has an In-Sample Sharpe of 0.90 against 0.31 for SPY: the universe itself beats the market. The results are an upper bound; the comparison with the equal weight of the same stocks is the one that counts |
| Pretrained model leakage | Not applicable: no pretrained model (no language model, no FinBERT). The genetic algorithm starts from random genomes with fixed seeds |

## Limits

- Weekly decisions: no exit inside the week, and weekly drawdowns understate the daily ones.
- Fixed costs of 10 bps: no spread, market impact or slippage beyond them.
- Constant risk-free rate of 2%.
- 4 stocks of the same sector: the result depends on a concentrated, hand-picked universe.
