# Setup

## Install uv

[uv](https://docs.astral.sh/uv/) installs the right Python version and all the dependencies for you: **you do not need to install Python separately.**

**macOS / Linux** (in a terminal):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows** (in PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen the terminal, then check that it works:

```bash
uv --version
```

## Install dependencies

From the project folder, create the environment with the Python version and dependencies pinned in `.python-version`, `pyproject.toml` and `uv.lock`:

```bash
uv sync
```

The environment is the `.venv/` folder: never edit it by hand. If it breaks, delete it and run `uv sync` again.

## Run the code

Run every script with `uv run`, which uses the environment of the project (no need to activate it):

```bash
uv run python <script>.py
```

## Add dependencies

Manage packages only with uv: it updates `pyproject.toml` (the packages you asked for) and `uv.lock` (the exact versions of every package,
also the indirect ones), then installs them in `.venv/`. **Do not use `pip install`**: the package would not be written in
`pyproject.toml` and `uv.lock`, so it would be missing for anyone else who runs `uv sync`.

| Task | Command |
|---|---|
| Add a package (e.g. scikit-learn) | `uv add scikit-learn` |
| Add a package with a minimum version | `uv add "scikit-learn>=1.5"` |
| Add a package used only while developing (e.g. Jupyter) | `uv add --dev ipykernel` |
| Remove a package | `uv remove scikit-learn` |
| Update one package to its latest version | `uv lock --upgrade-package yfinance`, then `uv sync` |
| Update all packages | `uv lock --upgrade`, then `uv sync` |
| See the installed packages and their dependencies | `uv tree` |
| Align `.venv/` with `uv.lock` (e.g. after receiving a new version of the project) | `uv sync` |

Share `pyproject.toml` and `uv.lock` together with the code: with them, `uv sync` rebuilds exactly the same environment on any computer.

Tools that are not needed by the code, such as the [ruff](https://docs.astral.sh/ruff/) linter, can run without adding them to the project:

```bash
uvx ruff check .     # style and common errors (settings in pyproject.toml)
uvx ruff format .    # format the code
```

## If something fails

| Message | What to do |
|---|---|
| `ModuleNotFoundError: No module named ...` | The package is not in the project: add it with `uv add <package>`; check that you ran the script with `uv run` |
| No prices from Yahoo Finance (`yfinance`) | Check the ticker on [Yahoo Finance](https://finance.yahoo.com); if it is right, wait a few minutes and retry (Yahoo limits the number of requests). If Yahoo changed its interface, update the library: `uv lock --upgrade-package yfinance`, then `uv sync` |
