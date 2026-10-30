"""Simple interactive charts (HTML), In-Sample and Out-of-Sample side by side."""

import pandas as pd
import plotly.express as px

from src.config import ROOT

# Strategies take these colors in order; benchmarks are gray
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
GRAYS = ["#5f5e58", "#9a9992"]


def colors(strategies: list[str], benchmarks: list[str]) -> dict[str, str]:
    return dict(zip(strategies, COLORS)) | dict(zip(benchmarks, GRAYS))


def line_chart(table: pd.DataFrame, title: str, colors: dict, path, percent: bool = False, **options) -> None:
    """table: one row per date, a column `period` and one column per series."""
    long = table.rename_axis("date").reset_index().melt(["date", "period"], var_name="series")
    fig = px.line(
        long,
        x="date",
        y="value",
        color="series",
        facet_col="period",
        title=title,
        color_discrete_map=colors,
        template="plotly_white",
        **options,
    )
    fig.update_xaxes(matches=None, title=None)
    fig.update_yaxes(title=None, tickformat=".0%" if percent else None)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))  # "period=IS" -> "IS"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(path)
    print(f"Saved {path.relative_to(ROOT)}")


def equity_curves(returns: pd.DataFrame, period: pd.Series, entered: pd.Series, realized: pd.Series) -> pd.DataFrame:
    """Equity curve of every series, starting at 100 in each period, dated when each return is realized."""
    curves = []
    for p in period.unique():
        in_p = period == p
        curve = 100 * (1 + returns[in_p]).cumprod()
        curve.index = realized[in_p]
        start = pd.DataFrame(100.0, index=[entered[in_p].iloc[0]], columns=returns.columns)
        curves.append(pd.concat([start, curve]).assign(period=p))
    return pd.concat(curves)


def save_plots(returns, signals, period, entered, realized, colors, plots_dir) -> None:
    equity = equity_curves(returns, period, entered, realized)
    line_chart(equity, "Equity curve (starting at 100, log scale)", colors, plots_dir / "equity.html", log_y=True)

    series = equity.columns.drop("period")
    drawdown = equity[series] / equity.groupby("period")[series].cummax() - 1
    line_chart(drawdown.assign(period=equity["period"]), "Drawdown", colors, plots_dir / "drawdown.html", percent=True)

    exposure = pd.DataFrame({name: s.mean(axis=1) for name, s in signals.items()})
    exposure = exposure.groupby(period.values).transform(lambda x: x.rolling(13).mean())  # within each period
    exposure.index = exposure.index.get_level_values("date_close")
    line_chart(
        exposure.assign(period=period.values),
        "Net exposure of the strategies (13-week average, week of the signal)",
        colors,
        plots_dir / "exposure.html",
        percent=True,
    )
