"""Ensemble of technical indicators whose windows, weights and threshold are chosen by the genetic algorithm.

Every indicator of week t uses only the closes up to C_t (rolling windows, never the whole sample), and is scaled to [-1, 1]
with tanh, so that the weights of different indicators are comparable:

    trend(n)      = tanh((C_t / SMA_n - 1)        / (sigma * sqrt(n)))   above / below its moving average
    momentum(n)   = tanh((C_t / C_(t-n) - 1)      / (sigma * sqrt(n)))   return of the last n weeks (long horizon)
    reversal(n)   = tanh((C_t / C_(t-n) - 1)      / (sigma * sqrt(n)))   return of the last n weeks (short horizon)
    volatility(n) = tanh(log(sigma_n / sigma_52))                        recent volatility compared with the last year

sigma is the standard deviation of the weekly returns over the last scale_window weeks: dividing by sigma * sqrt(n) turns
a return into a z-score, comparable across stocks and periods.

The score is the weighted average of the indicators, in [-1, 1]; the signal is long when it is above the threshold:

    score_t  = sum_k w_k * x_k,t / sum_k |w_k|
    signal_t = +1 if score_t > theta, 0 otherwise

The final strategy is a vote of several genomes (one per run of the genetic algorithm): long when at least k of them are long.
"""

import numpy as np
import pandas as pd

INDICATORS = ["trend", "momentum", "reversal", "volatility"]
LONG_VOLATILITY = 52  # weeks, reference of the volatility indicator


class Indicators:
    """Indicators of a table of weekly closes, cached by (name, window): the genetic algorithm asks for the same ones many times."""

    def __init__(self, close: pd.DataFrame, scale_window: int):
        self.close = close
        self.returns = close.pct_change(fill_method=None)
        self.sigma = self.returns.rolling(scale_window).std()
        self.cache = {}

    def get(self, name: str, n: int) -> pd.DataFrame:
        if (name, n) not in self.cache:
            self.cache[name, n] = getattr(self, name)(n)
        return self.cache[name, n]

    def zscore(self, move: pd.DataFrame, n: int) -> pd.DataFrame:
        return np.tanh(move / (self.sigma * np.sqrt(n)))

    def trend(self, n: int) -> pd.DataFrame:
        return self.zscore(self.close / self.close.rolling(n).mean() - 1, n)

    def momentum(self, n: int) -> pd.DataFrame:
        return self.zscore(self.close / self.close.shift(n) - 1, n)

    reversal = momentum  # same formula, short windows: a negative weight bets on the reversal of the last weeks

    def volatility(self, n: int) -> pd.DataFrame:
        return np.tanh(np.log(self.returns.rolling(n).std() / self.returns.rolling(LONG_VOLATILITY).std()))


def ready(close: pd.DataFrame, warmup: int) -> pd.DataFrame:
    """Weeks with at least warmup weekly returns: the same first week for every genome, so that all are compared on the same weeks."""
    return close.notna().cumsum() > warmup


def signals(indicators: Indicators, params: dict, warmup: int) -> pd.DataFrame:
    """Signals +1 / 0 of the genome decoded in params (windows, weights, threshold); missing before the warm-up."""
    total = sum(abs(params["weights"][name]) for name in INDICATORS)
    if total == 0:  # no indicator counts: always flat
        flat = pd.DataFrame(0, index=indicators.close.index, columns=indicators.close.columns)
        return flat.where(ready(indicators.close, warmup))
    score = sum(params["weights"][name] * indicators.get(name, params["windows"][name]) for name in INDICATORS) / total
    return (score > params["threshold"]).astype(int).where(ready(indicators.close, warmup))


def vote(member_signals: list[pd.DataFrame], k: int) -> pd.DataFrame:
    """Long when at least k members are long, flat otherwise; missing where any member is missing."""
    stacked = sum(member_signals)
    return (stacked >= k).astype(int).where(stacked.notna())
