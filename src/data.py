"""Download prices from Yahoo Finance and macro series from FRED, and read the weekly tables of data/."""

import pandas as pd

from src.config import ROOT

WEEK_COLUMNS = ["date_open", "date_close"]
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def read_weekly(path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run the scripts in order")
    return pd.read_csv(path, index_col=WEEK_COLUMNS, parse_dates=WEEK_COLUMNS)


def save(table: pd.DataFrame, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path)
    print(f"Saved {path.relative_to(ROOT)}: {table.shape[0]} rows, {table.shape[1]} columns")


def download_prices(tickers: list[str], start: str, end: str, prices_dir) -> None:
    """Download adjusted daily prices from yfinance and keep the open and close of each week.

    Outputs in prices_dir:
        raw/{open,high,low,close,volume}.csv, the downloaded daily prices, adjusted for splits and dividends
        raw/{close_split_only,dividends,splits}.csv, the close adjusted only for splits and the corporate actions,
        used by the validation to check the adjustment
        {open,close}.csv, indexed by (date_open, date_close) = (Monday, Friday) of each week
    """
    import yfinance as yf  # imported here: only the download scripts need it

    last_day = pd.Timestamp(end) + pd.Timedelta(days=1)  # yfinance excludes end
    data = yf.download(tickers, start=start, end=last_day, auto_adjust=True)
    daily_open, daily_close = data["Open"][tickers], data["Close"][tickers]

    failed = daily_close.columns[daily_close.isna().all()].tolist()
    if failed:
        raise ValueError(f"no prices downloaded for {failed}: check the tickers on Yahoo Finance, or retry in a few minutes")
    for field in ["Open", "High", "Low", "Close", "Volume"]:
        save(data[field][tickers], prices_dir / "raw" / f"{field.lower()}.csv")

    # Same days without the dividend adjustment, with the dates of dividends and splits
    actions = yf.download(tickers, start=start, end=last_day, auto_adjust=False, actions=True)
    for field, name in [("Close", "close_split_only"), ("Dividends", "dividends"), ("Stock Splits", "splits")]:
        save(actions[field][tickers].reindex(data.index), prices_dir / "raw" / f"{name}.csv")

    # First open and last close of each week, labeled with its Friday
    close = daily_close.resample("W-FRI").last().dropna(how="all")
    opens = daily_open.resample("W-FRI").first().loc[close.index]

    fridays = close.index
    weeks = pd.MultiIndex.from_arrays([fridays - pd.Timedelta(days=4), fridays], names=WEEK_COLUMNS)
    opens.index, close.index = weeks, weeks
    print(f"Missing closes: {close.isna().sum().to_dict()}")
    print(f"Missing opens:  {opens.isna().sum().to_dict()}")

    save(opens, prices_dir / "open.csv")
    save(close, prices_dir / "close.csv")


def macro_start(start: str) -> str:
    """First day of the macro series: one year before the prices, so that yearly changes exist from the start."""
    return (pd.Timestamp(start) - pd.DateOffset(years=1)).date().isoformat()


def download_fred(series: str, start: str, end: str, path) -> None:
    """Download a FRED series as published today (latest vintage), from start to end included."""
    table = pd.read_csv(FRED_URL.format(series), index_col=0, parse_dates=True, storage_options={"User-Agent": "Mozilla/5.0"})
    values = pd.to_numeric(table.iloc[:, 0], errors="coerce").loc[start:end].dropna()  # missing days are "." or empty
    if values.empty:
        raise ValueError(f"no data downloaded for the FRED series {series}: check its name on https://fred.stlouisfed.org")
    save(values.rename(series).rename_axis("date").to_frame(), path)
