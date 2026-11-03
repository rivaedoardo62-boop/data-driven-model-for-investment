"""Checks of downloaded data, shared by 02_validate_data.py (traded stocks) and 07_validate_extra_data.py (extra data).

Prices. Checks (FAIL stops the pipeline, WARN is reported and explained, PASS is fine):
    calendar      daily dates unique and sorted; weeks labeled (Monday, Friday), one row per week
    positive      every price above zero
    ohlc          low <= open, close <= high on every day
    missing       no gap after the first price of each ticker (a late listing, as GOOG in 2004, is not a gap)
    stale         no run of identical closes (a frozen feed)
    volume        no day with zero volume
    splits        on every split day the adjusted return is normal; the return without the adjustment is reported
    dividends     the dividend adjustment (adjusted close / close adjusted only for splits) changes only on ex-dividend days,
                  and on every one of them by about the dividend yield (tiny dividends, below 0.01%, included)
    weekly        the weekly open and close are the first open and the last close of the daily prices of the week
    outliers      daily moves above 20% and weekly moves above 25%: reported, never removed (they are real prices)

Macro series (FRED):
    coverage      the series starts by the first day asked and ends near the last one
    gaps          no missing month for a monthly series (except the KNOWN_GAPS, reported), no gap above 10 days for a daily one
    range         every value inside a plausible range (e.g. VIX between 5 and 100, recession indicator 0 or 1)
"""

import numpy as np
import pandas as pd

from src.config import ROOT
from src.data import read_weekly

PRICE_TOLERANCE = 1e-6  # relative, rounding of the prices of Yahoo
DIVIDEND_TOLERANCE = 1e-4  # relative change of the adjustment factor that needs a dividend to explain it
DIVIDEND_SHARE = 0.5  # a dividend is adjusted if the factor changes by at least half of its yield
SPLIT_DAY_MAX = 0.25  # an adjusted daily move above 25% on a split day means the split is not adjusted
STALE_DAYS = 5  # identical closes in a row
DAILY_OUTLIER, WEEKLY_OUTLIER = 0.20, 0.25
MAX_DAILY_GAP = 10  # calendar days between two observations of a daily series (holidays and the 2001 market closure are shorter)
MONTHLY_LAG = 45  # days a monthly series may end before the last day (publication lag), WARN beyond
MACRO_RANGES = {  # plausible values: outside them the series is wrong or misread
    "VIXCLS": (5, 100),
    "T10Y3M": (-5, 6),
    "USREC": (0, 1),
    "DFF": (-1, 25),
    "BAA10Y": (0, 8),
    "CPIAUCSL": (100, 500),
    "DTB3": (-1, 20),
}
KNOWN_GAPS = {  # months missing at the source, reported as WARN instead of FAIL
    "CPIAUCSL": ["2025-10"],  # not published by the BLS: no prices collected during the 2025 federal government shutdown
}


