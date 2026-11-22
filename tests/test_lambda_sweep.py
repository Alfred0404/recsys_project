import pytest

from src.eval.lambda_sweep import diversity


def test_diversity_measures_category_coverage_and_concentration():
    categories = {"A": "bond", "B": "bond", "C": "stock", "D": "fund"}
    result = diversity({"u1": ["A", "B"], "u2": ["A", "C", "D", "X"], "u3": []}, categories)
    # u1: one category, HHI 1. u2: four categories (unknown counts), HHI 0.25.
    assert result["mean_categories_top10"] == pytest.approx(2.5)
    assert result["mean_hhi_top10"] == pytest.approx(0.625)


def test_diversity_without_suggestions_reports_none():
    assert diversity({"u": []}, {}) == {"mean_categories_top10": None, "mean_hhi_top10": None}
