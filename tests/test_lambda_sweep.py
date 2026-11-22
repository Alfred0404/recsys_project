import tempfile

import numpy as np
import pandas as pd
import pytest

from src.eval import finance
from src.eval.lambda_sweep import diversity, score_saved_experiment, sweep


def test_diversity_measures_category_coverage_and_concentration():
    categories = {"A": "bond", "B": "bond", "C": "stock", "D": "fund"}
    result = diversity({"u1": ["A", "B"], "u2": ["A", "C", "D", "X"], "u3": []}, categories)
    # u1: one category, HHI 1. u2: four categories (unknown counts), HHI 0.25.
    assert result["mean_categories_top10"] == pytest.approx(2.5)
    assert result["mean_hhi_top10"] == pytest.approx(0.625)


def test_diversity_without_suggestions_reports_none():
    assert diversity({"u": []}, {}) == {"mean_categories_top10": None, "mean_hhi_top10": None}


def test_sweep_reports_empty_recommendations_without_a_defined_risk_rate(monkeypatch, tmp_path):
    assets = pd.DataFrame({"ISIN": ["A"], "assetName": ["A"], "assetCategory": ["stock"]})
    tables = {
        "mu": pd.DataFrame({"mu": [0.1]}, index=["A"]),
        "sigma": pd.DataFrame([[0.04]], index=["A"], columns=["A"]),
        "asset_risk": pd.DataFrame({"ISIN": ["A"], "risk_class": [7]}),
        "assets": assets,
        "holdings": pd.DataFrame(columns=["customerID", "ISIN", "value"]),
        "customers": pd.DataFrame(columns=["customerID", "riskLevel"]),
    }
    monkeypatch.setattr(finance, "snapshot", lambda *_: tables)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path.resolve()))
    cutoff = pd.Timestamp("2022-02-24")
    scored = {"user": [("A", 1.0)]}
    test = pd.DataFrame({"customerID": ["user"], "ISIN": ["A"]})

    [row] = sweep(scored, None, cutoff, tmp_path, test, set(), (0.25,))
    assert row["coverage_users"] == 0
    assert row["above_ceiling_rate"] is None
    assert row["variance_change_top1"] is None
    assert row["mean_hhi_top10"] is None

    empty_counts = {"suggestions": 0, "known": 0, "unknown": 0,
                    "above_ceiling": 0, "violation_rate_known": None}
    for tolerance in (0, 1):
        summary, _ = finance.evaluate_reranking(scored, None, cutoff, tmp_path, tmp_path, set(), tolerance=tolerance)
        risk = summary["top10_risk"]
        assert risk["nlgcl"]["violation_rate_known"] == 1
        assert risk["risk_only"] == risk["mpt_risk"] == empty_counts
        if tolerance:
            assert risk["risk_tolerant"] == empty_counts
        else:
            assert "risk_tolerant" not in risk


@pytest.mark.parametrize("mismatched_field", [None, "user_ids", "item_ids"])
def test_saved_embeddings_must_match_the_rebuilt_id_order(tmp_path, mismatched_field):
    tx = pd.DataFrame([
        ("U1", "A", "2022-01-01"),
        ("U2", "B", "2022-01-01"),
        ("U1", "B", "2022-02-01"),
        ("U2", "A", "2022-03-01"),
    ], columns=["customerID", "ISIN", "timestamp"])
    tx["timestamp"] = pd.to_datetime(tx["timestamp"])
    tx["transactionType"] = "Buy"
    model_path = tmp_path / "model.npz"
    data = {
        "user_ids": ["U1", "U2"],
        "item_ids": ["A", "B"],
        "user_embeddings": [[1.0], [1.0]],
        "item_embeddings": [[1.0], [2.0]],
        "train_cutoff": "2022-02-01",
        "test_cutoff": "2022-03-01",
    }
    if mismatched_field:
        data[mismatched_field] = data[mismatched_field][::-1]
    np.savez(model_path, **data)

    if mismatched_field:
        with pytest.raises(ValueError, match=f"Model {mismatched_field} do not match"):
            score_saved_experiment(tx, model_path)
    else:
        experiment, scored = score_saved_experiment(tx, model_path)
        assert experiment.test_history["U2"] == {"B"}
        assert scored == {"U2": [("A", 1.0)]}
