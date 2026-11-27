import json
import runpy

import numpy as np
import pandas as pd
import pytest

from src.llm import profile_benchmark, reflection
from src.llm.evaluate_profiles import evaluate_sample, holdout_cohort, portfolio_facts, stratified_sample


def test_synthetic_benchmark_keeps_the_previous_cli_working(monkeypatch, capsys):
    monkeypatch.setattr(profile_benchmark, "configured_generator", lambda: lambda _: {})

    profile_benchmark.main()
    expected = json.loads(capsys.readouterr().out)
    runpy.run_module("src.eval.profile_benchmark", run_name="__main__")

    assert json.loads(capsys.readouterr().out) == expected
    assert expected["cases"] == expected["final_matches"] == expected["fallbacks"] == 9


def test_holdout_uses_first_observed_questionnaire_and_latest_prior_bank_estimate():
    rows = [
        ("paired", "Predicted_Aggressive", "2000-01-01", "2022-01-01"),
        ("paired", "Predicted_Income", "2000-01-01", "2022-01-31"),
        ("paired", "Predicted_Balanced", "2000-01-01", "2022-02-01"),
        ("paired", "Balanced", "2022-02-05", "2022-02-08"),
        ("paired", "Aggressive", "2022-02-07", "2022-02-08"),
        ("missing", "Income", "2022-02-01", "2022-02-01"),
        ("old", "Conservative", "2022-01-10", "2022-02-11"),
        ("backdated", "Conservative", "2022-02-10", "2022-02-09"),
        ("predicted_only", "Predicted_Conservative", "2000-01-01", "2022-02-02"),
    ]
    columns = ["customerID", "riskLevel", "lastQuestionnaireDate", "timestamp"]
    customers = pd.DataFrame(rows, columns=columns)
    customers[columns[2:]] = customers[columns[2:]].apply(pd.to_datetime)
    cohort, stats = holdout_cohort(customers, pd.Timestamp("2022-02-01"))

    assert cohort["target"].to_dict() == {"missing": 2, "paired": 3}
    assert cohort.at["paired", "bank"] == 2
    assert pd.isna(cohort.at["missing", "bank"])
    assert stats["eligible_bank_pairs"] == 1
    assert stats["observed_predicted_customer_overlap_all_dates"] == 1


def test_portfolio_facts_ignore_prices_and_transactions_at_the_cutoff():
    cutoff = pd.Timestamp("2022-04-04")
    dates = pd.bdate_range(end=cutoff - pd.Timedelta(days=1), periods=80)
    prices = pd.DataFrame({
        "timestamp": dates.repeat(2),
        "ISIN": ["A", "B"] * len(dates),
        "closePrice": np.tile([20.0, 20.0], len(dates)),
    })
    columns = ["customerID", "ISIN", "units", "transactionType", "timestamp"]
    transactions = pd.DataFrame([
        ("user", "A", 10, "Buy", dates[0]),
        ("user", "B", 5, "Buy", dates[0]),
        ("partial", "A", 10, "Buy", dates[0]),
        ("partial", "X", 5, "Buy", dates[0]),
    ], columns=columns)
    ids = ["user", "partial", "empty"]
    expected = portfolio_facts(transactions, prices, cutoff, ids)
    future_prices = pd.concat([prices, pd.DataFrame([{
        "timestamp": cutoff, "ISIN": "A", "closePrice": 900.0,
    }])], ignore_index=True)
    future_trades = pd.concat([transactions, pd.DataFrame([
        ("user", "B", 100, "Buy", cutoff),
        ("empty", "A", 1, "Buy", cutoff),
    ], columns=columns)], ignore_index=True)

    assert portfolio_facts(future_trades, future_prices, cutoff, ids) == expected
    assert expected["user"] == {"position_count": 2, "priced_position_count": 2,
                                "largest_position_share": pytest.approx(2 / 3, abs=1e-6),
                                "annualized_volatility": 0.0}
    assert expected["partial"]["priced_position_count"] == 1
    assert expected["partial"]["largest_position_share"] is None
    assert expected["partial"]["annualized_volatility"] is None
    assert expected["empty"]["position_count"] == 0


def test_paired_metrics_share_targets_and_missing_output_counts_as_a_miss(monkeypatch):
    cohort = pd.DataFrame(
        {"target": [1, 4], "bank": pd.array([1, None], dtype="Int64")},
        index=["matched", "unmatched"],
    )
    sample = stratified_sample(cohort, 2, 42)
    facts = {
        "matched": {"position_count": 0, "priced_position_count": 0,
                    "largest_position_share": None, "annualized_volatility": None},
        "unmatched": {"position_count": 1, "priced_position_count": 1,
                      "largest_position_share": 1.0, "annualized_volatility": 0.25},
    }

    def infer(aggregate, level, _generate):
        assert set(aggregate) == {"position_count", "priced_position_count", "largest_position_share",
                                  "annualized_volatility"}
        return {"actor_level": 4 if aggregate["position_count"] else None,
                "risk_level": level, "status": "test"}

    monkeypatch.setattr(reflection, "infer_profile", infer)
    result = evaluate_sample(sample, facts, None)
    assert result["full_sample"]["actor"]["accuracy"] == 0.5
    assert result["full_sample"]["actor"]["macro_f1"] == 0.25
    assert result["full_sample"]["actor"]["missing_predictions"] == 1
    assert result["full_sample"]["verified"]["accuracy"] == 1.0
    assert result["bank_coverage_in_sample"] == 0.5
    assert {row["cases"] for row in result["paired_sample"].values()} == {1}
    assert result["paired_sample"]["bank"]["macro_f1"] == 0.25
    no_bank = sample.assign(bank=pd.NA)
    assert evaluate_sample(no_bank, facts, None)["paired_sample"]["bank"]["accuracy"] is None


def test_llm_timeout_comes_from_the_environment(monkeypatch):
    seen = {}

    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "{}"}

    def fake_post(url, json, timeout):
        seen["timeout"] = timeout
        return Reply()

    monkeypatch.setenv("RECSYS_OLLAMA_MODEL", "test-model")
    monkeypatch.delenv("RECSYS_OPENAI_COMPAT_URL", raising=False)
    monkeypatch.setattr(reflection.requests, "post", fake_post)

    monkeypatch.delenv("RECSYS_LLM_TIMEOUT", raising=False)
    reflection.configured_generator()("prompt")
    assert seen["timeout"] == 20

    monkeypatch.setenv("RECSYS_LLM_TIMEOUT", "90")
    reflection.configured_generator()("prompt")
    assert seen["timeout"] == 90

    monkeypatch.setenv("RECSYS_LLM_TIMEOUT", "0")
    with pytest.raises(ValueError):
        reflection.configured_generator()
