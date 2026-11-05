"""Clean the Bloomberg prices of the semiconductor universe: one series per company, checks, weekly tables, features.

Steps:
    1. one series per company: Bloomberg gives a stock once per exchange line; on each day the line with the largest
       volume is the listing exchange (src/bloomberg.py), the moves between exchanges are saved
    2. checks (FAIL stops, WARN is reported): positive prices, OHLC, trading days without a price against the trading
       calendar of SPY, stale prices, zero volume, adjustment for dividends (price against the total return index of
       Bloomberg), extreme moves (kept: they are real prices)
    3. weekly tables as data/prices (first open and last close of each week); a company that left the market is sold at
       its last price, in the week after it
    4. features of each company and week, with prices up to that Friday only, winsorized and z-scored week by week
    5. if data/bloomberg/raw/membership.csv exists: who was in the SOX index in each week (point in time)

Input:  data/bloomberg/raw/prices.parquet (and membership.csv), data/prices/raw/close.csv (trading calendar)
Output: data/bloomberg/clean/daily.parquet           one row per company and day
        data/bloomberg/clean/{open,close,market_cap,traded_value}.csv   weekly, one column per company
        data/bloomberg/clean/in_index.csv            (with membership.csv) True when the company was in the index
        data/bloomberg/clean/features.parquet        one row per company and week
        data/bloomberg/clean/companies.csv           one row per company: lines, first and last price, exit, risk
        data/bloomberg/clean/line_switches.csv       changes of exchange
        data/bloomberg/clean/validation/{checks,outliers}.csv
Bloomberg data are licensed: data/bloomberg/ is not on GitHub (see data/bloomberg/README.md).
"""

import pandas as pd

from src import bloomberg, features
from src.config import ROOT, load_config


def save(table: pd.DataFrame, path, index: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        table.to_parquet(path, index=index)
    else:
        table.to_csv(path, index=index)
    print(f"Saved {path.relative_to(ROOT)}: {table.shape[0]} rows, {table.shape[1]} columns")


def main() -> None:
    cfg = load_config()
    data, bb = cfg["data"], cfg["bloomberg"]
    start, end = pd.Timestamp(data["start"]), pd.Timestamp(data["end"])
    raw_dir, clean = ROOT / bb["dir"] / "raw", ROOT / bb["dir"] / "clean"
    if not (raw_dir / "prices.parquet").exists():
        raise FileNotFoundError(
            f"{(raw_dir / 'prices.parquet').relative_to(ROOT)} not found: copy there the files of 09_download_bloomberg.py"
        )

    raw = bloomberg.load_raw(raw_dir / "prices.parquet")
    daily = bloomberg.merge_lines(raw)
    dates = daily.index.get_level_values("date")
    daily = daily[(dates >= start) & (dates <= end)]
    print(
        f"{raw['ticker'].nunique()} exchange lines -> {daily.index.get_level_values('company').nunique()} companies, "
        f"{len(daily)} company-days from {start.date()} to {end.date()}"
    )

    calendar = pd.read_csv(ROOT / data["data_dir"] / "prices" / "raw" / "close.csv", index_col=0, parse_dates=True).index
    checks, outliers = bloomberg.check_daily(daily, calendar, end)
    tables = bloomberg.weekly_tables(daily, end, bb["exited_after"])
    companies = bloomberg.summary(daily, end, bb["exited_after"])
    feats = features.panel(
        features.compute(tables["close"], tables["market_cap"], tables["traded_value"], bb["features"]), bb["winsorize"]
    )

    save(daily.reset_index(), clean / "daily.parquet", index=False)
    for name in ["open", "close", "market_cap", "traded_value"]:
        save(tables[name], clean / f"{name}.csv")
    if (raw_dir / "membership.csv").exists():
        in_index = bloomberg.index_membership(
            pd.read_csv(raw_dir / "membership.csv"), tables["close"].index, tables["close"].columns
        )
        save(in_index, clean / "in_index.csv")
        feats = feats.join(in_index.stack().rename("in_index"))
    else:
        print("raw/membership.csv not found: no point-in-time membership yet (run 09_download_bloomberg.py --membership-only)")
    save(feats, clean / "features.parquet")
    save(companies, clean / "companies.csv")
    save(bloomberg.line_switches(daily), clean / "line_switches.csv", index=False)
    save(checks, clean / "validation" / "checks.csv", index=False)
    save(outliers, clean / "validation" / "outliers.csv", index=False)

    with pd.option_context("display.max_colwidth", 120, "display.width", 220):
        print("\nChecks:", checks["result"].value_counts().to_dict())
        print(checks[checks["result"] != "PASS"].to_string(index=False))
        print(f"\nCompanies that left the market: {int(companies['exited'].sum())} of {len(companies)}")
    failed = checks[checks["result"] == "FAIL"]
    if not failed.empty:
        raise ValueError(f"{len(failed)} checks failed: see {(clean / 'validation' / 'checks.csv').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
