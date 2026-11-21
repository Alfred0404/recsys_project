"""HTTP client shared by the Streamlit app and local integration checks."""
import os

import requests

API_URL = os.environ.get("RECSYS_API_URL", "http://localhost:8000")


def mock_recommend(payload: dict) -> dict:
    """Fake answer in the agreed format: {items: [{isin, name, score}], profile}."""
    return {
        "items": [
            {"isin": "FR0000000001", "name": "Mock ETF World", "score": 0.91},
            {"isin": "FR0000000002", "name": "Mock ETF Europe", "score": 0.84},
            {"isin": "FR0000000003", "name": "Mock Bond Fund", "score": 0.77},
        ],
        "profile": {"risk_level": 4, "ceiling": 5, "gamma": 2.0, "gaps": ["No bond exposure"]},
    }


def recommend(payload: dict, use_mock: bool = False) -> dict:
    if use_mock:
        return mock_recommend(payload)
    r = requests.post(f"{API_URL}/recommend", json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def catalog() -> list[dict]:
    r = requests.get(f"{API_URL}/assets", timeout=3)
    r.raise_for_status()
    return r.json()


def review_profile(payload: dict) -> dict:
    response = requests.post(f"{API_URL}/profile", json=payload, timeout=65)
    response.raise_for_status()
    return response.json()


def log_interaction(session_id: str, event: str, isin: str | None = None) -> int:
    response = requests.post(
        f"{API_URL}/log_interaction",
        json={"session_id": session_id, "event": event, "isin": isin},
        timeout=2,
    )
    response.raise_for_status()
    return response.json()["id"]
