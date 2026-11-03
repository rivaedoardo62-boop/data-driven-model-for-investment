"""Static figures (PNG) that explain the data, the signal and the results, for the slides and docs/figures.md.

Colors: blue is always the strategy (ga), grays the benchmarks; orange marks the other side of a comparison.

Inputs:  data/prices/, data/signals/ga.csv, data/ga/{best.yaml,members.csv}, data/metrics/returns.csv
         data/extra/ (optional: the coverage and macro figures are drawn only after 06_download_extra_data.py)
Outputs: data/figures/*.png
"""

import matplotlib
import matplotlib.dates

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from src import metrics
from src.backtest import execution_dates, forward_returns, strategy_returns
from src.config import ROOT, load_config
from src.data import read_weekly
from src.ensemble import Indicators, signals, vote

BLUE, ORANGE, RED = "#2a78d6", "#eb6834", "#e34948"
DARK_GRAY, LIGHT_GRAY = "#5f5e58", "#9a9992"
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3de"
SHADES = {"Training": "#f0efec", "Validation": "#e4e3de", "Out-of-Sample": "#cde2fb"}
NAMES = {"ga": "Strategy (vote of 5)", "Equal weight": "Equal weight, 4 stocks", "SPY": "SPY"}
SERIES_COLORS = {"ga": BLUE, "Equal weight": DARK_GRAY, "SPY": LIGHT_GRAY}

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "text.color": INK,
        "font.size": 9.5,
        "legend.frameon": False,
        "lines.linewidth": 1.6,
    }
)


def save(fig, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path.relative_to(ROOT)}")


def shade_periods(ax, bounds: dict, label: bool = False) -> None:
    """Background of the Training / Validation / Out-of-Sample periods."""
    for name, (start, end) in bounds.items():
        ax.axvspan(start, end, color=SHADES[name], zorder=0, lw=0)
        if label:
            ax.text(
                start + (end - start) / 2,
                1.01,
                name,
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="bottom",
                color=MUTED,
                fontsize=9,
            )


def plain_log_axis(ax) -> None:
    """Log scale with plain numbers (100, 200, 500) instead of powers of 10."""
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(subs=(1, 2, 5)))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())


def fig_periods(spy: pd.Series, bounds: dict, weeks: dict, path) -> None:
    fig, ax = plt.subplots(figsize=(10, 3.6))
    shade_periods(ax, bounds)
    spy = spy.loc[bounds["Training"][0] :]
    ax.plot(spy.index, spy.values, color=DARK_GRAY)
    plain_log_axis(ax)
    for name, (start, end) in bounds.items():
        ax.text(
            start + (end - start) / 2,
            1.01,
            f"{name}\n{weeks[name]} weeks",
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="bottom",
            color=MUTED,
            fontsize=9,
        )
    events = [
        ("2009-03-06", "2008 crisis", (40, 0)),
        ("2020-03-20", "Covid crash", (0, -26)),
        ("2022-10-14", "2022 bear market", (0, -26)),
    ]
    for day, text, offset in events:
        ax.annotate(
            text,
            (pd.Timestamp(day), spy.asof(pd.Timestamp(day))),
            xytext=offset,
            textcoords="offset points",
            ha="left" if offset[0] else "center",
            va="center" if offset[0] else "top",
            fontsize=8.5,
            color=INK,
            arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.8},
        )
    ax.set_title("Sample split by period, with the main market falls (SPY, adjusted weekly close, log scale)", pad=30)
    save(fig, path)


