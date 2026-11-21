import pandas as pd
import pytest

from src.rerank.mpt import mpt_rerank, portfolio_impact, risk_filter


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
