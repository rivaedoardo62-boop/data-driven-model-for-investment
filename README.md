# Systematic Trading Strategy

## Quick start

Install [uv](https://docs.astral.sh/uv/) (see [docs/setup.md](docs/setup.md)), then from the project folder:

```bash
uv sync                                  # environment with Python and all dependencies
uv run python 01_download_data.py        # download the prices
uv run python 02_compute_signals.py      # compute the signals
uv run python 03_evaluate_strategy.py    # returns, metrics and charts
```

All settings are in `config.yaml`. The scripts write their data and outputs in `data/`.

## Documentation

| File | Content |
|---|---|
| [docs/setup.md](docs/setup.md) | Install uv and the dependencies, run the code, add packages, what to do if something fails |
| [resources/instructions.pdf](resources/instructions.pdf) | Text of the exam project |
| [resources/presentation.pptx](resources/presentation.pptx) | Template of the presentation |
| [docs/metrics.md](docs/metrics.md) | Execution of the signals and returns, In-Sample / Out-of-Sample split, metrics to evaluate the strategies |
