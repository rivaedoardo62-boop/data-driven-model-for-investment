"""Choose the parameters of the ensemble with a genetic algorithm, looking only at the In-Sample period.

The In-Sample period is split by the day the returns are realized (as in 05_evaluate_strategy.py):
    training    up to ga.train_end:                   the genetic algorithm maximizes the Sharpe ratio here (net of costs)
    validation  from ga.train_end to metrics.is_end:  the final strategy is only evaluated here, nothing is chosen
The Out-of-Sample period is never used.

Final strategy: one run of the genetic algorithm per seed; the best genome of each run (on the training) is a member;
the members vote, long when at least ga.vote of them are long. Different seeds find different genomes with similar
training Sharpe: the vote does not depend on a single lucky run.

Control: a random search with the same number of backtests, split in as many batches as the seeds; the best genome of each
batch (on the training) is a member, same vote. If the genetic algorithm does not beat it, the optimization adds nothing.

Input:  data/prices/{open,close}.csv, data/validation/checks.csv (the prices must pass 02_validate_data.py)
Output: data/ga/best.yaml, the members and the vote, read by 04_compute_signals.py
        data/ga/members.csv, the members of both methods, with their training and validation metrics
        data/ga/history.csv, best and mean fitness of every generation of every run
        data/ga/config.yaml, the settings used
"""

import numpy as np
import pandas as pd
import yaml

from src import genetic, metrics
from src.backtest import execution_dates, forward_returns, strategy_returns
from src.config import DATA_KEYS, ROOT, check_used, load_config, save_used
from src.data import read_weekly
from src.ensemble import LONG_VOLATILITY, Indicators, ready, signals, vote

NO_SHARPE = -10.0  # fitness of a genome that is always flat (Sharpe not defined)


