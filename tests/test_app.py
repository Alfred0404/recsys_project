from app.client import mock_recommend


def test_mock_matches_contract():
    out = mock_recommend({"holdings": {}, "answers": {}, "free_text": ""})
    assert set(out) == {"items", "profile"}
    assert all(set(i) == {"isin", "name", "score"} for i in out["items"])
