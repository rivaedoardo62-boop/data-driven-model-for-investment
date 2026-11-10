"""Evaluate the frozen long/short strategy on semiconductors: training, validation and Out-of-Sample (docs/experiment_log.md).

The weights come from 12_optimize_longshort.py and are never changed here. Run it once on the point-in-time universe:
the Out-of-Sample period is opened by this script. --training-only stops at the end of the training period (to test the
script without looking at the validation or the Out-of-Sample).

Series (returns of week t earned from the open of week t+1 to the open of week t+2):
    Long/short          the strategy, net of 10 bps per trade and of the borrowing fee; dollar neutral, so its return is
                        already in excess of cash
    Random search       the average of the random-search members, the control of the optimization (never chosen)
    Equal weight        every company of the universe, long, rebalanced every week, no costs
    SPY                 the market
Sharpe ratios are computed on returns in excess of the 3-month T-bill (DTB3) for the long-only series, as they are for the
long/short (test 5 of the experiment log); the constant 2% of the pilot is reported too.

Input:  data/bloomberg/clean/, data/bloomberg/longshort/{best.yaml,members.csv}, data/prices/, data/extra/macro/
Output: data/bloomberg/longshort/evaluation/{returns,performance,market,behaviour,bootstrap,regimes}.csv and *.png
"""

import argparse

import matplotlib
import numpy as np
import pandas as pd
import yaml

from src import longshort, metrics
from src.backtest import execution_dates, forward_returns
from src.config import ROOT, check_used, load_config
from src.data import read_weekly
from src.style import BLUE, DARK_GRAY, LIGHT_GRAY, ORANGE, RED, SHADES, plain_log_axis, plt, save

PERIODS = ["Training", "Validation", "Out-of-Sample"]
COLORS = {"Long/short": BLUE, "Random search": ORANGE, "Equal weight": DARK_GRAY, "SPY": LIGHT_GRAY}
BLOCK, DRAWS = 8, 5000  # weeks per block and draws of the bootstrap


def load_macro(macro_dir, fridays: pd.DatetimeIndex) -> dict[str, pd.Series]:
    """Each FRED series at the Friday close (last value published by then), and the inflation over 12 months."""

    def read(name: str) -> pd.Series:
        return pd.read_csv(macro_dir / f"{name}.csv", index_col=0, parse_dates=True)[name]

    def at(series: pd.Series) -> pd.Series:
        return series.reindex(series.index.union(fridays)).ffill().reindex(fridays)

    cpi = read("CPIAUCSL").asfreq("MS")
    out = {name: at(read(name)) for name in ["VIXCLS", "T10Y3M", "DFF", "BAA10Y", "DTB3"]}
    out["USREC"] = read("USREC").reindex(fridays.to_period("M").to_timestamp()).set_axis(fridays)
    out["inflation"] = at(cpi / cpi.shift(12) - 1)
    return out


def regimes(macro: dict[str, pd.Series], weeks: pd.DatetimeIndex) -> dict[str, pd.Series]:
    """The market regimes written in the experiment log (test 4), True in the weeks of the regime."""
    baa = macro["BAA10Y"].reindex(weeks)
    return {
        "Stress (VIX above 25)": macro["VIXCLS"] > 25,
        "Inverted curve (10y minus 3m below 0)": macro["T10Y3M"] < 0,
        "Recession (NBER)": macro["USREC"] == 1,
        "Rate hikes (Fed funds up 0.25 in 26 weeks)": macro["DFF"] - macro["DFF"].shift(26) > 0.25,
        "Credit stress (Baa spread above median)": macro["BAA10Y"] > baa.median(),
        "High inflation (CPI above 3% in 12 months)": macro["inflation"] > 0.03,
    }


