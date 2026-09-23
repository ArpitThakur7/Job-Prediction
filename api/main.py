from __future__ import annotations

"""
main.py
=======
FastAPI service for the XGBoost job-candidate matcher.

Endpoints
---------
    GET  /health                  — liveness check
    GET  /model/info              — loaded model metadata
    POST /match                   — score a single resume/job pair
    POST /match/batch             — score a list of pairs (up to 1000)
    POST /match/explain           — score + SHAP contributions for one pair

Run locally
-----------
    uvicorn api.main:app --reload --port 8000

With Docker
-----------
    docker build -t job-matcher .
    docker run -p 8000:8000 job-matcher

Interactive docs
----------------
    http://localhost:8000/docs    — Swagger UI
    http://localhost:8000/redoc  — ReDoc
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

# ---------------------------------------------------------------------------
# Paths  (relative to project root; adjust if you move main.py)
# ---------------------------------------------------------------------------

MODEL_PATH         = Path("ml/model/xgb_matcher.pkl")
FEATURE_COLS_PATH  = Path("ml/model/feature_columns.json")
THRESHOLD_PATH     = Path("ml/model/optimal_threshold.json")

# ---------------------------------------------------------------------------
# App-level state (loaded once at startup)
# ---------------------------------------------------------------------------

class _ModelState:
    model        = None
    feature_cols : list[str] = []
    threshold    : float     = 0.5
    loaded_at    : str       = ""


state = _ModelState()


def _load_threshold() -> float:
    if THRESHOLD_PATH.exists():
        with THRESHOLD_PATH.open() as f:
            t = float(json.load(f)["optimal_threshold"])
        logger.info("Loaded optimal threshold: %.4f", t)
        return t
    logger.warning("optimal_threshold.json not found — using 0.5")
    return 0.5


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model artifacts once on startup; release on shutdown."""
    logger.info("Loading model from %s ...", MODEL_PATH)
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model not found: {MODEL_PATH}. Run ml/train.py first.")

    state.model = joblib.load(MODEL_PATH)

    with FEATURE_COLS_PATH.open() as f:
        state.feature_cols = json.load(f)

    state.threshold  = _load_threshold()
    state.loaded_at  = time.strftime("%Y-%m-%dT%H:%M:%S")

    logger.info(
        "Model ready — features: %s | threshold: %.4f",
        state.feature_cols, state.threshold,
    )
    yield
    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Job-Candidate Matcher API",
    description=(
        "XGBoost-powered matching service. "
        "Scores resume/job pairs and returns match probability, "
        "verdict, and optional SHAP explanations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class FeaturePayload(BaseModel):
    """Feature values for one resume/job pair."""

    skill_overlap_count  : float = Field(..., ge=0,  description="Number of overlapping skills")
    skill_overlap_ratio  : float = Field(..., ge=0, le=1, description="Overlap / total job skills")
    experience_gap       : float = Field(..., description="Candidate exp − required exp (years)")
    education_score      : float = Field(..., ge=0,  description="Education alignment score")
    location_match       : float = Field(..., ge=0, le=1, description="1 if locations match")
    category_match       : float = Field(0.0, ge=0, le=1, description="1 if categories match")
    title_relevance      : float = Field(0.0, ge=0, le=1, description="Title relevance score")
    semantic_similarity  : float = Field(0.0, ge=0, le=1, description="Semantic similarity score")
    skills_count_resume  : float = Field(..., ge=0,  description="Total skills on resume")

    # Optional metadata — passed through to the response, not used in scoring
    resume_id : str | None = Field(None, description="Candidate identifier")
    job_id    : str | None = Field(None, description="Job posting identifier")

    @model_validator(mode="after")
    def check_ratio(self) -> "FeaturePayload":
        if self.skill_overlap_count > 0 and self.skill_overlap_ratio == 0:
            raise ValueError(
                "skill_overlap_ratio should be > 0 when skill_overlap_count > 0"
            )
        return self


class MatchResponse(BaseModel):
    resume_id         : str | None
    job_id            : str | None
    match_probability : float
    predicted_match   : int
    verdict           : str
    confidence        : str
    threshold_used    : float


class ExplainResponse(MatchResponse):
    base_value      : float
    contributions   : list[dict[str, Any]]


class BatchRequest(BaseModel):
    pairs: list[FeaturePayload] = Field(
        ..., min_length=1, max_length=1000,
        description="1–1000 resume/job pairs to score",
    )
    use_optimal_threshold: bool = Field(
        True,
        description="Use tuned threshold (0.7232); set False to use 0.5",
    )


class BatchResponse(BaseModel):
    total        : int
    matched      : int
    match_rate   : float
    results      : list[MatchResponse]


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

_FEATURE_ORDER = [
    "skill_overlap_count",
    "skill_overlap_ratio",
    "experience_gap",
    "education_score",
    "location_match",
    "category_match",
    "title_relevance",
    "semantic_similarity",
    "skills_count_resume",
]

def _confidence(prob: float, threshold: float) -> str:
    d = abs(prob - threshold)
    if d >= 0.25: return "High"
    if d >= 0.10: return "Medium"
    return "Low"


def _score_one(payload: FeaturePayload, threshold: float) -> MatchResponse:
    X = np.array([[
        payload.skill_overlap_count,
        payload.skill_overlap_ratio,
        payload.experience_gap,
        payload.education_score,
        payload.location_match,
        payload.category_match,
        payload.title_relevance,
        payload.semantic_similarity,
        payload.skills_count_resume,
    ]], dtype=float)

    prob      = float(state.model.predict_proba(X)[0, 1])
    predicted = int(prob >= threshold)

    return MatchResponse(
        resume_id         = payload.resume_id,
        job_id            = payload.job_id,
        match_probability = round(prob, 4),
        predicted_match   = predicted,
        verdict           = "MATCH" if predicted else "NO MATCH",
        confidence        = _confidence(prob, threshold),
        threshold_used    = threshold,
    )


def _explain_one(payload: FeaturePayload, threshold: float) -> ExplainResponse:
    """Run SHAP on a single pair and return contributions."""
    try:
        import shap
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="shap is not installed. Run: pip install shap",
        )

    import pandas as pd

    row = pd.DataFrame([{
        col: getattr(payload, col) for col in state.feature_cols
    }])

    explainer = shap.TreeExplainer(state.model)
    sv        = explainer(row)

    if sv.values.ndim == 3:
        import shap as _shap
        sv = _shap.Explanation(
            values      = sv.values[:, :, 1],
            base_values = sv.base_values[:, 1],
            data        = sv.data,
            feature_names = sv.feature_names,
        )

    base_value  = float(sv.base_values[0])
    shap_vals   = sv.values[0]
    feat_vals   = sv.data[0]

    contributions = sorted(
        [
            {
                "feature"  : name,
                "value"    : float(feat_vals[i]),
                "shap"     : round(float(shap_vals[i]), 4),
                "direction": "↑ match" if shap_vals[i] > 0 else "↓ match",
            }
            for i, name in enumerate(state.feature_cols)
        ],
        key=lambda x: abs(x["shap"]),
        reverse=True,
    )

    base = _score_one(payload, threshold)

    return ExplainResponse(
        **base.model_dump(),
        base_value    = round(base_value, 4),
        contributions = contributions,
    )


