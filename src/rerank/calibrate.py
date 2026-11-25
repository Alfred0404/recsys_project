"""Risk-aversion gamma implied by real portfolios, per declared risk level.

If a portfolio w maximises u = mu'w - gamma w'Sigma w, then mu = 2 gamma Sigma w, so
w'mu = 2 gamma w'Sigma w and the implied gamma is w'mu / (2 w'Sigma w) (the reverse
optimisation of Black-Litterman). We compute it for every customer with a dated
questionnaire level and a fully priced portfolio at the train cutoff, then take the
median per level. The grid in src/llm/profile.py is replaced only if these medians are
positive and decrease from conservative to aggressive. It also reports the share of
portfolios whose volatility already sits within the band of the declared level.

    python -m src.rerank.calibrate
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.eval.finance import RISK_LABELS, snapshot
from src.llm.evaluate_profiles import VOLATILITY_BANDS


def implied_gamma(weights: np.ndarray, mu: np.ndarray, sigma: np.ndarray) -> float:
    weights = np.asarray(weights, dtype=float) / np.sum(weights)
    variance = float(weights @ sigma @ weights)
    return float(weights @ mu) / (2 * variance) if variance > 0 else float("nan")


def portfolio_table(tables) -> pd.DataFrame:
    mu = tables["mu"]["mu"].dropna()
    sigma = tables["sigma"]
    covered = set(mu.index) & set(sigma.index)
    labels = tables["customers"].set_index("customerID")["riskLevel"].astype(str).str.casefold()
    levels = labels[labels.isin(RISK_LABELS)].map(RISK_LABELS)
    rows = []
    for user, held in tables["holdings"].groupby("customerID"):
        values = held.set_index("ISIN")["value"]
        if user not in levels.index or not covered.issuperset(values.index):
            continue
        if not (np.isfinite(values) & (values > 0)).all():
            continue
        isins = list(values.index)
        weights = values.to_numpy(dtype=float) / values.sum()
        cov = sigma.loc[isins, isins].to_numpy()
        rows.append({
            "customerID": user,
            "level": int(levels[user]),
            "assets": len(isins),
            "volatility": float(np.sqrt(weights @ cov @ weights)),
            "expected_return": float(weights @ mu[isins].to_numpy()),
            "implied_gamma": implied_gamma(weights, mu[isins].to_numpy(), cov),
        })
    return pd.DataFrame(rows)


def summarize(table: pd.DataFrame) -> dict:
    # Volatility level of the portfolio, with the bands used by the profile rules.
    observed = 1 + sum((table["volatility"] >= bound).astype(int) for bound in VOLATILITY_BANDS)
    table = table.assign(within_band=observed <= table["level"])
    by_level = table.groupby("level").agg(
        customers=("customerID", "size"),
        median_volatility=("volatility", "median"),
        median_expected_return=("expected_return", "median"),
        median_implied_gamma=("implied_gamma", "median"),
        positive_gamma_share=("implied_gamma", lambda values: float((values > 0).mean())),
        within_volatility_band_share=("within_band", "mean"),
    )
    medians = by_level["median_implied_gamma"].to_numpy()
    usable = bool((medians > 0).all() and (np.diff(medians) < 0).all())
    return {"by_level": by_level.round(4).reset_index().to_dict(orient="records"), "usable": usable}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("dataset/processed"))
    parser.add_argument("--experiment-dir", type=Path, default=Path("dataset/experiment"))
    args = parser.parse_args()
    with np.load(args.experiment_dir / "model.npz", allow_pickle=False) as saved:
        cutoff = pd.Timestamp(str(saved["train_cutoff"]))
    tx = pd.read_parquet(args.processed_dir / "transactions.parquet")
    result = {"as_of": cutoff.isoformat(), **summarize(portfolio_table(snapshot(tx, cutoff, args.processed_dir)))}
    out = args.experiment_dir / "gamma_calibration.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(pd.DataFrame(result["by_level"]).to_string(index=False))
    print("Usable as gamma grid:", result["usable"])


if __name__ == "__main__":
    main()
