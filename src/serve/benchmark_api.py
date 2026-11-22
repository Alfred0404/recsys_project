"""Measure warm HTTP recommendation latency and the deferred explanation path."""

import argparse
import json
from pathlib import Path
from math import isfinite
from statistics import median, quantiles
from time import perf_counter
from uuid import uuid4

import requests

from src.llm.profile import QUESTIONNAIRE


def timed_post(client: requests.Session, base: str, route: str, data: dict, timeout: float) -> tuple[dict, float]:
    start = perf_counter()
    response = client.post(f"{base}/{route}", json=data, timeout=timeout)
    response.raise_for_status()
    return response.json(), (perf_counter() - start) * 1000


def benchmark(base: str, count: int, budget_ms: float, check_deferred: bool) -> dict:
    if count < 3 or not isfinite(budget_ms) or budget_ms <= 0:
        raise ValueError("Use at least 3 requests and a positive budget.")
    base = base.rstrip("/")
    with requests.Session() as client:
        assets = client.get(f"{base}/assets", timeout=5)
        assets.raise_for_status()
        selected = assets.json()[:3]
        if len(selected) != 3:
            raise ValueError("The benchmark requires at least three assets in the training catalogue.")
        portfolios = [
            {"holdings": {asset["isin"]: 1000}, "answers": dict.fromkeys(QUESTIONNAIRE, 1),
             "session_id": str(uuid4())}
            for asset in selected
        ]
        server_times, http_times = [], []
        for payload in portfolios:
            timed_post(client, base, "recommend", payload, 5)
        for index in range(count):
            payload = portfolios[index % len(portfolios)]
            ranking, elapsed = timed_post(client, base, "recommend", payload, 5)
            if ranking["ranking_source"] != "portfolio_embeddings" or not ranking["items"]:
                raise RuntimeError("Expected nonempty suggestions scored with the model embeddings.")
            if any(item["risk_class"] > ranking["profile"]["ceiling"] for item in ranking["items"]):
                raise RuntimeError("A suggestion exceeded the profile ceiling.")
            http_times.append(elapsed)
            server_times.append(ranking["server_ms"])

        p95 = quantiles(http_times, n=100, method="inclusive")[94]
        report = {
            "requests": count,
            "portfolios": len(portfolios),
            "http_median_ms": median(http_times),
            "http_p95_ms": p95,
            "http_max_ms": max(http_times),
            "server_p95_ms": quantiles(server_times, n=100, method="inclusive")[94],
            "budget_ms": budget_ms,
            "all_requests_under_budget": max(http_times) < budget_ms,
        }
        if check_deferred:
            explain_payload = {
                "recommendation_id": ranking["recommendation_id"],
                "isin": ranking["items"][0]["isin"],
                "session_id": payload["session_id"],
            }
            explanation, explain_ms = timed_post(client, base, "explain", explain_payload, 30)
            profile, first_profile_ms = timed_post(client, base, "profile", payload, 65)
            repeated, repeat_profile_ms = timed_post(client, base, "profile", payload, 65)
            reranked, _ = timed_post(client, base, "recommend", payload, 5)
            report["deferred"] = {
                "explanation_source": explanation["source"],
                "explanation_status": explanation["status"],
                "explanation_first_ms": explain_ms,
                "profile_status": profile["llm_status"],
                "profile_first_ms": first_profile_ms,
                "profile_repeat_ms": repeat_profile_ms,
                "profile_repeat_cache_hit": repeated["cached"],
                "recommendation_profile_cache_hit": reranked["profile_cache_hit"],
            }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=36)
    parser.add_argument("--budget-ms", type=float, default=2000)
    parser.add_argument("--check-deferred", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = benchmark(args.base_url, args.requests, args.budget_ms, args.check_deferred)
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        parser.exit(1, f"{exc}\n")
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not result["all_requests_under_budget"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
