"""Serve the trained recommender and the anonymous demo event log."""

from contextlib import asynccontextmanager
from dataclasses import asdict
from functools import partial
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter
from typing import Annotated, Literal
from uuid import UUID, uuid4

from anyio import CapacityLimiter, to_thread
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints, model_validator
import requests

from src.llm.explainer import ExplanationFacts, explain_suggestion
from src.llm.profile import Profile, QUESTIONNAIRE, build_profile
from src.llm.reflection import configured_generator, review_profile
from src.serve.cache import TTLCache
from src.serve.predict import Recommender
from src.storage.interactions import initialize, insert_event


Isin = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9]{1,20}$")]
Amount = Annotated[float, Field(gt=0, le=1e15)]
Answer = Annotated[int, Field(ge=0, le=2, strict=True)]


class RecommendationRequest(BaseModel):
    holdings: dict[Isin, Amount] = Field(default_factory=dict, max_length=100)
    answers: dict[str, Answer] = Field(default_factory=dict, max_length=len(QUESTIONNAIRE))
    free_text: str = Field(default="", max_length=500)
    session_id: UUID | None = Field(default=None, description="Opaque session UUID shared by the demo requests.")

    @model_validator(mode="after")
    def validate_answers(self) -> "RecommendationRequest":
        if self.answers.keys() - QUESTIONNAIRE.keys():
            raise ValueError("Unknown questionnaire key")
        return self

    def normalized_holdings(self) -> dict[str, float]:
        holdings: dict[str, float] = {}
        for raw_isin, amount in self.holdings.items():
            isin = raw_isin.upper()
            holdings[isin] = holdings.get(isin, 0.0) + amount
        return holdings

    def profile_cache_key(self, holdings: dict[str, float]) -> tuple[UUID, bytes] | None:
        if self.session_id is None:
            return None
        inputs = json.dumps((holdings, self.answers, self.free_text.strip()), sort_keys=True).encode("utf-8")
        return self.session_id, sha256(inputs).digest()


class ExplanationRequest(BaseModel):
    recommendation_id: UUID
    isin: Isin
    session_id: UUID | None = None


class Interaction(BaseModel):
    session_id: UUID
    event: Literal["portfolio_entered", "recommendation_viewed", "feedback_positive", "feedback_negative",
                   "profile_review_requested"]
    isin: Isin | None = None


def create_app(model_path: Path | None = None, finance_dir: Path | None = None,
               db_path: Path | None = None) -> FastAPI:
    model_path = model_path or Path(os.getenv("RECSYS_MODEL_PATH", "dataset/experiment/model.npz"))
    finance_dir = finance_dir or Path(os.getenv("RECSYS_FINANCE_DIR", "dataset/experiment/finance"))
    db_path = db_path or Path(os.getenv("RECSYS_DB_PATH", "dataset/interactions.sqlite3"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.recommender = Recommender(model_path, finance_dir)
        app.state.generator = configured_generator()
        app.state.model_calls = CapacityLimiter(2)
        app.state.profiles = TTLCache[tuple[UUID, bytes], dict](max_entries=256, ttl=600)
        app.state.explanation_facts = TTLCache[UUID, tuple[UUID | None, dict[str, ExplanationFacts]]](
            max_entries=1024, ttl=300,
        )
        initialize(db_path)
        yield

    app = FastAPI(title="FAR-Trans Recommendations", lifespan=lifespan)

    @app.get("/health")
    def health(request: Request) -> dict:
        return {"status": "ready", "catalog_size": len(request.app.state.recommender.item_ids)}

    @app.get("/assets")
    def assets(request: Request) -> list[dict]:
        return request.app.state.recommender.catalog()

    @app.post("/recommend")
    def recommend(payload: RecommendationRequest, request: Request) -> dict:
        """Serve the ranked list without running the local language model."""
        start = perf_counter()
        holdings = payload.normalized_holdings()
        cache_key = payload.profile_cache_key(holdings)
        state = request.app.state
        cached = state.profiles.get(cache_key) if cache_key is not None else None
        profile = Profile(**cached["profile"]) if cached is not None else build_profile(holdings, payload.answers)
        result = state.recommender.predict(holdings, profile)
        recommendation_id = uuid4()
        facts = {item["isin"]: ExplanationFacts(item["risk_class"], item["variance_change"]) for item in result["items"]}
        state.explanation_facts.put(recommendation_id, (payload.session_id, facts))
        return {
            **result, "profile": asdict(profile), "server_ms": (perf_counter() - start) * 1000,
            "profile_review_available": state.generator is not None,
            "profile_cache_hit": cached is not None,
            "profile_status": cached["status"] if cached is not None else "unreviewed",
            "recommendation_id": recommendation_id,
        }

    @app.post("/profile")
    async def profile(payload: RecommendationRequest, request: Request) -> dict:
        """Review the profile and warm the optional session cache for the same recommendation inputs."""
        holdings = payload.normalized_holdings()
        cache_key = payload.profile_cache_key(holdings)
        state = request.app.state
        cached = state.profiles.get(cache_key) if cache_key is not None else None
        if cached is not None and cached["llm_status"] != "model_unavailable":
            return {**cached, "cached": True}

        llm_status = "not_configured" if state.generator is None else "configured"

        def generate(prompt):
            nonlocal llm_status
            try:
                return state.generator(prompt)
            except requests.RequestException:
                llm_status = "model_unavailable"
                raise

        review_call = partial(review_profile, holdings, payload.answers, payload.free_text.strip())
        if state.generator is None:
            review = review_call(None)
        else:
            review = await to_thread.run_sync(review_call, generate, limiter=state.model_calls)
        result = {**review, "llm_status": llm_status}
        if llm_status == "not_configured":
            result["message"] = "Le modèle local n’est pas configuré. Le profil a été établi par les règles."
        elif llm_status == "model_unavailable":
            result["message"] = "Le modèle local est indisponible. Le profil a été établi par les règles."
        if cache_key is not None:
            state.profiles.put(cache_key, result)
        return {**result, "cached": False}

    @app.post("/explain")
    async def explain(payload: ExplanationRequest, request: Request) -> dict:
        """Explain one item after the ranked list arrives, using the exact facts issued by /recommend."""
        state = request.app.state
        entry = state.explanation_facts.get(payload.recommendation_id)
        isin = payload.isin.upper()
        if entry is None or entry[0] != payload.session_id or isin not in entry[1]:
            raise HTTPException(status_code=404, detail="Recommendation item was not found in this session or has expired.")
        facts = entry[1][isin]
        if state.generator is None:
            result = explain_suggestion(facts, None)
        else:
            result = await to_thread.run_sync(explain_suggestion, facts, state.generator, limiter=state.model_calls)
        return {"isin": isin, **result}

    @app.post("/log_interaction", status_code=201)
    def log_interaction(payload: Interaction) -> dict:
        return {"id": insert_event(db_path, str(payload.session_id), payload.event, payload.isin)}

    return app


app = create_app()
