"""Bloomberg prices of the semiconductor universe: one series per company, checks and weekly tables (10_clean_bloomberg.py).

Bloomberg gives a stock once per exchange line ("MU UN" on NYSE, "MU UW" on Nasdaq): the same company, with the prices
of each exchange. On each day the line with the largest volume is the listing exchange (on the others the volume is 14 to
42 times smaller), so merging by volume follows the moves between exchanges (Micron to Nasdaq on 2009-12-30, Texas
Instruments 2012-01-03, AMD 2015-01-02, Teradyne 2018-11-27, Wolfspeed to NYSE 2021-10-04, Coherent 2023-02-23).
"""

import numpy as np
import pandas as pd

from src.data import WEEK_COLUMNS

FIELDS = {
    "PX_OPEN": "open",
    "PX_HIGH": "high",
    "PX_LOW": "low",
    "PX_LAST": "close",
    "PX_VOLUME": "volume",
    "CUR_MKT_CAP": "market_cap",  # millions
    "TOT_RETURN_INDEX_GROSS_DVDS": "total_return",  # index of Bloomberg, dividends reinvested
}
PRICES = ["open", "high", "low", "close"]
PRICE_TOLERANCE = 1e-6  # relative
TOTAL_RETURN_DAY = 0.005  # a daily gap above 0.5% between price and total return is reported
TOTAL_RETURN_YEAR = 0.005  # an average gap above 0.5% per year means the prices are not adjusted for dividends: FAIL
STALE_DAYS = 5  # identical closes in a row
DAILY_OUTLIER, WEEKLY_OUTLIER = 0.20, 0.25
KNOWN_TOTAL_RETURN_ERRORS = {  # days when the total return index of Bloomberg is wrong and the adjusted price is right
    # synthetic share buyback: 9.18 euro repaid per share with 77 new shares for 100 old, neutral for the shareholder;
    # the total return index counts the repayment as income (+25% in a day against +5% for the price)
    "ASML": ["2012-11-29"],
}


def load_raw(path) -> pd.DataFrame:
    """Prices as downloaded: one row per exchange line and day."""
    raw = pd.read_parquet(path).rename(columns=FIELDS)
    parts = raw["ticker"].str.split()
    raw["company"], raw["line"] = parts.str[0], parts.str[1]
    raw["date"] = pd.to_datetime(raw["date"])
    return raw


def merge_lines(raw: pd.DataFrame) -> pd.DataFrame:
    """One row per company and day with a price: the exchange line with the largest volume (ties: the first line)."""
    traded = raw.dropna(subset=["close"]).assign(_volume=lambda x: x["volume"].fillna(-1))
    ranked = traded.sort_values(["company", "date", "_volume", "line"], ascending=[True, True, False, True], kind="stable")
    daily = ranked.drop_duplicates(["company", "date"]).drop(columns="_volume")
    return daily.set_index(["company", "date"]).sort_index()[["line", "ticker", *FIELDS.values()]]


def line_switches(daily: pd.DataFrame) -> pd.DataFrame:
    """Days when a company changes exchange line, with the line before and after."""
    line = daily["line"].reset_index()
    before = line.groupby("company")["line"].shift()
    changed = line[before.notna() & (line["line"] != before)]
    return changed.assign(previous=before[changed.index]).rename(columns={"line": "new"})[["company", "date", "previous", "new"]]