def fig_adjustment(raw_dir, ticker: str, day: str, path) -> None:
    read = lambda name: pd.read_csv(raw_dir / f"{name}.csv", index_col=0, parse_dates=True)[ticker]
    adjusted, split_only, splits = read("close"), read("close_split_only"), read("splits")
    later_splits = splits.where(splits > 0, 1.0)[::-1].cumprod()[::-1].shift(-1, fill_value=1.0)  # splits after each day
    unadjusted = split_only * later_splits
    window = slice(pd.Timestamp(day) - pd.Timedelta(days=60), pd.Timestamp(day) + pd.Timedelta(days=60))
    split_day = pd.Timestamp(day)
    before = adjusted.index[adjusted.index.get_loc(split_day) - 1]
    raw_move = unadjusted[split_day] / unadjusted[before] - 1
    adj_move = adjusted[split_day] / adjusted[before] - 1

    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(unadjusted[window].index, unadjusted[window].values, color=ORANGE, label="Price as quoted (not adjusted)")
    ax.plot(adjusted[window].index, adjusted[window].values, color=BLUE, label="Adjusted for splits and dividends (used)")
    ax.axvline(split_day, color=MUTED, lw=0.8)
    ax.annotate(
        f"{ticker} split {splits[split_day]:g}:1 on {split_day.date()}\nquoted price {raw_move:+.0%}, "
        f"adjusted return {adj_move:+.1%}",
        (split_day, unadjusted[before]),
        xytext=(10, -10),
        textcoords="offset points",
        va="top",
        fontsize=8.5,
    )
    ax.set_ylabel("USD")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b %Y"))
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator())
    ax.legend(loc="center left")
    ax.set_title("Why adjusted prices: a split is not a crash")
    save(fig, path)


def fig_signal(close: pd.DataFrame, params: dict, final: pd.DataFrame, ticker: str, start: str, end: str, path) -> None:
    indicators = Indicators(close, params["scale_window"])
    members = [signals(indicators, member, params["warmup"]) for member in params["members"]]
    long_count = sum(members)[ticker].droplevel("date_open").loc[start:end]
    price = close[ticker].droplevel("date_open").loc[start:end]
    flat = final[ticker].droplevel("date_open").loc[start:end] == 0

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 5), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    week = pd.Timedelta(days=7)
    for friday in flat[flat].index:  # the signal of week t is held from the open of week t+1
        for ax in (top, bottom):
            ax.axvspan(friday + pd.Timedelta(days=3), friday + pd.Timedelta(days=3) + week, color=SHADES["Validation"], lw=0)
    top.plot(price.index, price.values, color=BLUE)
    top.set_ylabel("USD")
    top.set_title(f"{ticker}: weekly close; gray weeks = flat (signal 0, out of the stock)")
    bottom.step(long_count.index, long_count.values, where="post", color=DARK_GRAY)
    bottom.axhline(2.5, color=ORANGE, lw=1)
    bottom.set_title("Members long, 0 to 5: under the orange line (fewer than 3) the signal is flat", fontsize=9.5)
    bottom.set_yticks(range(6))
    bottom.set_ylim(-0.3, 5.3)
    bottom.set_ylabel("members long")
    save(fig, path)


def fig_equity(returns: pd.DataFrame, realized: pd.Series, path, drawdown: bool = False) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"width_ratios": [696, 404]})
    for ax, period, title in zip(axes, ["IS", "OOS"], ["In-Sample", "Out-of-Sample"]):
        in_p = returns["period"] == period
        dates = realized[in_p]
        for name in ["SPY", "Equal weight", "ga"]:
            equity = 100 * (1 + returns.loc[in_p, name]).cumprod()
            values = equity / equity.cummax().clip(lower=100) - 1 if drawdown else equity
            final = f"max drawdown {values.min():.0%}" if drawdown else f"ends at {values.iloc[-1]:,.0f}"
            ax.plot(
                dates.values,
                values.values,
                color=SERIES_COLORS[name],
                label=f"{NAMES[name]}: {final}",
                lw=2 if name == "ga" else 1.4,
            )
        ax.set_title(f"{title}, {dates.iloc[0]:%b %Y} to {dates.iloc[-1]:%b %Y}")
        ax.xaxis.set_major_locator(matplotlib.dates.YearLocator(2))
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
        if drawdown:
            ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
        else:
            plain_log_axis(ax)
        handles, labels = ax.get_legend_handles_labels()
        place = {"loc": "upper left", "bbox_to_anchor": (0, -0.1)} if drawdown else {"loc": "upper left"}
        ax.legend(handles[::-1], labels[::-1], fontsize=8.5, **place)
    fig.suptitle(
        "Drawdown from the previous peak" if drawdown else "Equity curves, starting at 100 (log scale), net of costs",
        x=0.06,
        y=1.03,
        ha="left",
        fontweight="bold",
    )
    save(fig, path)


