"""Train and evaluate the FAR-Trans experiment using the temporal protocol.

Prepare typed input tables with python -m src.data.load_and_check, then run
python -m src.train.run. All outputs go under the local, ignored dataset directory.
"""

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.nn import functional as F

from src.eval.metrics import evaluate, most_popular_ranking, random_ranking
from src.eval.ranking import ordered_isins, popularity_order, purchase_history, rank_embeddings
from src.eval.split import COLS, check_no_leak, default_cutoffs, temporal_split
from src.graph.build import build_graph
from src.models.nlgcl import NLGCL


class NegativeSampler:
    """Uniformly sample the complement of each user's known positives."""

    def __init__(self, users, seen: dict[int, set[int]], n_items: int):
        order = np.argsort(users, kind="stable")
        ordered_users = users[order]
        boundaries = np.flatnonzero(np.diff(ordered_users)) + 1
        self.groups = []
        self.eligible = np.ones(len(users), dtype=bool)
        for rows in np.split(order, boundaries):
            if not len(rows):
                continue
            positive = np.array(sorted(seen[users[rows[0]]]), dtype=np.int64)
            remaining = n_items - len(positive)
            if not remaining:
                self.eligible[rows] = False
                continue
            # Positions in a compressed catalogue skip every known positive.
            self.groups.append((rows, positive - np.arange(len(positive)), remaining))

    def draw(self, rng: np.random.Generator) -> np.ndarray:
        samples = np.full(len(self.eligible), -1, dtype=np.int64)
        for rows, skips, count in self.groups:
            draw = rng.integers(count, size=len(rows))
            samples[rows] = draw + np.searchsorted(skips, draw, side="right")
        return samples


def indexed_history(history, user_index, item_index):
    return {
        user_index[user]: {item_index[item] for item in items if item in item_index}
        for user, items in history.items()
        if user in user_index
    }


@dataclass
class Experiment:
    edge_index: torch.Tensor
    user_index: dict[str, int]
    item_index: dict[str, int]
    popular: np.ndarray
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    train_history: dict[str, set[str]]
    test_history: dict[str, set[str]]
    t1: pd.Timestamp
    t2: pd.Timestamp

    @classmethod
    def from_transactions(cls, transactions: pd.DataFrame, t1=None, t2=None):
        buys = transactions.loc[transactions["transactionType"] == "Buy", COLS].drop_duplicates()
        if buys.empty:
            raise ValueError("No purchases found; check the FAR-Trans input tables.")
        d1, d2 = default_cutoffs(buys)
        t1 = pd.Timestamp(t1) if t1 is not None else d1
        t2 = pd.Timestamp(t2) if t2 is not None else d2
        train, validation, test = temporal_split(buys, t1, t2)
        if any(frame.empty for frame in (train, validation, test)):
            raise ValueError("Each temporal split needs purchases; check data and cutoffs.")
        check_no_leak(train, validation, test)
        edge_index, user_index, item_index = build_graph(train)
        if len(item_index) < 2:
            raise ValueError("BPR requires at least two assets in the train catalogue.")
        popular = popularity_order(train, list(item_index))
        return cls(
            edge_index,
            user_index,
            item_index,
            popular,
            train,
            validation,
            test,
            purchase_history(train),
            purchase_history(buys[buys["timestamp"] < t2]),
            t1,
            t2,
        )

    def rank(self, targets, embeddings, history, k=100):
        return rank_embeddings(
            sorted(targets["customerID"].unique()),
            *embeddings,
            self.user_index,
            self.item_index,
            history,
            self.popular,
            k=k,
        )


def validation_triplets(experiment: Experiment, seed: int):
    validation = experiment.validation
    u = validation["customerID"].map(experiment.user_index)
    i = validation["ISIN"].map(experiment.item_index)
    available = u.notna() & i.notna()
    users = u[available].to_numpy(dtype=np.int64)
    positive = i[available].to_numpy(dtype=np.int64)
    known = indexed_history(experiment.test_history, experiment.user_index, experiment.item_index)
    sampler = NegativeSampler(users, known, len(experiment.item_index))
    usable = sampler.eligible
    if not usable.any():
        raise ValueError("No validation triplets: no warm users with known assets and available negatives.")
    negative = sampler.draw(np.random.default_rng(seed))
    return users[usable], positive[usable], negative[usable]


@torch.no_grad()
def embeddings_for(model, experiment: Experiment):
    model.eval()
    return tuple(embedding.cpu().numpy() for embedding in model(experiment.edge_index))


