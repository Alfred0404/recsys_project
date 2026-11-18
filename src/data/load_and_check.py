"""Load FAR-Trans, run data-quality checks, measure density, save typed Parquet.

Usage: python -m src.data.load_and_check
Reads dataset/FAR-Trans/*.csv, writes dataset/processed/*.parquet and dataset/processed/stats.md.
"""
from pathlib import Path

import pandas as pd

from src.data.holdings import running_positions

RAW = Path("dataset/FAR-Trans")
OUT = Path("dataset/processed")

DATE_COLS = {
    "transactions": ["timestamp"],
    "customer_information": ["lastQuestionnaireDate", "timestamp"],
    "asset_information": ["timestamp"],
    "close_prices": ["timestamp"],
    "limit_prices": ["minDate", "maxDate"],
    "markets": [],
}
ID_COLS = {"customerID": str, "ISIN": str, "transactionID": str, "marketID": str}


def load(raw: Path = RAW) -> dict[str, pd.DataFrame]:
    tables = {}
    for name, dates in DATE_COLS.items():
        df = pd.read_csv(raw / f"{name}.csv", dtype=ID_COLS)
        for c in dates:
            df[c] = pd.to_datetime(df[c], errors="coerce")
        tables[name] = df
    return tables


def k_core(pairs: pd.DataFrame, min_items: int, min_users: int) -> pd.DataFrame:
    """Repeat both filters until stable: dropping an asset can push a customer under the threshold."""
    while True:
        n = len(pairs)
        pairs = pairs[pairs.groupby("ISIN")["customerID"].transform("size") >= min_users]
        pairs = pairs[pairs.groupby("customerID")["ISIN"].transform("size") >= min_items]
        if len(pairs) == n:
            return pairs


def checks(t: dict[str, pd.DataFrame]) -> list[tuple[str, object]]:
    tx, prices, assets, cust = t["transactions"], t["close_prices"], t["asset_information"], t["customer_information"]
    priced = set(prices["ISIN"])
    return [
        ("Duplicate rows (all tables)", sum(int(df.duplicated().sum()) for df in t.values())),
        # Same ID, asset, date and value but different customers: one order shared by co-holders (likely joint accounts).
        ("Transactions sharing a transactionID with another customer", int(tx["transactionID"].duplicated(keep=False).sum())),
        ("Missing values in transactions", int(tx.isna().sum().sum())),
        ("Unparsed dates (all tables)", sum(int(df[c].isna().sum()) for n, df in t.items()
                                            for c in DATE_COLS[n] if c != "lastQuestionnaireDate")),
        ("Transactions with totalValue <= 0 or units <= 0", int(((tx["totalValue"] <= 0) | (tx["units"] <= 0)).sum())),
        ("Transacted ISINs without close prices", int((~tx["ISIN"].drop_duplicates().isin(priced)).sum())),
        ("Transacted ISINs missing from asset_information", int((~tx["ISIN"].drop_duplicates().isin(assets["ISIN"])).sum())),
        ("Transacting customers missing from customer_information",
         int((~tx["customerID"].drop_duplicates().isin(cust["customerID"])).sum())),
        ("Customer-asset pairs selling more than their known position (clipped to 0)",
         len(running_positions(tx).query("raw_position < 0")[["customerID", "ISIN"]].drop_duplicates())),
        ("Customers with several profile records", int((cust.groupby("customerID").size() > 1).sum())),
        ("Assets with several description records", int((assets.groupby("ISIN").size() > 1).sum())),
    ]


def overview(t: dict[str, pd.DataFrame]) -> list[tuple[str, object]]:
    tx = t["transactions"]
    buys = tx[tx["transactionType"] == "Buy"]
    pairs = buys[["customerID", "ISIN"]].drop_duplicates()
    nu, ni = pairs["customerID"].nunique(), pairs["ISIN"].nunique()
    per_user = pairs.groupby("customerID").size()
    top10 = buys["ISIN"].value_counts().head(10).sum() / len(buys)
    return [
        ("Period", f"{tx['timestamp'].min():%Y-%m-%d} to {tx['timestamp'].max():%Y-%m-%d}"),
        ("Transactions (Buy / Sell)", f"{len(tx):,} ({len(buys):,} / {len(tx) - len(buys):,})"),
        ("Customers (all / with a buy)", f"{t['customer_information']['customerID'].nunique():,} / {nu:,}"),
        ("Assets (described / priced / bought)",
         f"{t['asset_information']['ISIN'].nunique():,} / {t['close_prices']['ISIN'].nunique():,} / {ni:,}"),
        ("Unique customer-asset buy pairs", f"{len(pairs):,}"),
        ("Density of the buy matrix", f"{len(pairs) / (nu * ni):.4%}"),
        ("Distinct assets bought per customer (median / mean)", f"{per_user.median():.0f} / {per_user.mean():.2f}"),
        ("Share of buys on the 10 most bought assets", f"{top10:.1%}"),
    ]


def density_grid(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    tx = t["transactions"]
    pairs = tx[tx["transactionType"] == "Buy"][["customerID", "ISIN"]].drop_duplicates()
    rows = []
    for mi in (1, 2, 3, 5):
        for mu in (1, 3, 5, 10):
            p = k_core(pairs, mi, mu)
            nu, ni = p["customerID"].nunique(), p["ISIN"].nunique()
            rows.append({"min assets / customer": mi, "min holders / asset": mu, "customers": nu,
                         "assets": ni, "pairs": len(p), "density": f"{len(p) / (nu * ni):.3%}" if nu else "-"})
    return pd.DataFrame(rows)


def md_table(rows: list[tuple[str, object]]) -> str:
    return "| Measure | Value |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows)


def main() -> None:
    t = load()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, df in t.items():
        df.to_parquet(OUT / f"{name}.parquet", index=False)

    grid = density_grid(t)
    report = "\n\n".join([
        "# FAR-Trans: data checks and density",
        "## Overview (interaction = a Buy)", md_table(overview(t)),
        "## Data-quality checks", md_table(checks(t)),
        "## Density after k-core filtering (not applied, for choosing thresholds)",
        grid.to_markdown(index=False),
    ])
    (OUT / "stats.md").write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
