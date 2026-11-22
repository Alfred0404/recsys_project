"""Suitability filter and mean-variance reranking for portfolio candidates."""

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

IMPACT_COLUMNS = ("variance_before", "variance_after", "variance_change", "utility_gain")


def risk_filter(
    isins: Iterable[str],
    asset_risk: Mapping[str, float] | pd.Series | pd.DataFrame,
    ceiling: int,
) -> list[str]:
    """Keep classified assets at or below the ceiling, in input ranking order."""
    if not 1 <= ceiling <= 7:
        raise ValueError("Risk ceiling must be in [1, 7]")
    candidates = list(isins)
    classes = _risk_classes(candidates, asset_risk)
    allowed = classes.between(1, ceiling).fillna(False)
    return [isin for isin, keep in zip(candidates, allowed) if keep]


def _risk_classes(candidates: list[str], asset_risk) -> pd.Series:
    if isinstance(asset_risk, pd.DataFrame):
        asset_risk = asset_risk.set_index("ISIN")["risk_class"]
    return pd.to_numeric(pd.Series(asset_risk).reindex(candidates), errors="coerce")


def risk_rerank(
    isins: Iterable[str],
    relevance: Mapping[str, float],
    asset_risk: Mapping[str, float] | pd.Series | pd.DataFrame,
    ceiling: int,
    *,
    tolerance: int = 0,
    penalty: float = 0.5,
) -> list[str]:
    """Rank by normalized relevance minus a penalty per class above the ceiling.

    Classes up to `ceiling + tolerance` are kept and unknown classes are dropped.
    Each class above the ceiling costs `penalty` on a [0, 1] relevance scale, so
    a suitable asset keeps its place unless the riskier one is clearly more
    relevant. With `tolerance=0` this is `risk_filter` ordered by relevance.
    Ties follow the incoming ranking.
    """
    if not 1 <= ceiling <= 7:
        raise ValueError("Risk ceiling must be in [1, 7]")
    if tolerance < 0 or not np.isfinite(penalty) or penalty < 0:
        raise ValueError("Tolerance and penalty must be non-negative")
    candidates = list(dict.fromkeys(isins))
    classes = _risk_classes(candidates, asset_risk)
    allowed = classes.between(1, min(ceiling + tolerance, 7)).fillna(False).to_numpy()
    kept = [isin for isin, keep in zip(candidates, allowed) if keep]
    if not kept:
        return []

    relevance_scores = np.array([relevance[isin] for isin in kept], dtype=float)
    if not np.isfinite(relevance_scores).all():
        raise ValueError("Relevance scores must all be finite")
    excess = np.maximum(classes.reindex(kept).to_numpy(dtype=float) - ceiling, 0)
    scores = _minmax(relevance_scores) - penalty * excess
    return [kept[i] for i in np.argsort(-scores, kind="stable")]


def portfolio_impact(
    isins: Iterable[str],
    weights: Mapping[str, float] | pd.Series,
    mu: Mapping[str, float] | pd.Series | pd.DataFrame,
    sigma: pd.DataFrame,
    gamma: float,
    *,
    allocation: float = 0.1,
) -> pd.DataFrame:
    """Compute before/after annual variance and gain in mean-variance utility.

    The new asset represents `allocation` of the resulting portfolio. Positive
    holdings covered by both financial tables are normalized to sum to one.
    With no covered holdings the hypothetical portfolio holds only the new
    asset. Candidates with incomplete financial inputs do not get MPT scores.
    """
    if not 0 < allocation <= 1 or not np.isfinite(gamma) or gamma < 0:
        raise ValueError("Allocation must be in (0, 1] and gamma must be finite and non-negative")
    if isinstance(mu, pd.DataFrame):
        mu = mu.iloc[:, 0]

    def covered(isin: str) -> bool:
        return isin in sigma.index and isin in sigma.columns and isin in mu and np.isfinite(mu[isin])

    candidates = [isin for isin in dict.fromkeys(isins) if covered(isin)]
    index = pd.Index(candidates, name="ISIN")
    if not candidates:
        return pd.DataFrame(index=index, columns=IMPACT_COLUMNS, dtype=float)

    held = [isin for isin, value in weights.items() if value > 0 and np.isfinite(value) and covered(isin)]
    diagonal = np.array([sigma.at[isin, isin] for isin in candidates], dtype=float)
    candidate_mu = np.array([mu[isin] for isin in candidates], dtype=float)
    if held:
        portfolio = np.array([weights[isin] for isin in held], dtype=float)
        portfolio /= portfolio.max()
        portfolio /= portfolio.sum()
        before_mu = portfolio @ np.array([mu[isin] for isin in held], dtype=float)
        before_var = max(float(portfolio @ sigma.loc[held, held].to_numpy() @ portfolio), 0.0)
        cross = sigma.loc[candidates, held].to_numpy() @ portfolio
        after_var = (
            (1 - allocation) ** 2 * before_var
            + 2 * allocation * (1 - allocation) * cross
            + allocation**2 * diagonal
        )
    else:
        allocation = 1.0
        before_mu = before_var = 0.0
        after_var = diagonal

    after_var = np.maximum(after_var, 0.0)
    variance_change = after_var - before_var
    utility_gain = allocation * (candidate_mu - before_mu) - gamma * variance_change
    impact = pd.DataFrame(
        {
            "variance_before": before_var,
            "variance_after": after_var,
            "variance_change": variance_change,
            "utility_gain": utility_gain,
        },
        index=index,
    )
    return impact.loc[np.isfinite(impact).all(axis=1)]


def _minmax(values: np.ndarray) -> np.ndarray:
    low, high = values.min(), values.max()
    return (values - low) / (high - low) if high > low else np.zeros_like(values)


def mpt_rerank(
    isins: Iterable[str],
    relevance: Mapping[str, float],
    weights: Mapping[str, float] | pd.Series,
    mu: Mapping[str, float] | pd.Series | pd.DataFrame,
    sigma: pd.DataFrame,
    gamma: float,
    lam: float,
    *,
    allocation: float = 0.1,
) -> list[str]:
    """Rank by (1-lam) × normalized relevance + lam × normalized utility gain.

    Candidates without a measurable gain receive zero MPT contribution.
    Ties follow the incoming ranking.
    """
    if not 0 <= lam <= 1:
        raise ValueError("MPT weight must be in [0, 1]")
    candidates = list(dict.fromkeys(isins))
    if not candidates:
        return []

    relevance_scores = np.array([relevance[isin] for isin in candidates], dtype=float)
    if not np.isfinite(relevance_scores).all():
        raise ValueError("Relevance scores must all be finite")
    if lam == 0:
        return [candidates[i] for i in np.argsort(-relevance_scores, kind="stable")]
    utility = portfolio_impact(candidates, weights, mu, sigma, gamma, allocation=allocation)
    scores = (1 - lam) * _minmax(relevance_scores)
    if not utility.empty:
        measured = pd.Series(_minmax(utility["utility_gain"].to_numpy()), index=utility.index)
        scores += lam * measured.reindex(candidates, fill_value=0).to_numpy()
    elif lam == 1:
        scores = relevance_scores
    return [candidates[i] for i in np.argsort(-scores, kind="stable")]
