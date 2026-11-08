"""Choose the weights of the long/short strategy on semiconductors with a genetic algorithm, on the training period only.

The design is in docs/experiment_log.md (final strategy) and src/longshort.py. One run of the genetic algorithm per seed
(settings of `ga` in config.yaml); the best genome of each run on the training period is a member; the final weights are
the average of the members. Control: a random search with the same budget, reported, never chosen.

Only the training period is computed here: the validation and the Out-of-Sample are evaluated by 13_evaluate_longshort.py
on the frozen weights.

Universe: the members of the SOX index at each date (data/bloomberg/clean/in_index.csv). Without it every company with a
price is used, which holds future members before they entered: the run is then marked PROVISIONAL, for development only.

Input:  data/bloomberg/clean/{open,close}.csv, features.parquet, in_index.csv
Output: data/bloomberg/longshort/best.yaml     members and final weights
        data/bloomberg/longshort/members.csv   training metrics of the members of both methods
        data/bloomberg/longshort/history.csv   best and mean fitness of every generation
        data/bloomberg/longshort/config.yaml   the settings used
"""

import numpy as np
import pandas as pd
import yaml

from src import genetic, longshort, metrics
from src.backtest import execution_dates, forward_returns
from src.config import ROOT, load_config, save_used
from src.data import read_weekly

NO_SHARPE = -10.0  # fitness of a genome that never trades (Sharpe not defined)


def load(clean, features: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame, bool]:
    opens, close = read_weekly(clean / "open.csv"), read_weekly(clean / "close.csv")
    panel = pd.read_parquet(clean / "features.parquet")
    raw = {name: panel[name].unstack("company").reindex(index=close.index, columns=close.columns) for name in features}
    point_in_time = (clean / "in_index.csv").exists()
    if point_in_time:
        members = read_weekly(clean / "in_index.csv").reindex(index=close.index, columns=close.columns).fillna(False).astype(bool)
    else:
        members = close.notna()
    return opens, close, raw, members, point_in_time


def main() -> None:
    cfg = load_config()
    ga, ls, bb = cfg["ga"], cfg["longshort"], cfg["bloomberg"]
    cost_bps, kind = cfg["metrics"]["cost_bps"], cfg["metrics"]["type"]
    train_end = pd.Timestamp(ga["train_end"])
    clean, out = ROOT / bb["dir"] / "clean", ROOT / bb["dir"] / "longshort"

    opens, close, raw, members, point_in_time = load(clean, ls["features"])
    if not point_in_time:
        print("PROVISIONAL: no in_index.csv, the universe is every company with a price (development only)")
    universe = longshort.Universe(raw, members, bb["winsorize"])
    forward = forward_returns(opens, close, kind)
    _, realized = execution_dates(close.index, kind)
    tradable = (universe.size >= ls["min_companies"]) & forward.notna().any(axis=1)
    train = tradable & (realized <= train_end)
    days = realized[train]
    print(f"training: {train.sum()} weeks, returns realized from {days.iloc[0].date()} to {days.iloc[-1].date()}, "
          f"{universe.size[train].mean():.0f} companies a week on average")  # fmt: skip

    def backtest(weights: dict[str, float]) -> dict:
        s = longshort.signals(universe.score(weights), ls["quantile"], ls["min_companies"])
        w = longshort.weights(s, universe.raw["beta_52w"] if ls["sizing"] == "beta" else None)[train]
        r = longshort.returns(w, forward[train], cost_bps, ls["borrow_bps_year"])
        perf = metrics.performance(r, 0.0)  # returns in excess of cash: risk-free 0
        sharpe = perf["sharpe_ratio"] if np.isfinite(perf["sharpe_ratio"]) else NO_SHARPE
        turnover = w.diff().fillna(w).abs().sum(axis=1).mean() * metrics.PERIODS_PER_YEAR
        return {"sharpe": sharpe, "return": perf["annualized_return"], "volatility": perf["annualized_volatility"],
                "max_dd": perf["max_drawdown"], "turnover": turnover}  # fmt: skip

    def fitness(genome) -> float:
        return backtest(longshort.decode(genome, ls["features"]))["sharpe"]

    n = len(ls["features"])
    members_ga, history, n_backtests = [], [], 0
    for seed in ga["seeds"]:
        best, log = genetic.run(fitness, ga, seed, n_genes=n)
        n_backtests += sum(log.select("nevals"))
        history += [{"seed": seed, **entry} for entry in log]
        members_ga.append(longshort.decode(best, ls["features"]))
        print(f"seed {seed}: best training Sharpe {best.fitness.values[0]:.3f}, {sum(log.select('nevals'))} backtests")

    rng = np.random.default_rng(ls["random_search_seed"])
    per_batch = n_backtests // len(ga["seeds"])
    members_random = []
    for _ in ga["seeds"]:
        draws = [longshort.decode(list(g), ls["features"]) for g in rng.random((per_batch, n))]
        members_random.append(max(draws, key=lambda w: backtest(w)["sharpe"]))

    rows = []
    for method, chosen in {"genetic algorithm": members_ga, "random search": members_random}.items():
        for i, w in enumerate(chosen, start=1):
            rows.append(
                {
                    "method": method,
                    "member": i,
                    **{f"w_{k}": v for k, v in w.items()},
                    **{f"train_{k}": v for k, v in backtest(w).items()},
                }
            )
        avg = longshort.average(chosen)
        rows.append(
            {
                "method": method,
                "member": "average",
                **{f"w_{k}": v for k, v in avg.items()},
                **{f"train_{k}": v for k, v in backtest(avg).items()},
            }
        )
    table = pd.DataFrame(rows)

    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "members.csv", index=False)
    pd.DataFrame(history).to_csv(out / "history.csv", index=False)
    best = {"point_in_time_universe": point_in_time, "members": members_ga, "weights": longshort.average(members_ga)}
    with open(out / "best.yaml", "w") as f:
        yaml.safe_dump(best, f, sort_keys=False)
    save_used({"ga": ga, "longshort": ls, "winsorize": bb["winsorize"], "cost_bps": cost_bps, "type": kind}, out / "config.yaml")

    with pd.option_context("display.width", 220, "display.max_columns", 30):
        print(f"\n{per_batch} backtests per member, for both methods. Training only:")
        print(table.drop(columns=[c for c in table.columns if c.startswith("w_")]).round(3).to_string(index=False))
        print("\nWeights (average of the genetic algorithm members, the final strategy):")
        print(pd.Series(best["weights"]).to_string())
    print(f"\nSaved {(out / 'best.yaml').relative_to(ROOT)}" + ("" if point_in_time else "  (PROVISIONAL universe)"))


if __name__ == "__main__":
    main()
