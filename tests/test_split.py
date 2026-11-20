import pandas as pd
import pytest

from src.eval.split import check_no_leak, temporal_split


def tx(rows):
    df = pd.DataFrame(rows, columns=["customerID", "ISIN", "timestamp", "transactionType"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


ROWS = [
    ("u1", "a", "2020-01-10", "Buy"),
    ("u1", "b", "2020-06-01", "Buy"),   # val
    ("u1", "a", "2020-07-01", "Buy"),   # repeat of a train pair: not new
    ("u1", "c", "2021-03-01", "Buy"),   # test, new
    ("u1", "b", "2021-04-01", "Buy"),   # test, already bought in val: not new
    ("u2", "a", "2020-02-01", "Buy"),
    ("u2", "d", "2021-05-01", "Buy"),   # test, new
    ("u2", "e", "2021-05-02", "Sell"),  # sells are ignored
]
T1, T2 = "2020-05-01", "2021-01-01"


def test_no_test_transaction_in_train():
    train, val, test = temporal_split(tx(ROWS), T1, T2)
    check_no_leak(train, val, test)
    assert train["timestamp"].max() < pd.Timestamp(T1) <= val["timestamp"].min()
    assert val["timestamp"].max() < pd.Timestamp(T2) <= test["timestamp"].min()
    pairs = lambda df: set(zip(df["customerID"], df["ISIN"]))
    assert not pairs(test) & pairs(train)
    assert not pairs(test) & pairs(val)


def test_expected_content():
    train, val, test = temporal_split(tx(ROWS), T1, T2)
    assert list(train.columns) == ["customerID", "ISIN", "timestamp"]
    assert set(zip(train["customerID"], train["ISIN"])) == {("u1", "a"), ("u2", "a")}
    assert set(zip(val["customerID"], val["ISIN"])) == {("u1", "b")}
    assert set(zip(test["customerID"], test["ISIN"])) == {("u1", "c"), ("u2", "d")}


def test_check_detects_a_leak():
    train, val, test = temporal_split(tx(ROWS), T1, T2)
    with pytest.raises(AssertionError):
        check_no_leak(train, val, pd.concat([test, train.iloc[:1].assign(timestamp=pd.Timestamp("2022-01-01"))]))


def test_default_cutoffs_and_bad_order():
    df = tx(ROWS)
    train, val, test = temporal_split(df)
    check_no_leak(train, val, test)
    with pytest.raises(ValueError):
        temporal_split(df, T2, T1)
