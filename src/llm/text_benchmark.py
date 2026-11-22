"""Compare profile stages on synthetic statements authored and labelled by the team."""

import argparse
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from sklearn.metrics import f1_score

from src.llm.profile import RISK_LEVELS
from src.llm.reflection import configured_generator, review_profile


THOMAS_FIXTURE = Path(__file__).with_name("fixtures") / "thomas_profiles.json"
TEAM = {"ethan", "alfred", "nicolas", "thomas"}


def load_cases(paths: list[Path], require_team: bool = False) -> list[dict]:
    cases = []
    ids, statements = set(), set()
    for path in paths:
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{path}: expected a nonempty JSON array.")
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"id", "author", "text", "risk_level"}:
                raise ValueError(f"{path}: each entry needs id, author, text and risk_level.")
            author, case_id, statement, level = (row[key] for key in ("author", "id", "text", "risk_level"))
            if (not isinstance(author, str) or author not in TEAM
                    or not isinstance(case_id, str) or not case_id.startswith(f"{author}-")
                    or not isinstance(statement, str) or not 1 <= len(statement.strip()) <= 500
                    or type(level) is not int or level not in RISK_LEVELS):
                raise ValueError(f"{path}: invalid author, ID, statement length, or risk level.")
            normalized_statement = " ".join(statement.casefold().split())
            if case_id in ids or normalized_statement in statements:
                raise ValueError(f"{path}: duplicate fixture {case_id}.")
            ids.add(case_id)
            statements.add(normalized_statement)
            cases.append(row)
    if require_team and Counter(row["author"] for row in cases) != {name: 10 for name in TEAM}:
        raise ValueError("The team benchmark requires exactly 10 cases from each of the four team members.")
    return cases


def compare(cases: list[dict], generate) -> dict:
    start = perf_counter()
    rows = []
    for case in cases:
        rule = review_profile({}, {}, case["text"], None)
        checked = review_profile({}, {}, case["text"], generate)
        rows.append({
            "id": case["id"],
            "expected": case["risk_level"],
            "rules": rule["profile"]["risk_level"],
            "actor": (checked["actor_profile"] or {}).get("risk_level"),
            "verified": checked["profile"]["risk_level"],
            "status": checked["status"],
        })
    expected = [row["expected"] for row in rows]
    scores = {}
    for key in ("rules", "actor", "verified"):
        predictions = [row[key] or 0 for row in rows]
        scores[key] = {
            "coverage": sum(level != 0 for level in predictions) / len(rows),
            "accuracy": sum(target == prediction for target, prediction in zip(expected, predictions)) / len(rows),
            "macro_f1": f1_score(expected, predictions, labels=list(RISK_LEVELS), average="macro", zero_division=0),
        }
    return {
        "cases": len(rows),
        "authors": dict(Counter(case["author"] for case in cases)),
        "reference_counts": dict(Counter(expected)),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "scores": scores,
        "elapsed_seconds": perf_counter() - start,
        "details": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, default=[THOMAS_FIXTURE])
    parser.add_argument("--require-team", action="store_true")
    args = parser.parse_args()
    generate = configured_generator()
    if generate is None:
        parser.error("Set RECSYS_OLLAMA_MODEL or RECSYS_OPENAI_COMPAT_URL first.")
    try:
        cases = load_cases(args.files, args.require_team)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(compare(cases, generate), indent=2))


if __name__ == "__main__":
    main()