def read_daily(path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run the scripts in order")
    return pd.read_csv(path, index_col=0, parse_dates=True)


def validate_prices(prices_dir, tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Checks of the prices in prices_dir (files written by src.data.download_prices): checks, splits and outliers."""
    raw = {
        name: read_daily(prices_dir / "raw" / f"{name}.csv")[tickers]
        for name in ["open", "high", "low", "close", "volume", "close_split_only", "dividends", "splits"]
    }
    weekly = {name: read_weekly(prices_dir / f"{name}.csv")[tickers] for name in ["open", "close"]}
    days = raw["close"].index

    checks = []

    def report(check: str, ticker: str, failed: bool, warned: bool, detail: str) -> None:
        checks.append(
            {"check": check, "ticker": ticker, "result": "FAIL" if failed else "WARN" if warned else "PASS", "detail": detail}
        )

    # Calendar
    weeks = weekly["close"].index
    fridays = weeks.get_level_values("date_close")
    report(
        "calendar",
        "all",
        not (days.is_unique and days.is_monotonic_increasing),
        False,
        f"{len(days)} days from {days[0].date()} to {days[-1].date()}",
    )
    week_ok = (
        (fridays.day_name() == "Friday").all()
        and fridays.is_unique
        and (weeks.get_level_values("date_open") == fridays - pd.Timedelta(days=4)).all()
    )
    days_per_week = raw["close"].iloc[:, 0].resample("W-FRI").size().reindex(fridays)
    report(
        "calendar",
        "weeks",
        not week_ok,
        False,
        f"{len(weeks)} weeks; {(days_per_week < 5).sum()} with fewer than 5 trading days (holidays)",
    )

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
            split_rows.append(
                {
                    "ticker": t,
                    "date": day.date(),
                    "ratio": ratio,
                    "adjusted_return": adjusted,
                    "unadjusted_return": (1 + adjusted) / ratio - 1,
                }
            )
        crashes = [r for r in split_rows if r["ticker"] == t and abs(r["adjusted_return"]) > SPLIT_DAY_MAX]
        report(
            "splits",
            t,
            len(crashes) > 0,
            False,
            f"{len(ratios)} splits" + ("".join(f", {r['date']} {r['ratio']:g}:1" for r in split_rows if r["ticker"] == t)),
        )

        # Dividends: the adjustment factor changes on the ex-dividend days by about the dividend yield, and only there
        factor = raw["close"][t] / raw["close_split_only"][t]
        change = factor.pct_change(fill_method=None).abs()
        ex_days = raw["dividends"][t] > 0
        dividend_yield = raw["dividends"][t] / raw["close_split_only"][t].shift()
        unexpected = int((change.gt(DIVIDEND_TOLERANCE) & ~ex_days).sum())
        missed = int((ex_days & ~change.ge(DIVIDEND_SHARE * dividend_yield)).sum())
        report(
            "dividends",
            t,
            unexpected > 0 or missed > 0,
            False,
            f"{int(ex_days.sum())} dividends; adjustment off the ex-dividend days: {unexpected}; dividends not adjusted: {missed}",
        )

        # Weekly prices rebuilt from the daily ones
        rebuilt_close = raw["close"][t].resample("W-FRI").last().reindex(fridays)
        rebuilt_open = raw["open"][t].resample("W-FRI").first().reindex(fridays)
        diff, same_missing = 0.0, True
        for saved, rebuilt in [(weekly["close"][t], rebuilt_close), (weekly["open"][t], rebuilt_open)]:
            saved = saved.droplevel("date_open")
            diff = max(diff, (saved / rebuilt - 1).abs().max())
            same_missing &= saved.isna().equals(rebuilt.isna())
        report(
            "weekly",
            t,
            diff > PRICE_TOLERANCE or not same_missing,
            False,
            f"largest difference from the daily prices: {diff:.1e}; same missing weeks: {same_missing}",
        )

        # Outliers: reported, kept
        split_days = set(ratios.index)
        for kind, series, limit in [("daily", returns[t], DAILY_OUTLIER), ("weekly", weekly_returns[t], WEEKLY_OUTLIER)]:
            for day, value in series[series.abs() > limit].items():
                day = day[1] if isinstance(day, tuple) else day
                outlier_rows.append(
                    {
                        "ticker": t,
                        "frequency": kind,
                        "date": day.date(),
                        "return": value,
                        "split_day": kind == "daily" and day in split_days,
                    }
                )
        n_out = sum(1 for r in outlier_rows if r["ticker"] == t)
        report(
            "outliers", t, False, n_out > 0, f"{n_out} moves above {DAILY_OUTLIER:.0%} daily or {WEEKLY_OUTLIER:.0%} weekly, kept"
        )

    return pd.DataFrame(checks), pd.DataFrame(split_rows), pd.DataFrame(outlier_rows)


def validate_macro(macro_dir, series: list[str], start: str, end: str) -> pd.DataFrame:
    """Checks of the FRED series in macro_dir, asked from start to end: one row per check and series."""
    checks = []
    for name in series:
        values = read_daily(macro_dir / f"{name}.csv")[name]
        dates = values.index
        monthly = dates.to_series().diff().median() >= pd.Timedelta(days=28)
        first, last = dates[0], dates[-1]

        late_start = first > pd.Timestamp(start) + pd.Timedelta(days=31 if monthly else 7)
        lag = (pd.Timestamp(end) - last).days
        early_end = lag > (3 * MONTHLY_LAG if monthly else MAX_DAILY_GAP)
        checks.append(
            {
                "check": "coverage",
                "ticker": name,
                "result": "FAIL" if late_start or early_end else "WARN" if monthly and lag > MONTHLY_LAG else "PASS",
                "detail": f"{'monthly' if monthly else 'daily'}, {len(values)} values from {first.date()} to {last.date()}"
                f" ({lag} days before {pd.Timestamp(end).date()})",
            }
        )

        if monthly:
            months = pd.period_range(first, last, freq="M")
            missing = [str(m) for m in months.difference(dates.to_period("M"))]
            unknown = [m for m in missing if m not in KNOWN_GAPS.get(name, [])]
            checks.append(
                {
                    "check": "gaps",
                    "ticker": name,
                    "result": "FAIL" if unknown else "WARN" if missing else "PASS",
                    "detail": f"{len(missing)} missing months"
                    + (
                        f": {', '.join(missing)} (known: not published)"
                        if missing and not unknown
                        else f": {', '.join(missing)}"
                        if missing
                        else ""
                    ),
                }
            )
        else:
            gap = dates.to_series().diff().max().days
            checks.append(
                {
                    "check": "gaps",
                    "ticker": name,
                    "result": "FAIL" if gap > MAX_DAILY_GAP else "PASS",
                    "detail": f"largest gap between two values: {gap} days",
                }
            )

        low, high = MACRO_RANGES.get(name, (-np.inf, np.inf))
        outside = int(((values < low) | (values > high)).sum())
        checks.append(
            {
                "check": "range",
                "ticker": name,
                "result": "FAIL" if outside else "PASS",
                "detail": f"min {values.min():g}, max {values.max():g}; {outside} values outside [{low:g}, {high:g}]",
            }
        )
    return pd.DataFrame(checks)


def save_report(checks: pd.DataFrame, splits: pd.DataFrame, outliers: pd.DataFrame, out_dir) -> None:
    """Save and print the checks, then stop if any failed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    checks.to_csv(out_dir / "checks.csv", index=False)
    splits.to_csv(out_dir / "splits.csv", index=False)
    outliers.to_csv(out_dir / "outliers.csv", index=False)

    with pd.option_context("display.max_colwidth", 110, "display.width", 200):
        print(checks.to_string(index=False))
        print("\nSplits: adjusted return of the day vs the return without the adjustment")
        print(splits.round(4).to_string(index=False))
        print("\nOutliers (kept, they are real prices):")
        print(outliers.round(4).to_string(index=False))
    print(f"\nSaved {out_dir.relative_to(ROOT)}/{{checks,splits,outliers}}.csv")
    failed = checks[checks["result"] == "FAIL"]
    if not failed.empty:
        raise ValueError(f"{len(failed)} checks failed: see {(out_dir / 'checks.csv').relative_to(ROOT)}")
