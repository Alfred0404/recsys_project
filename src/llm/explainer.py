"""Generate an optional explanation and verify it against known numerical facts."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
import json
from math import isfinite
import re
from typing import Literal

import requests


ExplanationLanguage = Literal["fr", "en"]


@dataclass(frozen=True)
class ExplanationFacts:
    risk_class: int
    variance_change: float | None

    def __post_init__(self):
        if self.risk_class not in range(1, 8):
            raise ValueError("Risk class must be in [1, 7]")
        if self.variance_change is not None and not isfinite(self.variance_change):
            raise ValueError("Variance delta must be finite")

    @property
    def rounded_delta(self) -> Decimal | None:
        if self.variance_change is None:
            return None
        return Decimal(f"{self.variance_change:.4f}")


RISK_CLAUSE = (
    r"(?:La classe de risque estimée est de|Le risque estimé est de|L['’]actif présente un risque estimé de)"
    r" (?P<risk>[0-9]{1,2})(?:/| sur )(?P<scale>[0-9]{1,2})"
)
ALLOCATION_CLAUSE = (
    r" et,? (?:avec|pour) une allocation hypothétique de (?P<allocation>[0-9]{1,3})\s?%,?"
    r" la variance annualisée (?:varierait|évoluerait) de (?P<delta>[+−-]?[0-9]+(?:[.,][0-9]{1,6})?)"
)
ENGLISH_RISK_CLAUSE = (
    r"(?:The estimated risk class is|The estimated risk is)"
    r" (?P<risk>[0-9]{1,2})(?:/| out of )(?P<scale>[0-9]{1,2})"
)
ENGLISH_ALLOCATION_CLAUSE = (
    r" and,? (?:with|for) a hypothetical (?P<allocation>[0-9]{1,3})\s?% allocation,?"
    r" annualized variance would (?:change|vary) by (?P<delta>[+−-]?[0-9]+(?:\.[0-9]{1,6})?)"
)
SENTENCES = {
    "fr": re.compile(rf"{RISK_CLAUSE}(?:{ALLOCATION_CLAUSE})?\.", re.IGNORECASE),
    "en": re.compile(rf"{ENGLISH_RISK_CLAUSE}(?:{ENGLISH_ALLOCATION_CLAUSE})?\.", re.IGNORECASE),
}


def compact_number(value: Decimal, language: ExplanationLanguage = "fr") -> str:
    value = abs(value) if value == 0 else value
    formatted = f"{value:+.4f}"
    return formatted if language == "en" else formatted.replace(".", ",")


def template_explanation(facts: ExplanationFacts, language: ExplanationLanguage = "fr") -> str:
    delta = facts.rounded_delta
    if language == "en":
        risk = f"The estimated risk class is {facts.risk_class}/7"
        if delta is None:
            return f"{risk}."
        return (f"{risk} and, with a hypothetical 10% allocation, "
                f"annualized variance would change by {compact_number(delta, language)}.")
    risk = f"La classe de risque estimée est de {facts.risk_class}/7"
    if delta is None:
        return f"{risk}."
    return (f"{risk} et, avec une allocation hypothétique de 10 %, "
            f"la variance annualisée varierait de {compact_number(delta)}.")


def assess_sentence(
    sentence: object, facts: ExplanationFacts, language: ExplanationLanguage = "fr",
) -> Literal["faithful", "incorrect_facts", "unverifiable"]:
    """Require the whole sentence to be an approved structure, without extra claims."""
    if not isinstance(sentence, str) or len(sentence) > 300 or "\n" in sentence or "\r" in sentence:
        return "unverifiable"
    match = SENTENCES[language].fullmatch(" ".join(sentence.split()))
    if match is None:
        return "unverifiable"
    if int(match["risk"]) != facts.risk_class or int(match["scale"]) != 7:
        return "incorrect_facts"
    expected_delta = facts.rounded_delta
    if match["allocation"] is None:
        return "faithful" if expected_delta is None else "incorrect_facts"
    delta = Decimal(match["delta"].replace(",", ".").replace("−", "-"))
    return "faithful" if int(match["allocation"]) == 10 and delta == expected_delta else "incorrect_facts"


def generate_sentence(
    facts: ExplanationFacts, generate: Callable[[str], dict], language: ExplanationLanguage = "fr",
) -> object:
    risk = facts.risk_class
    delta = facts.rounded_delta
    sentence = f"Le risque estimé est de {risk}/7."
    if delta is not None:
        sentence = (f"Le risque estimé est de {risk}/7 et, pour une allocation hypothétique de 10 %, "
                    f"la variance annualisée évoluerait de {compact_number(delta)}.")
    if language == "en":
        sentence = template_explanation(facts, language)
    verified_facts = {
        "risk": risk,
        "scale": 7,
        "allocation_percent": 10 if delta is not None else None,
        "delta": str(abs(delta) if delta == 0 else delta) if delta is not None else None,
    }
    response_example = json.dumps({"explanation": sentence}, ensure_ascii=False)
    source = json.dumps(verified_facts)
    if language == "en":
        prompt = (f"Copy only this English JSON object: {response_example}\n"
                  f"Source facts: {source}\nReply with only the explanation key:")
    else:
        prompt = (f"Recopie uniquement cet objet JSON : {response_example}\n"
                  f"Source factuelle : {source}\nRéponse avec une seule clé explanation :")
    result = generate(prompt)
    return result.get("explanation") if isinstance(result, dict) else None


def explain_suggestion(
    facts: ExplanationFacts, generate: Callable[[str], dict] | None, language: ExplanationLanguage = "fr",
) -> dict:
    """Return a checked LLM sentence or the deterministic one-sentence explanation."""
    result = {"explanation": template_explanation(facts, language), "source": "template", "status": "not_configured"}
    if generate is None:
        message = ("The local model is not configured. The explanation uses the calculated facts." if language == "en"
                   else "Le modèle local n’est pas configuré. L’explication utilise les faits calculés.")
        return {**result, "message": message}
    try:
        candidate = generate_sentence(facts, generate, language)
    except requests.RequestException:
        message = ("The local model is unavailable. The explanation uses the calculated facts." if language == "en"
                   else "Le modèle local est indisponible. L’explication utilise les faits calculés.")
        return {**result, "status": "model_unavailable", "message": message}
    except (IndexError, KeyError, TypeError, ValueError):
        return {**result, "status": "invalid_model_response"}
    status = assess_sentence(candidate, facts, language)
    if status == "faithful":
        return {"explanation": candidate.strip(), "source": "llm", "status": "verified"}
    return {**result, "status": status}
