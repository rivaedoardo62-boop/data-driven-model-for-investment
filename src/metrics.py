"""Metrics of weekly returns and signals (definitions in docs/metrics.md)."""

import numpy as np
import pandas as pd

PERIODS_PER_YEAR = 52


def ratio(numerator: float, denominator: float) -> float:
    """numerator / denominator, NaN if the denominator is zero (e.g. a strategy always flat)."""
    return numerator / denominator if denominator != 0 else np.nan


def annualized_return(r: pd.Series) -> float:
    return (1 + r).prod() ** (PERIODS_PER_YEAR / len(r)) - 1


def annualized_volatility(r: pd.Series) -> float:
    return r.std() * np.sqrt(PERIODS_PER_YEAR)


def sharpe_ratio(r: pd.Series, risk_free: float) -> float:
    return ratio(annualized_return(r) - risk_free, annualized_volatility(r))


def max_drawdown(r: pd.Series) -> float:
    equity = (1 + r).cumprod()
    peak = equity.cummax().clip(lower=1)  # the starting capital is the first peak
    return (equity / peak - 1).min()


def performance(r: pd.Series, risk_free: float) -> dict:
    downside = np.sqrt((r.clip(upper=0) ** 2).mean()) * np.sqrt(PERIODS_PER_YEAR)
    return {
        "cumulative_return": (1 + r).prod() - 1,
        "annualized_return": annualized_return(r),
        "annualized_volatility": annualized_volatility(r),
        "sharpe_ratio": sharpe_ratio(r, risk_free),
        "sortino_ratio": ratio(annualized_return(r) - risk_free, downside),
        "max_drawdown": max_drawdown(r),
        "calmar_ratio": ratio(annualized_return(r), abs(max_drawdown(r))),
    }


def return_stats(r: pd.Series) -> dict:
    return {
        "hit_rate": (r > 0).mean(),
        "avg_gain": r[r > 0].mean(),
        "avg_loss": r[r < 0].mean(),
        "profit_factor": ratio(r[r > 0].sum(), abs(r[r < 0].sum())),
        "best": r.max(),
        "worst": r.min(),
        "skew": r.skew() if r.std() > 0 else np.nan,
        "kurtosis": r.kurt() if r.std() > 0 else np.nan,
    }


def holding_periods(s: pd.Series) -> pd.Series:
    """Lengths of the runs of the same non-zero signal."""
    run = (s != s.shift()).cumsum()
    runs = s.groupby(run).agg(["first", "size"])
    return runs.loc[runs["first"] != 0, "size"]


def behaviour(signals: pd.DataFrame) -> dict:
    trades = signals.diff().fillna(signals)  # before the first week every stock is flat
    holdings = pd.concat([holding_periods(signals[ticker]) for ticker in signals.columns])
    return {
        "net_exposure": signals.mean(axis=1).mean(),
        "gross_exposure": signals.abs().mean(axis=1).mean(),
        "long": (signals == 1).mean().mean(),
        "flat": (signals == 0).mean().mean(),
        "short": (signals == -1).mean().mean(),
        "turnover_per_year": trades.abs().mean(axis=1).sum() * PERIODS_PER_YEAR / len(signals),
        "avg_holding": holdings.mean(),
    }


def market(r: pd.Series, m: pd.Series, risk_free: float) -> dict:
    beta = ratio(r.cov(m), m.var())
    tracking_error = (r - m).std() * np.sqrt(PERIODS_PER_YEAR)
    return {
        "beta": beta,
        "correlation": ratio(r.cov(m), r.std() * m.std()),
        "alpha": (r.mean() - beta * m.mean()) * PERIODS_PER_YEAR - risk_free * (1 - beta),  # Jensen
        "tracking_error": tracking_error,
        "information_ratio": ratio((r.mean() - m.mean()) * PERIODS_PER_YEAR, tracking_error),
        "down_market": r[m < 0].mean(),
        "up_market": r[m > 0].mean(),
        "sharpe_vs_market": sharpe_ratio(r, risk_free) - sharpe_ratio(m, risk_free),
    }
