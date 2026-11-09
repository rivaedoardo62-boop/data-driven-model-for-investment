"""Descriptive features of each company and week (10_clean_bloomberg.py), for the exploratory analysis.

Every feature of week t uses only the prices up to the Friday close of week t (rolling windows, never the whole sample).
The strategy does not use them: it keeps its own four indicators (src/ensemble.py). Testing whether they predict returns
would be a new strategy, to be designed on the training period only.

    return_4w          return of the last 4 weeks
    momentum_52_4      return from 52 to 4 weeks ago (the last month left out, as in the momentum literature)
    volatility_26w     annualized volatility of the weekly returns of the last 26 weeks
    volatility_ratio   log of the volatility of the last 10 weeks over that of the last 52: positive when it jumps
    trend_26w          close over its 26-week moving average, minus 1
    from_high_52w      close over the highest close of the last 52 weeks, minus 1 (0 at a new high)
    beta_52w           beta of the weekly returns against the equal weight of the universe, last 52 weeks
    log_market_cap     log of the market value (millions)
    log_traded_value   log of the average daily traded value of the last 4 weeks (millions)
    overnight_momentum_52_4, daytime_momentum_52_4
                       the momentum 52-4 split into its overnight part (sum of the log returns from each close to the next
                       open) and its daytime part (open to close), as in Lou, Polk and Skouras (2019), "A tug of war:
                       overnight versus intraday expected returns"
    overnight_return_4w, daytime_return_4w
                       the same split of the return of the last 4 weeks

Pre-processing, week by week across companies (so that no week uses the others): each feature is cut at its 1% and 99%
quantiles (winsorized) and turned into a z-score (`<feature>_z`), comparable across weeks and features.
"""

import numpy as np
import pandas as pd

MIN_COMPANIES = 5  # z-scores need at least this many companies in the week


def compute(
    close: pd.DataFrame,
    market_cap: pd.DataFrame,
    traded_value: pd.DataFrame,
    overnight: pd.DataFrame,
    daytime: pd.DataFrame,
    cfg: dict,
) -> dict[str, pd.DataFrame]:
    """Raw features, one table (weeks x companies) each. overnight and daytime: weekly sums of daily log returns."""
    r = close.pct_change(fill_method=None)
    market = r.mean(axis=1)  # equal weight of the companies with a return in the week
    far, near = cfg["momentum"]
    short, long = cfg["volatility_ratio"]
    n = cfg["beta"]
    out = {
        "return_4w": close / close.shift(cfg["short_return"]) - 1,
        "momentum_52_4": close.shift(near) / close.shift(far) - 1,
        "volatility_26w": r.rolling(cfg["volatility"]).std() * np.sqrt(52),
        "volatility_ratio": np.log(r.rolling(short).std() / r.rolling(long).std()),
        "trend_26w": close / close.rolling(cfg["trend"]).mean() - 1,
        "from_high_52w": close / close.rolling(cfg["high"]).max() - 1,
        "beta_52w": r.rolling(n).cov(market).div(market.rolling(n).var(), axis=0),
        "log_market_cap": np.log(market_cap.where(market_cap > 0)),
        "log_traded_value": np.log(traded_value.rolling(cfg["liquidity"]).mean().where(lambda x: x > 0)),
        "overnight_momentum_52_4": overnight.shift(near).rolling(far - near).sum(),
        "daytime_momentum_52_4": daytime.shift(near).rolling(far - near).sum(),
        "overnight_return_4w": overnight.rolling(cfg["short_return"]).sum(),
        "daytime_return_4w": daytime.rolling(cfg["short_return"]).sum(),
    }
    return {name: table.replace([np.inf, -np.inf], np.nan) for name, table in out.items()}


def cross_section(table: pd.DataFrame, q: float) -> pd.DataFrame:
    """Winsorize at the q and 1-q quantiles of each week, then z-score within the week."""
    low, high = table.quantile(q, axis=1), table.quantile(1 - q, axis=1)
    clipped = table.clip(lower=low, upper=high, axis=0)
    z = clipped.sub(clipped.mean(axis=1), axis=0).div(clipped.std(axis=1), axis=0)
    return z.where(clipped.count(axis=1) >= MIN_COMPANIES, axis=0)


def panel(features: dict[str, pd.DataFrame], q: float) -> pd.DataFrame:
    """Long table: one row per week and company with a close, raw features and their z-scores."""
    columns = {}
    for name, table in features.items():
        columns[name] = table.stack()  # pandas 3 keeps the missing values
        columns[f"{name}_z"] = cross_section(table, q).stack()
    out = pd.DataFrame(columns)
    out.index.names = ["date_open", "date_close", "company"]
    return out.dropna(how="all")
