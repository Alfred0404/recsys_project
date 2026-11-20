"""Run the whole data pipeline and write every table the model and the API need.

Usage: python -m src.data.build [--before YYYY-MM-DD]
Without --before, uses the whole dataset. Prices are cut at `before` first, so nothing after it is used.
Writes to dataset/processed/: holdings, returns, mu, sigma, asset_risk, customers (parquet).
"""
import argparse

import pandas as pd

from src.data import load_and_check
from src.data.holdings import holdings_at, latest_before
from src.data.load_and_check import OUT
from src.data.asset_returns import asset_risk, covariance, expected_returns, returns_matrix


def build(before=None) -> None:
    load_and_check.main()  # typed parquet + stats.md
    tx = pd.read_parquet(OUT / "transactions.parquet")
    prices = pd.read_parquet(OUT / "close_prices.parquet")
    assets = pd.read_parquet(OUT / "asset_information.parquet")
    customers = pd.read_parquet(OUT / "customer_information.parquet")

    last_day = max(tx["timestamp"].max(), prices["timestamp"].max())
    before = pd.Timestamp(before) if before else last_day + pd.Timedelta(days=1)
    prices = prices[prices["timestamp"] < before]
    returns = returns_matrix(prices)
    sigma = covariance(returns, before)
    mu = expected_returns(returns, before).reindex(sigma.index)  # same assets, same order as Sigma

    tables = {
        "holdings": holdings_at(tx, prices, before),
        "returns": returns,
        "mu": mu.to_frame("mu"),
        "sigma": sigma,
        "asset_risk": asset_risk(prices, assets, before),
        "customers": latest_before(customers, "customerID", before),
    }
    for name, df in tables.items():
        df.to_parquet(OUT / f"{name}.parquet")
    print(f"\nBuilt with data before {before:%Y-%m-%d}: " +
          ", ".join(f"{n} {df.shape}" for n, df in tables.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", help="cutoff date, YYYY-MM-DD (default: whole dataset)")
    build(parser.parse_args().before)
