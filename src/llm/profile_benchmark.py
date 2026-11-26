"""Measure the optional R4ec-inspired check on fixed synthetic profiles."""

import json

from src.llm.profile import QUESTIONNAIRE
from src.llm.reflection import configured_generator, verify_profile


def answers(scores):
    return dict(zip(QUESTIONNAIRE, scores))


# Expected (level, ceiling, gamma, concentrated) tuples are set independently
# from the code under test. Each holding dictionary represents a synthetic user.
CASES = (
    ({}, {}, (1, 3, 4.0, False)),
    ({"A": 1000}, answers((2, 2, 2)), (1, 3, 4.0, True)),
    ({"A": 700, "B": 300}, answers((0, 0, 0, 1)), (1, 3, 4.0, True)),
    ({"A": 699, "B": 301}, answers((0, 0, 2, 0)), (2, 4, 3.0, False)),
    ({"A": 50, "B": 50}, answers((0, 1, 1, 1)), (2, 4, 3.0, False)),
    ({"A": 60, "B": 20, "C": 20}, answers((1, 1, 1, 1)), (3, 5, 2.0, False)),
    ({"A": 90, "B": 10}, answers((1, 1, 1, 2)), (3, 5, 2.0, True)),
    ({"A": 80, "B": 20}, answers((0, 2, 2, 2)), (4, 7, 1.0, True)),
    ({"A": 33, "B": 33, "C": 34}, answers((2, 2, 2, 2)), (4, 7, 1.0, False)),
)


def benchmark(generate):
    fields = ("risk_level", "ceiling", "gamma", "concentrated")
    results = []
    for case, (holdings, response, expected) in enumerate(CASES, 1):
        review = verify_profile(holdings, response, "", generate)
        profile = review["profile"]
        checked = (profile["risk_level"], profile["ceiling"], profile["gamma"],
                   bool(holdings and profile["gaps"]))
        results.append({
            "case": case,
            "actor_match": review["actor_matches"] is True
            and review["actor_profile"] == dict(zip(fields, expected)),
            "final_match": checked == expected,
            "status": review["status"],
        })
    return {
        "cases": len(results),
        "actor_matches": sum(row["actor_match"] for row in results),
        "final_matches": sum(row["final_match"] for row in results),
        "refined": sum(row["status"] == "refined" for row in results),
        "fallbacks": sum(row["status"] == "rules_fallback" for row in results),
        "details": results,
    }


def main():
    generate = configured_generator()
    if generate is None:
        raise SystemExit("Configure RECSYS_OLLAMA_MODEL or RECSYS_OPENAI_COMPAT_URL first.")
    print(json.dumps(benchmark(generate), indent=2))


if __name__ == "__main__":
    main()
