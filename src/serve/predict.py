"""Score a portfolio against frozen model embeddings and financial estimates."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.llm.profile import Profile, explain
from src.rerank.mpt import mpt_rerank, portfolio_impact, risk_filter


class Recommender:
    def __init__(self, model_path: Path, finance_dir: Path):
        with np.load(model_path, allow_pickle=False) as model:
            item_ids = model["item_ids"].tolist()
            self.item_embeddings = model["item_embeddings"].astype(np.float32)
            self.popular_order = model["popular_order"]
            self.mpt_weight = float(model["mpt_weight"].item()) if "mpt_weight" in model else 0.25
        if not 0 <= self.mpt_weight <= 1:
            raise ValueError("The model MPT weight must be in [0, 1]")
        self.item_index = {isin: i for i, isin in enumerate(item_ids)}
        if len(item_ids) != len(self.item_index) or self.item_embeddings.ndim != 2:
            raise ValueError("The model must contain a two-dimensional embedding for each distinct ISIN")
        if not np.isfinite(self.item_embeddings).all() or len(self.item_embeddings) != len(item_ids):
            raise ValueError("Invalid or missing model embeddings")
        if sorted(self.popular_order.tolist()) != list(range(len(item_ids))):
            raise ValueError("The model popularity order must list each distinct index once")
        self.item_ids = item_ids

        asset_risk = pd.read_parquet(finance_dir / "asset_risk.parquet")
        self.risk_classes = asset_risk.set_index("ISIN")["risk_class"].dropna().astype(int).to_dict()
        self.mu = pd.read_parquet(finance_dir / "mu.parquet")["mu"]
        self.sigma = pd.read_parquet(finance_dir / "sigma.parquet")
        assets = pd.read_parquet(finance_dir / "assets.parquet")
        self.names = assets.set_index("ISIN")["assetName"].dropna().astype(str).to_dict()

    def catalog(self) -> list[dict]:
        return [{"isin": isin, "name": self.names.get(isin, isin)} for isin in self.item_ids]

    def predict(self, holdings: dict[str, float], profile: Profile, k: int = 10) -> dict:
        known = [isin for isin in holdings if isin in self.item_index]
        if known:
            weights = np.asarray([holdings[isin] for isin in known], dtype=float)
            vectors = self.item_embeddings[[self.item_index[isin] for isin in known]]
            user_embedding = np.average(vectors, axis=0, weights=weights).astype(np.float32)
            scores = self.item_embeddings @ user_embedding
            order = np.argsort(-scores, kind="stable")
            ranking_source = "portfolio_embeddings"
        else:
            order = self.popular_order
            scores = np.empty(len(order))
            scores[order] = 1 - np.arange(len(order)) / max(1, len(order))
            ranking_source = "popularity"

        # The whole catalogue stays eligible so a low ceiling still fills k suggestions.
        candidates = [self.item_ids[i] for i in order if self.item_ids[i] not in holdings]
        candidates = risk_filter(candidates, self.risk_classes, profile.ceiling)
        relevance = {isin: float(scores[self.item_index[isin]]) for isin in candidates}
        # The covariance of a portfolio with unpriced positions is only partially observable.
        covered_portfolio = bool(holdings) and all(
            isin in self.sigma.index and isin in self.sigma.columns and isin in self.mu and np.isfinite(self.mu[isin])
            for isin in holdings
        )
        if covered_portfolio:
            candidates = mpt_rerank(candidates, relevance, holdings, self.mu, self.sigma, profile.gamma, self.mpt_weight)
            impact = portfolio_impact(candidates[:k], holdings, self.mu, self.sigma, profile.gamma)
            changes = impact["variance_change"].to_dict()
        else:
            changes = {}
        items = [
            {
                "isin": isin,
                "name": self.names.get(isin, isin),
                "score": relevance[isin],
                "risk_class": self.risk_classes[isin],
                "variance_change": float(changes[isin]) if isin in changes else None,
                "explanation": explain(self.risk_classes[isin], changes.get(isin)),
            }
            for isin in candidates[:k]
        ]
        return {
            "items": items,
            "ranking_source": ranking_source,
            "unrecognized_isins": [isin for isin in holdings if isin not in self.item_index],
        }
