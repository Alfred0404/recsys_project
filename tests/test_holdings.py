import pandas as pd
import pytest

from src.data.holdings import holdings_at, latest_before

D = pd.Timestamp


def tx(rows):
    return pd.DataFrame(rows, columns=["customerID", "ISIN", "transactionType", "timestamp", "units"])


PRICES = pd.DataFrame({"ISIN": ["A", "A", "B"], "timestamp": [D("2020-01-01"), D("2020-06-01"), D("2020-01-01")],
                       "closePrice": [10.0, 20.0, 5.0]})


def units(h):
    return dict(zip(zip(h["customerID"], h["ISIN"]), h["units"]))


def test_buy_then_sell():
    t = tx([("u", "A", "Buy", D("2020-01-01"), 10), ("u", "A", "Sell", D("2020-02-01"), 4)])
    assert units(holdings_at(t, PRICES, "2021-01-01")) == {("u", "A"): 6}


def test_sell_of_unseen_units_is_clipped():
    t = tx([("u", "A", "Sell", D("2020-01-01"), 5), ("u", "A", "Buy", D("2020-02-01"), 3)])
    assert units(holdings_at(t, PRICES, "2021-01-01")) == {("u", "A"): 3}
    assert holdings_at(t, PRICES, "2020-01-15").empty


def test_same_day_buy_comes_before_sell():
    t = tx([("u", "A", "Sell", D("2020-01-01"), 5), ("u", "A", "Buy", D("2020-01-01"), 5)])
    assert holdings_at(t, PRICES, "2021-01-01").empty


def test_ignores_transactions_and_prices_after_date():
    t = tx([("u", "A", "Buy", D("2020-01-01"), 1), ("u", "A", "Buy", D("2020-07-01"), 1)])
    h = holdings_at(t, PRICES, "2020-07-01")
    assert units(h) == {("u", "A"): 1}
    assert h["value"].iloc[0] == 20.0  # June price, not a later one


def test_weights_sum_to_one():
    t = tx([("u", "A", "Buy", D("2020-01-01"), 1), ("u", "B", "Buy", D("2020-01-01"), 2),
            ("v", "B", "Buy", D("2020-01-01"), 1)])
    h = holdings_at(t, PRICES, "2020-03-01")
    assert h.groupby("customerID")["weight"].sum().tolist() == pytest.approx([1, 1])
    assert h.set_index("customerID").loc["u"].set_index("ISIN")["weight"].to_dict() == pytest.approx({"A": .5, "B": .5})


def test_latest_before_picks_last_valid_record():
    c = pd.DataFrame({"customerID": ["u", "u", "u"], "riskLevel": ["Income", "Balanced", "Aggressive"],
                      "timestamp": [D("2019-01-01"), D("2020-01-01"), D("2022-01-01")]})
    assert latest_before(c, "customerID", "2021-01-01")["riskLevel"].tolist() == ["Balanced"]
