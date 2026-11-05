"""Exploratory analysis of the semiconductor universe cleaned by 10_clean_bloomberg.py: figures and tables.

Descriptive only: no signal of the strategy and no test of whether a feature predicts returns (that would be designing a
strategy on the whole sample, Out-of-Sample included). Until data/bloomberg/raw/membership.csv exists, the universe is
every company ever in the SOX index from 2000 to 2026, also in the years before it entered: a curve of this universe is
biased upwards (it holds future members before they were chosen).

Input:  data/bloomberg/clean/
Output: data/bloomberg/eda/*.png and *.csv
"""

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from src.config import ROOT, load_config
from src.data import read_weekly
from src.style import BLUE, DARK_GRAY, INK, LIGHT_GRAY, MUTED, ORANGE, RED, SURFACE, plain_log_axis, plt, save

LABELLED = ["NVDA", "AVGO", "AMD", "INTC", "TSM", "ASML", "SUNEQ", "9966620D", "MU"]


def fig_universe(close: pd.DataFrame, companies: pd.DataFrame, in_index: pd.DataFrame | None, path) -> None:
    alive = close.droplevel("date_open").notna().sum(axis=1)
    exits = pd.to_datetime(companies.loc[companies["exited"], "last"]).dt.year.value_counts().sort_index()
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(10, 5.2), sharex=False, gridspec_kw={"height_ratios": [3, 2], "hspace": 0.45}
    )
    top.plot(alive.index, alive.values, color=BLUE, label="Companies with a price")
    if in_index is not None:
        members = in_index.droplevel("date_open").sum(axis=1)
        top.plot(members.index, members.values, color=DARK_GRAY, label="of which in the SOX index that week")
        top.legend(loc="lower right")
    top.set_title("Companies ever in the SOX index (2000-2026) that are listed each week")
    top.set_ylim(0, alive.max() * 1.15)
    bottom.bar(exits.index, exits.values, color=ORANGE, width=0.7)
    bottom.set_title("Companies that left the market each year (acquired, merged or bankrupt): kept until their last price")
    bottom.set_xlim(alive.index[0].year - 0.5, alive.index[-1].year + 0.5)
    save(fig, path)


def fig_coverage(companies: pd.DataFrame, path) -> None:
    c = companies.sort_values(["first", "last"])
    first, last = pd.to_datetime(c["first"]), pd.to_datetime(c["last"])
    fig, ax = plt.subplots(figsize=(10, 0.16 * len(c) + 1.4))
    y = np.arange(len(c))[::-1]
    colors = [ORANGE if exited else BLUE for exited in c["exited"]]
    ax.barh(y, (last - first).dt.days, left=first, height=0.65, color=colors)
    ax.set_yticks(y, c.index, fontsize=6.5)
    ax.set_ylim(-1, len(c))
    ax.grid(axis="y", visible=False)
    ax.legend(
        handles=[
            matplotlib.patches.Patch(color=BLUE, label="still listed"),
            matplotlib.patches.Patch(color=ORANGE, label="left the market"),
        ],
        loc="upper left",
        bbox_to_anchor=(1.0, 1.0),
    )
    ax.set_title(
        "Prices available for each company (numeric codes: delisted companies, named in meta.csv)\n"
        "ADI before 2012, CY before 2009 and IPHI before 2020 are missing: they were listed on another exchange",
        fontsize=10,
    )
    save(fig, path)


