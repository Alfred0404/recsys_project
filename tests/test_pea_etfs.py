import pytest

from src.data.pea_etfs import UNKNOWN_COUNTRY, exposure, load_pea


def isin_is_valid(isin: str) -> bool:
    """ISO 6166 check digit: letters to numbers (A=10), then Luhn."""
    digits = "".join(str(int(ch, 36)) for ch in isin)
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def test_pea_data_is_consistent():
    etfs, countries = load_pea()
    assert etfs["isin"].is_unique and len(etfs) == 19
    assert all(isin_is_valid(i) for i in etfs["isin"])
    assert set(countries["isin"]) <= set(etfs["isin"])
    sums = countries.groupby("isin")["weight"].sum()
    assert sums.between(98.5, 100.5).all(), sums[~sums.between(98.5, 100.5)]
    assert etfs["risk_class"].dropna().between(1, 7).all()


def test_exposure_weights_by_amount():
    _, countries = load_pea()
    # 50/50 S&P 500 + CAC 40: US is about half of the portfolio.
    e = exposure({"FR0011871128": 1000, "FR0007052782": 1000}, countries)
    assert e["United States"] == pytest.approx(96.97 / 2)
    assert e["France"] == pytest.approx(88.87 / 2)


def test_exposure_reports_unpublished_country_weights():
    _, countries = load_pea()
    paej, sp500 = "FR0011869312", "FR0011871128"
    assert exposure({paej: 1000}, countries).to_dict() == {UNKNOWN_COUNTRY: 100.0}

    mixed = exposure({paej: 1000, sp500: 1000}, countries)
    assert mixed[UNKNOWN_COUNTRY] == pytest.approx(50.0)
    assert mixed["United States"] == pytest.approx(96.97 / 2)
    assert mixed.sum() == pytest.approx(100.0)
