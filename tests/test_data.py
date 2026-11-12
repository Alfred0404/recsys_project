import pandas as pd

from src.data.load_and_check import k_core


def test_k_core_iterates_until_stable():
    # u3 only bought "b"; once "b" falls under 2 holders, u3 must go too.
    pairs = pd.DataFrame({"customerID": ["u1", "u1", "u2", "u2", "u3"],
                          "ISIN": ["a", "c", "a", "c", "b"]})
    out = k_core(pairs, min_items=2, min_users=2)
    assert set(out["customerID"]) == {"u1", "u2"}
    assert set(out["ISIN"]) == {"a", "c"}