# ---------------------------------------------------------------------------
# Middleware: request timing
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    ms       = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{ms:.1f}"
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health():
    """Liveness check — returns 200 when the model is loaded."""
    if state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ok", "loaded_at": state.loaded_at}


@app.get("/model/info", tags=["System"])
def model_info():
    """Returns metadata about the currently loaded model."""
    if state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {
        "feature_columns" : state.feature_cols,
        "threshold"       : state.threshold,
        "n_estimators"    : int(state.model.n_estimators),
        "max_depth"       : int(state.model.max_depth),
        "loaded_at"       : state.loaded_at,
    }


@app.post(
    "/match",
    response_model=MatchResponse,
    tags=["Matching"],
    summary="Score a single resume/job pair",
)
def match_single(payload: FeaturePayload):
    """
    Score one resume/job pair.

    Returns match probability, binary verdict, and a High/Medium/Low
    confidence band based on distance from the decision threshold.
    """
    if state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    try:
        return _score_one(payload, state.threshold)
    except Exception as exc:
        logger.exception("Scoring error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/match/batch",
    response_model=BatchResponse,
    tags=["Matching"],
    summary="Score up to 1000 pairs in one request",
)
def match_batch(request: BatchRequest):
    """
    Score a list of resume/job pairs in a single request.

    Returns per-pair results plus aggregate statistics
    (total, matched count, match rate).
    """
    if state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    threshold = state.threshold if request.use_optimal_threshold else 0.5

    try:
        results = [_score_one(p, threshold) for p in request.pairs]
    except Exception as exc:
        logger.exception("Batch scoring error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    matched    = sum(1 for r in results if r.predicted_match == 1)
    match_rate = round(matched / len(results), 4)

    logger.info(
        "Batch scored %d pairs — matched: %d (%.1f%%)",
        len(results), matched, match_rate * 100,
    )

    return BatchResponse(
        total      = len(results),
        matched    = matched,
        match_rate = match_rate,
        results    = results,
    )


@app.post(
    "/match/explain",
    response_model=ExplainResponse,
    tags=["Matching"],
    summary="Score + SHAP explanation for one pair",
)
def match_explain(payload: FeaturePayload):
    """
    Score one pair and return per-feature SHAP contributions.

    Contributions are sorted by absolute impact descending.
    Requires the `shap` package to be installed.
    """
    if state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    try:
        return _explain_one(payload, state.threshold)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Explain error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s", request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )
