"""Validate the downloaded prices before using them: stop if a check fails, report the warnings.

Checks (FAIL stops the pipeline, WARN is reported and explained, PASS is fine):
    calendar      daily dates unique and sorted; weeks labeled (Monday, Friday), one row per week
    positive      every price above zero
    ohlc          low <= open, close <= high on every day
    missing       no gap after the first price of each ticker (a late listing, as GOOG in 2004, is not a gap)
    stale         no run of identical closes (a frozen feed)
    volume        no day with zero volume
    splits        on every split day the adjusted return is normal; the return without the adjustment is reported
    dividends     the dividend adjustment (adjusted close / close adjusted only for splits) changes only on ex-dividend days,
                  and changes on every one of them
    weekly        the weekly open and close are the first open and the last close of the daily prices of the week
    outliers      daily moves above 20% and weekly moves above 25%: reported, never removed (they are real prices)

Input:  data/prices/raw/*.csv, data/prices/{open,close}.csv
Output: data/validation/checks.csv, one row per check and ticker
        data/validation/splits.csv, every split with the adjusted and unadjusted return of the day
        data/validation/outliers.csv, the extreme moves
"""

import numpy as np
import pandas as pd

from src.config import DATA_KEYS, ROOT, check_used, load_config
from src.data import read_weekly

PRICE_TOLERANCE = 1e-6  # relative, rounding of the prices of Yahoo
DIVIDEND_TOLERANCE = 1e-4  # relative change of the adjustment factor that counts as an adjustment (a dividend is > 0.01%)
SPLIT_DAY_MAX = 0.25  # an adjusted daily move above 25% on a split day means the split is not adjusted
STALE_DAYS = 5  # identical closes in a row
DAILY_OUTLIER, WEEKLY_OUTLIER = 0.20, 0.25


def read_daily(path) -> pd.DataFrame:
    return pd.read_csv(path, index_col=0, parse_dates=True)


def main() -> None:
    cfg = load_config()["data"]
    data_dir = ROOT / cfg["data_dir"]
    check_used({key: cfg[key] for key in DATA_KEYS}, data_dir / "prices" / "config.yaml", "01_download_data.py")
    tickers = cfg["tickers"] + [cfg["benchmark"]]
    raw = {name: read_daily(data_dir / "prices" / "raw" / f"{name}.csv")[tickers] for name in
           ["open", "high", "low", "close", "volume", "close_split_only", "dividends", "splits"]}
    weekly = {name: read_weekly(data_dir / "prices" / f"{name}.csv")[tickers] for name in ["open", "close"]}
    days = raw["close"].index

    checks = []

    def report(check: str, ticker: str, failed: bool, warned: bool, detail: str) -> None:
        checks.append({"check": check, "ticker": ticker, "result": "FAIL" if failed else "WARN" if warned else "PASS", "detail": detail})

    # Calendar
    weeks = weekly["close"].index
    fridays = weeks.get_level_values("date_close")
    report("calendar", "all", not (days.is_unique and days.is_monotonic_increasing), False,
           f"{len(days)} days from {days[0].date()} to {days[-1].date()}")
    week_ok = (fridays.day_name() == "Friday").all() and fridays.is_unique and \
        (weeks.get_level_values("date_open") == fridays - pd.Timedelta(days=4)).all()
    days_per_week = raw["close"].iloc[:, 0].resample("W-FRI").size().reindex(fridays)
    report("calendar", "weeks", not week_ok, False,
           f"{len(weeks)} weeks; {(days_per_week < 5).sum()} with fewer than 5 trading days (holidays)")

    returns = raw["close"].pct_change(fill_method=None)
    weekly_returns = weekly["close"].pct_change(fill_method=None)
    split_rows, outlier_rows = [], []
    for t in tickers:
        close = raw["close"][t]
        first = close.first_valid_index()
        listed = close.loc[first:]

        prices = pd.concat([raw[f][t] for f in ["open", "high", "low", "close"]], axis=1)
        report("positive", t, bool((prices <= 0).any().any()), False, f"min price {prices.min().min():.4f}")

        tol = PRICE_TOLERANCE * raw["high"][t]
        low_bad = raw["low"][t] > np.minimum(raw["open"][t], raw["close"][t]) + tol
        high_bad = raw["high"][t] < np.maximum(raw["open"][t], raw["close"][t]) - tol
        bad = int((low_bad | high_bad).sum())
        report("ohlc", t, False, bad > 0, f"{bad} days with low above or high below open/close")

        gaps = int(listed.isna().sum())
        late = f"first price {first.date()}" + (" (listed after the start)" if first > days[0] else "")
        report("missing", t, gaps > 0, False, f"{late}; {gaps} missing days after it")

        same = listed.diff().eq(0)
        longest = int(same.groupby((~same).cumsum()).sum().max()) + 1
        report("stale", t, False, longest >= STALE_DAYS, f"longest run of identical closes: {longest} days")

        zero_volume = int((raw["volume"][t].loc[first:] == 0).sum())
        report("volume", t, False, zero_volume > 0, f"{zero_volume} days with zero volume")

        # Splits: adjusted return of the day, and the return a series not adjusted for the split would show
        ratios = raw["splits"][t][raw["splits"][t] > 0]
        for day, ratio in ratios.items():
            adjusted = returns.loc[day, t]
            split_rows.append({"ticker": t, "date": day.date(), "ratio": ratio, "adjusted_return": adjusted,
                               "unadjusted_return": (1 + adjusted) / ratio - 1})
        crashes = [r for r in split_rows if r["ticker"] == t and abs(r["adjusted_return"]) > SPLIT_DAY_MAX]
        report("splits", t, len(crashes) > 0, False,
               f"{len(ratios)} splits" + ("".join(f", {r['date']} {r['ratio']:g}:1" for r in split_rows if r["ticker"] == t)))

        # Dividends: the adjustment factor changes on the ex-dividend days, and only there
        factor = raw["close"][t] / raw["close_split_only"][t]
        changed = factor.pct_change(fill_method=None).abs() > DIVIDEND_TOLERANCE
        ex_days = raw["dividends"][t] > 0
        unexpected = int((changed & ~ex_days).sum())
        missed = int((ex_days & ~changed).sum())
        report("dividends", t, unexpected > 0 or missed > 0, False,
               f"{int(ex_days.sum())} dividends; adjustment off the ex-dividend days: {unexpected}; dividends not adjusted: {missed}")

        # Weekly prices rebuilt from the daily ones
        rebuilt_close = raw["close"][t].resample("W-FRI").last().reindex(fridays)
        rebuilt_open = raw["open"][t].resample("W-FRI").first().reindex(fridays)
        diff, same_missing = 0.0, True
        for saved, rebuilt in [(weekly["close"][t], rebuilt_close), (weekly["open"][t], rebuilt_open)]:
            saved = saved.droplevel("date_open")
            diff = max(diff, (saved / rebuilt - 1).abs().max())
            same_missing &= saved.isna().equals(rebuilt.isna())
        report("weekly", t, diff > PRICE_TOLERANCE or not same_missing, False,
               f"largest difference from the daily prices: {diff:.1e}; same missing weeks: {same_missing}")

        # Outliers: reported, kept
        split_days = set(ratios.index)
        for kind, series, limit in [("daily", returns[t], DAILY_OUTLIER), ("weekly", weekly_returns[t], WEEKLY_OUTLIER)]:
            for day, value in series[series.abs() > limit].items():
                day = day[1] if isinstance(day, tuple) else day
                outlier_rows.append({"ticker": t, "frequency": kind, "date": day.date(), "return": value,
                                     "split_day": kind == "daily" and day in split_days})
        n_out = sum(1 for r in outlier_rows if r["ticker"] == t)
        report("outliers", t, False, n_out > 0, f"{n_out} moves above {DAILY_OUTLIER:.0%} daily or {WEEKLY_OUTLIER:.0%} weekly, kept")

    out_dir = data_dir / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    checks = pd.DataFrame(checks)
    checks.to_csv(out_dir / "checks.csv", index=False)
    pd.DataFrame(split_rows).to_csv(out_dir / "splits.csv", index=False)
    pd.DataFrame(outlier_rows).to_csv(out_dir / "outliers.csv", index=False)

    with pd.option_context("display.max_colwidth", 110, "display.width", 200):
        print(checks.to_string(index=False))
        print("\nSplits: adjusted return of the day vs the return without the adjustment")
        print(pd.DataFrame(split_rows).round(4).to_string(index=False))
        print("\nOutliers (kept, they are real prices):")
        print(pd.DataFrame(outlier_rows).round(4).to_string(index=False))
    print(f"\nSaved {(out_dir).relative_to(ROOT)}/{{checks,splits,outliers}}.csv")
    failed = checks[checks["result"] == "FAIL"]
    if not failed.empty:
        raise ValueError(f"{len(failed)} checks failed: see {(out_dir / 'checks.csv').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
