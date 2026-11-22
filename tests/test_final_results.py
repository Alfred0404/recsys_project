import numpy as np
import pandas as pd
import pytest

from src.data.asset_returns import shrink_mu
from src.eval.finance import suitable_targets
from src.eval.tune import select
from src.rerank.calibrate import implied_gamma, summarize
from src.rerank.mpt import mpt_rerank


def test_full_shrinkage_gives_every_asset_the_mean_return():
    mu = pd.Series({"A": 0.5, "B": -0.1, "C": 0.2})
    assert np.allclose(shrink_mu(mu, 1.0), mu.mean())
    pd.testing.assert_series_equal(shrink_mu(mu, 0.0), mu)
    with pytest.raises(ValueError):
        shrink_mu(mu, 1.5)


def test_full_shrinkage_makes_mpt_rank_by_added_variance_only():
    sigma = pd.DataFrame(np.diag([0.04, 0.01, 0.09]), index=list("HLX"), columns=list("HLX"))
    mu = shrink_mu(pd.Series({"H": 0.0, "L": -0.5, "X": 0.9}), 1.0)
    ranked = mpt_rerank(["X", "L"], {"X": 1.0, "L": 1.0}, {"H": 1.0}, mu, sigma, gamma=1.0, lam=1.0)
    assert ranked == ["L", "X"]


def test_implied_gamma_recovers_the_gamma_of_an_optimal_portfolio():
    sigma = np.array([[0.04, 0.01], [0.01, 0.09]])
    weights = np.array([0.6, 0.4])
    mu = 2 * 3.0 * sigma @ weights
    assert implied_gamma(weights, mu, sigma) == pytest.approx(3.0)


def test_gamma_grid_is_usable_only_when_positive_and_decreasing():
    table = pd.DataFrame({
        "customerID": list("abcd"), "level": [1, 2, 3, 4], "volatility": 0.2,
        "expected_return": 0.1, "implied_gamma": [4.0, 3.0, 2.0, 1.0],
    })
    assert summarize(table)["usable"]
    table["implied_gamma"] = [-1.0, 3.0, 2.0, 1.0]
    assert not summarize(table)["usable"]


def test_suitable_targets_drop_purchases_above_the_users_ceiling():
    tables = {
        "asset_risk": pd.DataFrame({"ISIN": ["LOW", "HIGH"], "risk_class": [2, 6]}),
        "customers": pd.DataFrame({"customerID": ["u"], "riskLevel": ["Conservative"]}),
    }
    targets = pd.DataFrame({"customerID": ["u", "u", "u"], "ISIN": ["LOW", "HIGH", "UNKNOWN"]})
    kept, stats = suitable_targets(targets, tables)
    assert kept["ISIN"].tolist() == ["LOW"]
    assert stats["above_ceiling_share"] == pytest.approx(0.5)


def test_tuning_keeps_the_largest_variance_cut_within_the_ndcg_floor():
    rows = [
        {"lambda": 0.0, "mu_shrinkage": 0.0, "ndcg@10": 0.10, "filter_ndcg@10": 0.10, "variance_vs_filter": 0.0},
        {"lambda": 0.5, "mu_shrinkage": 1.0, "ndcg@10": 0.096, "filter_ndcg@10": 0.10, "variance_vs_filter": -0.004},
        {"lambda": 1.0, "mu_shrinkage": 1.0, "ndcg@10": 0.05, "filter_ndcg@10": 0.10, "variance_vs_filter": -0.01},
    ]
    assert select(rows) == rows[1]
