"""19 PEA-eligible ETFs listed on Euronext Paris, and the site's before/after country exposure view.

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
UNKNOWN_COUNTRY = "Non renseigné"


def load_pea() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (etfs, countries). countries: isin, country, weight in % of the ETF."""
    etfs = pd.read_csv(DIR / "etfs.csv", parse_dates=["as_of"])
    countries = pd.read_csv(DIR / "countries.csv")
    cls = np.searchsorted(SRRI_BANDS, etfs["volatility"] / 100, side="right") + 1
    etfs["risk_class"] = pd.array(np.where(etfs["volatility"].isna(), pd.NA, cls), dtype="Int64")
    return etfs, countries


def exposure(holdings: dict[str, float], countries: pd.DataFrame) -> pd.Series:
    """Country exposure in %, with a bucket for holdings without published weights."""
    amounts = pd.Series({isin: amount for isin, amount in holdings.items() if amount > 0}, dtype=float)
    if amounts.empty:
        return amounts

    weights = amounts / amounts.sum()
    covered = countries[countries["isin"].isin(weights.index)]
    result = pd.Series(dtype=float)
    if not covered.empty:
        contributions = covered["weight"] * covered["isin"].map(weights)
        result = contributions.groupby(covered["country"]).sum()
    unknown = weights.loc[~weights.index.isin(covered["isin"])].sum() * 100
    if unknown > 0:
        result.loc[UNKNOWN_COUNTRY] = unknown
    return result.sort_values(ascending=False)


def exposure_after(holdings: dict[str, float], candidate: str, countries: pd.DataFrame,
                   share: float = 0.10) -> pd.DataFrame:
    """Country exposure (% of portfolio) before and after moving `share` of it into `candidate`.

    The existing positions keep their relative weights and are scaled to 1 - share.
    An empty portfolio has no "before" and ends up fully in the candidate.
    """
    if not 0 < share <= 1:
        raise ValueError("share must be in (0, 1]")
    held = {isin: amount for isin, amount in holdings.items() if amount > 0}
    before = exposure(held, countries) if held else pd.Series(dtype=float)
    total = sum(held.values())
    after_amounts = {isin: amount / total * (1 - share) for isin, amount in held.items()} if held else {}
    after_amounts[candidate] = after_amounts.get(candidate, 0.0) + (share if held else 1.0)
    after = exposure(after_amounts, countries)
    table = pd.concat({"Avant": before, "Après": after}, axis=1).fillna(0.0)
    return table.sort_values("Après", ascending=False)


def concentration(exposures: pd.Series) -> dict[str, float | str | None]:
    """Largest named country and published-bucket HHI, when the allocation is covered."""
    unknown_share = float(exposures.get(UNKNOWN_COUNTRY, 0)) / 100
    known = exposures[exposures > 0].drop(labels=UNKNOWN_COUNTRY, errors="ignore")
    result = {"top_country": None, "top_share": None, "hhi": None, "unknown_share": unknown_share}
    if known.empty or unknown_share > 0:
        return result

    shares = known / known.sum()
    named_countries = shares.drop(labels="Other", errors="ignore")
    result["hhi"] = float((shares**2).sum())
    if not named_countries.empty:
        result["top_country"] = named_countries.idxmax()
        result["top_share"] = float(named_countries.max())
    return result