def main() -> None:
    cfg = load_config()
    data_dir = ROOT / cfg["data"]["data_dir"]
    tickers = cfg["data"]["tickers"]
    ga, kind = cfg["ga"], cfg["metrics"]["type"]
    risk_free, cost_bps = cfg["metrics"]["risk_free"], cfg["metrics"]["cost_bps"]
    train_end, is_end = pd.Timestamp(ga["train_end"]), pd.Timestamp(cfg["metrics"]["is_end"])
    if train_end.day_name() != "Friday" or not train_end < is_end:
        raise ValueError(f"ga.train_end ({train_end.date()}) must be a Friday before metrics.is_end ({is_end.date()})")
    longest = max([high for _, high in ga["bounds"].values()] + [LONG_VOLATILITY, ga["scale_window"]])
    if ga["warmup"] < longest:
        raise ValueError(f"ga.warmup ({ga['warmup']}) must be at least the longest window ({longest} weeks)")

    data_used = {key: cfg["data"][key] for key in DATA_KEYS}
    check_used(data_used, data_dir / "prices" / "config.yaml", "01_download_data.py")
    validation = data_dir / "validation" / "checks.csv"
    if not validation.exists() or validation.stat().st_mtime < (data_dir / "prices" / "close.csv").stat().st_mtime:
        raise FileNotFoundError("the prices are not validated: run 02_validate_data.py")
    if (pd.read_csv(validation)["result"] == "FAIL").any():
        raise ValueError(f"some checks of the prices failed: see {validation.relative_to(ROOT)}")
    opens = read_weekly(data_dir / "prices" / "open.csv")[tickers]
    close = read_weekly(data_dir / "prices" / "close.csv")[tickers]

    forward = forward_returns(opens, close, kind)
    _, realized = execution_dates(close.index, kind)
    usable = ready(close, ga["warmup"]).all(axis=1) & forward.notna().all(axis=1)  # same weeks for every genome
    periods = {"train": usable & (realized <= train_end), "validation": usable & (realized > train_end) & (realized <= is_end)}
    for name, weeks in periods.items():
        days = realized[weeks]
        print(f"{name}: {weeks.sum()} weeks, returns realized from {days.iloc[0].date()} to {days.iloc[-1].date()}")

    indicators = Indicators(close, ga["scale_window"])

    def backtest(s: pd.DataFrame, period: str) -> dict:
        weeks = periods[period]
        r = strategy_returns(s[weeks], forward[weeks], cost_bps)
        perf = metrics.performance(r, risk_free)
        sharpe = perf["sharpe_ratio"] if np.isfinite(perf["sharpe_ratio"]) else NO_SHARPE
        return {
            "sharpe": sharpe,
            "return": perf["annualized_return"],
            "max_dd": perf["max_drawdown"],
            "long": s[weeks].mean().mean(),
        }

    def member_signals(params: dict) -> pd.DataFrame:
        return signals(indicators, params, ga["warmup"])

    def fitness(genome) -> float:
        return backtest(member_signals(genetic.decode(genome, ga["bounds"])), "train")["sharpe"]

    def row(s: pd.DataFrame, params: dict | None = None, **labels) -> dict:
        out = dict(labels)
        if params:
            out |= {f"window_{k}": v for k, v in params["windows"].items()}
            out |= {f"weight_{k}": v for k, v in params["weights"].items()}
            out["threshold"] = params["threshold"]
        for period in periods:
            out |= {f"{period}_{k}": v for k, v in backtest(s, period).items()}
        return out

    # Genetic algorithm: one run per seed, its best genome on the training is a member
    members, history, n_backtests = [], [], 0
    for seed in ga["seeds"]:
        best, log = genetic.run(fitness, ga, seed)
        n_backtests += sum(log.select("nevals"))
        history += [{"seed": seed, **entry} for entry in log]
        members.append(genetic.decode(best, ga["bounds"]))
        print(f"seed {seed}: best training Sharpe {best.fitness.values[0]:.3f}, {sum(log.select('nevals'))} backtests")

    # Control: random genomes in as many batches as the seeds, same budget per batch, best of each batch on the training
    rng = np.random.default_rng(ga["random_search_seed"])
    per_batch = n_backtests // len(ga["seeds"])
    random_members = []
    for _ in ga["seeds"]:
        draws = [genetic.decode(list(g), ga["bounds"]) for g in rng.random((per_batch, genetic.N_GENES))]
        random_members.append(max(draws, key=lambda params: backtest(member_signals(params), "train")["sharpe"]))

    table, summary = [], {}
    for method, chosen in {"genetic algorithm": members, "random search": random_members}.items():
        table += [row(member_signals(p), p, method=method, member=i) for i, p in enumerate(chosen, start=1)]
        summary[f"{method}, vote"] = row(vote([member_signals(p) for p in chosen], ga["vote"]))

    out_dir = data_dir / "ga"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(table).to_csv(out_dir / "members.csv", index=False)
    pd.DataFrame(history).to_csv(out_dir / "history.csv", index=False)
    params = {"members": members, "vote": ga["vote"], "warmup": ga["warmup"], "scale_window": ga["scale_window"]}
    with open(out_dir / "best.yaml", "w") as f:
        yaml.safe_dump(params, f, sort_keys=False)
    save_used({"data": data_used, "ga": ga, "metrics": cfg["metrics"]}, out_dir / "config.yaml")

    columns = ["method", "member", "train_sharpe", "validation_sharpe", "validation_max_dd", "validation_long"]
    print(f"\n{per_batch} backtests per member, for both methods. Members:")
    print(pd.DataFrame(table)[columns].round(3).to_string(index=False))
    print(f"\nVote, long when at least {ga['vote']} of {len(members)} members are long:")
    print(pd.DataFrame(summary).T.drop(columns="long", errors="ignore").round(3).to_string())
    print(f"\nSaved {(out_dir / 'best.yaml').relative_to(ROOT)}")

if __name__ == "__main__":
    main()
