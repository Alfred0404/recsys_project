import pandas as pd
import pytest

from src.rerank.mpt import mpt_rerank, portfolio_impact, risk_filter, risk_rerank


def test_risk_filter_drops_unknown_and_excessive_classes():
    risk = pd.DataFrame({"ISIN": ["B", "C", "D"], "risk_class": pd.array([4, 7, None], dtype="Int64")})
    assert risk_filter(["C", "B", "unknown", "D"], risk, ceiling=4) == ["B"]


def test_mpt_prefers_the_lower_variance_candidate_at_high_mpt_weight():
    names = ["A", "B", "C"]
    sigma = pd.DataFrame(
        [[0.04, 0.00, 0.06], [0.00, 0.01, 0.00], [0.06, 0.00, 0.09]],
        index=names,
        columns=names,
    )
    mu = pd.Series([0.05, 0.05, 0.05], index=names)
    weights = {"A": 1000.0, "unknown holding": 100.0}
    ranking = ["C", "B", "unknown candidate"]
    relevance = {"B": 0.2, "C": 0.9, "unknown candidate": 0.1}

    impact = portfolio_impact(ranking, weights, mu, sigma, gamma=2)
    assert impact.index.tolist() == ["C", "B"]
    assert impact.at["B", "variance_before"] == pytest.approx(0.04)
    assert impact.at["B", "variance_after"] == pytest.approx(0.0325)
    assert impact.at["C", "variance_after"] == pytest.approx(0.0441)
    assert mpt_rerank(ranking, relevance, weights, mu, sigma, 2, 0.8) == ["B", "C", "unknown candidate"]
    assert mpt_rerank(ranking, relevance, weights, mu, sigma, 2, 0) == ranking


def test_risk_rerank_without_tolerance_matches_the_hard_filter():
    risk = pd.DataFrame({"ISIN": ["A", "B", "C", "D"], "risk_class": pd.array([2, 5, 3, None], dtype="Int64")})
    ranking = ["B", "A", "D", "C"]
    relevance = {"B": 0.9, "A": 0.8, "D": 0.7, "C": 0.1}
    assert risk_rerank(ranking, relevance, risk, ceiling=3) == risk_filter(ranking, risk, ceiling=3) == ["A", "C"]


def test_risk_tolerance_admits_one_class_above_the_ceiling_with_a_penalty():
    risk = {"safe": 3, "near": 4, "far": 5, "far_safe": 1}
    relevance = {"near": 1.0, "far": 0.95, "safe": 0.9, "far_safe": 0.0}
    ranking = ["near", "far", "safe", "far_safe"]
    # One class over costs 0.5 on the normalized scale: 1.0 - 0.5 < 0.9.
    assert risk_rerank(ranking, relevance, risk, ceiling=3, tolerance=1) == ["safe", "near", "far_safe"]
    # Without a penalty the tolerated asset keeps its relevance rank.
    assert risk_rerank(ranking, relevance, risk, ceiling=3, tolerance=1, penalty=0) == ["near", "safe", "far_safe"]
    # The tolerance stops at class 7 and never admits unknown classes.
    assert risk_rerank(["x", "y"], {"x": 1, "y": 0}, {"x": 7}, ceiling=7, tolerance=2) == ["x"]


@pytest.mark.parametrize("kwargs", [{"ceiling": 0}, {"ceiling": 3, "tolerance": -1}, {"ceiling": 3, "penalty": -0.1}])
def test_risk_rerank_rejects_invalid_settings(kwargs):
    with pytest.raises(ValueError):
        risk_rerank(["A"], {"A": 1.0}, {"A": 1}, **kwargs)
