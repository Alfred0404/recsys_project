import numpy as np
import pandas as pd

from src.data.asset_returns import (asset_risk, covariance, drop_price_glitches, expected_returns,
                             returns_matrix)

DATES = pd.bdate_range("2020-01-01", periods=300)


def long(wide):
    return wide.rename_axis("timestamp").reset_index().melt("timestamp", var_name="ISIN", value_name="closePrice")


def random_prices(seed=0, vols=(0.001, 0.01, 0.03)):
    rng = np.random.default_rng(seed)
    data = {f"A{i}": 100 * np.cumprod(1 + rng.normal(0, v, len(DATES))) for i, v in enumerate(vols)}
    return pd.DataFrame(data, index=DATES)


ASSETS = pd.DataFrame({"ISIN": ["A0", "A1", "A2", "S"], "assetSubCategory": ["x", "x", "x", "x"],
                       "timestamp": [DATES[0]] * 4})


def test_glitch_that_comes_back_is_erased_real_crash_is_kept():
    w = pd.DataFrame({"g": [1.8, 1.8, 0.6, 1.8, 1.8], "c": [10, 10, 2.6, 2.5, 2.4]}, index=DATES[:5])
    out = drop_price_glitches(w)
    assert np.isnan(out.loc[DATES[2], "g"])
    assert out["c"].equals(w["c"])


def test_constant_price_is_class_1():
    w = pd.DataFrame({"S": [5.0] * 100}, index=DATES[:100])
    risk = asset_risk(long(w), ASSETS, DATES[-1])
    assert risk[["volatility", "max_drawdown", "risk_class"]].iloc[0].tolist() == [0, 0, 1]


def test_classes_follow_volatility_and_short_history_is_imputed():
    w = random_prices()
    w["S"] = np.nan
    w.loc[DATES[:10], "S"] = 50.0  # 9 returns only
    risk = asset_risk(long(w), ASSETS, DATES[-1]).set_index("ISIN")
    assert risk.loc["A0", "risk_class"] < risk.loc["A1", "risk_class"] < risk.loc["A2", "risk_class"]
    assert risk.loc["S", "risk_class_imputed"]
    assert risk.loc["S", "risk_class"] == risk.loc[["A0", "A1", "A2"], "risk_class"].median()


def test_sigma_is_symmetric_and_positive_semidefinite():
    w = random_prices()
    w.iloc[:50, 0] = np.nan
    sigma = covariance(returns_matrix(long(w)), DATES[-1])
    assert np.allclose(sigma, sigma.T)
    assert np.linalg.eigvalsh(sigma).min() >= -1e-12


def test_no_leakage_after_before_date():
    w = random_prices()
    cut = DATES[200]
    changed = w.copy()
    changed.loc[DATES[200]:] *= 3
    p, q = long(w), long(changed)
    pd.testing.assert_series_equal(expected_returns(returns_matrix(p), cut), expected_returns(returns_matrix(q), cut))
    pd.testing.assert_frame_equal(covariance(returns_matrix(p), cut), covariance(returns_matrix(q), cut))
    pd.testing.assert_frame_equal(asset_risk(p, ASSETS, cut), asset_risk(q, ASSETS, cut))
