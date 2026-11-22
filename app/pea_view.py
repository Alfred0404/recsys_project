"""PEA before/after country exposure view (demo only, independent of the trained model)."""

import pandas as pd

from src.data.pea_etfs import exposure


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


def concentration(exposures: pd.Series) -> dict[str, float | str]:
    """Largest country and HHI (0-1) of a country exposure in %."""
    shares = exposures[exposures > 0] / exposures.sum()
    return {"top_country": shares.idxmax(), "top_share": float(shares.max()), "hhi": float((shares**2).sum())}
