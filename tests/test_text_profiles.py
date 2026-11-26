from collections import Counter

import pytest

from src.llm.profile import QUESTIONNAIRE
from src.llm.reflection import infer_profile, review_profile
from src.llm.text_benchmark import DRAFT_FIXTURE, THOMAS_FIXTURE, load_cases

TEAM_FIXTURES = {name: THOMAS_FIXTURE.with_name(f"{name}_profiles.json") for name in ("alfred", "ethan", "nicolas", "thomas")}


def test_successful_reflection_uses_actual_text_and_records_actor_separately():
    statement = "I accept small fluctuations, but stability matters most."
    prompts = []
    responses = iter(({"risk_level": 4}, {"risk_level": 2, "accepted": False}, {"risk_level": 2}))

    def generate(prompt):
        prompts.append(prompt)
        return next(responses)

    result = review_profile({}, {}, statement, generate)

    assert result["actor_profile"] == {"risk_level": 4}
    assert result["profile"]["risk_level"] == 2
    assert result["profile"]["source"] == "text_verified"
    assert result["status"] == "refined"
    assert all(statement in prompt for prompt in prompts)


def test_explicit_capital_preservation_overrides_model_acceptance():
    responses = iter(({"risk_level": 4}, {"risk_level": 4, "accepted": True}))
    result = review_profile({}, {}, "Je dois préserver le capital.", lambda _: next(responses))
    assert result["profile"]["risk_level"] == 1
    assert result["status"] == "rules_fallback"
    assert result["actor_profile"]["risk_level"] == 4


def test_complete_questionnaire_retains_precedence_and_invalid_actor_abstains():
    result = review_profile({}, dict.fromkeys(QUESTIONNAIRE, 0), "J’accepte de fortes baisses.", None)
    assert result["profile"]["risk_level"] == 1
    assert result["profile"]["source"] == "questionnaire"
    assert infer_profile({}, 2, lambda _: {"risk_level": True}) == {
        "actor_level": None, "risk_level": 2, "status": "rules_fallback",
    }


def test_team_benchmark_rejects_incomplete_and_duplicate_contributions():
    assert len(load_cases([THOMAS_FIXTURE])) == 10
    with pytest.raises(ValueError, match="10 cases from each"):
        load_cases([THOMAS_FIXTURE], require_team=True)
    with pytest.raises(ValueError, match="duplicate fixture"):
        load_cases([THOMAS_FIXTURE, THOMAS_FIXTURE])


def test_draft_suite_is_balanced_and_cannot_pass_as_team_contributions():
    cases = load_cases([THOMAS_FIXTURE, DRAFT_FIXTURE])
    assert Counter(row["risk_level"] for row in cases) == dict.fromkeys(range(1, 5), 10)
    assert Counter(row["author"] for row in cases) == {"thomas": 10, "draft": 30}
    with pytest.raises(ValueError, match="10 cases from each"):
        load_cases([THOMAS_FIXTURE, DRAFT_FIXTURE], require_team=True)


@pytest.mark.parametrize("author", sorted(TEAM_FIXTURES))
def test_team_contribution_has_ten_cases_covering_every_level(author):
    cases = load_cases([TEAM_FIXTURES[author]])
    assert len(cases) == 10
    assert {row["author"] for row in cases} == {author}
    assert set(Counter(row["risk_level"] for row in cases)) == set(range(1, 5))


def test_team_contributions_do_not_collide():
    assert len(load_cases(list(TEAM_FIXTURES.values()))) == 40


def test_english_set_mirrors_every_french_contribution_and_passes_team_check():
    english = [THOMAS_FIXTURE.parent / "en" / path.name for path in TEAM_FIXTURES.values()]
    originals = {row["id"]: row for row in load_cases(list(TEAM_FIXTURES.values()))}
    translated = load_cases(english, require_team=True)
    assert {row["id"]: row["risk_level"] for row in translated} == {key: row["risk_level"] for key, row in originals.items()}