def bpr_validation_loss(embeddings, triplets):
    users, positive, negative = triplets
    user_vectors = embeddings[0][users]
    margin = (user_vectors * (embeddings[1][positive] - embeddings[1][negative])).sum(axis=1)
    return float(F.softplus(-torch.from_numpy(margin)).mean())


def train_model(experiment: Experiment, name: str, contrastive_weight: float, args):
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    contrast_rng = torch.Generator().manual_seed(args.seed)
    model = NLGCL(
        len(experiment.user_index),
        len(experiment.item_index),
        dim=args.dim,
        n_layers=args.layers,
        contrastive_weight=contrastive_weight,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    users, positive = experiment.edge_index
    train_seen = indexed_history(experiment.train_history, experiment.user_index, experiment.item_index)
    sampler = NegativeSampler(users.numpy(), train_seen, len(experiment.item_index))
    eligible = np.flatnonzero(sampler.eligible)
    if not len(eligible):
        raise ValueError("No training users have available negative items.")
    val_triplets = validation_triplets(experiment, args.seed + 1)
    fixed_negatives = sampler.draw(np.random.default_rng(args.seed + 2))
    train_triplets = (users.numpy()[eligible], positive.numpy()[eligible], fixed_negatives[eligible])
    best_key = (-np.inf, -np.inf)
    best_state = None
    best_epoch = 0
    rows = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        negatives = torch.from_numpy(sampler.draw(rng))
        totals = np.zeros(3)
        for indices in np.array_split(rng.permutation(eligible), min(args.steps, len(eligible))):
            optimizer.zero_grad(set_to_none=True)
            loss, bpr, contrast = model.loss_parts(
                users[indices], positive[indices], negatives[indices], experiment.edge_index, generator=contrast_rng,
            )
            if not torch.isfinite(loss):
                raise RuntimeError(f"Non-finite {name} loss at epoch {epoch}.")
            loss.backward()
            optimizer.step()
            totals += len(indices) * np.array([loss.item(), bpr.item(), contrast.item()])

        objective, train_step_bpr, train_contrast = totals / len(eligible)
        embeddings = embeddings_for(model, experiment)
        train_bpr = bpr_validation_loss(embeddings, train_triplets)
        val_bpr = bpr_validation_loss(embeddings, val_triplets)
        validation = experiment.rank(experiment.validation, embeddings, experiment.train_history, k=20)
        metrics = evaluate(ordered_isins(validation), experiment.validation)
        rows.append({
            "model": name,
            "epoch": epoch,
            "train_bpr": train_bpr,
            "validation_bpr": val_bpr,
            "objective": objective,
            "train_step_bpr": train_step_bpr,
            "train_contrastive": train_contrast,
            "validation_ndcg@10": metrics["ndcg@10"],
            "validation_recall@20": metrics["recall@20"],
        })
        print(
            f"{name} epoch {epoch:02d} train BPR={train_bpr:.4f} val BPR={val_bpr:.4f} "
            f"NDCG@10={metrics['ndcg@10']:.4f} Recall@20={metrics['recall@20']:.4f}",
            flush=True,
        )
        key = (metrics["ndcg@10"], metrics["recall@20"])
        if key > best_key:
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
            best_key = key
            best_epoch = epoch
        if epoch >= best_epoch + args.patience:
            break

    model.load_state_dict(best_state)
    return model, rows, best_epoch, len(val_triplets[0])


def test_statistics(experiment: Experiment):
    test = experiment.test
    items_known = test["ISIN"].isin(experiment.item_index)
    users_known = test["customerID"].isin(experiment.user_index)
    return {
        "train_rows": len(experiment.train),
        "validation_rows": len(experiment.validation),
        "test_rows": len(test),
        "train_edges": experiment.edge_index.shape[1],
        "train_users": len(experiment.user_index),
        "train_assets": len(experiment.item_index),
        "test_users": int(test["customerID"].nunique()),
        "test_cold_users": int(test.loc[~users_known, "customerID"].nunique()),
        "test_targets_in_catalogue": int(items_known.sum()),
    }


def run(args):
    start = time.perf_counter()
    torch.set_num_threads(args.threads)
    tx = pd.read_parquet(args.processed_dir / "transactions.parquet")
    experiment = Experiment.from_transactions(tx, args.t1, args.t2)
    print(f"Train cutoff {experiment.t1.isoformat()}, test cutoff {experiment.t2.isoformat()}", flush=True)
    print(test_statistics(experiment), flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    nlgcl, loss, selected, val_pairs = train_model(experiment, "NLGCL", args.contrastive_weight, args)
    lightgcn, ablation_loss, ablation_selected, _ = train_model(experiment, "LightGCN", 0.0, args)

    # Selection has finished before generating any rankings on the test period.
    nlgcl_embeddings = embeddings_for(nlgcl, experiment)
    lightgcn_embeddings = embeddings_for(lightgcn, experiment)
    scored = experiment.rank(experiment.test, nlgcl_embeddings, experiment.test_history)
    light_ranked = experiment.rank(experiment.test, lightgcn_embeddings, experiment.test_history, k=20)
    users = sorted(experiment.test["customerID"].unique())
    available = set(experiment.item_index)
    # The baseline and learned model exclude the same complete purchase histories.
    history = pd.concat([experiment.train, experiment.validation], ignore_index=True)
    baseline_random = random_ranking(users, available, history, seed=args.seed)
    baseline_popular = most_popular_ranking(users, experiment.train, history)
    rankings = {
        "random": baseline_random,
        "most_popular": baseline_popular,
        "lightgcn": ordered_isins(light_ranked),
        "nlgcl": ordered_isins(scored),
    }
    summary = {
        "seed": args.seed,
        "training": {
            "dim": args.dim,
            "learning_rate": args.lr,
            "layers": args.layers,
            "contrastive_weight": args.contrastive_weight,
            "steps_per_epoch": args.steps,
            "evaluation_bpr_pairs": val_pairs,
            "nlgcl_best_epoch": selected,
            "lightgcn_best_epoch": ablation_selected,
        },
        "cutoffs": {"train": experiment.t1.isoformat(), "test": experiment.t2.isoformat()},
        "counts": test_statistics(experiment),
    }
    if not args.skip_finance:
        from src.eval.finance import evaluate_reranking

        finance, financial_rankings = evaluate_reranking(
            scored, tx, experiment.t2, args.processed_dir, args.out, set(experiment.user_index), args.mpt_weight,
        )
        summary["finance"] = finance
        rankings.update(financial_rankings)
    summary["test_metrics"] = {name: evaluate(ranked, experiment.test) for name, ranked in rankings.items()}
    summary["elapsed_seconds"] = time.perf_counter() - start

    pd.DataFrame(loss + ablation_loss).to_csv(args.out / "loss.csv", index=False)
    torch.save(nlgcl.state_dict(), args.out / "checkpoint.pt")
    np.savez_compressed(
        args.out / "model.npz",
        user_ids=np.array(list(experiment.user_index), dtype=str),
        item_ids=np.array(list(experiment.item_index), dtype=str),
        user_embeddings=nlgcl_embeddings[0],
        item_embeddings=nlgcl_embeddings[1],
        popular_order=experiment.popular,
        train_cutoff=experiment.t1.isoformat(),
        test_cutoff=experiment.t2.isoformat(),
        mpt_weight=args.mpt_weight,
    )
    (args.out / "metrics.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary["test_metrics"], indent=2), flush=True)
    print(f"Experiment complete in {summary['elapsed_seconds']:.1f}s. Outputs: {args.out}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("dataset/processed"))
    parser.add_argument("--out", type=Path, default=Path("dataset/experiment"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--dim", type=int, default=32)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--lr", type=float, default=0.02)
    parser.add_argument("--contrastive-weight", type=float, default=0.05)
    parser.add_argument("--mpt-weight", type=float, default=0.25, help="Pre-specified MPT weight for the test ablation")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--t1", help="Manual train cutoff (before validation)")
    parser.add_argument("--t2", help="Manual test cutoff")
    parser.add_argument("--skip-finance", action="store_true", help="Skip the financial ablation and serving snapshot")
    args = parser.parse_args()
    if min(args.epochs, args.patience, args.dim, args.layers, args.steps, args.threads) < 1:
        parser.error("Epochs, patience, dimension, layers, steps and threads must be positive.")
    if not np.isfinite([args.lr, args.contrastive_weight]).all() or args.lr <= 0 or args.contrastive_weight <= 0:
        parser.error("Learning rate and contrastive weight must be finite and positive.")
    if not 0 <= args.mpt_weight <= 1:
        parser.error("MPT weight must be between zero and one.")
    run(args)


if __name__ == "__main__":
    main()
