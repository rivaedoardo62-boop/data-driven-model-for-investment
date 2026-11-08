"""Download the macro series that describe the market regimes (never used as a signal).

    extra.macro    FRED series as published today (latest vintage), from one year before data.start (for yearly changes)
                   to data.end

Outputs: data/extra/macro/<series>.csv
         data/extra/config.yaml, the settings used
         data/extra/sources.yaml, the day of the download and the sources
"""

from datetime import date

import pandas as pd
import yaml

from src.config import ROOT, load_config, save_used
from src.data import FRED_URL, download_fred, macro_start


def main() -> None:
    cfg = load_config()
    data, extra = cfg["data"], cfg["extra"]
    data_dir = ROOT / data["data_dir"]

    if pd.Timestamp(data["end"]).day_name() != "Friday":
        raise ValueError(f"data.end ({data['end']}) must be a Friday: the last week must be complete")

    for series in extra["macro"]:
        download_fred(series, macro_start(data["start"]), data["end"], data_dir / "extra" / "macro" / f"{series}.csv")

    save_used({"start": data["start"], "end": data["end"], **extra}, data_dir / "extra" / "config.yaml")
    sources = {
        "downloaded": date.today().isoformat(),
        "macro": FRED_URL.format("<series>") + " (latest vintage, not point-in-time)",
    }
    with open(data_dir / "extra" / "sources.yaml", "w") as f:
        yaml.safe_dump(sources, f, sort_keys=False)
    print(f"Saved {(data_dir / 'extra').relative_to(ROOT)}/{{config,sources}}.yaml")


if __name__ == "__main__":
    main()
