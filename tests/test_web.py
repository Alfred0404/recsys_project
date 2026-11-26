from fastapi.testclient import TestClient
import numpy as np
import pandas as pd
import pytest

from src.api.main import create_app

IDS = ["A", "B", "C", "D"]


@pytest.fixture
def site(tmp_path):
    model = tmp_path / "model.npz"
    np.savez(model, item_ids=np.array(IDS), item_embeddings=np.array([[1], [0.8], [0.9], [0.2]]),
             popular_order=np.array([2, 1, 0, 3]))
    pd.DataFrame({"ISIN": IDS, "risk_class": [6, 3, 7, 2]}).to_parquet(tmp_path / "asset_risk.parquet")
    pd.DataFrame({"ISIN": IDS, "assetName": ["Held", "Bond", "Risky", "Fund"]}).to_parquet(tmp_path / "assets.parquet")
    pd.DataFrame({"mu": [0.02, 0.03, 0.10, 0.01]}, index=IDS).to_parquet(tmp_path / "mu.parquet")
    pd.DataFrame(np.eye(4) * 0.04, index=IDS, columns=IDS).to_parquet(tmp_path / "sigma.parquet")

    data = tmp_path / "processed"
    data.mkdir()
    days = pd.bdate_range("2019-01-01", "2022-11-29")
    prices = pd.concat([
        pd.DataFrame({"ISIN": "B", "timestamp": days, "closePrice": np.linspace(10, 20, len(days))}),  # doubles
        pd.DataFrame({"ISIN": "C", "timestamp": days, "closePrice": np.linspace(20, 10, len(days))}),  # halves
        pd.DataFrame({"ISIN": "D", "timestamp": days[:3], "closePrice": [5, 0, 6]}),
    ])
    prices.to_parquet(data / "close_prices.parquet")
    pd.DataFrame({"ISIN": ["B"], "assetName": ["Bond"], "assetCategory": ["Bond"], "assetSubCategory": ["Gov"],
                  "sector": [None], "timestamp": [days[0]]}).to_parquet(data / "asset_information.parquet")
    with TestClient(create_app(model, tmp_path, tmp_path / "log.sqlite3", data)) as client:
        yield client


def test_site_pages_are_served_next_to_the_api(site):
    for path in ("/", "/asset.html", "/assets.html", "/styles.css", "/i18n.js", "/chart.js", "/app.js", "/asset.js",
                 "/assets.js", "/search.js", "/logo.svg"):
        assert site.get(path).status_code == 200, path
    assert site.get("/health").json()["status"] == "ready"  # API routes keep priority over the site


def test_catalogue_lists_every_asset_with_its_risk_class(site):
    catalog = {a["isin"]: a for a in site.get("/assets").json()}
    assert list(catalog) == IDS
    assert catalog["B"]["risk_class"] == 3 and catalog["B"]["name"] == "Bond"
    assert sorted(a["popularity"] for a in catalog.values()) == list(range(1, len(IDS) + 1))  # 1 = most held


def test_prices_give_the_trend_over_the_chosen_window(site):
    data = site.get("/prices", params={"isins": "b,C,UNKNOWN", "years": 1}).json()
    assert set(data) == {"B", "C"}
    assert data["B"]["change"] > 0 > data["C"]["change"]
    assert data["B"]["end"] == "2022-11-29" and data["B"]["start"] >= "2021-11-29"
    assert len(data["B"]["points"]) <= 54  # weekly points
    assert data["B"]["points"][-1][0] == data["B"]["end"]


def test_asset_page_data(site):
    asset = site.get("/asset/b").json()
    assert (asset["name"], asset["risk_class"], asset["category"]) == ("Bond", 3, "Bond")
    assert asset["sector"] is None
    assert asset["prices"][0][0] == "2019-01-01" and asset["prices"][-1][1] == pytest.approx(20)
    assert site.get("/asset/NOPE").status_code == 404


def test_prices_report_a_missing_history(tmp_path, site):
    (tmp_path / "processed" / "close_prices.parquet").unlink()
    app = create_app(tmp_path / "model.npz", tmp_path, tmp_path / "other.sqlite3", tmp_path / "processed")
    with TestClient(app) as client:
        assert client.get("/prices", params={"isins": "B"}).status_code == 404


def test_charts_keep_observed_dates_and_ignore_nonpositive_closes(site):
    prices = site.get("/asset/D").json()["prices"]
    assert prices == [["2019-01-01", 5], ["2019-01-03", 6]]
    trend = site.get("/prices", params={"isins": " d ", "years": 5}).json()["D"]
    assert (trend["start"], trend["end"]) == ("2019-01-01", "2019-01-03")
    assert trend["points"] == [["2019-01-03", 6]]
    assert trend["change"] == pytest.approx(0.2)
