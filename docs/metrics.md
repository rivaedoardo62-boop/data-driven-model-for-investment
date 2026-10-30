# Metrics

How to compute the returns of a strategy from weekly signals without lookahead bias, how to split them into In-Sample and Out-of-Sample,
and the metrics to evaluate and compare the strategies. Prices are adjusted for splits and dividends; **no transaction costs**.

The returns can be computed in two ways, which differ only in the execution price:

| Execution | Prices | Execution of the signal of week $t$ | Return earned |
|---|---|---|---|
| [At the close](#execution-at-the-close) | closes | at the close of week $t$ (Friday) | $C_{t+1} / C_t - 1$ |
| [At the next open](#execution-at-the-next-open) | closes and opens | at the open of week $t+1$ (Monday) | $O_{t+2} / O_{t+1} - 1$ |

In both cases the **signals are the same**: they use only the information available at the close of week $t$ (e.g. the closes up to $C_t$).
All the metrics, from [Performance](#performance) on, are then computed in the same way from the returns $r_t$,
separately on the [In-Sample and Out-of-Sample periods](#evaluated-period-in-sample-and-out-of-sample).

## Notation

| Symbol | Meaning |
|---|---|
| $t$ | Week, from its Monday to its Friday; $t+1$ is the next week |
| $C_{t,i}$ | Close of stock $i$ in week $t$: close of the last trading day of the week |
| $O_{t,i}$ | Open of stock $i$ in week $t$: open of the first trading day of the week |
| $s_{t,i}$ | Signal of stock $i$ in week $t$: computed after the close of week $t$, with the information available at that close (e.g. the closes up to $C_t$ included); $+1$ long, $0$ flat, $-1$ short |
| $N$ | Number of stocks traded by the strategy |
| $R^{fwd}_{t,i}$ | Forward return of stock $i$: return earned by the signal of week $t$ (depends on the execution) |
| $r_t$ | Return of a series (strategy or benchmark) earned by the signal of week $t$ |
| $m_t$ | Return of the market benchmark (e.g. an ETF such as SPY) earned in the same weeks |
| $T$ | Number of weeks in the period (In-Sample or Out-of-Sample) |
| $P$ | Periods per year: $P = 52$ |
| $r_f$ | Annual risk-free rate (state the rate you assume) |
| $E_t$ | Equity curve: $E_t = 100 \cdot \prod_{\tau \le t} (1 + r_\tau)$, with $E_0 = 100$ (starting capital) |

Common to both executions:

- Signals are **discrete**: $+1$, $0$ or $-1$, with no intensity.
- The portfolio is **equal weight across the stocks, with no leverage**: each stock gets $1/N$ of the capital, long, flat or short,
  **rebalanced to $1/N$ every week**.
- Returns are simple (not logarithmic) and compounded over time: $E_{t+1} / E_t = 1 + r_{t+1}$.
- No transaction costs: the return of a stock is the same whatever the change of signal.
- Benchmarks: **Equal weight** (the same stocks, always long, rebalanced to $1/N$ every week) and a **market ETF** bought and held,
  never traded by the strategies.
- The worst mistake is the **lookahead bias**: $s_{t,i} \cdot \left(C_{t,i} / C_{t-1,i} - 1\right)$ uses $C_t$ to earn a move that already
  happened (results far too good). Likewise, the signal of week $t$ may use only the information available at the close of week $t$
  (no moving average centered on $t$, no normalization with the whole sample, no data published later).

## Execution at the close

At the close of week $t$ the strategy reads $C_t$, computes $s_t$ instantly and enters **at the same price $C_t$**:
as if the entry price of the next week were $C_t$. The position is held for one week and changed at the next close.

```
close of week t (Friday)       close of week t+1 (Friday)
s_t computed,          --->    return of s_t realized,
entry at C_t                   s_(t+1) computed, entry at C_(t+1)
```

The return earned by the signal of week $t$ (forward return) is therefore

$$R^{fwd}_{t,i} = \frac{C_{t+1,i}}{C_{t,i}} - 1$$

| Series | Return $r_t$ (realized at the close of week $t+1$) |
|---|---|
| Stock $i$ | $R^{fwd}_{t,i} = C_{t+1,i} / C_{t,i} - 1$ |
| Strategy | $\dfrac{1}{N} \sum_{i=1}^{N} s_{t,i} \, R^{fwd}_{t,i}$ |
| Equal weight | $\dfrac{1}{N} \sum_{i=1}^{N} R^{fwd}_{t,i}$ |
| Market ETF | $R^{fwd}_{t}$ of the ETF |

In pandas, with one row per week and one column per stock: `forward = close.shift(-1) / close - 1` (row $t$: $C_{t+1} / C_t - 1$),
then `signals * forward`. The last week has no forward return.

This execution is slightly **optimistic**: when the close is known the market is already closed, so in practice one should compute the signal
a few minutes before the close (market-on-close order). On weekly data the error is small, and only close prices are needed.

## Execution at the next open

A signal computed with the close $C_t$ is known only when the market is **closed**: it is executed at the **open of the next week**
(Monday, or the first trading day), and the position is held until the following open, when the next signal is executed.

```
close of week t (Friday)   --->   open of week t+1 (Monday)   --->   open of week t+2 (Monday)
s_t computed                      s_t executed                       return of s_t realized,
                                                                     s_(t+1) executed
```

The return earned by the signal of week $t$ (forward return) is therefore

$$R^{fwd}_{t,i} = \frac{O_{t+2,i}}{O_{t+1,i}} - 1$$

| Series | Return $r_t$ (realized at the open of week $t+2$) |
|---|---|
| Stock $i$ | $R^{fwd}_{t,i} = O_{t+2,i} / O_{t+1,i} - 1$ |
| Strategy | $\dfrac{1}{N} \sum_{i=1}^{N} s_{t,i} \, R^{fwd}_{t,i}$ |
| Equal weight | $\dfrac{1}{N} \sum_{i=1}^{N} R^{fwd}_{t,i}$ |
| Market ETF | $R^{fwd}_{t}$ of the ETF |

- The weekend gap from $C_t$ to $O_{t+1}$ happens **before** entry: the strategy neither earns nor loses it.
- In pandas, with the opens and the closes on the same rows (weeks): `forward = opens.shift(-2) / opens.shift(-1) - 1`
  (row $t$: $O_{t+2} / O_{t+1} - 1$), then `signals * forward`.
- The last two weeks have no forward return: their signals are not executed within the data.
- Use ETFs as market benchmark, not indices: Yahoo index opens can be stale (e.g. ^GSPC opens before 2017 are unreliable).

Common mistake with this execution:

| Mistake | Formula | Problem |
|---|---|---|
| Trading at the close | $s_{t,i} \cdot \left(C_{t+1,i} / C_{t,i} - 1\right)$ | Optimistic: assumes trading at $C_t$, when the market is already closed (the assumption of the execution at the close) |

## Evaluated period, In-Sample and Out-of-Sample

The **evaluated period** is the same for every series: from the first week when every strategy has a signal for every stock
(e.g. after the warm-up of the longest moving average) to the last week with a forward return.

It is split into an **In-Sample** (IS) and an **Out-of-Sample** (OOS) period by the day the return $r_t$ is **realized**
(close of week $t+1$ or open of week $t+2$, depending on the execution): IS if realized up to the last day of the In-Sample period
(included), OOS otherwise. The last day of the In-Sample period is a Friday, so that the In-Sample period ends with a whole week:
in this way no In-Sample return depends on Out-of-Sample prices, also when the first trading day of a week is not its Monday.

Choose the sample and the end of the In-Sample period so that (see [instructions.pdf](../resources/instructions.pdf)):

- the sample is long enough (for weekly data at least 10 years);
- the In-Sample and the Out-of-Sample periods contain **different market regimes** (e.g. a crisis or a bear market in each);
- the Out-of-Sample period is big enough to evaluate the strategy (e.g. about 30% of the evaluated period).

Then:

- Choose strategies and parameters looking **only at the In-Sample** results (on a validation set carved out of it, or walk-forward within it).
- Look at the Out-of-Sample results **once**, at the end: a strategy changed after looking at them is no longer tested out of sample.
- Compute every metric below separately on each period: e.g. the equity curve restarts from 100 at the start of each period,
  and turnover and holding periods restart at the first week of each period.

## Performance

| Metric | Definition | Meaning |
|---|---|---|
| Cumulative return | $\prod_t (1 + r_t) - 1 = E_T / E_0 - 1$ | Total return over the period |
| Annualized return | $(1 + \text{cumulative return})^{P/T} - 1$ | Compound return per year |
| Annualized volatility | $\sigma(r) \cdot \sqrt{P}$ (sample standard deviation of the weekly returns) | Risk per year |
| Sharpe ratio | $\dfrac{\text{annualized return} - r_f}{\text{annualized volatility}}$ | Excess return per unit of risk: the main metric to compare strategies. It uses the compound annualized return, so it differs slightly from the textbook $\sqrt{P}\,(\bar{r} - r_f/P)/\sigma(r)$ |
| Sortino ratio | $\dfrac{\text{annualized return} - r_f}{\sigma_{down} \cdot \sqrt{P}}$, with $\sigma_{down} = \sqrt{\frac{1}{T} \sum_t \min(r_t, 0)^2}$ | Like Sharpe, but only losses count as risk |
| Max drawdown | $\min_{t} \left( E_t / \max_{0 \le \tau \le t} E_\tau - 1 \right)$ | Worst loss from a previous peak (the starting capital is the first peak) |
| Calmar ratio | $\text{annualized return} \,/\, \lvert \text{max drawdown} \rvert$ | Return per unit of worst loss |

## Return statistics

| Metric | Definition | Meaning |
|---|---|---|
| Hit rate | Share of weeks with $r_t > 0$ | How often the strategy gains |
| Average gain / average loss | Mean of $r_t$ over weeks with $r_t > 0$ / $r_t < 0$ | Size of typical wins and losses |
| Profit factor | $\sum_{r_t > 0} r_t \,/\, \lvert \sum_{r_t < 0} r_t \rvert$ | Gains per unit of losses (above 1: profitable) |
| Best / worst week | $\max_t r_t$ / $\min_t r_t$ | Extreme weeks |
| Skewness | Sample skewness of $r_t$ | Negative: large losses are more likely than large gains |
| Excess kurtosis | Sample excess kurtosis of $r_t$ (kurtosis − 3) | Above 0: more extreme weeks than a normal distribution |

## Behaviour

Computed from the signals of the weeks of the period, not from the returns (strategies only).

| Metric | Definition | Meaning |
|---|---|---|
| Net exposure | Average over time of $\frac{1}{N} \sum_i s_{t,i}$ | Directional exposure ($+100\%$ fully long, $-100\%$ fully short) |
| Gross exposure | Average over time of $\frac{1}{N} \sum_i \lvert s_{t,i} \rvert$ | Share of capital invested |
| Long / flat / short | Share of (week, stock) pairs with signal $+1$ / $0$ / $-1$ | How the strategy spends its time |
| Turnover per year | $\frac{P}{T} \sum_t \frac{1}{N} \sum_i \lvert s_{t,i} - s_{t-1,i} \rvert$, with every stock flat before the first week of the period | Capital traded per year (a switch long ↔ short counts 2): how often the strategy trades |
| Average holding period | Mean length, in weeks, of consecutive weeks with the same non-zero signal | Fast or slow strategy |

## Comparison with the market

With respect to the returns $m_t$ of the market benchmark.

| Metric | Definition | Meaning |
|---|---|---|
| Beta | $\operatorname{cov}(r, m) / \operatorname{var}(m)$ | Sensitivity to the market (market-neutral: close to 0) |
| Correlation | $\operatorname{corr}(r, m)$ | How closely returns follow the market (market-neutral: close to 0) |
| Alpha (Jensen), annualized | $\left(\bar{r} - r_f/P - \beta \, (\bar{m} - r_f/P)\right) \cdot P$ | Annual excess return over the risk-free not explained by the market exposure |
| Tracking error | $\sigma(r - m) \cdot \sqrt{P}$ | How much the strategy deviates from the market |
| Information ratio | $\dfrac{(\bar{r} - \bar{m}) \cdot P}{\text{tracking error}}$ | Excess return over the market per unit of deviation |
| Down / up market | Mean of $r_t$ over weeks with $m_t < 0$ / $m_t > 0$ | Behaviour in falling and rising markets |
| Δ Sharpe | Sharpe of the strategy − Sharpe of the market | Risk-adjusted outperformance |

A ratio whose denominator is zero is not defined, e.g. the Sharpe ratio of a strategy always flat or the profit factor without losing weeks.

## Robustness

| Check | How | Meaning |
|---|---|---|
| Random baseline | Compare with random signals | A good strategy should clearly beat random signals |
| In-Sample / Out-of-Sample | Choose the parameters on the In-Sample period only (on a validation set carved out of it, or walk-forward), evaluate them once on the Out-of-Sample | A strategy tuned on the whole sample looks better than it is (overfitting) |
| Parameters | Recompute the metrics for nearby parameters (e.g. a moving average of 8, 10, 12 weeks) | A good result only for one exact value is probably luck |
| Sub-periods | Metrics year by year, or in bull and bear markets | Whether the result comes from a single lucky period |

## Limits of weekly prices

- **The execution at the close is optimistic** (see [Execution at the close](#execution-at-the-close)): it ignores the gap to the next open.
- **No transaction costs**: a strategy that trades often looks better than it would be in practice (see the turnover).
- **Weekly prices hide what happens inside the week**: max drawdown and worst week are measured week by week, so the real ones are larger.
- **One decision per week**: no stop losses or signals inside the week.
- **Survivorship bias**: tickers chosen today, knowing which companies survived and grew, make every strategy look better.
