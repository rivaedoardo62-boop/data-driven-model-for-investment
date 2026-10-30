"""Genetic algorithm (DEAP) that searches the windows, weights and threshold of the ensemble (see src/ensemble.py).

A genome is a list of genes in [0, 1], decoded into the parameters of the ensemble:

    4 windows    one per indicator, rounded to whole weeks within the bounds of config.yaml
    4 weights    in [-1, 1]: the sign says whether the indicator pushes towards long or towards flat
    1 threshold  in [-0.5, 0.5]: the score must exceed it to go long

Operators, the standard ones for genes with bounds:
    selection  tournament: draw k genomes at random and keep the best, repeated for the whole population
    crossover  simulated binary (SBX): two parents give two children with genes near theirs, inside [0, 1]
    mutation   polynomial: each gene changes with probability 1 / number of genes, by a small step inside [0, 1]
"""

import random

import numpy as np
from deap import algorithms, base, creator, tools

from src.ensemble import INDICATORS

N_GENES = 2 * len(INDICATORS) + 1
ETA_CROSSOVER = 15  # higher: children closer to the parents
ETA_MUTATION = 20  # higher: smaller mutations

creator.create("FitnessMax", base.Fitness, weights=(1.0,))  # one objective, maximized
creator.create("Individual", list, fitness=creator.FitnessMax)


def decode(genome: list[float], bounds: dict) -> dict:
    """Genes in [0, 1] -> windows (weeks), weights and threshold of the ensemble."""
    windows = {
        name: int(round(bounds[name][0] + gene * (bounds[name][1] - bounds[name][0])))
        for name, gene in zip(INDICATORS, genome)
    }
    weights = {name: round(2 * gene - 1, 4) for name, gene in zip(INDICATORS, genome[len(INDICATORS) :])}
    return {"windows": windows, "weights": weights, "threshold": round(genome[-1] - 0.5, 4)}


def run(evaluate, cfg: dict, seed: int):
    """One run of the genetic algorithm: returns the best genome found and the log of the generations."""
    random.seed(seed)  # DEAP draws its random numbers from the random module

    toolbox = base.Toolbox()
    toolbox.register("gene", random.random)
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.gene, N_GENES)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", lambda genome: (evaluate(genome),))
    toolbox.register("mate", tools.cxSimulatedBinaryBounded, eta=ETA_CROSSOVER, low=0.0, up=1.0)
    toolbox.register("mutate", tools.mutPolynomialBounded, eta=ETA_MUTATION, low=0.0, up=1.0, indpb=1 / N_GENES)
    toolbox.register("select", tools.selTournament, tournsize=cfg["tournament"])

    stats = tools.Statistics(lambda genome: genome.fitness.values[0])
    stats.register("max", np.max)
    stats.register("mean", np.mean)
    hall_of_fame = tools.HallOfFame(1)  # best genome ever evaluated, even if lost in a later generation

    _, log = algorithms.eaSimple(
        toolbox.population(cfg["population"]),
        toolbox,
        cxpb=cfg["crossover"],
        mutpb=cfg["mutation"],
        ngen=cfg["generations"],
        stats=stats,
        halloffame=hall_of_fame,
        verbose=False,
    )
    return hall_of_fame[0], log
