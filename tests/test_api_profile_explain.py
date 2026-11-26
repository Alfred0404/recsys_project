from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

from fastapi.testclient import TestClient
import numpy as np
import pandas as pd
import pytest
import requests

import src.api.main as api
from src.llm.explainer import ExplanationFacts, assess_sentence, explain_suggestion
from src.serve.cache import TTLCache


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "configured_generator", lambda: None)
    identifiers = ["A", "B", "C"]
    model = tmp_path / "model.npz"
    np.savez(model, item_ids=identifiers, item_embeddings=np.array([[1.0], [0.7], [0.9]]), popular_order=[0, 2, 1])
    pd.DataFrame({"ISIN": identifiers, "risk_class": [6, 3, 7]}).to_parquet(tmp_path / "asset_risk.parquet")
    pd.DataFrame({"ISIN": identifiers, "assetName": identifiers}).to_parquet(tmp_path / "assets.parquet")
    pd.DataFrame({"mu": [0.02, 0.03, 0.06]}, index=identifiers).to_parquet(tmp_path / "mu.parquet")
    pd.DataFrame(np.eye(3) * 0.04, index=identifiers, columns=identifiers).to_parquet(tmp_path / "sigma.parquet")
    with TestClient(api.create_app(model, tmp_path, tmp_path / "demo.sqlite3")) as connected:
        yield connected


def test_profile_cache_changes_the_ranking_only_for_matching_session_and_inputs(client):
    session = str(uuid4())
    payload = {"session_id": session, "holdings": {"a": 1000}, "free_text": "Croissance à long terme, fortes baisses acceptées."}
    before = client.post("/recommend", json=payload).json()
    assert not before["profile_cache_hit"]
    assert [item["isin"] for item in before["items"]] == ["B"]

    review = client.post("/profile", json=payload).json()
    assert not review["cached"]
    assert review["llm_status"] == "not_configured"
    assert review["profile"]["source"] == "text_rules"
    assert client.post("/profile", json={**payload, "holdings": {"A": 1000}}).json()["cached"]
    after = client.post("/recommend", json=payload).json()
    assert after["profile_cache_hit"]
    assert after["profile"] == review["profile"]
    assert {item["isin"] for item in after["items"]} == {"B", "C"}

    different_inputs = [{"session_id": str(uuid4())}, {"holdings": {"A": 500}}, {"free_text": "Court terme."},
                        {"answers": {"horizon": 0}}, {"session_id": None}]
    for change in different_inputs:
        result = client.post("/recommend", json={**payload, **change}).json()
        assert not result["profile_cache_hit"]
        assert result["profile"]["ceiling"] == 3


def test_explain_uses_issued_facts_and_requires_same_session(client):
    session = str(uuid4())
    ranking = client.post("/recommend", json={"holdings": {"A": 1000}, "session_id": session}).json()
    item = ranking["items"][0]
    payload = {"recommendation_id": ranking["recommendation_id"], "isin": item["isin"].lower(), "session_id": session}
    assert client.post("/explain", json={**payload, "isin": "C"}).status_code == 404
    assert client.post("/explain", json={**payload, "session_id": str(uuid4())}).status_code == 404
    assert client.post("/explain", json={**payload, "session_id": None}).status_code == 404

    response = client.post("/explain", json={**payload, "risk_class": 7, "variance_change": 99})
    assert response.status_code == 200
    explanation = response.json()
    assert explanation["language"] == "fr"
    assert explanation["source"] == "template"
    assert explanation["status"] == "not_configured"
    facts = ExplanationFacts(item["risk_class"], item["variance_change"])
    assert assess_sentence(explanation["explanation"], facts) == "faithful"


def test_explain_returns_english_facts_with_or_without_the_local_model(client):
    session = str(uuid4())
    ranking = client.post("/recommend", json={"holdings": {"A": 1000}, "session_id": session}).json()
    payload = {"recommendation_id": ranking["recommendation_id"], "isin": "B",
               "session_id": session, "language": "en"}
    sentence = ("The estimated risk class is 3/7 and, with a hypothetical 10% allocation, "
                "annualized variance would change by -0.0072.")

    fallback = client.post("/explain", json=payload).json()
    assert (fallback["language"], fallback["source"], fallback["explanation"]) == ("en", "template", sentence)

    def generate(prompt):
        assert "Copy only this English JSON object" in prompt
        return {"explanation": sentence}

    client.app.state.generator = generate
    verified = client.post("/explain", json=payload).json()
    assert (verified["language"], verified["source"], verified["status"]) == ("en", "llm", "verified")

    client.app.state.generator = lambda _: {"explanation": sentence.replace("-0.0072", "+0.0072")}
    rejected = client.post("/explain", json=payload).json()
    assert (rejected["source"], rejected["status"], rejected["explanation"]) == ("template", "incorrect_facts", sentence)
    assert client.post("/explain", json={**payload, "language": "es"}).status_code == 422


def test_llm_explainer_never_emits_wrong_numbers_or_unsupported_claims():
    facts = ExplanationFacts(3, -0.0225)
    sentence = "Le risque estimé est de 3/7 et, pour une allocation hypothétique de 10 %, la variance annualisée évoluerait de -0,0225."
    assert explain_suggestion(facts, lambda _: {"explanation": sentence})["source"] == "llm"
    for candidate in [sentence.replace("3/7", "7/7"), sentence.replace("3/7", "3/10"),
                      sentence.replace("10 %", "20 %"), sentence.replace("-0,0225", "+0,0225")]:
        result = explain_suggestion(facts, lambda _: {"explanation": candidate})
        assert (result["source"], result["status"]) == ("template", "incorrect_facts")
        assert assess_sentence(result["explanation"], facts) == "faithful"
    result = explain_suggestion(facts, lambda _: {"explanation": sentence + " Le rendement est garanti."})
    assert (result["source"], result["status"]) == ("template", "unverifiable")


def test_unavailable_model_does_not_prevent_recommendations_and_can_be_retried(client):
    entered, release = Event(), Event()

    def unavailable(_):
        entered.set()
        assert release.wait(5)
        raise requests.ConnectionError("local model is down")

    payload = {"holdings": {"A": 1000}, "session_id": str(uuid4())}
    client.app.state.generator = unavailable
    with ThreadPoolExecutor(max_workers=1) as tasks:
        pending = tasks.submit(client.post, "/profile", json=payload)
        try:
            assert entered.wait(3)
            ranking = client.post("/recommend", json=payload).json()
            assert not pending.done()
            assert ranking["items"]
        finally:
            release.set()
        review = pending.result(timeout=3).json()

    assert review["llm_status"] == "model_unavailable"
    assert not client.post("/profile", json=payload).json()["cached"]
    response = client.post("/explain", json={
        "session_id": payload["session_id"], "recommendation_id": ranking["recommendation_id"], "isin": "B",
    }).json()
    assert (response["source"], response["status"]) == ("template", "model_unavailable")


def test_cache_reuses_recent_entries_only_until_expiry_or_eviction():
    now = 0
    cache = TTLCache[str, str](max_entries=2, ttl=5, clock=lambda: now)
    cache.put("a", "first")
    cache.put("b", "second")
    assert cache.get("a") == "first"
    now = 3
    cache.put("c", "third")
    assert cache.get("b") is None
    now = 5
    assert cache.get("a") is None
    assert cache.get("c") == "third"
