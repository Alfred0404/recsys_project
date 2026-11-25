"""Financial ablations on identical pre-test candidates and portfolios."""

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.asset_returns import asset_risk, covariance, expected_returns, returns_matrix, shrink_mu
from src.data.holdings import holdings_at, latest_before
from src.llm.profile import RISK_LEVELS
from src.rerank.mpt import mpt_rerank, portfolio_impact, risk_filter, risk_rerank

RISK_LABELS = {"conservative": 1, "income": 2, "balanced": 3, "aggressive": 4}
ALLOCATION = 0.10


def snapshot(tx: pd.DataFrame, cutoff: pd.Timestamp, processed: Path):
    prices = pd.read_parquet(processed / "close_prices.parquet")
    prices = prices[prices["timestamp"] < cutoff]
    assets = pd.read_parquet(processed / "asset_information.parquet")
    customers = pd.read_parquet(processed / "customer_information.parquet")
    # The attached questionnaire date can be later than the profile row timestamp.
    questionnaire = customers["lastQuestionnaireDate"]
    customers = customers[questionnaire < cutoff]
    returns = returns_matrix(prices)
    sigma = covariance(returns, cutoff)
    mu = expected_returns(returns, cutoff).reindex(sigma.index)
    risk = asset_risk(prices, assets, cutoff)
    holdings = holdings_at(tx, prices, cutoff)
    return {
        "mu": mu.to_frame("mu"),
        "sigma": sigma,
        "asset_risk": risk,
        "assets": latest_before(assets, "ISIN", cutoff),
        "holdings": holdings,
        "customers": latest_before(customers, "customerID", cutoff),
    }


def _exposures(holdings: pd.DataFrame) -> dict[str, dict[str, float]]:
    # Retain missing prices so a partially covered portfolio cannot look fully covered.
    return {user: dict(zip(rows["ISIN"], rows["value"])) for user, rows in holdings.groupby("customerID")}


def _risk_counts(candidates: list[str], classes: dict[str, int], ceiling: int) -> Counter:
    known = [classes[isin] for isin in candidates if isin in classes]
    return Counter(total=len(candidates), known=len(known), above_ceiling=sum(value > ceiling for value in known))


def _summarize_risk(counts: Counter):
    return {
        "suggestions": counts["total"],
        "known": counts["known"],
        "unknown": counts["total"] - counts["known"],
        "above_ceiling": counts["above_ceiling"],
        "violation_rate_known": counts["above_ceiling"] / counts["known"] if counts["known"] else None,
    }


def select_examples(examples, warm_users):
    """Pick cohorts using only pre-test holdings, profile and training membership."""
    candidates = [(user, row) for user, row in examples.items() if row["recommendations"]]
    selected = []
    for category, eligible in (
        ("concentrated", sorted(
            ((user, row) for user, row in candidates
             if user in warm_users and row["top1_variance_change"] is not None),
            key=lambda pair: -pair[1]["largest_holding_share"],
        )),
        ("cautious", [(user, row) for user, row in candidates
                      if row["risk_level"] <= 2 and row["risk_level_source"] == "observed"]),
        ("cold_start", [(user, row) for user, row in candidates if user not in warm_users]),
    ):
        match = next(((user, row) for user, row in eligible if user not in selected), None)
        if match is not None:
            user, row = match
            selected.append(user)
            yield {"cohort": category, **row}


def user_level(labels: dict, user) -> tuple[int, str]:
    """Dated questionnaire level, else the conservative serving default (level 1)."""
    label = str(labels.get(user, "")).casefold()
    # Provider Predicted_* labels have no documented pre-cutoff training
    # provenance. Use dated questionnaire profiles or the serving default.
    return RISK_LABELS.get(label, 1), "observed" if label in RISK_LABELS else "default"


def suitable_targets(targets: pd.DataFrame, tables) -> tuple[pd.DataFrame, dict]:
    """Keep the target purchases at or below each user's risk ceiling.

    A ranking that respects the ceiling can only retrieve these, so they bound what
    the filtered rankings can score. Purchases of unclassified assets are dropped.
    """
    classes = tables["asset_risk"].set_index("ISIN")["risk_class"].astype(int)
    labels = tables["customers"].set_index("customerID")["riskLevel"].to_dict()
    ceilings = {user: RISK_LEVELS[user_level(labels, user)[0]][0] for user in targets["customerID"].unique()}
    known = targets.loc[targets["ISIN"].isin(classes.index)]
    within = known["ISIN"].map(classes) <= known["customerID"].map(ceilings)
    stats = {
        "targets_with_class": len(known),
        "above_ceiling_share": float(1 - within.mean()) if len(known) else None,
        "users_with_suitable_target": int(known.loc[within, "customerID"].nunique()),
    }
    return known.loc[within], stats


