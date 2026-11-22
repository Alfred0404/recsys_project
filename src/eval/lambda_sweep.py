"""Sweep the MPT weight lambda and report the relevance vs diversification trade-off.

Reads the artifacts of `python -m src.train.run` (model.npz) and re-ranks the same
test users for each lambda. Every row shares the split, candidates and risk filter,
so only the re-ranking weight changes.
"""

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from src.eval.finance import evaluate_reranking
from src.eval.metrics import evaluate

DEFAULT_LAMBDAS = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)


def diversity(rankings: dict, categories: dict[str, str], k: int = 10) -> dict:
    """Average category coverage and concentration (HHI) of each user's top-k.

    Coverage is the number of distinct categories; HHI is the sum of squared
    category shares (1 = everything in one category). Unknown categories are
    grouped as "unknown". Users without suggestions are skipped.
    """
    coverage, hhi = [], []
    for items in rankings.values():
        top = list(items[:k])
        if not top:
            continue
        counts = Counter(categories.get(isin, "unknown") for isin in top)
        shares = np.array(list(counts.values()), dtype=float) / len(top)
        coverage.append(len(counts))
        hhi.append(float((shares**2).sum()))
    return {
        "mean_categories_top10": float(np.mean(coverage)) if coverage else None,
        "mean_hhi_top10": float(np.mean(hhi)) if hhi else None,
    }


def sweep(scored, tx, cutoff, processed, test, warm_users, lambdas=DEFAULT_LAMBDAS) -> list[dict]:
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        categories = None
        for lam in lambdas:
            summary, rankings = evaluate_reranking(scored, tx, cutoff, processed, scratch, warm_users, lam)
            if categories is None:
                assets = pd.read_parquet(scratch / "finance" / "assets.parquet")
                column = "assetSubCategory" if "assetSubCategory" in assets else "assetCategory"
                categories = assets.set_index("ISIN")[column].dropna().to_dict()
            ranked = rankings["mpt_risk"]
            metrics = evaluate(ranked, test)
            variance = summary["paired_top1_variance"]
            rows.append({
                "lambda": lam,
                "ndcg@10": metrics["ndcg@10"],
                "recall@20": metrics["recall@20"],
                "coverage_users": metrics["coverage_users"],
                "above_ceiling_rate": summary["top10_risk"]["mpt_risk"]["violation_rate_known"],
                "variance_change_top1": variance["mpt_risk_mean_change"],
                **diversity(ranked, categories),
            })
    return rows


def main():
    from src.train.run import Experiment

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("dataset/processed"))
    parser.add_argument("--experiment-dir", type=Path, default=Path("dataset/experiment"))
    parser.add_argument("--lambdas", type=float, nargs="+", default=list(DEFAULT_LAMBDAS))
    args = parser.parse_args()
    if any(not 0 <= lam <= 1 for lam in args.lambdas):
        parser.error("Every lambda must be between zero and one.")

    tx = pd.read_parquet(args.processed_dir / "transactions.parquet")
    saved = np.load(args.experiment_dir / "model.npz", allow_pickle=False)
    experiment = Experiment.from_transactions(
        tx, str(saved["train_cutoff"]), str(saved["test_cutoff"]),
    )
    # Same candidates as the training run: full catalogue, purchase history masked.
    scored = experiment.rank(
        experiment.test, (saved["user_embeddings"], saved["item_embeddings"]),
        experiment.test_history, k=len(experiment.item_index),
    )
    rows = sweep(scored, tx, experiment.t2, args.processed_dir, experiment.test,
                 set(experiment.user_index), args.lambdas)
    table = pd.DataFrame(rows)
    out = args.experiment_dir / "lambda_sweep"
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "lambda_sweep.csv", index=False)
    (out / "lambda_sweep.json").write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(table.to_string(index=False, float_format=lambda value: f"{value:.4f}"))


if __name__ == "__main__":
    main()
