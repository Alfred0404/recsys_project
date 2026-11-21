"""Optional R4ec-inspired profile review using a local chat model."""

import json
import os
from collections.abc import Callable
from dataclasses import asdict
from math import isfinite

import requests

from src.llm.profile import QUESTIONNAIRE, RISK_LEVELS, build_profile


def configured_generator() -> Callable[[str], dict] | None:
    chat_url = os.getenv("RECSYS_OPENAI_COMPAT_URL")
    model = os.getenv("RECSYS_OLLAMA_MODEL")
    if not chat_url and not model:
        return None

    def generate(prompt: str) -> dict:
        if chat_url:
            payload = {
                "model": os.getenv("RECSYS_PROFILE_MODEL", "local"),
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}, "max_tokens": 192, "temperature": 0,
            }
            response = requests.post(chat_url, json=payload, timeout=20)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        else:
            url = os.getenv("RECSYS_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
            payload = {
                "model": model, "prompt": prompt, "format": "json", "stream": False,
                "options": {"temperature": 0, "num_predict": 192},
            }
            response = requests.post(f"{url}/api/generate", json=payload, timeout=20)
            response.raise_for_status()
            content = response.json()["response"]
        return json.loads(content)

    return generate


def verify_profile(holdings: dict[str, float], answers: dict[str, int], free_text: str,
                   generate: Callable[[str], dict] | None) -> dict:
    """Run an actor, a reviewer, and at most one refinement before falling back to rules."""
    reference = build_profile(holdings, answers)
    result = {"profile": asdict(reference), "actor_profile": None, "actor_matches": None,
              "final_matches": True, "status": "rules"}
    if generate is None:
        return result

    expected = {"risk_level": reference.risk_level, "ceiling": reference.ceiling, "gamma": reference.gamma,
                "concentrated": bool(holdings and reference.gaps)}
    total_value = sum(holdings.values())
    facts = {"answers": answers, "position_shares": [amount / total_value for amount in holdings.values()],
             "text_provided": bool(free_text)}
    instructions = (
        "Calculate an educational investment risk profile, returning only JSON with exact keys "
        "risk_level (integer), ceiling (integer), gamma (number), concentrated (boolean). "
        f"If any of {list(QUESTIONNAIRE)} are missing, risk_level is 1. Otherwise sum the four answers. "
        "Risk levels: total 0–1 → 1, 2–3 → 2, 4–5 → 3, 6–8 → 4. "
        f"Level maps to (ceiling, gamma) as {RISK_LEVELS}. "
        "A portfolio is concentrated exactly when at least one share is 0.7 or more. "
        f"Facts: {json.dumps(facts)}."
    )

    def matches(proposal: dict) -> bool:
        return (isinstance(proposal, dict) and proposal.keys() == expected.keys()
                and type(proposal["risk_level"]) is int and type(proposal["ceiling"]) is int
                and type(proposal["gamma"]) in (int, float) and type(proposal["concentrated"]) is bool
                and proposal == expected)

    result["status"] = "rules_fallback"
    try:
        initial = generate(instructions)
        result["actor_matches"] = matches(initial)
        if isinstance(initial, dict):
            # Keep the trace limited to the expected numeric/boolean fields.
            result["actor_profile"] = {
                key: value for key, value in initial.items()
                if key in expected and type(value) in (int, bool, float)
                and (type(value) is not float or isfinite(value))
            }
        review = generate(
            f"{instructions}\nReview the proposal {json.dumps(initial)} against the facts and rules. "
            'Return JSON with exactly two keys, "accepted" (boolean) and "feedback" (string).'
        )
        if result["actor_matches"] and isinstance(review, dict) and review.get("accepted") is True:
            result["status"] = "verified"
        else:
            corrections = {key: value for key, value in expected.items()
                           if not isinstance(initial, dict) or initial.get(key) != value}
            refined = generate(
                f"{instructions}\nFirst proposal: {json.dumps(initial)}. Review: {json.dumps(review)}. "
                f"Apply the checked corrections {json.dumps(corrections)} and return the corrected profile JSON."
            )
            if matches(refined):
                result["status"] = "refined"
    except (requests.RequestException, IndexError, KeyError, TypeError, ValueError):
        # A malformed or unavailable optional model cannot change the checked profile.
        pass
    return result