def fig_years(returns: pd.DataFrame, realized: pd.Series, is_end: pd.Timestamp, path) -> None:
    by_year = returns[["ga", "Equal weight"]].groupby(realized.dt.year.values).apply(lambda r: (1 + r).prod() - 1)
    excess = by_year["ga"] - by_year["Equal weight"]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.axvspan(is_end.year + 0.5, excess.index[-1] + 0.6, color=SHADES["Out-of-Sample"], lw=0, zorder=0)
    ax.bar(excess.index, excess.values, width=0.7, color=[BLUE if v >= 0 else RED for v in excess.values])
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.text(is_end.year + 0.6, 0.98, "Out-of-Sample", transform=ax.get_xaxis_transform(), va="top", color=MUTED)
    best = excess.idxmax()
    ax.annotate(
        f"{best}: {excess[best]:+.0%}",
        (best + 0.35, excess[best]),
        xytext=(4, 0),
        textcoords="offset points",
        va="center",
        fontsize=8.5,
    )
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xticks(excess.index)
    ax.tick_params(axis="x", rotation=90)
    ax.set_title("Strategy minus equal weight of the same stocks, by calendar year (blue: the timing helped)")
    ax.text(
        0,
        -0.28,
        f"{excess.index[0]} and {excess.index[-1]} are partial years.",
        transform=ax.transAxes,
        color=MUTED,
        fontsize=8.5,
    )
    save(fig, path)


def fig_ga_vs_random(members: pd.DataFrame, votes: dict, benchmark: float, path) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 5))
    for method, color, marker in [("genetic algorithm", BLUE, "o"), ("random search", ORANGE, "^")]:
        rows = members[members["method"] == method]
        ax.scatter(
            rows["train_sharpe"],
            rows["validation_sharpe"],
            s=45,
            color=color,
            marker=marker,
            edgecolor=SURFACE,
            linewidth=1.5,
            label=f"{method.capitalize()}: one member per run",
            zorder=3,
        )
        train, validation = votes[method]
        ax.scatter([train], [validation], s=160, color=color, marker=marker, edgecolor=INK, linewidth=1, zorder=4)
        ax.annotate(
            f"{method.split()[0].capitalize()} vote",
            (train, validation),
            xytext=(9, 0),
            textcoords="offset points",
            va="center",
            fontsize=8.5,
        )
    ax.axhline(benchmark, color=DARK_GRAY, lw=1)
    ax.text(
        ax.get_xlim()[1], benchmark, f"equal weight, validation Sharpe {benchmark:.2f} ", ha="right", va="bottom", fontsize=8.5
    )
    ax.set_xlabel("Sharpe ratio, training (where the parameters are chosen)")
    ax.set_ylabel("Sharpe ratio, validation (never used to choose)")
    ax.legend(loc="upper center", fontsize=8.5)
    ax.set_title("The genetic algorithm does not beat random parameters")
    save(fig, path)


