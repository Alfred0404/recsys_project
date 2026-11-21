"""LightGCN with the heterogeneous neighbour-layer objective of Xu et al.

The contrastive denominator uses a shared sample of opposite-type nodes to
bound CPU memory. Positive edges come from the original training graph.
See https://doi.org/10.1145/3705328.3748059, section 4.
"""

import math

import torch
from torch import nn
from torch.nn import functional as F

from src.graph.build import to_symmetric


class NLGCL(nn.Module):
    def __init__(
        self,
        n_users: int,
        n_items: int,
        dim: int = 32,
        n_layers: int = 2,
        contrastive_weight: float = 0.05,
        *,
        temperature: float = 0.2,
        contrastive_layers: int = 1,
        contrastive_candidates: int = 128,
        contrastive_edges: int = 4096,
        regularization: float = 1e-4,
    ):
        super().__init__()
        if min(n_users, n_items, dim, contrastive_candidates, contrastive_edges) <= 0:
            raise ValueError("Node counts, embedding size, and sample sizes must be positive")
        if n_layers < 0 or contrastive_layers < 0 or temperature <= 0 or not math.isfinite(temperature):
            raise ValueError("Layer counts must be non-negative and temperature must be positive")
        if any(not math.isfinite(weight) or weight < 0 for weight in (contrastive_weight, regularization)):
            raise ValueError("Loss weights must be non-negative")

        self.n_users = n_users
        self.n_items = n_items
        self.n_layers = n_layers
        self.contrastive_weight = contrastive_weight
        self.temperature = temperature
        self.contrastive_layers = min(contrastive_layers, n_layers)
        self.contrastive_candidates = contrastive_candidates
        self.contrastive_edges = contrastive_edges
        self.regularization = regularization
        self.user_embedding = nn.Embedding(n_users, dim)
        self.item_embedding = nn.Embedding(n_items, dim)
        nn.init.xavier_uniform_(self.user_embedding.weight)
        nn.init.xavier_uniform_(self.item_embedding.weight)

    def _propagate(self, edge_index: torch.Tensor):
        """Return the initial and propagated embeddings and original node degrees."""
        initial = torch.cat((self.user_embedding.weight, self.item_embedding.weight))
        edges = to_symmetric(edge_index, self.n_users)
        degree = torch.bincount(edges[0], minlength=len(initial)).to(initial.dtype)
        scale = degree.clamp_min(1).rsqrt()
        weights = scale[edges[0]] * scale[edges[1]]
        graph = torch.sparse_coo_tensor(
            edges, weights, (len(initial), len(initial)), check_invariants=True
        ).coalesce()

        layers = [initial]
        for _ in range(self.n_layers):
            layers.append(torch.sparse.mm(graph, layers[-1]))
        return layers, degree

    def _readout(self, layers: list[torch.Tensor]):
        return torch.stack(layers).mean(dim=0).split((self.n_users, self.n_items))

    def forward(self, edge_index: torch.Tensor):
        """Return one matrix per node type; item indices never need an offset."""
        layers, _ = self._propagate(edge_index)
        return self._readout(layers)

    def _contrastive_direction(
        self,
        anchor: torch.Tensor,
        target: torch.Tensor,
        anchor_index: torch.Tensor,
        positive_index: torch.Tensor,
        degree: torch.Tensor,
        generator: torch.Generator | None,
    ) -> torch.Tensor:
        sample_size = min(len(target), self.contrastive_candidates)
        sample = torch.randperm(len(target), device=target.device, generator=generator)[:sample_size]

        anchors = anchor[anchor_index]
        positive = (anchors * target[positive_index]).sum(dim=1) / self.temperature
        sampled_logits = (anchors @ target[sample].T) / self.temperature
        # Append the edge's positive to the denominator exactly once. Other
        # neighbours can occur in the denominator, as in the full softmax.
        sampled_logits = sampled_logits.masked_fill(
            positive_index[:, None] == sample[None, :], -torch.inf
        )
        denominator = torch.cat((positive[:, None], sampled_logits), dim=1).logsumexp(dim=1)
        # Each edge represents one of an anchor's neighbours. Inverse degree
        # weighting keeps hubs from dominating either direction of the loss.
        weight = degree[anchor_index].reciprocal()
        return ((denominator - positive) * weight).sum() / weight.sum()

    def _contrastive_loss(
        self,
        layers: list[torch.Tensor],
        degree: torch.Tensor,
        edge_index: torch.Tensor,
        generator: torch.Generator | None,
    ) -> torch.Tensor:
        users, items = edge_index
        if len(users) > self.contrastive_edges:
            keep = torch.randperm(len(users), device=users.device, generator=generator)
            keep = keep[: self.contrastive_edges]
            users, items = users[keep], items[keep]

        counts = (self.n_users, self.n_items)
        user_degree, item_degree = degree.split(counts)
        loss = layers[0].new_zeros(())
        for index in range(self.contrastive_layers):
            user, item = layers[index].split(counts)
            user_next, item_next = layers[index + 1].split(counts)
            loss = loss + self._contrastive_direction(
                user, item_next, users, items, user_degree, generator
            )
            loss = loss + self._contrastive_direction(
                item, user_next, items, users, item_degree, generator
            )
        return loss / self.contrastive_layers

    def loss_parts(
        self,
        users: torch.Tensor,
        pos: torch.Tensor,
        neg: torch.Tensor,
        edge_index: torch.Tensor,
        *,
        generator: torch.Generator | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return total loss, unregularized BPR, and neighbour-layer loss."""
        if not len(users):
            raise ValueError("BPR requires at least one positive/negative training pair")

        layers, degree = self._propagate(edge_index)
        user_emb, item_emb = self._readout(layers)
        margin = (user_emb[users] * (item_emb[pos] - item_emb[neg])).sum(dim=1)
        bpr = F.softplus(-margin).mean()
        regularization = (
            self.user_embedding(users).square().sum(dim=1)
            + self.item_embedding(pos).square().sum(dim=1)
            + self.item_embedding(neg).square().sum(dim=1)
        ).mean() / 2
        contrastive = bpr.new_zeros(())
        if self.contrastive_weight and self.contrastive_layers and edge_index.shape[1]:
            contrastive = self._contrastive_loss(layers, degree, edge_index, generator)
        total = bpr + self.regularization * regularization + self.contrastive_weight * contrastive
        return total, bpr, contrastive

    def loss(
        self,
        users: torch.Tensor,
        pos: torch.Tensor,
        neg: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        return self.loss_parts(users, pos, neg, edge_index)[0]