def bootstrap_sharpe(r: pd.Series, seed: int = 0) -> dict:
    """Circular block bootstrap of the Sharpe ratio (risk-free 0: r is already an excess return)."""
    rng, n, x = np.random.default_rng(seed), len(r), r.to_numpy()
    draws = []
    for _ in range(DRAWS):
        starts = rng.integers(0, n, size=n // BLOCK + 1)
        idx = (starts[:, None] + np.arange(BLOCK)).ravel()[:n] % n
        s = x[idx]
        draws.append(s.mean() / s.std(ddof=1) * np.sqrt(metrics.PERIODS_PER_YEAR))
    d = np.array(draws)
    point = x.mean() / x.std(ddof=1) * np.sqrt(metrics.PERIODS_PER_YEAR)
    return {
        "sharpe (mean/std)": point,
        "ci_2.5%": np.percentile(d, 2.5),
        "ci_97.5%": np.percentile(d, 97.5),
        "share_draws_at_or_below_0": (d <= 0).mean(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--training-only", action="store_true", help="stop at the end of the training period")
    a = ap.parse_args()

    cfg = load_config()
    ga, ls, bb, m = cfg["ga"], cfg["longshort"], cfg["bloomberg"], cfg["metrics"]
    kind, cost_bps = m["type"], m["cost_bps"]
    train_end, is_end = pd.Timestamp(ga["train_end"]), pd.Timestamp(m["is_end"])
    clean, ls_dir = ROOT / bb["dir"] / "clean", ROOT / bb["dir"] / "longshort"
    out = ls_dir / ("evaluation_training" if a.training_only else "evaluation")
    check_used(
        {"ga": ga, "longshort": ls, "winsorize": bb["winsorize"], "cost_bps": cost_bps, "type": kind},
        ls_dir / "config.yaml",
        "12_optimize_longshort.py",
    )
    with open(ls_dir / "best.yaml") as f:
        best = yaml.safe_load(f)
    if not best["point_in_time_universe"]:
        print("PROVISIONAL: the weights were chosen on the universe without the point-in-time composition")

    opens, close = read_weekly(clean / "open.csv"), read_weekly(clean / "close.csv")
    panel = pd.read_parquet(clean / "features.parquet")
    raw = {k: panel[k].unstack("company").reindex(index=close.index, columns=close.columns) for k in ls["features"]}
    if (clean / "in_index.csv").exists():
        members = read_weekly(clean / "in_index.csv").reindex(index=close.index, columns=close.columns).fillna(False).astype(bool)
    else:
        members = close.notna()
    universe = longshort.Universe(raw, members, bb["winsorize"])
    forward = forward_returns(opens, close, kind)
    _, realized = execution_dates(close.index, kind)

    weeks = (universe.size >= ls["min_companies"]) & forward.notna().any(axis=1) & realized.notna()
    if a.training_only:
        weeks &= realized <= train_end
    weeks = weeks[weeks].index
    period = pd.Series(np.select([realized[weeks] <= train_end, realized[weeks] <= is_end], PERIODS[:2], PERIODS[2]), index=weeks)

    def strategy(weights: dict) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
        s = longshort.signals(universe.score(weights), ls["quantile"], ls["min_companies"])
        w = longshort.weights(s, universe.raw["beta_52w"] if ls["sizing"] == "beta" else None).loc[weeks]
        return longshort.returns(w, forward.loc[weeks], cost_bps, ls["borrow_bps_year"]), s.loc[weeks], w

    members_table = pd.read_csv(ls_dir / "members.csv")
    random_avg = members_table[(members_table["method"] == "random search") & (members_table["member"] == "average")].iloc[0]
    random_weights = {k: float(random_avg[f"w_{k}"]) for k in ls["features"]}
    r_ls, s_ls, w_ls = strategy(best["weights"])
    r_random, _, _ = strategy(random_weights)
    spy = forward_returns(read_weekly(ROOT / "data/prices/open.csv"), read_weekly(ROOT / "data/prices/close.csv"), kind)["SPY"]
    fridays = weeks.get_level_values("date_close")
    macro = load_macro(ROOT / cfg["data"]["data_dir"] / "extra" / "macro", fridays)
    tbill = (macro["DTB3"] / 100 / metrics.PERIODS_PER_YEAR).set_axis(weeks)  # weekly T-bill, known at the Friday close
    returns = pd.DataFrame({
        "Long/short": r_ls, "Random search": r_random,
        "Equal weight": forward.loc[weeks].where(universe.eligible.loc[weeks]).mean(axis=1), "SPY": spy.reindex(weeks),
    })  # fmt: skip
    excess = returns.copy()
    excess[["Equal weight", "SPY"]] = excess[["Equal weight", "SPY"]].sub(tbill, axis=0)

    tables = {"performance": {}, "market": {}, "behaviour": {}}
    for p in [x for x in PERIODS if (period == x).any()]:
        in_p = period == p
        for name in returns:
            perf = metrics.performance(excess.loc[in_p, name], 0.0)
            perf["sharpe_ratio_rf_2%"] = metrics.sharpe_ratio(
                returns.loc[in_p, name], 0.0 if name in ["Long/short", "Random search"] else 0.02
            )
            tables["performance"][p, name] = perf | metrics.return_stats(returns.loc[in_p, name])
            if name != "SPY":
                tables["market"][p, name] = metrics.market(excess.loc[in_p, name], excess.loc[in_p, "SPY"], 0.0)
        s, w = s_ls[in_p], w_ls[in_p]
        holdings = pd.concat([metrics.holding_periods(s[c].fillna(0)) for c in s.columns])
        tables["behaviour"][p, "Long/short"] = {
            "companies_per_week": s.notna().sum(axis=1).mean(),
            "longs_per_week": (s == 1).sum(axis=1).mean(),
            "shorts_per_week": (s == -1).sum(axis=1).mean(),
            "net_exposure": w.sum(axis=1).mean(),
            "gross_exposure": w.abs().sum(axis=1).mean(),
            "turnover_per_year": w.diff().fillna(w).abs().sum(axis=1).mean() * metrics.PERIODS_PER_YEAR,
            "avg_holding_weeks": holdings.mean(),
        }
    boot = {p: bootstrap_sharpe(excess.loc[period == p, "Long/short"]) for p in PERIODS if (period == p).any()}
    regime_rows = {}
    for p in [x for x in PERIODS if (period == x).any()]:
        in_p = (period == p).to_numpy()
        for name, flag in regimes(macro, fridays).items():
            f = flag.to_numpy() & in_p
            for series in ["Long/short", "Equal weight"]:
                r = excess[series][f]
                regime_rows[p, name, series] = {"weeks": int(f.sum()), "annual_return": r.mean() * 52 if len(r) else np.nan,
                                                "annual_volatility": r.std() * np.sqrt(52) if len(r) > 1 else np.nan,
                                                "sharpe": metrics.ratio(r.mean() * 52, r.std() * np.sqrt(52)) if len(r) > 1 else np.nan}  # fmt: skip

    out.mkdir(parents=True, exist_ok=True)
    pd.concat([period.rename("period"), returns], axis=1).to_csv(out / "returns.csv")
    for name, rows in tables.items():
        pd.DataFrame(rows).T.rename_axis(["period", "series"]).to_csv(out / f"{name}.csv")
    pd.DataFrame(boot).T.to_csv(out / "bootstrap.csv")
    pd.DataFrame(regime_rows).T.rename_axis(["period", "regime", "series"]).to_csv(out / "regimes.csv")
    figures(returns, period, realized.loc[weeks], out)

    with pd.option_context("display.width", 220, "display.max_columns", 20):
        perf = pd.DataFrame(tables["performance"]).T[
            ["annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown", "profit_factor"]
        ]
        print("Performance (Sharpe on returns in excess of the T-bill; the long/short is already an excess return):")
        print(perf.round(3).to_string())
        print("\nAgainst SPY:")
        print(pd.DataFrame(tables["market"]).T[["beta", "correlation", "alpha", "down_market", "up_market"]].round(4).to_string())
        print("\nBootstrap of the Sharpe ratio of the long/short:")
        print(pd.DataFrame(boot).T.round(3).to_string())
    print(f"\nSaved {out.relative_to(ROOT)}/")


def figures(returns: pd.DataFrame, period: pd.Series, realized: pd.Series, out) -> None:
    shown = [p for p in PERIODS if (period == p).any()]
    fig, axes = plt.subplots(1, len(shown), figsize=(5 * len(shown), 4), squeeze=False)
    for ax, p in zip(axes[0], shown):
        in_p = period == p
        dates = realized[in_p]
        for name in ["SPY", "Equal weight", "Random search", "Long/short"]:
            equity = 100 * (1 + returns.loc[in_p, name].fillna(0)).cumprod()
            ax.plot(
                dates.values,
                equity.values,
                color=COLORS[name],
                lw=2 if name == "Long/short" else 1.3,
                label=f"{name}: {equity.iloc[-1]:,.0f}",
            )
        plain_log_axis(ax)
        ax.set_title(f"{p}, {dates.iloc[0]:%b %Y} to {dates.iloc[-1]:%b %Y}", fontsize=10)
        ax.legend(loc="upper left", fontsize=8)
    fig.suptitle("Growth of 100, net of costs for the strategies (log scale)", x=0.06, y=1.03, ha="left", fontweight="bold")
    save(fig, out / "equity.png")

    r = returns["Long/short"]
    by_year = (1 + r).groupby(realized.dt.year.values).prod() - 1
    fig, ax = plt.subplots(figsize=(10, 3.6))
    for p in PERIODS:
        years = realized[period == p].dt.year
        if len(years):
            ax.axvspan(years.min() - 0.5, years.max() + 0.5, color=SHADES[p], lw=0, zorder=0)
    ax.bar(by_year.index, by_year.values, width=0.7, color=[BLUE if v >= 0 else RED for v in by_year.values])
    ax.axhline(0, color=DARK_GRAY, lw=0.8)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xticks(by_year.index)
    ax.tick_params(axis="x", rotation=90)
    ax.set_title("Long/short, return by calendar year (background: training, validation, Out-of-Sample)")
    save(fig, out / "years.png")


if __name__ == "__main__":
    main()
