from contextlib import closing
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient
import numpy as np
import pandas as pd
import pytest

from src.api.main import create_app
from src.llm.profile import QUESTIONNAIRE
from src.llm.reflection import verify_profile


@pytest.fixture
def demo_artifacts(tmp_path):
    identifiers = ["A", "B", "C", "D"]
    model = tmp_path / "model.npz"
    np.savez(model, item_ids=np.array(identifiers), item_embeddings=np.array([[1], [0.8], [0.9], [0.2]]),
             popular_order=np.array([2, 1, 0, 3]))
    pd.DataFrame({"ISIN": identifiers, "risk_class": [6, 3, 7, 2]}).to_parquet(tmp_path / "asset_risk.parquet")
    pd.DataFrame({"ISIN": identifiers, "assetName": ["Held", "Bond", "Risky", "Fund"]}).to_parquet(tmp_path / "assets.parquet")
    pd.DataFrame({"mu": [0.02, 0.03, 0.10, 0.01]}, index=identifiers).to_parquet(tmp_path / "mu.parquet")
    pd.DataFrame(np.eye(4) * 0.04, index=identifiers, columns=identifiers).to_parquet(tmp_path / "sigma.parquet")
    database = tmp_path / "demo.sqlite3"
    with TestClient(create_app(model, tmp_path, database)) as client:
        yield client, database


def test_live_recommendation_filters_holds_and_risk_and_logs_in_sqlite(demo_artifacts):
    client, database = demo_artifacts
    assert client.get("/health").json()["catalog_size"] == 4
    response = client.post("/recommend", json={"holdings": {"a": 1000}, "answers": {key: 0 for key in QUESTIONNAIRE}})
    assert response.status_code == 200
    result = response.json()
    assert result["ranking_source"] == "portfolio_embeddings"
    assert result["profile"]["ceiling"] == 3
    assert {item["isin"] for item in result["items"]} == {"B", "D"}
    assert all(item["variance_change"] < 0 for item in result["items"])

    session_id = str(uuid4())
    response = client.post("/log_interaction", json={"session_id": session_id, "event": "recommendation_viewed"})
    assert response.status_code == 201
    with closing(sqlite3.connect(database)) as conn:
        recorded = conn.execute("SELECT session_id, event FROM interactions WHERE id = ?", (response.json()["id"],)).fetchone()
    assert recorded == (session_id, "recommendation_viewed")


def test_unseen_portfolios_use_popularity_and_invalid_amounts_are_rejected(demo_artifacts):
    client, _ = demo_artifacts
    result = client.post("/recommend", json={"holdings": {"UNKNOWN": 100}}).json()
    assert result["ranking_source"] == "popularity"
    assert result["unrecognized_isins"] == ["UNKNOWN"]
    assert result["items"][0]["isin"] == "B"
    assert result["items"][0]["variance_change"] is None
    assert client.post("/recommend", json={"holdings": {"A": -2}}).status_code == 422


def test_a_low_ceiling_still_fills_ten_suggestions_from_deep_in_the_catalogue(tmp_path):
    # Only the 12 least relevant of 121 assets are suitable for a cautious profile.
    identifiers = [f"I{i:03d}" for i in range(121)]
    model = tmp_path / "model.npz"
    np.savez(model, item_ids=np.array(identifiers), item_embeddings=np.linspace(1, 0.1, 121)[:, None],
             popular_order=np.arange(121))
    risk_classes = [7] * 109 + [2] * 12
    pd.DataFrame({"ISIN": identifiers, "risk_class": risk_classes}).to_parquet(tmp_path / "asset_risk.parquet")
    pd.DataFrame({"ISIN": identifiers, "assetName": identifiers}).to_parquet(tmp_path / "assets.parquet")
    pd.DataFrame({"mu": np.full(121, 0.02)}, index=identifiers).to_parquet(tmp_path / "mu.parquet")
    pd.DataFrame(np.eye(121) * 0.04, index=identifiers, columns=identifiers).to_parquet(tmp_path / "sigma.parquet")
    with TestClient(create_app(model, tmp_path, tmp_path / "demo.sqlite3")) as client:
        response = client.post("/recommend", json={"holdings": {"I000": 1000},
                                                   "answers": {key: 0 for key in QUESTIONNAIRE}})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 10
    assert all(item["risk_class"] == 2 for item in items)

def test_profile_reflection_checks_its_output_and_can_fall_back():
    incorrect = {"risk_level": 4, "ceiling": 7, "gamma": 1.0, "concentrated": True}
    correct = {"risk_level": 1, "ceiling": 3, "gamma": 4.0, "concentrated": True}
    feedback = {"accepted": True, "feedback": "approved even though the actor overstates tolerance"}
    for refined, status in [(correct, "refined"), (incorrect, "rules_fallback")]:
        outputs = iter([incorrect, feedback, refined])
        result = verify_profile({"A": 100}, {}, "", lambda _: next(outputs))
        assert result["status"] == status
        assert result["actor_matches"] is False
        assert result["profile"]["ceiling"] == 3
