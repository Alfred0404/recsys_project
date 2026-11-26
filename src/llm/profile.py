"""Score the risk questionnaire and format factual explanations."""

from dataclasses import dataclass
from math import fsum


# Scores are ordered from the least to the most tolerant response to each question.
QUESTIONNAIRE = {
    "horizon": ("Horizon de placement", ("Moins de 2 ans", "2 à 5 ans", "Plus de 5 ans")),
    "goal": ("Objectif", ("Préserver le capital", "Équilibrer sécurité et croissance", "Chercher la croissance")),
    "loss": ("Réaction à une baisse de 20 %", ("Vendre", "Conserver", "Accepter la baisse et envisager de renforcer")),
    "experience": ("Expérience des placements", ("Débutant", "Intermédiaire", "Expérimenté")),
}

# Risk level -> (maximum asset class, risk coefficient).
RISK_LEVELS = {1: (3, 4.0), 2: (4, 3.0), 3: (5, 2.0), 4: (7, 1.0)}


@dataclass(frozen=True)
class Profile:
    risk_level: int
    ceiling: int
    gamma: float
    gaps: list[str]
    source: str


def portfolio_gaps(holdings: dict[str, float]) -> list[str]:
    if not holdings:
        return ["Aucune position renseignée."]
    largest = max(holdings.values())
    concentration = 1 / fsum(amount / largest for amount in holdings.values())
    # Put the largest position's size in context without inferring any sector or asset type.
    return ["Une position représente au moins 70 % du portefeuille."] if concentration >= 0.7 else []


def build_profile(holdings: dict[str, float], answers: dict[str, int]) -> Profile:
    """Score all four answers, defaulting conservatively if any answer is missing."""
    level = 1
    source = "default"
    if set(QUESTIONNAIRE).issubset(answers):
        total = sum(answers[key] for key in QUESTIONNAIRE)
        level = 1 + sum(total >= threshold for threshold in (2, 4, 6))
        source = "questionnaire"
    return profile_for_level(holdings, level, source)


def profile_for_level(holdings: dict[str, float], level: int, source: str) -> Profile:
    ceiling, gamma = RISK_LEVELS[level]
    return Profile(level, ceiling, gamma, portfolio_gaps(holdings), source)


def explain(risk_class: int, variance_change: float | None) -> str:
    risk = f"Classe de risque estimée : {risk_class}/7."
    if variance_change is None:
        return risk
    return f"{risk} Avec une allocation hypothétique de 10 %, variation de la variance estimée : {variance_change:+.4f}."
