"""Read the weekly tables of data/."""

import pandas as pd

WEEK_COLUMNS = ["date_open", "date_close"]


def read_weekly(path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run the scripts in order")
    return pd.read_csv(path, index_col=WEEK_COLUMNS, parse_dates=WEEK_COLUMNS)
