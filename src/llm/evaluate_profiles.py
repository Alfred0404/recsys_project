"""Evaluate portfolio-based risk estimates against held-out FAR-Trans questionnaire labels.

Prepare the input tables with python -m src.data.load_and_check and configure
a local chat model before running python -m src.llm.evaluate_profiles.
"""

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from src.data.asset_returns import MIN_HISTORY, TRADING_DAYS, covariance, returns_matrix
from src.data.holdings import holdings_at
from src.llm.reflection import configured_generator

LEVELS = {"Conservative": 1, "Income": 2, "Balanced": 3, "Aggressive": 4}
PREDICTED_LEVELS = {f"Predicted_{name}": level for name, level in LEVELS.items()}
VOLATILITY_BANDS = (0.05, 0.10, 0.20)


def holdout_cohort(customers: pd.DataFrame, cutoff: pd.Timestamp):
    """First valid post-cutoff questionnaire per customer, with prior bank prediction if present."""
    observed = customers.loc[customers["riskLevel"].isin(LEVELS)]
    predicted = customers.loc[customers["riskLevel"].isin(PREDICTED_LEVELS)]
    questionnaire = observed["lastQuestionnaireDate"]
    holdout = observed.loc[(questionnaire >= cutoff) & (observed["timestamp"] >= questionnaire)]
    holdout = (
        holdout.sort_values(["lastQuestionnaireDate", "timestamp"], kind="stable")
        .drop_duplicates("customerID")
        .set_index("customerID")
        .sort_index()
    )
    prior = predicted.loc[predicted["timestamp"] < cutoff]
    prior = prior.sort_values("timestamp", kind="stable").drop_duplicates("customerID", keep="last")
    bank_levels = prior.set_index("customerID")["riskLevel"].map(PREDICTED_LEVELS)
    cohort = pd.DataFrame({
        "target": holdout["riskLevel"].map(LEVELS),
        "questionnaire_date": holdout["lastQuestionnaireDate"],
        "bank": bank_levels.reindex(holdout.index).astype("Int64"),
    })
    stats = {
        "customer_records": len(customers),
        "customers_with_observed_label_all_dates": int(observed["customerID"].nunique()),
        "customers_with_predicted_label_all_dates": int(predicted["customerID"].nunique()),
        "observed_predicted_customer_overlap_all_dates": len(
            set(observed["customerID"]) & set(predicted["customerID"])
        ),
        "customers_with_prior_bank_prediction": len(prior),
        "eligible_observed_customers": len(cohort),
        "eligible_bank_pairs": int(cohort["bank"].notna().sum()),
        "eligible_target_support": {name: int(cohort["target"].eq(level).sum()) for name, level in LEVELS.items()},
    }
    return cohort, stats


def stratified_sample(cohort: pd.DataFrame, size: int, seed: int) -> pd.DataFrame:
    """Sample up to size with equal quotas, redistributing unfilled slots."""
    rng = np.random.default_rng(seed)
    cohort = cohort.sort_index()
    target = min(size, len(cohort))
    quota, extra = divmod(target, len(LEVELS))
    selected = []
    for index, level in enumerate(LEVELS.values()):
        group = cohort.index[cohort["target"].eq(level)]
        count = min(len(group), quota + (index < extra))
        selected.extend(rng.choice(group, size=count, replace=False).tolist())
    need = target - len(selected)
    if need:
        remaining = cohort.index.difference(selected)
        selected.extend(rng.choice(remaining, size=need, replace=False).tolist())
    return cohort.loc[sorted(selected)]


def portfolio_facts(transactions: pd.DataFrame, prices: pd.DataFrame, cutoff: pd.Timestamp, customer_ids):
    """Return only aggregate pre-cutoff portfolio facts, with unknowns explicit."""
    prior_prices = prices.loc[prices["timestamp"] < cutoff]
    tx = transactions.loc[transactions["customerID"].isin(customer_ids)]
    positions = holdings_at(tx, prior_prices, cutoff)
    portfolios = dict(tuple(positions.groupby("customerID")))

    sigma = pd.DataFrame()
    if not prior_prices.empty and not positions.empty:
        returns = returns_matrix(prior_prices)
        recent_counts = returns.tail(TRADING_DAYS).count()
        if recent_counts.ge(MIN_HISTORY).any():
            sigma = covariance(returns, cutoff)

    facts_by_customer = {}
    for customer in customer_ids:
        facts = {"position_count": 0, "priced_position_count": 0,
                 "largest_position_share": None, "annualized_volatility": None}
        position = portfolios.get(customer)
        if position is not None:
            values = position["value"].to_numpy(dtype=float)
            priced = (np.isfinite(values) & (values > 0)).sum()
            facts["position_count"] = len(values)
            facts["priced_position_count"] = int(priced)
            if priced == len(values):
                weights = values / values.sum()
                facts["largest_position_share"] = round(float(weights.max()), 6)
                assets = position["ISIN"]
                if assets.isin(sigma.index).all():
                    variance = float(weights @ sigma.loc[assets, assets].to_numpy() @ weights)
                    facts["annualized_volatility"] = round(float(np.sqrt(max(variance, 0))), 6)
        facts_by_customer[customer] = facts
    return facts_by_customer