def fig_survivors(companies: pd.DataFrame, path) -> pd.DataFrame:
    fig, ax = plt.subplots(figsize=(8, 5.5))
    rows = {}
    for exited, color, marker, label in [(False, BLUE, "o", "still listed"), (True, ORANGE, "^", "left the market")]:
        c = companies[companies["exited"] == exited]
        ax.scatter(c["annual_volatility"], c["annual_return"], s=40, color=color, marker=marker, edgecolor=SURFACE, linewidth=1.2, zorder=3,
                   label=f"{label} ({len(c)}): median {c['annual_return'].median():.1%} a year")  # fmt: skip
        rows[label] = c[["annual_return", "annual_volatility", "max_drawdown"]].median()
    for name in LABELLED:
        if name in companies.index:
            r = companies.loc[name]
            offset = {"TSM": (-6, 6), "ASML": (6, -10)}.get(name, (5, 2))
            ax.annotate(
                name,
                (r["annual_volatility"], r["annual_return"]),
                xytext=offset,
                textcoords="offset points",
                fontsize=8,
                ha="right" if offset[0] < 0 else "left",
            )
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Annualized volatility (daily returns)")
    ax.set_ylabel("Annualized return, from first to last price")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.14), fontsize=8.5, ncols=2)
    ratio = rows["left the market"]["annual_return"] / rows["still listed"]["annual_return"]
    ax.set_title(f"Survivorship bias, visible: the companies that left earned {ratio:.0%} of the others (medians)")
    save(fig, path)
    return pd.DataFrame(rows).T


def fig_concentration(market_cap: pd.DataFrame, path) -> None:
    cap = market_cap.droplevel("date_open")
    total = cap.sum(axis=1, min_count=1)
    nvda = cap["NVDA"] / total
    top5 = cap.apply(lambda row: row.nlargest(5).sum(), axis=1) / total
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.plot(top5.index, top5.values, color=DARK_GRAY, label=f"5 largest companies: {top5.iloc[-1]:.0%} at the end")
    ax.plot(nvda.index, nvda.values, color=BLUE, label=f"NVIDIA: {nvda.iloc[-1]:.0%} at the end")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left")
    ax.set_title(f"Share of the market value of the universe: NVIDIA alone is {nvda.iloc[-1]:.0%} ({nvda.max():.0%} at the peak)")
    save(fig, path)


def fig_benchmarks(
    close: pd.DataFrame, market_cap: pd.DataFrame, start: pd.Timestamp, sox: pd.Series | None, in_index, path
) -> None:
    c = close.droplevel("date_open")
    r = c.pct_change(fill_method=None)
    if in_index is not None:
        r = r.where(
            in_index.droplevel("date_open").shift(1, fill_value=False).astype(bool)
        )  # held if a member at the last Friday
    weights = market_cap.droplevel("date_open").shift(1).where(r.notna())  # caps known at the previous Friday
    series = {
        "Equal weight": r.mean(axis=1),
        "Equal weight without NVIDIA": r.drop(columns="NVDA").mean(axis=1),
        "Cap weighted": (r * weights).sum(axis=1) / weights.sum(axis=1),
    }
    colors = {
        "Equal weight": BLUE,
        "Equal weight without NVIDIA": ORANGE,
        "Cap weighted": DARK_GRAY,
        "SOX index (total return)": LIGHT_GRAY,
    }
    if sox is not None:
        series["SOX index (total return)"] = sox.resample("W-FRI").last().pct_change(fill_method=None).reindex(r.index)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for name, ret in series.items():
        ret = ret.loc[start:].fillna(0)
        equity = 100 * (1 + ret).cumprod()
        ax.plot(
            equity.index,
            equity.values,
            color=colors[name],
            lw=2 if name == "Equal weight" else 1.4,
            label=f"{name}: ends at {equity.iloc[-1]:,.0f}",
        )
    plain_log_axis(ax)
    ax.legend(loc="upper left", fontsize=8.5)
    caveat = (
        "members of the SOX at each date"
        if in_index is not None
        else "every company ever in the SOX, also before it entered: biased upwards"
    )
    ax.set_title(f"Growth of 100 from {start.date()}, weekly, before costs ({caveat})", fontsize=10)
    save(fig, path)


