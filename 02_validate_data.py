"""Validate the downloaded prices before using them: stop if a check fails, report the warnings.

The checks are in src/validation.py (FAIL stops the pipeline, WARN is reported and explained, PASS is fine): calendar,
positive prices, OHLC consistency, gaps, stale prices, zero volume, splits, dividend adjustment, weekly prices, outliers.

Input:  data/prices/raw/*.csv, data/prices/{open,close}.csv
Output: data/validation/checks.csv, one row per check and ticker
        data/validation/splits.csv, every split with the adjusted and unadjusted return of the day
        data/validation/outliers.csv, the extreme moves
"""

from src.config import DATA_KEYS, ROOT, check_used, load_config
from src.validation import save_report, validate_prices


def main() -> None:
    cfg = load_config()["data"]
    data_dir = ROOT / cfg["data_dir"]
    check_used({key: cfg[key] for key in DATA_KEYS}, data_dir / "prices" / "config.yaml", "01_download_data.py")

    checks, splits, outliers = validate_prices(data_dir / "prices", cfg["tickers"] + [cfg["benchmark"]])
    save_report(checks, splits, outliers, data_dir / "validation")


if __name__ == "__main__":
    main()
