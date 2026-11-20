"""Bipartite user-asset graph built from the TRAIN split only.

edge_index: torch.long [2, E]; row 0 = user index, row 1 = item index.
Item indices are NOT offset by n_users and the graph is NOT symmetrised
(one edge per distinct (customer, asset) pair). See README, "Précision sur edge_index".
"""
import pandas as pd
import torch


def build_graph(train: pd.DataFrame):
    """Return (edge_index, user2idx, item2idx). Indices follow sorted ID order, so runs are reproducible."""
    pairs = train[["customerID", "ISIN"]].drop_duplicates()
    user2idx = {u: i for i, u in enumerate(sorted(pairs["customerID"].unique()))}
    item2idx = {a: i for i, a in enumerate(sorted(pairs["ISIN"].unique()))}
    users = torch.as_tensor(pairs["customerID"].map(user2idx).to_numpy(), dtype=torch.long)
    items = torch.as_tensor(pairs["ISIN"].map(item2idx).to_numpy(), dtype=torch.long)
    return torch.stack([users, items]), user2idx, item2idx


def to_symmetric(edge_index: torch.Tensor, n_users: int) -> torch.Tensor:
    """Helper for models: single node space (items shifted by n_users) with both directions."""
    u, i = edge_index[0], edge_index[1] + n_users
    return torch.stack([torch.cat([u, i]), torch.cat([i, u])])