def evaluate_reranking(scored, tx, cutoff, processed, out, warm_users, lam=0.25, tolerance=0, penalty=0.5,
                       mu_shrinkage=0.0, tables=None):
    tables = snapshot(tx, cutoff, processed) if tables is None else tables
    mu = shrink_mu(tables["mu"]["mu"].dropna(), mu_shrinkage)
    sigma = tables["sigma"]
    covered_isins = set(mu.index) & set(sigma.index) & set(sigma.columns)
    classes = tables["asset_risk"].set_index("ISIN")["risk_class"].astype(int).to_dict()
    names = tables["assets"].set_index("ISIN")["assetName"].dropna().to_dict()
    labels = tables["customers"].set_index("customerID")["riskLevel"].to_dict()
    exposures = _exposures(tables["holdings"])

    filtered_rankings, reranked_rankings, tolerant_rankings = {}, {}, {}
    examples = {}
    variance_pairs = []
    fully_covered_users = 0
    risk_counts = {name: Counter() for name in ("nlgcl", "risk_only", "mpt_risk")}
    if tolerance:
        risk_counts["risk_tolerant"] = Counter()
    level_source = Counter()
    for user, scores in scored.items():
        level, source = user_level(labels, user)
        level_source[source] += 1
        ceiling, gamma = RISK_LEVELS[level]
        relevance = dict(scores)
        holdings = exposures.get(user, {})
        allowed = risk_filter(relevance, classes, ceiling)
        priced_portfolio = bool(holdings) and all(np.isfinite(value) and value > 0 for value in holdings.values())
        covered_portfolio = priced_portfolio and covered_isins.issuperset(holdings)
        fully_covered_users += covered_portfolio
        reranked = allowed
        if covered_portfolio:
            reranked = mpt_rerank(allowed, relevance, holdings, mu, sigma, gamma, lam, allocation=ALLOCATION)
        filtered_rankings[user] = allowed
        reranked_rankings[user] = reranked
        variants = [("nlgcl", list(relevance)), ("risk_only", allowed), ("mpt_risk", reranked)]
        if tolerance:
            tolerant_rankings[user] = risk_rerank(
                relevance, relevance, classes, ceiling, tolerance=tolerance, penalty=penalty,
            )
            variants.append(("risk_tolerant", tolerant_rankings[user]))

        for name, items in variants:
            risk_counts[name].update(_risk_counts(items[:10], classes, ceiling))

        impact = pd.DataFrame()
        # Compare both top choices only for users with fully covered portfolios.
        if allowed and reranked and covered_portfolio:
            impact = portfolio_impact(
                [allowed[0], reranked[0]], holdings, mu, sigma, gamma, allocation=ALLOCATION,
            )
            if allowed[0] in impact.index and reranked[0] in impact.index:
                variance_pairs.append((impact.at[allowed[0], "variance_change"], impact.at[reranked[0], "variance_change"]))

        first = reranked[0] if reranked else None
        examples[user] = {
            "risk_level": level,
            "risk_level_source": source,
            "ceiling": ceiling,
            "holding_count": len(holdings),
            "largest_holding_share": max(holdings.values()) / sum(holdings.values()) if priced_portfolio else None,
            "recommendations": [
                {"isin": isin, "name": names.get(isin, isin), "risk_class": classes[isin]} for isin in reranked[:3]
            ],
            "top1_variance_change": float(impact.at[first, "variance_change"]) if first in impact.index else None,
        }

    finance = out / "finance"
    finance.mkdir(parents=True, exist_ok=True)
    for name in ("mu", "sigma", "asset_risk", "assets"):
        tables[name].to_parquet(finance / f"{name}.parquet")

    variance = np.array(variance_pairs)
    summary = {
        "as_of": cutoff.isoformat(),
        "mpt_weight": lam,
        "mu_shrinkage": mu_shrinkage,
        "risk_tolerance": tolerance,
        "risk_penalty": penalty,
        "allocation": ALLOCATION,
        "risk_level_source": dict(level_source),
        "fully_covered_portfolio_users": int(fully_covered_users),
        "top10_risk": {name: _summarize_risk(counts) for name, counts in risk_counts.items()},
        "paired_top1_variance": {
            "users": len(variance),
            "risk_only_mean_change": float(variance[:, 0].mean()) if len(variance) else None,
            "mpt_risk_mean_change": float(variance[:, 1].mean()) if len(variance) else None,
            "mpt_minus_risk_only": float((variance[:, 1] - variance[:, 0]).mean()) if len(variance) else None,
        },
        "examples": list(select_examples(examples, warm_users)),
    }
    rankings = {"risk_only": filtered_rankings, "mpt_risk": reranked_rankings}
    if tolerance:
        rankings["risk_tolerant"] = tolerant_rankings
    return summary, rankings
