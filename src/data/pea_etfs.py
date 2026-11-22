"""19 PEA-eligible ETFs listed on Euronext Paris, for the demo's before/after exposure view.

Source: justETF French profile pages (PEA eligibility, Paris ticker, TER, volatility, country
breakdown), read in November 2026; dates of each breakdown in `as_of`, one URL per ETF.
Countries are stored exactly as published, "Other" included: nothing is reallocated.
risk_class uses the same SRRI bands as the FAR-Trans assets, on justETF's annualised volatility
(3 years when published, else 1 year); empty when justETF shows no volatility.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.asset_returns import SRRI_BANDS

DIR = Path(__file__).parent / "pea"


def load_pea() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (etfs, countries). countries: isin, country, weight in % of the ETF."""
    etfs = pd.read_csv(DIR / "etfs.csv", parse_dates=["as_of"])
    countries = pd.read_csv(DIR / "countries.csv")
    cls = np.searchsorted(SRRI_BANDS, etfs["volatility"] / 100, side="right") + 1
    etfs["risk_class"] = pd.array(np.where(etfs["volatility"].isna(), pd.NA, cls), dtype="Int64")
    return etfs, countries


def exposure(holdings: dict[str, float], countries: pd.DataFrame) -> pd.Series:
    """Country exposure in % of a portfolio of PEA ETFs, from amounts per ISIN."""
    w = pd.Series(holdings, dtype=float)
    w = w / w.sum()
    c = countries[countries["isin"].isin(w.index)]
    return (c["weight"] * c["isin"].map(w)).groupby(c["country"]).sum().sort_values(ascending=False)
