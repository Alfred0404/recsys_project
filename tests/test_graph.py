import pandas as pd

from src.graph.build import build_graph, to_symmetric


def test_graph_from_train_only():
    train = pd.DataFrame({"customerID": ["u2", "u1", "u1", "u1"], "ISIN": ["b", "a", "b", "a"],
                          "timestamp": pd.to_datetime(["2020-01-01"] * 4)})
    ei, user2idx, item2idx = build_graph(train)
    assert user2idx == {"u1": 0, "u2": 1} and item2idx == {"a": 0, "b": 1}
    assert ei.dtype.is_floating_point is False and ei.shape == (2, 3)  # duplicate (u1, a) collapsed
    assert set(map(tuple, ei.t().tolist())) == {(1, 1), (0, 0), (0, 1)}
    # an asset that only appears outside train has no index
    assert "c" not in item2idx


def test_symmetric_version():
    train = pd.DataFrame({"customerID": ["u1", "u2"], "ISIN": ["a", "a"]})
    ei, _, _ = build_graph(train)
    sym = to_symmetric(ei, n_users=2)
    assert sym.shape == (2, 4) and sym.max().item() == 2
