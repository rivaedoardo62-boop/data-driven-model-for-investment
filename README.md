# Systematic Trading Strategy

Weekly long / flat strategy on AAPL, MSFT, AMZN, GOOG: an ensemble of four technical indicators (trend, momentum,
short-term reversal, volatility) whose windows, weights and threshold are chosen by a genetic algorithm on the training
period; five runs of the genetic algorithm vote, and a stock is long when at least three of them are long.
Benchmarks: equal weight buy and hold of the same stocks, and SPY.

## Quick start

Install [uv](https://docs.astral.sh/uv/) (see [docs/setup.md](docs/setup.md)), then from the project folder:

```bash
uv sync                                  # environment with Python and all dependencies
uv run python 01_download_data.py        # download the prices (optional: they are already in data/)
uv run python 02_validate_data.py        # validate the prices: stops if a check fails
uv run python 03_optimize_ga.py          # choose the parameters with the genetic algorithm (a few minutes)
uv run python 04_compute_signals.py      # compute the signals
uv run python 05_evaluate_strategy.py    # returns, metrics and charts, In-Sample and Out-of-Sample
```

The data are in the repository, so the results are reproducible without downloading anything: start from
`02_validate_data.py`. Running `01_download_data.py` again downloads the prices as Yahoo Finance gives them today, which
may differ slightly from the saved ones (Yahoo recomputes the adjusted prices).

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

Shared code is in `src/`: `backtest.py` (forward returns, costs), `ensemble.py` (indicators and vote), `genetic.py`
(genetic algorithm, DEAP), `metrics.py`, `plots.py`, `data.py`, `config.py`.

Periods (by the day each return is realized): training up to 2014-12-26, validation up to 2018-12-28 (together the
In-Sample period), Out-of-Sample from 2018-12-31. Execution at the next open, 10 bps per trade, risk-free 2%.

## Documentation

| File | Content |
|---|---|
| [docs/setup.md](docs/setup.md) | Install uv and the dependencies, run the code, add packages, what to do if something fails |
| [docs/metrics.md](docs/metrics.md) | Execution of the signals and returns, In-Sample / Out-of-Sample split, metrics to evaluate the strategies |
| [docs/experiment_log.md](docs/experiment_log.md) | Every configuration tried, with its result, and the Out-of-Sample result |
| [notebooks/00_esplora_dati.ipynb](notebooks/00_esplora_dati.ipynb) | Exploration of the prices, signals and metrics saved in `data/` |
| [resources/instructions.pdf](resources/instructions.pdf) | Text of the exam project |
| [resources/presentation.pptx](resources/presentation.pptx) | Template of the presentation |