def fig_coverage(starts: pd.DataFrame, bounds: dict, first_signal: pd.Timestamp, path) -> None:
    fig, ax = plt.subplots(figsize=(10, 0.28 * len(starts) + 1.2))
    shade_periods(ax, bounds, label=True)
    y = np.arange(len(starts))[::-1]
    warmup = pd.Timedelta(weeks=52)  # the strategy needs 52 weeks of prices before its first signal
    long_enough = starts["last"] - starts["first"] - warmup >= pd.Timedelta(days=3652)
    colors = [
        LIGHT_GRAY if group.startswith("macro") else BLUE if long else ORANGE for group, long in zip(starts["group"], long_enough)
    ]
    ax.barh(
        y,
        (starts["last"] - starts["first"]).dt.days,
        left=starts["first"],
        height=0.6,
        color=colors,
    )
    ax.set_yticks(y, [f"{name}  ({group})" for name, group in zip(starts.index, starts["group"])], fontsize=8)
    ax.axvline(first_signal, color=INK, lw=0.8)
    ax.text(first_signal, -1.2, " first signal of the strategy", fontsize=8, va="center")
    ax.grid(axis="y", visible=False)
    ax.legend(
        handles=[
            matplotlib.patches.Patch(color=BLUE, label="10+ years of signals"),
            matplotlib.patches.Patch(color=ORANGE, label="fewer than 10 years"),
            matplotlib.patches.Patch(color=LIGHT_GRAY, label="macro series"),
        ],
        loc="upper left",
        bbox_to_anchor=(1.0, 1.0),
    )
    ax.set_title("Data available: an empty cell before a bar is a later listing, not a missing price", pad=22)
    save(fig, path)


def fig_macro(macro: dict, bounds: dict, path) -> None:
    cpi = macro["CPIAUCSL"]
    panels = [
        ("VIXCLS", macro["VIXCLS"], 25, "VIX (stress above 25)"),
        ("T10Y3M", macro["T10Y3M"], 0, "10-year minus 3-month yield, points (inverted below 0)"),
        ("DFF", macro["DFF"], None, "Fed funds rate, %"),
        ("BAA10Y", macro["BAA10Y"], None, "Baa corporate minus 10-year yield, points (credit stress)"),
        ("CPI", cpi / cpi.shift(12) - 1, 0.03, "Inflation, CPI over 12 months (high above 3%)"),
    ]
    recession = macro["USREC"]
    fig, axes = plt.subplots(len(panels), 1, figsize=(10, 10), sharex=True, gridspec_kw={"hspace": 0.45})
    start = bounds["Training"][0]
    in_recession = recession.loc[start:] == 1
    runs = (in_recession != in_recession.shift()).cumsum()[in_recession]  # consecutive recession months
    for ax, (name, series, threshold, title) in zip(axes, panels):
        series = series.loc[start:].dropna()
        for _, months in runs.groupby(runs):
            ax.axvspan(months.index[0], months.index[-1] + pd.offsets.MonthEnd(1), color=SHADES["Validation"], lw=0, zorder=0)
        for _, end in list(bounds.values())[:-1]:
            ax.axvline(end, color=MUTED, lw=0.8)
        ax.plot(series.index, series.values, color=BLUE, lw=1.1)
        if threshold is not None:
            ax.axhline(threshold, color=ORANGE, lw=1)
        if name == "CPI":
            ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
        ax.set_title(title, fontsize=9.5)
    axes[0].text(
        1.0,
        1.25,
        "gray: recessions (NBER); vertical lines: end of training and of In-Sample",
        ha="right",
        transform=axes[0].transAxes,
        color=MUTED,
        fontsize=8.5,
    )
    fig.suptitle(
        "Market regimes, from FRED (latest data: used to describe the results, never as a signal)",
        x=0.06,
        ha="left",
        fontweight="bold",
    )
    save(fig, path)


