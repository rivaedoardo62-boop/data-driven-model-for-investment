# Systematic Trading Strategy

Weekly long / flat strategy on AAPL, MSFT, AMZN, GOOG: an ensemble of four technical indicators (trend, momentum,
short-term reversal, volatility) whose windows, weights and threshold are chosen by a genetic algorithm on the training
period; five runs of the genetic algorithm vote, and a stock is long when at least three of them are long.
Benchmarks: equal weight buy and hold of the same stocks, and SPY.

## Quick start

Install [uv](https://docs.astral.sh/uv/) (see [docs/setup.md](docs/setup.md)), then from the project folder:

```bash
uv sync                                  # environment with Python and all dependencies
uv run python 01_download_data.py        # download the prices (already in data/: do not run it again)
uv run python 02_validate_data.py        # validate the prices: stops if a check fails
uv run python 03_optimize_ga.py          # choose the parameters with the genetic algorithm (a few minutes)
uv run python 04_compute_signals.py      # compute the signals
uv run python 05_evaluate_strategy.py    # returns, metrics and charts, In-Sample and Out-of-Sample
uv run python 06_download_extra_data.py  # macro series from FRED, to describe the market regimes
uv run python 07_validate_extra_data.py  # validate the macro series: stops if a check fails
uv run python 08_make_figures.py         # figures for the slides, in data/figures/ (see docs/figures.md)
python 09_download_bloomberg.py          # only on a Bloomberg Terminal PC: semiconductor universe, saved in data/bloomberg/
uv run python 10_clean_bloomberg.py      # one series per company, checks, weekly tables, features (data/bloomberg/clean/)
uv run python 11_eda_bloomberg.py        # exploratory figures and tables (data/bloomberg/eda/)
uv run python 12_optimize_longshort.py   # final strategy: weights of the long/short on semiconductors, training only
uv run python 13_evaluate_longshort.py   # final strategy: training, validation and Out-of-Sample (run once)
```

The data are in the repository, so the results are reproducible without downloading anything: start from
`02_validate_data.py`. Running `01_download_data.py` again downloads the prices as Yahoo Finance gives them today, which
may differ slightly from the saved ones (Yahoo recomputes the adjusted prices): do not run it again, the strategy is frozen
on the saved prices.

All settings are in `config.yaml`. Every script saves the settings it used next to its outputs and stops if a later
script runs with a different `config.yaml`.

## Pipeline

| Script | Input | Output |
|---|---|---|
| `01_download_data.py` | Yahoo Finance | `data/prices/raw/` daily prices and corporate actions, `data/prices/{open,close}.csv` weekly |
| `02_validate_data.py` | `data/prices/` | `data/validation/{checks,splits,outliers}.csv` |
| `03_optimize_ga.py` | `data/prices/`, `data/validation/checks.csv` | `data/ga/best.yaml` (members of the vote), `members.csv`, `history.csv` |
| `04_compute_signals.py` | `data/prices/close.csv`, `data/ga/best.yaml` | `data/signals/{sma,random,ga}.csv` |
| `05_evaluate_strategy.py` | `data/prices/`, `data/signals/` | `data/metrics/*.csv`, `data/plots/{equity,drawdown,exposure}.html` |
| `06_download_extra_data.py` | FRED | `data/extra/macro/` macro series |
| `07_validate_extra_data.py` | `data/extra/macro/` | `data/extra/validation/checks.csv` |
| `08_make_figures.py` | `data/prices/`, `data/signals/`, `data/ga/`, `data/metrics/`, `data/extra/macro/` (optional) | `data/figures/*.png` |
| `09_download_bloomberg.py` | Bloomberg Terminal (Desktop API, `blpapi`) | members of the SOX index at the end of every year, daily prices adjusted and not adjusted, dividends and splits, monthly P/E, SOX index; copied to `data/bloomberg/` |
| `10_clean_bloomberg.py` | `data/bloomberg/raw/prices.parquet` (and `membership.csv`) | `data/bloomberg/clean/`: daily and weekly prices per company, `features.parquet`, `companies.csv`, checks |
| `11_eda_bloomberg.py` | `data/bloomberg/clean/` | `data/bloomberg/eda/*.png`, `*.csv` |
| `12_optimize_longshort.py` | `data/bloomberg/clean/` | `data/bloomberg/longshort/`: `best.yaml` (weights), `members.csv`, `history.csv` |
| `13_evaluate_longshort.py` | `data/bloomberg/`, `data/prices/`, `data/extra/macro/` | `data/bloomberg/longshort/evaluation/`: returns, metrics, bootstrap, market regimes, figures |

Shared code is in `src/`: `backtest.py` (forward returns, costs), `ensemble.py` (indicators and vote), `genetic.py`
(genetic algorithm, DEAP), `metrics.py`, `plots.py`, `data.py` (downloads and weekly tables), `validation.py`
(checks of the data), `bloomberg.py`, `features.py` and `longshort.py` (semiconductor universe and final strategy), `style.py` (figures), `config.py`.

Periods (by the day each return is realized): training up to 2014-12-26, validation up to 2018-12-28 (together the
In-Sample period), Out-of-Sample from 2018-12-31. Execution at the next open, 10 bps per trade, risk-free 2%.

## Documentation

| File | Content |
|---|---|
| [docs/bloomberg.md](docs/bloomberg.md) | Semiconductor universe from Bloomberg: cleaning, checks, exploratory analysis, limits |
| [docs/figures.md](docs/figures.md) | The figures for the slides, each with what it shows |
| [docs/strategy.md](docs/strategy.md) | Hypothesis, data, periods, exact signal logic, genetic algorithm, execution, benchmarks, pitfalls |
| [docs/setup.md](docs/setup.md) | Install uv and the dependencies, run the code, add packages, what to do if something fails |
| [docs/metrics.md](docs/metrics.md) | Execution of the signals and returns, In-Sample / Out-of-Sample split, metrics to evaluate the strategies |
| [docs/experiment_log.md](docs/experiment_log.md) | Every configuration tried, with its result, and the Out-of-Sample result |
| [notebooks/00_esplora_dati.ipynb](notebooks/00_esplora_dati.ipynb) | Exploration of the prices, signals and metrics saved in `data/` |
| [notebooks/01_bloomberg.ipynb](notebooks/01_bloomberg.ipynb) | Exploration of the cleaned Bloomberg data (needs the files in `data/bloomberg/`) |
| [resources/instructions.pdf](resources/instructions.pdf) | Text of the exam project |
| [resources/presentation.pptx](resources/presentation.pptx) | Template of the presentation |