def rules_level(facts: dict) -> int:
    """Conservative default for missing vol; otherwise use fixed volatility bands."""
    volatility = facts["annualized_volatility"]
    return 1 if volatility is None else 1 + sum(volatility >= bound for bound in VOLATILITY_BANDS)


def classification_metrics(targets, predictions):
    """Four-class macro-F1; invalid or missing model outputs count as misses."""
    targets = list(targets)
    predicted = [value if type(value) is int and value in LEVELS.values() else 0 for value in predictions]
    valid = sum(value != 0 for value in predicted)
    return {
        "cases": len(targets),
        "predictions": valid,
        "missing_predictions": len(targets) - valid,
        "coverage": valid / len(targets) if targets else None,
        "accuracy": sum(a == b for a, b in zip(targets, predicted)) / len(targets) if targets else None,
        "macro_f1": float(f1_score(
            targets, predicted, labels=list(LEVELS.values()), average="macro", zero_division=0,
        )) if targets else None,
    }


def evaluate_sample(sample, facts_by_customer, generate, *, progress=None):
    from src.llm.reflection import infer_profile

    predictions = {method: [] for method in ("actor", "verified", "rules", "bank")}
    statuses = Counter()
    for index, (customer, row) in enumerate(sample.iterrows(), 1):
        facts = facts_by_customer[customer]
        rule = rules_level(facts)
        result = infer_profile(facts, rule, generate)
        predictions["actor"].append(result["actor_level"])
        predictions["verified"].append(result["risk_level"])
        predictions["rules"].append(rule)
        predictions["bank"].append(int(row["bank"]) if pd.notna(row["bank"]) else None)
        statuses[result["status"]] += 1
        if progress and (index % 5 == 0 or index == len(sample)):
            progress(index, len(sample))

    targets = sample["target"].astype(int).tolist()
    paired = [i for i, prediction in enumerate(predictions["bank"]) if prediction is not None]
    full = {name: classification_metrics(targets, predictions[name]) for name in ("actor", "verified", "rules")}
    matched = {
        name: classification_metrics([targets[i] for i in paired], [values[i] for i in paired])
        for name, values in predictions.items()
    }
    return {
        "full_sample": full,
        "paired_sample": matched,
        "bank_matches_in_sample": len(paired),
        "bank_coverage_in_sample": len(paired) / len(sample) if len(sample) else None,
        "inference_status": dict(statuses),
    }


def evaluate(processed: Path, cutoff: pd.Timestamp, sample_size: int, seed: int, generate, *, progress=None):
    start = time.perf_counter()
    customers = pd.read_parquet(processed / "customer_information.parquet")
    cohort, cohort_stats = holdout_cohort(customers, cutoff)
    if cohort.empty:
        raise ValueError("No dated observed questionnaires after the cutoff.")
    sample = stratified_sample(cohort, sample_size, seed)
    tx = pd.read_parquet(processed / "transactions.parquet")
    prices = pd.read_parquet(processed / "close_prices.parquet")
    facts = portfolio_facts(tx, prices, cutoff, sample.index)
    inference_start = time.perf_counter()
    results = evaluate_sample(sample, facts, generate, progress=progress)
    return {
        "dataset": "FAR-Trans",
        "cutoff": cutoff.isoformat(),
        "seed": seed,
        "requested_sample_size": sample_size,
        "sample_size": len(sample),
        "sample_target_support": {name: int(sample["target"].eq(level).sum()) for name, level in LEVELS.items()},
        "feature_coverage": {
            key: sum(fact[key] is not None for fact in facts.values())
            for key in ("largest_position_share", "annualized_volatility")
        },
        "rules_volatility_bands": list(VOLATILITY_BANDS),
        "cohort": cohort_stats,
        "bank_coverage_in_eligible_cohort": cohort_stats["eligible_bank_pairs"] / len(cohort),
        "model": os.getenv("RECSYS_PROFILE_MODEL") or os.getenv("RECSYS_OLLAMA_MODEL"),
        "inference_seconds": time.perf_counter() - inference_start,
        "total_seconds": time.perf_counter() - start,
        "limitations": [
            "Observed bank risk levels are questionnaire-label proxies, not independent suitability judgments.",
            "The stratified sample is for a four-class comparison, not an estimate of population prevalence.",
            "Only questionnaires on or after the cutoff with a row timestamp at or after their date are eligible.",
            "No bank-prediction scores are reported without customer-level matches; their training provenance is unknown.",
        ],
        **results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("dataset/processed"))
    parser.add_argument("--cutoff", default="2022-02-24")
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("dataset/experiment/profile_evaluation.json"))
    args = parser.parse_args()
    if args.sample_size < 1 or args.seed < 0:
        parser.error("Sample size must be positive and seed non-negative.")
    try:
        cutoff = pd.Timestamp(args.cutoff)
        if pd.isna(cutoff) or cutoff.tzinfo is not None:
            raise ValueError
    except ValueError:
        parser.error("Cutoff must be a valid date or timezone-naive timestamp.")
    generate = configured_generator()
    if generate is None:
        parser.error("Configure a local model with RECSYS_OLLAMA_MODEL or RECSYS_OPENAI_COMPAT_URL.")
    result = evaluate(
        args.processed_dir, cutoff, args.sample_size, args.seed, generate,
        progress=lambda done, total: print(f"Profiles evaluated: {done}/{total}", flush=True),
    )
    report = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
