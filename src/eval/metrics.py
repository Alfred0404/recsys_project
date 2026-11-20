"""Ranking evaluation (NDCG@10, Recall@20) and the random / most-popular baselines.

`ranked` maps customerID -> list of ISIN, best first. `test` is a DataFrame with
[customerID, ISIN, ...]: the held-out new acquisitions. Customers in test without a
ranking score 0, so a model cannot look better by skipping hard users.
"""
import math
import random

import pandas as pd


def ndcg_at_k(ranking: list, relevant: set, k: int) -> float:
    dcg = sum(1 / math.log2(i + 2) for i, isin in enumerate(ranking[:k]) if isin in relevant)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal if ideal else 0.0


def recall_at_k(ranking: list, relevant: set, k: int) -> float:
    return len(set(ranking[:k]) & relevant) / len(relevant) if relevant else 0.0


def evaluate(ranked: dict, test: pd.DataFrame, ndcg_k: int = 10, recall_k: int = 20) -> dict:
    targets = test.groupby("customerID")["ISIN"].agg(set)
    ndcg, recall = [], []
    for user, relevant in targets.items():
        ranking = list(ranked.get(user, []))
        ndcg.append(ndcg_at_k(ranking, relevant, ndcg_k))
        recall.append(recall_at_k(ranking, relevant, recall_k))
    n = len(targets)
    return {
        f"ndcg@{ndcg_k}": sum(ndcg) / n if n else 0.0,
        f"recall@{recall_k}": sum(recall) / n if n else 0.0,
        "n_users": n,
        "coverage_users": sum(1 for u in targets.index if ranked.get(u)) / n if n else 0.0,
    }


def _owned(seen: pd.DataFrame) -> dict:
    return seen.groupby("customerID")["ISIN"].agg(set).to_dict()


def random_ranking(users, items, seen: pd.DataFrame, k: int = 20, seed: int = 0) -> dict:
    """k random assets per user, never one the user already owns (`seen` = train, plus val for test)."""
    rng, owned, items = random.Random(seed), _owned(seen), sorted(set(items))
    out = {}
    for u in users:
        pool = [i for i in items if i not in owned.get(u, set())]
        out[u] = rng.sample(pool, min(k, len(pool)))
    return out


def most_popular_ranking(users, train: pd.DataFrame, seen: pd.DataFrame | None = None, k: int = 20) -> dict:
    """The k assets with most distinct holders in train, skipping what the user already owns."""
    seen = train if seen is None else seen
    popularity = train.drop_duplicates(["customerID", "ISIN"])["ISIN"].value_counts()
    order = sorted(popularity.index, key=lambda i: (-popularity[i], i))
    owned = _owned(seen)
    return {u: [i for i in order if i not in owned.get(u, set())][:k] for u in users}
