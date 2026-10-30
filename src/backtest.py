"""Returns earned by weekly signals, shared by the optimization and the evaluation (see docs/metrics.md)."""

import pandas as pd

TYPES = ["close_to_close", "open_to_open"]


def forward_returns(opens: pd.DataFrame, close: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Return earned by the signal of each week."""
    if kind == "close_to_close":
        return close.shift(-1) / close - 1  # C(t+1) / C(t) - 1
    return opens.shift(-2) / opens.shift(-1) - 1  # O(t+2) / O(t+1) - 1


def execution_dates(weeks: pd.MultiIndex, kind: str) -> tuple[pd.Series, pd.Series]:
    """Days when the position of each week is taken and when its return is realized."""
    date_open = pd.Series(weeks.get_level_values("date_open"), index=weeks)
    date_close = pd.Series(weeks.get_level_values("date_close"), index=weeks)
    if kind == "close_to_close":
        return date_close, date_close.shift(-1)  # close of week t, close of week t+1
    return date_open.shift(-1), date_open.shift(-2)  # open of week t+1, open of week t+2


def strategy_returns(signals: pd.DataFrame, forward: pd.DataFrame, cost_bps: float) -> pd.Series:
    """Equal weight return of the signals, net of a cost of cost_bps on the capital traded at each change of signal.

    Every stock is flat before the first week, so the first week pays the cost of entering.
    """
    gross = (signals * forward).mean(axis=1)
    traded = signals.diff().fillna(signals).abs().mean(axis=1)  # same turnover as metrics.behaviour
    return gross - cost_bps / 10_000 * traded
