import math

import pandas as pd

from src.eval.metrics import evaluate, most_popular_ranking, ndcg_at_k, random_ranking


def df(pairs):
    return pd.DataFrame(pairs, columns=["customerID", "ISIN"])


def test_ndcg_known_values():
    assert ndcg_at_k(["a", "b"], {"a"}, 10) == 1.0
    assert math.isclose(ndcg_at_k(["x", "a"], {"a"}, 10), 1 / math.log2(3))
    assert ndcg_at_k(["x", "y"], {"a"}, 10) == 0.0


def test_evaluate_counts_missing_users_as_zero():
    test = df([("u1", "a"), ("u2", "b"), ("u2", "c")])
    res = evaluate({"u1": ["a"], "u2": ["b", "z"]}, test)
    assert math.isclose(res["recall@20"], (1 + 0.5) / 2)
    assert math.isclose(evaluate({"u1": ["a"]}, test)["recall@20"], 0.5)  # u2 has no ranking: 0
    assert res["ndcg@10"] <= 1.0


def test_baselines_exclude_owned_assets():
    train = df([("u1", "a"), ("u2", "a"), ("u3", "a"), ("u2", "b"), ("u1", "c")])
    pop = most_popular_ranking(["u1", "u4"], train, k=3)
    assert pop["u1"] == ["b"]            # a and c owned by u1
    assert pop["u4"] == ["a", "b", "c"]  # popularity order, ties broken by ISIN
    rnd = random_ranking(["u1"], ["a", "b", "c", "d"], train, k=10, seed=1)
    assert set(rnd["u1"]) == {"b", "d"}
    assert random_ranking(["u1"], ["a", "b", "c", "d"], train, seed=1) == rnd
