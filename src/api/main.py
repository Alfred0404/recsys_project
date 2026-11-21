"""Serve the trained recommender and the anonymous demo event log."""

from contextlib import asynccontextmanager
from dataclasses import asdict
import os
from pathlib import Path
from time import perf_counter
from typing import Annotated, Literal
from uuid import UUID

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field, StringConstraints, model_validator

from src.llm.profile import QUESTIONNAIRE, build_profile
from src.llm.reflection import configured_generator, verify_profile
from src.serve.predict import Recommender
from src.storage.interactions import initialize, insert_event


Isin = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9]{1,20}$")]
Amount = Annotated[float, Field(gt=0, le=1e15)]
Answer = Annotated[int, Field(ge=0, le=2, strict=True)]


class RecommendationRequest(BaseModel):
    holdings: dict[Isin, Amount] = Field(default_factory=dict, max_length=100)
    answers: dict[str, Answer] = Field(default_factory=dict, max_length=len(QUESTIONNAIRE))
    free_text: str = Field(default="", max_length=500)

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


class Interaction(BaseModel):
    session_id: UUID
    event: Literal["portfolio_entered", "recommendation_viewed", "feedback_positive", "feedback_negative"]
    isin: Isin | None = None


def create_app(model_path: Path | None = None, finance_dir: Path | None = None,
               db_path: Path | None = None) -> FastAPI:
    model_path = model_path or Path(os.getenv("RECSYS_MODEL_PATH", "dataset/experiment/model.npz"))
    finance_dir = finance_dir or Path(os.getenv("RECSYS_FINANCE_DIR", "dataset/experiment/finance"))
    db_path = db_path or Path(os.getenv("RECSYS_DB_PATH", "dataset/interactions.sqlite3"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.recommender = Recommender(model_path, finance_dir)
        app.state.profile_generator = configured_generator()
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
        start = perf_counter()
        holdings = payload.normalized_holdings()
        profile = build_profile(holdings, payload.answers)
        result = request.app.state.recommender.predict(holdings, profile)
        return {
            **result, "profile": asdict(profile), "server_ms": (perf_counter() - start) * 1000,
            "profile_review_available": request.app.state.profile_generator is not None,
        }

    @app.post("/profile")
    def profile(payload: RecommendationRequest, request: Request) -> dict:
        return verify_profile(payload.normalized_holdings(), payload.answers, payload.free_text,
                              request.app.state.profile_generator)

    @app.post("/log_interaction", status_code=201)
    def log_interaction(payload: Interaction) -> dict:
        return {"id": insert_event(db_path, str(payload.session_id), payload.event, payload.isin)}

    return app


app = create_app()
