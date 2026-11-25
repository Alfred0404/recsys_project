"""Choose the MPT weight lambda and the expected-return shrinkage on the validation period.

Reads model.npz from `python -m src.train.run`, scores the validation users from the
train cutoff (train graph, train purchase history, finance tables before the train
cutoff) and re-ranks them for every (lambda, shrinkage) pair. The test period is not read.

Selection rule, fixed before looking at the grid: among the settings whose validation
NDCG@10 stays at or above 95% of the risk filter alone, keep the one with the largest
mean reduction of top-1 portfolio variance relative to the filter alone. Ties go to the
smaller lambda, then the smaller shrinkage.
"""

import argparse
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from src.eval.finance import evaluate_reranking, snapshot
from src.eval.lambda_sweep import diversity
from src.eval.metrics import evaluate

LAMBDAS = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)
SHRINKAGES = (0.0, 0.5, 0.9, 1.0)
NDCG_FLOOR = 0.95


def score_validation(tx: pd.DataFrame, model_path: Path):
    from src.train.run import Experiment

    with np.load(model_path, allow_pickle=False) as saved:
        experiment = Experiment.from_transactions(tx, str(saved["train_cutoff"]), str(saved["test_cutoff"]))
        for field, rebuilt in (("user_ids", experiment.user_index), ("item_ids", experiment.item_index)):
            if not np.array_equal(saved[field], list(rebuilt)):
                raise ValueError(f"Model {field} do not match the rebuilt training split.")
        scored = experiment.rank(
            experiment.validation, (saved["user_embeddings"], saved["item_embeddings"]),
            experiment.train_history, k=len(experiment.item_index),
        )
    return experiment, scored


def grid(scored, tx, experiment, processed, lambdas=LAMBDAS, shrinkages=SHRINKAGES) -> list[dict]:
    tables = snapshot(tx, experiment.t1, processed)
    categories = tables["assets"].set_index("ISIN")["assetSubCategory"].dropna().to_dict()
    warm = set(experiment.user_index)
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        for shrinkage in shrinkages:
            for lam in lambdas:
                if lam == 0 and shrinkage != shrinkages[0]:
                    continue  # lambda = 0 ignores the MPT score
                summary, rankings = evaluate_reranking(
                    scored, tx, experiment.t1, processed, Path(scratch), warm, lam,
                    mu_shrinkage=shrinkage, tables=tables,
                )
                variance = summary["paired_top1_variance"]
                rows.append({
                    "lambda": lam,
                    "mu_shrinkage": shrinkage,
                    "ndcg@10": evaluate(rankings["mpt_risk"], experiment.validation)["ndcg@10"],
                    "filter_ndcg@10": evaluate(rankings["risk_only"], experiment.validation)["ndcg@10"],
                    "variance_vs_filter": variance["mpt_minus_risk_only"],
                    "paired_users": variance["users"],
                    **diversity(rankings["mpt_risk"], categories),
                })
    return rows


def select(rows: list[dict], floor: float = NDCG_FLOOR) -> dict:
    eligible = [row for row in rows if row["ndcg@10"] >= floor * row["filter_ndcg@10"]]
    return min(eligible, key=lambda row: (row["variance_vs_filter"], row["lambda"], row["mu_shrinkage"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("dataset/processed"))
    parser.add_argument("--experiment-dir", type=Path, default=Path("dataset/experiment"))
    args = parser.parse_args()
    tx = pd.read_parquet(args.processed_dir / "transactions.parquet")
    experiment, scored = score_validation(tx, args.experiment_dir / "model.npz")
    rows = grid(scored, tx, experiment, args.processed_dir)
    chosen = select(rows)
    out = args.experiment_dir / "tuning"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "validation_grid.csv", index=False)
    (out / "selected.json").write_text(json.dumps(chosen, indent=2) + "\n", encoding="utf-8")
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda value: f"{value:.5f}"))
    print("Selected:", json.dumps(chosen))


if __name__ == "__main__":
    main()
