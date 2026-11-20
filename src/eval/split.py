"""Temporal split of Buy transactions: train < T1 <= val < T2 <= test.

Output frames all have the columns [customerID, ISIN, timestamp], one buy per row.
Validation and test keep only *new* acquisitions: a (customer, asset) pair already
bought in an earlier period is dropped, so the target is what a customer newly acquires.
"""
import pandas as pd

COLS = ["customerID", "ISIN", "timestamp"]


def default_cutoffs(buys: pd.DataFrame, train_frac: float = 0.7, val_frac: float = 0.15):
    """T1 / T2 as timestamp quantiles of the buys (70% train, 15% val, 15% test)."""
    ts = buys["timestamp"]
    return ts.quantile(train_frac), ts.quantile(train_frac + val_frac)


def temporal_split(transactions: pd.DataFrame, t1=None, t2=None):
    """Return (train, val, test). Only rows with transactionType == 'Buy' are used."""
    buys = transactions
    if "transactionType" in buys.columns:
        buys = buys[buys["transactionType"] == "Buy"]
    buys = buys[COLS].drop_duplicates().sort_values("timestamp", kind="stable")
    if t1 is None or t2 is None:
        d1, d2 = default_cutoffs(buys)
        t1, t2 = t1 if t1 is not None else d1, t2 if t2 is not None else d2
    t1, t2 = pd.Timestamp(t1), pd.Timestamp(t2)
    if not t1 < t2:
        raise ValueError(f"T1 must be before T2, got {t1} and {t2}")

    train = buys[buys["timestamp"] < t1]
    val = buys[(buys["timestamp"] >= t1) & (buys["timestamp"] < t2)]
    test = buys[buys["timestamp"] >= t2]

    val = _only_new(val, train)
    test = _only_new(test, pd.concat([train, val_full(buys, t1, t2)]))
    return train.reset_index(drop=True), val.reset_index(drop=True), test.reset_index(drop=True)


def val_full(buys: pd.DataFrame, t1, t2) -> pd.DataFrame:
    """Every buy in the validation window, including repeats: they count as already owned for the test."""
    return buys[(buys["timestamp"] >= t1) & (buys["timestamp"] < t2)]


def _only_new(window: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Drop the pairs already in `history`, and keep each remaining pair once (its first buy)."""
    seen = pd.MultiIndex.from_frame(history[["customerID", "ISIN"]])
    pairs = pd.MultiIndex.from_frame(window[["customerID", "ISIN"]])
    window = window[~pairs.isin(seen)]
    return window.drop_duplicates(["customerID", "ISIN"], keep="first")


def check_no_leak(train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame) -> None:
    """Raise if time ordering is broken or a val/test pair is already known earlier."""
    if len(train) and len(val) and train["timestamp"].max() >= val["timestamp"].min():
        raise AssertionError("train overlaps validation in time")
    if len(val) and len(test) and val["timestamp"].max() >= test["timestamp"].min():
        raise AssertionError("validation overlaps test in time")
    key = lambda df: set(zip(df["customerID"], df["ISIN"]))
    if key(test) & (key(train) | key(val)):
        raise AssertionError("a test pair is already in train or validation")
    if key(val) & key(train):
        raise AssertionError("a validation pair is already in train")