def fig_returns(close: pd.DataFrame, path) -> pd.Series:
    r = close.pct_change(fill_method=None).stack().dropna()
    stats = pd.Series({"weeks": len(r), "mean": r.mean(), "std": r.std(), "skew": r.skew(), "excess_kurtosis": r.kurt(),
                       "share_below_-25%": (r < -0.25).mean(), "share_above_25%": (r > 0.25).mean()})  # fmt: skip
    fig, ax = plt.subplots(figsize=(8, 4))
    bins = np.linspace(-0.6, 0.6, 121)
    ax.hist(r.clip(-0.6, 0.6), bins=bins, color=BLUE, alpha=0.85, label="weekly returns, every company")
    x = (bins[:-1] + bins[1:]) / 2
    normal = len(r) * (bins[1] - bins[0]) * np.exp(-0.5 * ((x - r.mean()) / r.std()) ** 2) / (r.std() * np.sqrt(2 * np.pi))
    ax.plot(x, normal, color=INK, lw=1.2, label="normal with the same mean and volatility")
    plain_log_axis(ax)
    ax.set_ylim(0.8, None)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.legend(loc="upper left", fontsize=8.5)
    ax.set_title(f"Fat tails: excess kurtosis {stats['excess_kurtosis']:.1f}, skew {stats['skew']:.2f} (log scale)")
    save(fig, path)
    return stats


def fig_feature_correlation(features: pd.DataFrame, path) -> pd.DataFrame:
    z = features[[c for c in features.columns if c.endswith("_z")]]
    corr = z.corr()
    names = [c.removesuffix("_z") for c in corr.columns]
    cmap = LinearSegmentedColormap.from_list("diverging", [RED, "#f0efec", BLUE])
    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1)
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right", fontsize=8.5)
    ax.set_yticks(range(len(names)), names, fontsize=8.5)
    ax.grid(False)
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=7.5, color=INK)
    ax.set_title("Correlation of the features (z-scores, every company and week)")
    save(fig, path)
    corr.index = corr.columns = names
    return corr


def main() -> None:
    cfg = load_config()
    bb_dir = ROOT / cfg["bloomberg"]["dir"]
    clean, out = bb_dir / "clean", bb_dir / "eda"
    if not (clean / "close.csv").exists():
        raise FileNotFoundError("data/bloomberg/clean/ not found: run 10_clean_bloomberg.py")
    close = read_weekly(clean / "close.csv")
    market_cap = read_weekly(clean / "market_cap.csv")
    companies = pd.read_csv(clean / "companies.csv", index_col=0)
    features = pd.read_parquet(clean / "features.parquet")
    in_index = read_weekly(clean / "in_index.csv").astype(bool) if (clean / "in_index.csv").exists() else None
    sox = None
    if (bb_dir / "raw" / "benchmark_sox.parquet").exists():
        b = pd.read_parquet(bb_dir / "raw" / "benchmark_sox.parquet")
        sox = b.set_index(pd.to_datetime(b["date"]))["TOT_RETURN_INDEX_GROSS_DVDS"].dropna()
    first_signal = pd.Timestamp("2005-08-19")  # first signal of the strategy (docs/strategy.md)

    fig_universe(close, companies, in_index, out / "universe.png")
    fig_coverage(companies, out / "coverage.png")
    survivors = fig_survivors(companies, out / "survivors.png")
    fig_concentration(market_cap, out / "concentration.png")
    fig_benchmarks(close, market_cap, first_signal, sox, in_index, out / "benchmarks.png")
    stats = fig_returns(close, out / "returns.png")
    corr = fig_feature_correlation(features, out / "feature_correlation.png")

    raw_features = features[[c for c in features.columns if not c.endswith("_z") and c != "in_index"]]
    feature_stats = raw_features.describe(percentiles=[0.01, 0.5, 0.99]).T.assign(missing_share=raw_features.isna().mean())
    for name, table in {"survivorship": survivors, "weekly_returns": stats.to_frame("value"), "feature_stats": feature_stats,
                        "feature_correlation": corr}.items():  # fmt: skip
        out.mkdir(parents=True, exist_ok=True)
        table.to_csv(out / f"{name}.csv")
        print(f"Saved {(out / f'{name}.csv').relative_to(ROOT)}")
    with pd.option_context("display.width", 200):
        print("\nMedians, still listed against left the market:")
        print(survivors.round(3).to_string())
        print("\nWeekly returns of every company:")
        print(stats.round(4).to_string())


if __name__ == "__main__":
    main()
