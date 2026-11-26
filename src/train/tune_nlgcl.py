"""Tune the NLGCL weight and temperature using validation rankings.

Supply a grid of positive weights and temperatures. Evaluate the chosen setting
on test separately with python -m src.train.run and the settings in selected.json.
"""

import argparse
import json
from itertools import product
from math import isfinite
from pathlib import Path

import pandas as pd
import torch

from src.train.run import DEFAULT_TEMPERATURE, Experiment, train_model


def validation_row(experiment, model_name, weight, temperature, args):
    fit_args = argparse.Namespace(**vars(args))
    fit_args.temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
    _, history, epoch, _ = train_model(experiment, model_name, weight, fit_args)
    best = history[epoch - 1]
    return {
        "model": model_name,
        "contrastive_weight": weight,
        "temperature": temperature,
        "best_epoch": epoch,
        "ndcg@10": best["validation_ndcg@10"],
        "recall@20": best["validation_recall@20"],
    }


def tune(experiment, args):
    weights = sorted(set(args.contrastive_weights))
    temperatures = sorted(set(args.temperatures))
    rows = [
        validation_row(experiment, "NLGCL", weight, temperature, args)
        for weight, temperature in product(weights, temperatures)
    ]
    # The sorted grid makes lower weight, then lower temperature win exact ties.
    selected = max(rows, key=lambda row: (row["ndcg@10"], row["recall@20"]))
    baseline = validation_row(experiment, "LightGCN", 0.0, None, args)
    return [baseline, *rows], selected, baseline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("dataset/processed"))
    parser.add_argument("--out", type=Path, default=Path("dataset/experiment/nlgcl_tuning"))
    parser.add_argument("--contrastive-weights", type=float, nargs="+", required=True)
    parser.add_argument("--temperatures", type=float, nargs="+", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--t1", help="Manual train cutoff (before validation)")
    parser.add_argument("--t2", help="Manual test cutoff (before the held-out period)")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--dim", type=int, default=32)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--lr", type=float, default=0.02)
    args = parser.parse_args()
    if min(args.epochs, args.patience, args.dim, args.layers, args.steps, args.threads) < 1:
        parser.error("Epochs, patience, dimension, layers, steps and threads must be positive.")
    if not all(isfinite(value) and value > 0 for value in (args.lr, *args.contrastive_weights, *args.temperatures)):
        parser.error("Learning rate, contrastive weights and temperatures must be finite and positive.")
    if not 0 <= args.seed < 2**64:
        parser.error("Seed must be an unsigned 64-bit integer.")

    torch.set_num_threads(args.threads)
    transactions = pd.read_parquet(args.processed_dir / "transactions.parquet")
    experiment = Experiment.from_transactions(transactions, args.t1, args.t2, validation_only=True)
    rows, selected, baseline = tune(experiment, args)

    args.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.out / "validation_grid.csv", index=False)
    training_options = ("epochs", "patience", "dim", "layers", "steps", "threads", "lr")
    result = {
        "selection_metrics": ["ndcg@10", "recall@20"],
        "selected": selected,
        "lightgcn": baseline,
        "seed": args.seed,
        "cutoffs": {"train": experiment.t1.isoformat(), "test": experiment.t2.isoformat()},
        "training": {key: getattr(args, key) for key in training_options},
    }
    (args.out / "selected.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(pd.DataFrame(rows).to_string(index=False))
    print("Selected:", json.dumps(selected))


if __name__ == "__main__":
    main()
