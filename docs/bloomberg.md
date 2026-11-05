# Bloomberg data: the semiconductor universe

The universe of the PHLX Semiconductor index (SOX), downloaded from a Bloomberg Terminal by `09_download_bloomberg.py`,
cleaned by `10_clean_bloomberg.py` and explored by `11_eda_bloomberg.py` and `notebooks/01_bloomberg.ipynb`.
Bloomberg data are licensed and this repository is public: `data/bloomberg/` is not on GitHub (see its README).

The numbers below come from the **first download (2026-11-05)**, made with an earlier version of the script: every stock
in the SOX at the end of any year from 2000 to 2026 or today, daily prices adjusted for splits and dividends, one series
per exchange line (102 lines). Its limits are listed at the end; the current script fixes them.

## Cleaning

| Step | What | Why |
|---|---|---|
| One series per company | On each day, the exchange line with the largest volume | Bloomberg gives a stock once per exchange (`MU UN` on NYSE, `MU UW` on Nasdaq). The listing exchange has 14 to 42 times the volume of the others, so this rule finds every known move between exchanges: Micron 2009-12-30, Texas Instruments 2012-01-03, AMD 2015-01-02, Teradyne 2018-11-27, Wolfspeed 2021-10-04, Coherent 2023-02-23 (`clean/line_switches.csv`). 102 lines become 82 companies |
| Sample | 2000-01-03 to 2026-09-25, as the main strategy | Same dates as `data/prices` |
| Checks | Positive prices, OHLC, trading days without a price (against the trading days of SPY), stale prices, zero volume, dividend adjustment, extreme moves | FAIL stops the pipeline; WARN is reported and explained below |
| Dividend adjustment | Daily return of the adjusted price against the total return index of Bloomberg | Equal for every company (e.g. Intel 3.25% a year for both): the prices include dividends |
| Exits | A company whose prices stop before the end is sold at its last price, in the week after | 30 of 82 companies left the market (acquired, merged or bankrupt): keeping their last move matters (Wolfspeed falls from 2.24 to 1.21 in its last week, SunEdison ends at 0.34) |
| Weekly tables | First open and last close of each week, labeled (Monday, Friday) | The same format as `data/prices`, so `src/` works on them unchanged |
| Features | Nine features per company and week (`src/features.py`), with the prices up to that Friday only | Cut at the 1% and 99% quantiles and z-scored week by week: no week uses information from another |

## What the warnings mean

| Warning | Meaning |
|---|---|
| Gaps: MXIM 257 days from 2007-10, POWI 161 days from 2006-08, NOVT 320 days from 2009-11 | Suspended from their exchange (Maxim and Power Integrations in the stock-option backdating cases): not tradable, so out of the portfolio in those weeks |
| Gaps of a few days (NVMI, TSEM, RBCN, ONTO, IDCC) | Days without trades, often half days after Thanksgiving |
| ASML total return on 2012-11-29 | Synthetic share buyback: 9.18 euro repaid per share with 77 new shares for 100. Neutral for the shareholder; the total return index counts the repayment as income (+25% in a day against +5% for the price). The adjusted price is right; the day is excluded from the check |
| Total return on the day of a change of exchange | The total return index has a different base on each exchange line (TXN: 32.4 on NYSE, 29.8 on Nasdaq the next day): not comparable on that day, the price is continuous |
| OHLC, stale prices | A few days, in thinly traded years |
| Extreme moves | Real: dot-com crash, 2008, earnings days, takeover bids. Kept |

## Exploratory analysis (`data/bloomberg/eda/`)

| Figure | What it shows |
|---|---|
| `universe.png` | 44 companies in 2000, up to 67 in 2011, 52 today; exits every year from 2011 |
| `coverage.png` | When each company has prices |
| `survivors.png` | Companies still listed: median 10.6% a year; companies that left: 5.8%. A universe of today's survivors overstates every result |
| `concentration.png` | NVIDIA is 34% of the market value of the universe (47% at the peak), the 5 largest 72%: a cap-weighted benchmark is mostly NVIDIA. Equal weight is the benchmark: with it, removing NVIDIA changes little (growth of 100 to 6,799 with it, 6,323 without) |
| `benchmarks.png` | Equal weight, equal weight without NVIDIA, cap weighted (weights of the previous week) |
| `returns.png` | Weekly returns have fat tails (excess kurtosis 15.6, skew +0.96) |
| `feature_correlation.png` | Size and liquidity move together (0.87), as volatility and beta (0.62); the volatility ratio used by the strategy is almost unrelated to the others |

The analysis is descriptive: it never checks whether a feature predicts future returns, which would be designing a
strategy on the whole sample, Out-of-Sample included.

## Limits of the first download (fixed by the current `09_download_bloomberg.py`)

| Limit | Effect | Fix |
|---|---|---|
| No composition by date | Every company ever in the SOX counts from its first price, also before it entered the index: the universe holds future winners and its returns are biased upwards. How much the universe matters: with only stocks trading more than 5 million dollars a day, the equal weight grows to 4,051 instead of 6,799 | `membership.csv` (`--membership-only`): the test uses only the members of the index at each date |
| One ticker per exchange | ADI before 2012, CY before 2009 and IPHI before 2020 are missing: their old exchange line was not returned | Composite tickers (`MU US Equity`) |
| Delisted companies without names | Eight numeric codes (e.g. `9966620D`, which by its prices is Cree/Wolfspeed) | `meta.csv` |
| No unadjusted prices, dividends, P/E | Adjustment checked only against the total return index; no valuation data | `prices_raw`, `actions`, `monthly` |
