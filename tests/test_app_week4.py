from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import requests
from streamlit.testing.v1 import AppTest

import app.client as app_client
from tests.test_week4_serving import client as backend_client  # reuse the test FastAPI and artifacts


APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def click(app, label):
    return next(button for button in app.button if button.label == label).click().run()


def test_text_profile_is_explicit_and_explanation_uses_the_displayed_session(backend_client, monkeypatch):
    requests_seen = []

    def send(method, url, *, json=None, timeout):
        path = urlsplit(url).path
        actual = backend_client.request(method, path, json=json)
        requests_seen.append((path, json, actual.status_code))
        adapted = requests.Response()
        adapted.url = url
        adapted.status_code = actual.status_code
        adapted._content = actual.content
        return adapted

    monkeypatch.setattr(app_client, "requests", SimpleNamespace(
        get=lambda *args, **kwargs: send("GET", *args, **kwargs),
        post=lambda *args, **kwargs: send("POST", *args, **kwargs),
    ))

    app = AppTest.from_file(str(APP), default_timeout=15).run()
    assert not app.exception
    app.radio[0].set_value("Texte libre").run()
    app.multiselect[0].set_value(["A"]).run()
    objective = "Croissance à long terme, fortes baisses acceptées."
    app.text_area[0].set_value(objective)
    click(app, "Afficher les suggestions")

    initial = app.session_state["recommendation_result"]
    session_id = app.session_state["session_uuid"]
    payload = {"holdings": {"A": 1000.0}, "answers": {}, "free_text": objective, "session_id": session_id}
    assert initial["profile"]["ceiling"] == 3
    assert initial["profile_review_available"] is False
    assert [(path, body) for path, body, _ in requests_seen if path in ("/recommend", "/profile", "/explain")] == [
        ("/recommend", payload),
    ]
    assert len(app.dataframe) >= 1

    click(app, "Analyser le texte et actualiser les suggestions")
    refreshed = app.session_state["recommendation_result"]
    assert refreshed["recommendation_id"] != initial["recommendation_id"]
    assert refreshed["profile_cache_hit"]
    assert refreshed["profile"]["source"] == "text_rules"
    assert {row["isin"] for row in refreshed["items"]} == {"B", "C"}
    assert ("/profile", payload, 200) in requests_seen
    assert sum(row == ("/recommend", payload, 200) for row in requests_seen) == 2
    assert any("n’est pas configuré" in caption.value for caption in app.caption)

    explanation_key = f"explanation_item_{refreshed['recommendation_id']}"
    app.selectbox(key=explanation_key).set_value("B").run()
    assert not any(path == "/explain" for path, _, _ in requests_seen)
    click(app, "Expliquer cet actif")
    assert ("/explain", {"recommendation_id": refreshed["recommendation_id"], "isin": "B", "session_id": session_id},
            200) in requests_seen
    assert app.session_state["explanations"]["B"]["source"] == "template"
    assert any(caption.value == "Gabarit factuel" for caption in app.caption)
    assert any(path == "/log_interaction" and body["event"] == "profile_review_requested"
               and body["session_id"] == session_id and status == 201 for path, body, status in requests_seen)
    assert not app.exception

    app.session_state["recommendation_payload"] = {"holdings": {"A": 1000.0}, "answers": {}}
    app.run()
    assert not app.exception
    assert not any(button.label == "Expliquer cet actif" for button in app.button)
