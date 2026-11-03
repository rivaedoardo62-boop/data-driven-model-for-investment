"""Download adjusted daily prices from yfinance and keep the open and close of each week.

Outputs: data/prices/raw/{open,high,low,close,volume}.csv, the downloaded daily prices, adjusted for splits and dividends
         data/prices/raw/{close_split_only,dividends,splits}.csv, the close adjusted only for splits and the corporate
         actions, used by 02_validate_data.py to check the adjustment
         data/prices/{open,close}.csv, indexed by (date_open, date_close) = (Monday, Friday) of each week
         data/prices/config.yaml, the settings used

Do not run it again once the strategy is frozen: Yahoo recomputes the adjusted prices, so 03_optimize_ga.py would have to
run again on different prices. The saved prices are the ones the strategy was built and tested on.
"""

import pandas as pd

from src.config import DATA_KEYS, ROOT, load_config, save_used
from src.data import download_prices


def main() -> None:
    cfg = load_config()["data"]
    data_dir = ROOT / cfg["data_dir"]

    if cfg["benchmark"] in cfg["tickers"]:
        raise ValueError(f"data.benchmark ({cfg['benchmark']}) must not be one of data.tickers")
    if pd.Timestamp(cfg["end"]).day_name() != "Friday":
        raise ValueError(f"data.end ({cfg['end']}) must be a Friday: the last week must be complete")

    download_prices(cfg["tickers"] + [cfg["benchmark"]], cfg["start"], cfg["end"], data_dir / "prices")
    save_used({key: cfg[key] for key in DATA_KEYS}, data_dir / "prices" / "config.yaml")


if __name__ == "__main__":
    main()
