"""Download adjusted daily prices from yfinance and keep the open and close of each week.

Outputs: data/prices/raw/{open,high,low,close,volume}.csv, the downloaded daily prices, adjusted for splits and dividends
         data/prices/raw/{close_split_only,dividends,splits}.csv, the close adjusted only for splits and the corporate
         actions, used by 02_validate_data.py to check the adjustment
         data/prices/{open,close}.csv, indexed by (date_open, date_close) = (Monday, Friday) of each week
         data/prices/config.yaml, the settings used
"""

import pandas as pd
import yfinance as yf

from src.config import DATA_KEYS, ROOT, load_config, save_used


def save(prices: pd.DataFrame, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(path)
    print(f"Saved {path.relative_to(ROOT)}: {prices.shape[0]} rows, {prices.shape[1]} columns")


def main() -> None:
    cfg = load_config()["data"]
    data_dir = ROOT / cfg["data_dir"]

    if cfg["benchmark"] in cfg["tickers"]:
        raise ValueError(f"data.benchmark ({cfg['benchmark']}) must not be one of data.tickers")
    if pd.Timestamp(cfg["end"]).day_name() != "Friday":
        raise ValueError(f"data.end ({cfg['end']}) must be a Friday: the last week must be complete")
    tickers = cfg["tickers"] + [cfg["benchmark"]]

    data = yf.download(
        tickers,
        start=cfg["start"],
        end=pd.Timestamp(cfg["end"]) + pd.Timedelta(days=1),  # yfinance excludes end
        auto_adjust=True,
    )
    daily_open, daily_close = data["Open"][tickers], data["Close"][tickers]

    failed = daily_close.columns[daily_close.isna().all()].tolist()
    if failed:
        raise ValueError(f"no prices downloaded for {failed}: check the tickers on Yahoo Finance, or retry in a few minutes")
    for field in ["Open", "High", "Low", "Close", "Volume"]:
        save(data[field][tickers], data_dir / "prices" / "raw" / f"{field.lower()}.csv")

    # Same days without the dividend adjustment, with the dates of dividends and splits
    actions = yf.download(
        tickers,
        start=cfg["start"],
        end=pd.Timestamp(cfg["end"]) + pd.Timedelta(days=1),
        auto_adjust=False,
        actions=True,
    )
    for field, name in [("Close", "close_split_only"), ("Dividends", "dividends"), ("Stock Splits", "splits")]:
        save(actions[field][tickers].reindex(data.index), data_dir / "prices" / "raw" / f"{name}.csv")

    # First open and last close of each week, labeled with its Friday
    close = daily_close.resample("W-FRI").last().dropna(how="all")
    opens = daily_open.resample("W-FRI").first().loc[close.index]

    fridays = close.index
    weeks = pd.MultiIndex.from_arrays([fridays - pd.Timedelta(days=4), fridays], names=["date_open", "date_close"])
    opens.index, close.index = weeks, weeks
    print(f"Missing closes: {close.isna().sum().to_dict()}")
    print(f"Missing opens:  {opens.isna().sum().to_dict()}")

    save(opens, data_dir / "prices" / "open.csv")
    save(close, data_dir / "prices" / "close.csv")
    save_used({key: cfg[key] for key in DATA_KEYS}, data_dir / "prices" / "config.yaml")


if __name__ == "__main__":
    main()
