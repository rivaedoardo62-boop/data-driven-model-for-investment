"""Load config.yaml, and detect outputs built with a different config.yaml."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# Settings that change the downloaded prices
DATA_KEYS = ["tickers", "benchmark", "start", "end"]


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def save_used(settings: dict, path) -> None:
    """Save the settings used to build the files of a folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(settings, f)


def check_used(settings: dict, path, script: str) -> None:
    """Stop if the files of a folder were built with different settings."""
    if not path.exists():
        raise FileNotFoundError(f"{path.relative_to(ROOT)} not found: run the scripts in order")
    with open(path) as f:
        if yaml.safe_load(f) != settings:
            raise ValueError(f"{path.parent.relative_to(ROOT)} was built with a different config.yaml: run {script} again")
