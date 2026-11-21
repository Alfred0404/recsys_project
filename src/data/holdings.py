"""Rebuild customer portfolios at any date by replaying buys and sells.

Every function takes a `before` date and only uses data strictly before it (no leakage).
Shared transactions (same transactionID, several customers, likely joint accounts) are kept
in full for each co-holder: weights inside each portfolio stay right; only sums across
customers are inflated, and the model never uses those.
"""
import pandas as pd

EPS = 1e-6  # units below this are float leftovers of a full sale


def running_positions(tx: pd.DataFrame) -> pd.DataFrame:
    """Add the position after each transaction, per customer and asset.

    Dates have no time, so on the same day buys come before sells. A sell larger than the
    known position sells units bought before 2018, which the dataset does not show: the
    position is clipped at 0 (`raw_position` keeps the unclipped value for diagnostics).
    """
    t = tx.assign(_sell=(tx["transactionType"] == "Sell").astype(int))
    t = t.sort_values(["customerID", "ISIN", "timestamp", "_sell"], kind="stable").drop(columns="_sell")
    signed = t["units"].where(t["transactionType"] == "Buy", -t["units"])
    keys = [t["customerID"], t["ISIN"]]
    raw = signed.groupby(keys).cumsum()
    # Running max(0, x + d) in closed form: x_t = S_t - min(0, min_{k<=t} S_k).
    floor = raw.groupby(keys).cummin().clip(upper=0)

    return t.assign(raw_position=raw, position=raw - floor)


def holdings_at(tx: pd.DataFrame, prices: pd.DataFrame, before) -> pd.DataFrame:
    """Portfolio of every customer just before `before`: customerID, ISIN, units, value, weight.

    value = units x last close price before the date (NaN if the asset has no price yet).
    """
    before = pd.Timestamp(before)
    pos = running_positions(tx[tx["timestamp"] < before])
    h = pos.groupby(["customerID", "ISIN"])["position"].last().reset_index(name="units")
    h = h[h["units"] > EPS].reset_index(drop=True)
    last_price = (prices[prices["timestamp"] < before].sort_values("timestamp")
                  .groupby("ISIN")["closePrice"].last())
    h["value"] = h["units"] * h["ISIN"].map(last_price).astype(float)
    h["weight"] = h["value"] / h.groupby("customerID")["value"].transform("sum")

    return h


def latest_before(df: pd.DataFrame, key: str, before) -> pd.DataFrame:
    """Last record per `key` (customerID or ISIN) with timestamp before the date.

    Use for customer_information (risk level can change) and asset_information.
    """
    d = df[df["timestamp"] < pd.Timestamp(before)].sort_values("timestamp", kind="stable")

    return d.drop_duplicates(key, keep="last").reset_index(drop=True)
