"""Long/short strategy on the semiconductor universe: the final strategy (docs/experiment_log.md, 12_optimize_longshort.py).

Each week, after the Friday close:
    universe   the companies in the SOX index that week (in_index.csv), with a close and every feature
    z-scores   each feature winsorized at 1%/99% and standardized across the universe of that week
    score      weighted average of the z-scores, weights in [-1, 1] (the sign says whether a high value is good or bad)
    signal     +1 for the k highest scores, -1 for the k lowest (k = quantile x companies, rounded down), 0 otherwise
    weights    half of the capital on the longs, half on the shorts, equally within each side: dollar neutral, gross 100%
The return of week t is earned from the open of week t+1 to the open of week t+2 (as the pilot), minus 10 bps on the
capital traded and the yearly borrowing fee on the short side, paid week by week.
"""

import numpy as np
import pandas as pd

from src.features import cross_section

PERIODS_PER_YEAR = 52


class Universe:
    """z-scores of the features within the universe of each week, computed once and reused by every genome."""

    def __init__(self, raw: dict[str, pd.DataFrame], members: pd.DataFrame, winsorize: float):
        eligible = members.astype(bool)
        for table in raw.values():
            eligible &= table.notna()
        self.eligible = eligible
        self.raw = raw
        self.z = {name: cross_section(table.where(eligible), winsorize) for name, table in raw.items()}
        self.size = eligible.sum(axis=1)

    def score(self, weights: dict[str, float]) -> pd.DataFrame:
        total = sum(abs(w) for w in weights.values())
        if total == 0:
            return pd.DataFrame(np.nan, index=self.eligible.index, columns=self.eligible.columns)
        return sum(w * self.z[name] for name, w in weights.items()) / total


def signals(score: pd.DataFrame, quantile: float, min_companies: int) -> pd.DataFrame:
    """+1 for the k highest scores, -1 for the k lowest, k = quantile x companies (rounded down), 0 otherwise;
    missing outside the universe; 0 in weeks with too few companies."""
    rank = score.rank(axis=1, method="first")
    n = score.notna().sum(axis=1)
    k = np.floor(quantile * n)
    s = rank.gt(n - k, axis=0).astype(float) - rank.le(k, axis=0).astype(float)
    s = s.where(score.notna())
    enough = score.notna().sum(axis=1) >= min_companies
    return s.mul(enough.astype(float), axis=0)  # weeks with too few companies: 0 (missing stays missing)


def weights(s: pd.DataFrame, beta: pd.DataFrame | None = None) -> pd.DataFrame:
    """Gross exposure 100%, equal weights within each side.

    dollar neutral (beta None): half of the capital on the longs, half on the shorts.
    beta neutral: the sides are sized so that the beta of the portfolio is zero, with the 52-week beta of each company
    known at the Friday close: longs a, shorts b, a x (average beta of the longs) = b x (average beta of the shorts),
    a + b = 1. Half and half when a side has no positive average beta.
    """
    longs, shorts = (s == 1), (s == -1)
    n_long, n_short = longs.sum(axis=1).replace(0, np.nan), shorts.sum(axis=1).replace(0, np.nan)
    a = pd.Series(0.5, index=s.index)
    if beta is not None:
        beta_long = beta.where(longs).sum(axis=1) / n_long
        beta_short = beta.where(shorts).sum(axis=1) / n_short
        a = (beta_short / (beta_long + beta_short)).where((beta_long > 0) & (beta_short > 0), 0.5)
    w = longs.div(n_long, axis=0).mul(a, axis=0) - shorts.div(n_short, axis=0).mul(1 - a, axis=0)
    return w.fillna(0.0)


def returns(w: pd.DataFrame, forward: pd.DataFrame, cost_bps: float, borrow_bps_year: float) -> pd.Series:
    """Weekly return net of trading costs (on the change of weights, from flat) and of the borrowing fee on the shorts.

    A held company without a forward return (a suspended stock) earns 0 that week.
    """
    gross = (w * forward.reindex_like(w)).sum(axis=1, min_count=1).fillna(0.0)
    traded = w.diff().fillna(w).abs().sum(axis=1)
    short_side = w.clip(upper=0).abs().sum(axis=1)
    return gross - cost_bps / 10_000 * traded - borrow_bps_year / 10_000 / PERIODS_PER_YEAR * short_side


def decode(genome: list[float], features: list[str]) -> dict[str, float]:
    """Genes in [0, 1] -> weights in [-1, 1], one per feature."""
    return {name: round(2 * gene - 1, 4) for name, gene in zip(features, genome)}


def average(members: list[dict[str, float]]) -> dict[str, float]:
    """Average of the members, each normalized by the sum of its absolute weights (the scale of a score does not matter)."""
    names = members[0].keys()
    norm = [{k: v / (sum(abs(x) for x in m.values()) or 1) for k, v in m.items()} for m in members]
    return {k: round(float(np.mean([m[k] for m in norm])), 4) for k in names}
