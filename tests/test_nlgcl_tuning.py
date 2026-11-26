import json
import sys

import pandas as pd

from src.train import run, tune_nlgcl


def test_tuning_keeps_the_calendar_split_but_never_passes_test_targets_to_training(monkeypatch):
    cutoff_days = pd.date_range("2022-01-01", periods=20)
    transactions = pd.DataFrame({
        "customerID": "user",
        "ISIN": [f"asset-{date.day}" for date in cutoff_days],
        "timestamp": cutoff_days,
        "transactionType": "Buy",
    })
    complete = run.Experiment.from_transactions(transactions)
    temporal_split = run.temporal_split

    def check_validation_input(buys, t1, t2):
        assert (t1, t2) == (complete.t1, complete.t2)
        assert buys["timestamp"].max() < t2
        return temporal_split(buys, t1, t2)

    monkeypatch.setattr(run, "temporal_split", check_validation_input)
    held_out = run.Experiment.from_transactions(transactions, validation_only=True)
    assert held_out.test.empty
    pd.testing.assert_frame_equal(held_out.validation, complete.validation)
    assert held_out.item_index == complete.item_index


def test_tuning_cli_writes_selected_validation_setting_and_lightgcn(monkeypatch, tmp_path):
    transactions = pd.DataFrame([
        ("u1", "A", "2022-01-01"),
        ("u2", "B", "2022-01-01"),
        ("u3", "C", "2022-01-01"),
        ("u1", "B", "2022-02-01"),
        ("future", "unseen", "2022-03-01"),
    ], columns=["customerID", "ISIN", "timestamp"])
    transactions["timestamp"] = pd.to_datetime(transactions["timestamp"])
    transactions["transactionType"] = "Buy"
    transactions.to_parquet(tmp_path / "transactions.parquet")
    out = tmp_path / "tuning"
    monkeypatch.setattr(sys, "argv", [
        "tune_nlgcl", "--processed-dir", str(tmp_path), "--out", str(out),
        "--t1", "2022-02-01", "--t2", "2022-03-01", "--seed", "9",
        "--contrastive-weights", "0.05", "0.02", "--temperatures", "0.2", "0.1",
        "--epochs", "1", "--dim", "2", "--threads", "1",
    ])

    tune_nlgcl.main()

    rows = pd.read_csv(out / "validation_grid.csv")
    selected = json.loads((out / "selected.json").read_text(encoding="utf-8"))
    assert rows["model"].tolist() == ["LightGCN", "NLGCL", "NLGCL", "NLGCL", "NLGCL"]
    assert selected["lightgcn"]["contrastive_weight"] == 0.0
    best = rows.loc[rows["model"] == "NLGCL"].sort_values(
        ["ndcg@10", "recall@20", "contrastive_weight", "temperature"],
        ascending=[False, False, True, True],
    ).iloc[0]
    assert selected["selected"] == best.to_dict()
    assert selected["seed"] == 9
    assert selected["training"]["epochs"] == 1
    assert selected["cutoffs"]["test"] == "2022-03-01T00:00:00"
