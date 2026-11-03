"""Download the extra data used only to evaluate the frozen strategy: ETFs and funds linked to AI, and macro series.

Nothing here is used to choose the strategy: its parameters stay the ones in data/ga/best.yaml.

    extra.groups   ETFs and funds from Yahoo Finance, adjusted for splits and dividends, same dates as data.start and data.end:
                   ai_long      AI supply chain with 10+ years of prices, traded by the frozen strategy (transfer test)
                   ai_short     the same test on short histories, secondary
                   quant_funds  quantitative and AI-managed funds, peer benchmarks bought and held
    extra.macro    FRED series as published today, from one year before data.start (for yearly changes)

Outputs: data/extra/prices/, the same files as data/prices/ (see 01_download_data.py)
         data/extra/macro/<series>.csv
         data/extra/config.yaml, the settings used
         data/extra/sources.yaml, the day of the download and the sources
"""

from datetime import date
from importlib.metadata import version

import pandas as pd
import yaml

from src.config import ROOT, load_config, save_used
from src.data import FRED_URL, download_fred, download_prices


def main() -> None:
    cfg = load_config()
    data, extra = cfg["data"], cfg["extra"]
    data_dir = ROOT / data["data_dir"]

    tickers = [ticker for group in extra["groups"].values() for ticker in group]
    repeated = sorted({t for t in tickers if tickers.count(t) > 1} | set(tickers) & set(data["tickers"] + [data["benchmark"]]))
    if repeated:
        raise ValueError(f"{repeated} appear twice in extra.groups, or are already in data.tickers / data.benchmark")
    if pd.Timestamp(data["end"]).day_name() != "Friday":
        raise ValueError(f"data.end ({data['end']}) must be a Friday: the last week must be complete")

    download_prices(tickers, data["start"], data["end"], data_dir / "extra" / "prices")

    macro_start = (pd.Timestamp(data["start"]) - pd.DateOffset(years=1)).date().isoformat()
    for series in extra["macro"]:
        download_fred(series, macro_start, data["end"], data_dir / "extra" / "macro" / f"{series}.csv")

    save_used({"start": data["start"], "end": data["end"], **extra}, data_dir / "extra" / "config.yaml")
    sources = {
        "downloaded": date.today().isoformat(),
        "prices": f"Yahoo Finance, yfinance {version('yfinance')}, auto_adjust=True",
        "macro": FRED_URL.format("<series>") + " (latest vintage, not point-in-time)",
    }
    with open(data_dir / "extra" / "sources.yaml", "w") as f:
        yaml.safe_dump(sources, f, sort_keys=False)
    print(f"Saved {(data_dir / 'extra').relative_to(ROOT)}/{{config,sources}}.yaml")


if __name__ == "__main__":
    main()
