"""Validate the extra data downloaded by 06_download_extra_data.py: stop if a check fails, report the warnings.

The ETFs and funds get the same checks as the traded stocks (src/validation.py); the macro series get their own (coverage,
gaps, plausible range). A late listing is not a gap: each ETF is checked from its first price.

Input:  data/extra/prices/, data/extra/macro/
Output: data/extra/validation/checks.csv, one row per check and ticker or series
        data/extra/validation/splits.csv, data/extra/validation/outliers.csv
"""

import pandas as pd

from src.config import ROOT, check_used, load_config
from src.data import macro_start
from src.validation import save_report, validate_macro, validate_prices


def main() -> None:
    cfg = load_config()
    data, extra = cfg["data"], cfg["extra"]
    extra_dir = ROOT / data["data_dir"] / "extra"
    check_used({"start": data["start"], "end": data["end"], **extra}, extra_dir / "config.yaml", "06_download_extra_data.py")

    tickers = [ticker for group in extra["groups"].values() for ticker in group]
    checks, splits, outliers = validate_prices(extra_dir / "prices", tickers)
    macro = validate_macro(extra_dir / "macro", extra["macro"], macro_start(data["start"]), data["end"])
    checks = pd.concat([checks, macro], ignore_index=True)
    save_report(checks, splits, outliers, extra_dir / "validation")


if __name__ == "__main__":
    main()
