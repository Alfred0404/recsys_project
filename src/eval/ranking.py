"""Rank the train catalogue while excluding all purchases before the evaluation cutoff."""

from collections.abc import Iterable

import numpy as np
import pandas as pd


def purchase_history(seen: pd.DataFrame) -> dict[str, set[str]]:
    return seen.groupby("customerID")["ISIN"].agg(set).to_dict()


def popularity_order(train: pd.DataFrame, item_ids: list[str]) -> np.ndarray:
    counts = train.drop_duplicates(["customerID", "ISIN"])["ISIN"].value_counts()
    return np.array(sorted(range(len(item_ids)), key=lambda i: (-counts[item_ids[i]], item_ids[i])))


def rank_embeddings(
    users: Iterable[str],
    user_embeddings: np.ndarray,
    item_embeddings: np.ndarray,
    user_index: dict[str, int],
    item_index: dict[str, int],
    history: dict[str, set[str]],
    popular_order: np.ndarray,
    k: int = 100,
    batch_size: int = 256,
) -> dict[str, list[tuple[str, float]]]:
    """Use learned user embeddings, or an average over a new user's known purchases.

    A new user without matching history falls back to train popularity. Keep scores
    alongside ISINs so that re-ranking uses the exact same candidates.
    """
    users = list(users)
    items = np.array(list(item_index))
    # Score columns follow item_index values, even if the caller's dict was reordered.
    items = items[np.argsort(list(item_index.values()))]
    popularity_scores = np.empty(len(items), dtype=np.float32)
    popularity_scores[popular_order] = -np.arange(len(items), dtype=np.float32)
    rankings = {}
    for start in range(0, len(users), batch_size):
        batch = users[start:start + batch_size]
        vectors = np.zeros((len(batch), item_embeddings.shape[1]), dtype=item_embeddings.dtype)
        excluded = []
        fallback = []
        for row, user in enumerate(batch):
            known = sorted(item_index[item] for item in history.get(user, ()) if item in item_index)
            excluded.append(known)
            if user in user_index:
                vectors[row] = user_embeddings[user_index[user]]
            elif known:
                vectors[row] = item_embeddings[known].mean(axis=0)
            else:
                fallback.append(row)
        scores = vectors @ item_embeddings.T
        scores[fallback] = popularity_scores
        for row, known in enumerate(excluded):
            scores[row, known] = -np.inf

        order = np.argsort(-scores, axis=1, kind="stable")[:, :k]
        for row, user in enumerate(batch):
            rankings[user] = [
                (items[i].item(), float(scores[row, i]))
                for i in order[row]
                if np.isfinite(scores[row, i])
            ]
    return rankings


def ordered_isins(scored: dict[str, list[tuple[str, float]]], k: int | None = None) -> dict[str, list[str]]:
    return {user: [isin for isin, _ in entries[:k]] for user, entries in scored.items()}
