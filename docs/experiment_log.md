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