def check_daily(daily: pd.DataFrame, calendar: pd.DatetimeIndex, end: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Checks of each company (FAIL stops the pipeline, WARN is reported and explained) and the extreme moves."""
    checks, outliers = [], []

    def report(check: str, company: str, failed: bool, warned: bool, detail: str) -> None:
        result = "FAIL" if failed else "WARN" if warned else "PASS"
        checks.append({"check": check, "company": company, "result": result, "detail": detail})

    report("calendar", "all", not daily.index.is_unique, False, f"{daily.index.get_level_values('company').nunique()} companies")
    for company, x in daily.groupby(level="company"):
        x = x.droplevel("company")
        prices = x[PRICES]
        report("positive", company, bool((prices <= 0).any().any()), False, f"min price {prices.min().min():.4f}")

        tol = PRICE_TOLERANCE * x["high"]
        bad = int(
            ((x["low"] > x[["open", "close"]].min(axis=1) + tol) | (x["high"] < x[["open", "close"]].max(axis=1) - tol)).sum()
        )
        report("ohlc", company, False, bad > 0, f"{bad} days with low above or high below open/close")

        span = calendar[(calendar >= x.index[0]) & (calendar <= min(x.index[-1], end))]
        missing = span.difference(x.index)
        absent = pd.Series(span.isin(missing), index=span)
        longest = int(absent.groupby((absent != absent.shift()).cumsum()).sum().max()) if len(missing) else 0
        report(
            "gaps", company, False, len(missing) > 0,
            f"first price {x.index[0].date()}, last {x.index[-1].date()}; {len(missing)} trading days without a price"
            + (f" (longest run {longest} days, from {missing[0].date()})" if len(missing) else ""),
        )  # fmt: skip

        same = x["close"].diff().eq(0)
        stale = int(same.groupby((~same).cumsum()).sum().max()) + 1
        report("stale", company, False, stale >= STALE_DAYS, f"longest run of identical closes: {stale} days")

        zero = int((x["volume"] == 0).sum())
        report("volume", company, False, zero > 0, f"{zero} days with zero volume")

        price_return = x["close"].pct_change(fill_method=None)
        # the total return index has a different base on each exchange line: not comparable on the day of a switch
        comparable = (x["line"] == x["line"].shift()) & ~x.index.isin(pd.to_datetime(KNOWN_TOTAL_RETURN_ERRORS.get(company, [])))
        total = x["total_return"].pct_change(fill_method=None).where(comparable)
        price_return_cmp = price_return.where(comparable)
        gap = (total - price_return_cmp).dropna()
        years = max((x.index[-1] - x.index[0]).days / 365.25, 1 / 365.25)
        yearly_gap = (1 + total.fillna(0)).prod() ** (1 / years) - (1 + price_return_cmp.fillna(0)).prod() ** (1 / years)
        days_off = gap[gap.abs() > TOTAL_RETURN_DAY]
        known = KNOWN_TOTAL_RETURN_ERRORS.get(company, [])
        report(
            "dividends", company, abs(yearly_gap) > TOTAL_RETURN_YEAR, len(days_off) > 0 or len(known) > 0,
            f"total return minus price return {yearly_gap:+.2%} per year; {len(days_off)} days with a gap above "
            f"{TOTAL_RETURN_DAY:.1%}"
            + (f": {', '.join(str(d.date()) for d in days_off.index[:5])}" if len(days_off) else "")
            + (f"; known error of the total return index on {', '.join(known)}, excluded" if known else ""),
        )  # fmt: skip

        weekly = x["close"].resample("W-FRI").last().pct_change(fill_method=None)
        for kind, series, limit in [("daily", price_return, DAILY_OUTLIER), ("weekly", weekly, WEEKLY_OUTLIER)]:
            for day, value in series[series.abs() > limit].items():
                outliers.append({"company": company, "frequency": kind, "date": day.date(), "return": value})
        n_out = sum(1 for r in outliers if r["company"] == company)
        report(
            "outliers",
            company,
            False,
            n_out > 0,
            f"{n_out} moves above {DAILY_OUTLIER:.0%} daily or {WEEKLY_OUTLIER:.0%} weekly, kept",
        )
    return pd.DataFrame(checks), pd.DataFrame(outliers)


def weekly_tables(daily: pd.DataFrame, end: pd.Timestamp, exited_after: int) -> dict[str, pd.DataFrame]:
    """Weekly tables (rows: weeks labeled (Monday, Friday) as in data/prices; columns: companies).

    open, close            first open and last close of the week
    market_cap             last market value of the week, millions
    traded_value           average daily close x volume of the week, millions
    overnight, daytime     sums of the daily log returns from the previous close to the open (overnight) and from the
                           open to the close (daytime), by the week of the day: at the Friday close of week t the
                           overnight returns up to that Friday's open are known; the weekend gap belongs to week t+1
    A company whose prices stop more than exited_after days before end has left the market (acquired, merged, bankrupt):
    its last close becomes the open of the following week, so that a position held in its last week is sold at that price
    (without it the last move, e.g. the fall before a bankruptcy, would be lost).
    """
    wide = daily.drop(columns=["line", "ticker"]).unstack("company")
    wide = wide.loc[:end]
    fridays = pd.date_range(wide.index[0] - pd.Timedelta(days=wide.index[0].weekday()), end, freq="W-FRI")
    resampled = wide.resample("W-FRI")
    tables = {
        "open": resampled.first()["open"],
        "close": resampled.last()["close"],
        "market_cap": resampled.last()["market_cap"],
        "traded_value": (wide["close"] * wide["volume"] / 1e6).resample("W-FRI").mean(),
        # from the last available close of the company (a day without trades does not break the chain)
        "overnight": np.log(wide["open"] / wide["close"].ffill().shift(1)).resample("W-FRI").sum(min_count=1),
        "daytime": np.log(wide["close"] / wide["open"]).resample("W-FRI").sum(min_count=1),
    }
    last_day = wide["close"].apply(lambda s: s.last_valid_index())
    for company, day in last_day.items():
        exit_week = day + pd.Timedelta(days=(4 - day.weekday()) % 7 + 7)  # Friday of the week after the last price
        if (end - day).days > exited_after and exit_week in tables["open"].index:
            tables["open"].loc[exit_week, company] = wide["close"][company].loc[day]
    weeks = pd.MultiIndex.from_arrays([fridays - pd.Timedelta(days=4), fridays], names=WEEK_COLUMNS)
    for name, table in tables.items():
        table = table.reindex(fridays)
        table.index = weeks
        table.columns.name = None
        tables[name] = table
    tables["last_day"] = last_day.rename("last_day").to_frame()
    return tables


def summary(daily: pd.DataFrame, end: pd.Timestamp, exited_after: int) -> pd.DataFrame:
    """One row per company: exchange lines, first and last price, whether it left the market, size and behaviour."""
    rows = []
    for company, x in daily.groupby(level="company"):
        x = x.droplevel("company")
        r = x["close"].pct_change(fill_method=None)
        equity = (1 + r.fillna(0)).cumprod()
        years = (x.index[-1] - x.index[0]).days / 365.25
        rows.append(
            {
                "company": company,
                "lines": " ".join(sorted(x["line"].unique())),
                "first": x.index[0].date(),
                "last": x.index[-1].date(),
                "exited": (end - x.index[-1]).days > exited_after,
                "days": len(x),
                "last_close": round(x["close"].iloc[-1], 2),
                "market_cap_bn": round(x["market_cap"].dropna().iloc[-1] / 1000, 1) if x["market_cap"].notna().any() else np.nan,
                "annual_return": equity.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan,
                "annual_volatility": r.std() * np.sqrt(252),
                "max_drawdown": (equity / equity.cummax() - 1).min(),
            }
        )
    return pd.DataFrame(rows).set_index("company")


def index_membership(membership: pd.DataFrame, weeks: pd.MultiIndex, companies: pd.Index) -> pd.DataFrame:
    """True where a company was in the index in a week: the last composition published before that Friday.

    sox_membership.csv holds the composition at the end of every quarter (09_download_bloomberg.py): a company that entered
    during a quarter counts from the next quarter end (conservative), one that left counts until it disappears from one.
    """
    m = membership.assign(company=membership["ticker"].str.split().str[0], date=pd.to_datetime(membership["date"]))
    snapshots = m.groupby("date")["company"].apply(set).sort_index()
    out = pd.DataFrame(False, index=weeks, columns=companies)
    for i, friday in enumerate(weeks.get_level_values("date_close")):
        known = snapshots[snapshots.index <= friday]
        if len(known):
            out.iloc[i] = companies.isin(known.iloc[-1])
    return out