def main() -> None:
    cfg = load_config()
    data_dir = ROOT / cfg["data"]["data_dir"]
    tickers, kind = cfg["data"]["tickers"], cfg["metrics"]["type"]
    risk_free, cost_bps = cfg["metrics"]["risk_free"], cfg["metrics"]["cost_bps"]
    train_end, is_end = pd.Timestamp(cfg["ga"]["train_end"]), pd.Timestamp(cfg["metrics"]["is_end"])
    out = data_dir / "figures"

    close = read_weekly(data_dir / "prices" / "close.csv")
    opens = read_weekly(data_dir / "prices" / "open.csv")
    returns = read_weekly(data_dir / "metrics" / "returns.csv")
    _, realized_all = execution_dates(close.index, kind)
    realized = realized_all.reindex(returns.index)
    first, last = realized.iloc[0], realized.iloc[-1]
    bounds = {"Training": (first, train_end), "Validation": (train_end, is_end), "Out-of-Sample": (is_end, last)}
    weeks = {
        "Training": int((realized <= train_end).sum()),
        "Validation": int(((realized > train_end) & (realized <= is_end)).sum()),
        "Out-of-Sample": int((realized > is_end).sum()),
    }

    fig_periods(close[cfg["data"]["benchmark"]].droplevel("date_open"), bounds, weeks, out / "periods.png")
    fig_adjustment(data_dir / "prices" / "raw", "AAPL", "2020-08-31", out / "adjustment.png")
    with open(data_dir / "ga" / "best.yaml") as f:
        params = yaml.safe_load(f)
    final = read_weekly(data_dir / "signals" / "ga.csv")
    fig_signal(close[tickers], params, final, "AAPL", "2019-06-01", "2022-12-31", out / "signal_example.png")
    fig_equity(returns, realized, out / "equity.png")
    fig_equity(returns, realized, out / "drawdown.png", drawdown=True)
    fig_years(returns, realized, is_end, out / "years.png")

    # Training and validation Sharpe of the two votes, recomputed from the members saved by 03_optimize_ga.py
    members = pd.read_csv(data_dir / "ga" / "members.csv")
    indicators = Indicators(close[tickers], params["scale_window"])
    forward = forward_returns(opens[tickers], close[tickers], kind)
    split = {"train": realized <= train_end, "validation": (realized > train_end) & (realized <= is_end)}
    votes = {}
    for method, rows in members.groupby("method"):
        chosen = [
            {
                "windows": {k: int(r[f"window_{k}"]) for k in ["trend", "momentum", "reversal", "volatility"]},
                "weights": {k: float(r[f"weight_{k}"]) for k in ["trend", "momentum", "reversal", "volatility"]},
                "threshold": float(r["threshold"]),
            }
            for _, r in rows.iterrows()
        ]
        s = vote([signals(indicators, p, params["warmup"]) for p in chosen], params["vote"]).loc[returns.index]
        fwd = forward.loc[returns.index]
        votes[method] = tuple(  # each period starts flat, as in 03_optimize_ga.py
            metrics.sharpe_ratio(strategy_returns(s[split[p].values], fwd[split[p].values], cost_bps), risk_free)
            for p in ["train", "validation"]
        )
        print(
            f"{method} vote, Sharpe: training {votes[method][0]:.3f}, validation {votes[method][1]:.3f} "
            "(must match 03_optimize_ga.py)"
        )
    benchmark = metrics.sharpe_ratio(returns.loc[split["validation"].values, "Equal weight"], risk_free)
    fig_ga_vs_random(members, votes, benchmark, out / "ga_vs_random.png")

    extra_dir = data_dir / "extra"
    if (extra_dir / "prices" / "close.csv").exists():
        all_close = pd.concat([close, read_weekly(extra_dir / "prices" / "close.csv")], axis=1).droplevel("date_open")
        groups = {t: "traded" for t in tickers} | {cfg["data"]["benchmark"]: "benchmark"}
        groups |= {t: group for group, members_ in cfg["extra"]["groups"].items() for t in members_}
        rows = {t: (all_close[t].first_valid_index(), all_close[t].last_valid_index(), groups[t]) for t in groups}
        macro = {
            name: pd.read_csv(extra_dir / "macro" / f"{name}.csv", index_col=0, parse_dates=True)[name]
            for name in cfg["extra"]["macro"]
        }
        rows |= {name: (s.index[0], s.index[-1], "macro, FRED") for name, s in macro.items()}
        starts = pd.DataFrame(rows, index=["first", "last", "group"]).T
        starts[["first", "last"]] = starts[["first", "last"]].apply(pd.to_datetime)
        fig_coverage(starts, bounds, realized.index[0][1], out / "coverage.png")
        fig_macro(macro, bounds, out / "macro.png")
    else:
        print("data/extra/ not found: coverage.png and macro.png skipped (run 06_download_extra_data.py)")


if __name__ == "__main__":
    main()
