"""Compare raw model, template and served explanations on the same fixed facts."""

import json
from collections import Counter

from src.llm.explainer import ExplanationFacts, assess_sentence, explain_suggestion, template_explanation
from src.llm.reflection import configured_generator


CASES = (
    ExplanationFacts(1, None), ExplanationFacts(3, None), ExplanationFacts(7, None),
    ExplanationFacts(2, -0.00013), ExplanationFacts(3, -0.0225), ExplanationFacts(4, 0.0),
    ExplanationFacts(5, 0.00258), ExplanationFacts(6, 0.10543), ExplanationFacts(7, -0.01002),
)


def benchmark(generate) -> dict:
    rows = []
    for case, facts in enumerate(CASES, 1):
        raw = None

        def capture(prompt):
            nonlocal raw
            result = generate(prompt)
            raw = result.get("explanation") if isinstance(result, dict) else None
            return result

        served = explain_suggestion(facts, capture)
        raw_assessment = assess_sentence(raw, facts)
        if served["status"] in ("model_unavailable", "invalid_model_response"):
            raw_assessment = served["status"]
        rows.append({
            "case": case,
            "risk_class": facts.risk_class,
            "variance_change": facts.variance_change,
            "raw_llm": raw_assessment,
            "raw_sentence": raw if isinstance(raw, str) else None,
            "template": assess_sentence(template_explanation(facts), facts),
            "served": assess_sentence(served["explanation"], facts),
            "served_source": served["source"],
        })

    return {
        "cases": len(rows),
        "raw_llm": dict(Counter(row["raw_llm"] for row in rows)),
        "template": dict(Counter(row["template"] for row in rows)),
        "served": dict(Counter(row["served"] for row in rows)),
        "served_sources": dict(Counter(row["served_source"] for row in rows)),
        "details": rows,
    }


def main():
    generate = configured_generator()
    if generate is None:
        raise SystemExit("Configure RECSYS_OLLAMA_MODEL or RECSYS_OPENAI_COMPAT_URL first.")
    print(json.dumps(benchmark(generate), indent=2))


if __name__ == "__main__":
    main()
