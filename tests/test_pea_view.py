import pandas as pd
import pytest

from app.pea_view import concentration, exposure_after
from src.data.pea_etfs import UNKNOWN_COUNTRY, load_pea

COUNTRIES = pd.DataFrame({
    "isin": ["US", "US", "FR", "WORLD", "WORLD"],
    "country": ["United States", "Other", "France", "United States", "France"],
    "weight": [90.0, 10.0, 100.0, 60.0, 40.0],
})


def test_adding_a_french_etf_lowers_us_exposure():
    table = exposure_after({"US": 1000.0}, "FR", COUNTRIES, share=0.2)
    assert table.at["United States", "Avant"] == pytest.approx(90.0)
    assert table.at["United States", "Après"] == pytest.approx(72.0)
    assert table.at["France", "Après"] == pytest.approx(20.0)
    assert table["Après"].sum() == pytest.approx(100.0)


def test_empty_portfolio_ends_fully_in_the_candidate():
    table = exposure_after({}, "FR", COUNTRIES)
    assert table["Avant"].sum() == 0
    assert table.at["France", "Après"] == pytest.approx(100.0)


def test_adding_an_already_held_etf_keeps_total_exposure():
    table = exposure_after({"US": 500.0, "FR": 500.0}, "US", COUNTRIES, share=0.5)
    assert table["Après"].sum() == pytest.approx(100.0)


def test_concentration_reports_largest_country_and_hhi():
    result = concentration(pd.Series({"A": 50.0, "B": 50.0, "C": 0.0}))
    assert result["top_share"] == pytest.approx(0.5)
    assert result["hhi"] == pytest.approx(0.5)


def test_concentration_never_labels_other_as_a_country():
    result = concentration(pd.Series({"France": 30.0, "Other": 70.0}))
    assert result["top_country"] == "France"
    assert result["top_share"] == pytest.approx(0.3)
    assert result["hhi"] == pytest.approx(0.58)


def test_portfolio_with_unpublished_exposure_has_no_comparable_concentration():
    _, countries = load_pea()
    table = exposure_after({"FR0011869312": 1000.0}, "FR0011871128", countries)
    assert table.loc[UNKNOWN_COUNTRY].to_dict() == pytest.approx({"Avant": 100.0, "Après": 90.0})
    for column in table:
        result = concentration(table[column])
        assert result["unknown_share"] == pytest.approx(table.at[UNKNOWN_COUNTRY, column] / 100)
        assert result["top_country"] is None
        assert result["top_share"] is None
        assert result["hhi"] is None
