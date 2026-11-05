"""Style of the static figures (matplotlib), shared by 08_make_figures.py and 11_eda_bloomberg.py.

Colors follow one rule: blue is the series that matters (the strategy), grays the references, orange the other side of a
comparison, red only for losses.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import ROOT

BLUE, ORANGE, RED = "#2a78d6", "#eb6834", "#e34948"
DARK_GRAY, LIGHT_GRAY = "#5f5e58", "#9a9992"
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3de"
SHADES = {"Training": "#f0efec", "Validation": "#e4e3de", "Out-of-Sample": "#cde2fb"}

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
