import numpy as np
import pandas as pd

from src.eval import finance
from src.eval.ranking import ordered_isins, rank_embeddings
from src.train.run import Experiment, NegativeSampler


def test_negatives_exclude_known_assets_and_skip_users_without_candidates():
    users = np.array([1, 0, 0, 1, 2, 2])
    seen = {0: {0, 1, 3}, 1: {1}, 2: {0, 1, 2, 3}}
    sampler = NegativeSampler(users, seen, 4)
    result = sampler.draw(np.random.default_rng(3))
    assert result[[1, 2]].tolist() == [2, 2]
    assert all(value in {0, 2, 3} for value in result[[0, 3]])
    assert result[[4, 5]].tolist() == [-1, -1]
    assert not sampler.eligible[[4, 5]].any()


def test_test_only_assets_and_users_never_enter_the_training_graph():
    data = pd.DataFrame(
        [
            ("warm", "A", "2022-01-01", "Buy"),
            ("other", "B", "2022-01-01", "Buy"),
            ("warm", "B", "2022-02-01", "Buy"),
            ("cold", "C", "2022-03-01", "Buy"),
            ("warm", "D", "2022-03-01", "Sell"),
        ],
        columns=["customerID", "ISIN", "timestamp", "transactionType"],
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    experiment = Experiment.from_transactions(data, "2022-02-01", "2022-03-01")
    assert list(experiment.item_index) == ["A", "B"]
    assert "cold" not in experiment.user_index
    assert experiment.train_history["warm"] == {"A"}
    assert experiment.test_history["warm"] == {"A", "B"}
    assert experiment.test["ISIN"].tolist() == ["C"]


def test_rankings_mask_history_for_warm_and_cold_users():
    scores = rank_embeddings(
        ["warm", "new", "empty"],
        np.array([[1.0, 0.0]]),
        np.array([[2.0, 1.0], [1.0, 1.0], [0.0, 1.0]]),
        {"warm": 0},
        {"A": 0, "B": 1, "C": 2},
        {"warm": {"A"}, "new": {"A", "unseen"}},
        np.array([2, 1, 0]),
        k=2,
    )
    assert ordered_isins(scores) == {"warm": ["B", "C"], "new": ["B", "C"], "empty": ["C", "B"]}


def test_finance_ignores_predicted_profiles_and_requires_full_price_coverage(monkeypatch, tmp_path):
    assets = ["A", "B", "H"]
    tables = {
        "mu": pd.DataFrame({"mu": [0.1, 0.2, 0.1]}, index=assets),
        "sigma": pd.DataFrame(np.eye(3), index=assets, columns=assets),
        "asset_risk": pd.DataFrame({"ISIN": assets, "risk_class": [7, 2, 2]}),
        "assets": pd.DataFrame({"ISIN": assets, "assetName": assets}),
        "holdings": pd.DataFrame({
            "customerID": ["observed", "partially_priced", "partially_priced"],
            "ISIN": ["H", "H", "unpriced"],
            "value": [100.0, 100.0, np.nan],
        }),
        "customers": pd.DataFrame({
            "customerID": ["observed", "partially_priced", "predicted"],
            "riskLevel": ["Aggressive", "Aggressive", "Predicted_Aggressive"],
        }),
    }
    monkeypatch.setattr(finance, "snapshot", lambda *_: tables)
    called = []

    def rerank(items, _relevance, weights, *_args, **_kwargs):
        called.append(weights)
        return items[::-1]

    monkeypatch.setattr(finance, "mpt_rerank", rerank)
    scored = {user: [("A", 1.0), ("B", 0.5)] for user in tables["customers"]["customerID"]}
    summary, ranked = finance.evaluate_reranking(
        scored, None, pd.Timestamp("2022-03-01"), tmp_path, tmp_path, {"observed", "partially_priced"},
    )
    assert called == [{"H": 100.0}]
    assert ranked["mpt_risk"] == {"observed": ["B", "A"], "partially_priced": ["A", "B"], "predicted": ["B"]}
    assert summary["risk_level_source"] == {"observed": 2, "default": 1}
    assert summary["paired_top1_variance"]["users"] == 1
