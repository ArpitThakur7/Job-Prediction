from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

logger = logging.getLogger("backend.matcher")

_MODEL: Any | None = None
_FEATURE_COLUMNS: List[str] | None = None

_SKILL_OVERLAP_COUNT_KEY = "skill_overlap_count"
_SKILL_OVERLAP_RATIO_KEY = "skill_overlap_ratio"
_EXPERIENCE_GAP_KEY = "experience_gap"
_EDUCATION_SCORE_KEY = "education_score"
_LOCATION_MATCH_KEY = "location_match"
_CATEGORY_MATCH_KEY = "category_match"
_TITLE_RELEVANCE_KEY = "title_relevance"
_DESCRIPTION_LENGTH_KEY = "description_length"
_SKILLS_COUNT_RESUME_KEY = "skills_count_resume"
_SKILLS_COUNT_JOB_KEY = "skills_count_job"


def _load_model() -> Any:
    """
    Load XGBoost model and feature columns from disk, caching the result.

    Returns:
        Loaded XGBoost model.
    """
    global _MODEL, _FEATURE_COLUMNS

    if _MODEL is not None and _FEATURE_COLUMNS is not None:
        return _MODEL

    base_dir = Path(__file__).resolve().parents[2]  # backend/services -> backend -> repo root
    model_path = base_dir / "ml" / "model" / "xgb_matcher.pkl"
    feature_cols_path = base_dir / "ml" / "model" / "feature_columns.json"

    _MODEL = joblib.load(model_path)

    with open(feature_cols_path, "r", encoding="utf-8") as f:
        _FEATURE_COLUMNS = json.load(f)

    return _MODEL


def _education_score(resume_education: str, job_category: str) -> float:
    """
    Lightweight education scoring heuristic. The ML feature engineering pipeline
    likely had more nuance; here we keep a deterministic fallback.

    Args:
        resume_education: Education text from resume.
        job_category: Job category text.

    Returns:
        Education score between 0 and 1.
    """
    text = (resume_education or "").lower()
    score = 0.0
    if any(k in text for k in ["phd", "doctorate"]):
        score = 1.0
    elif any(k in text for k in ["master", "m.tech", "m.tech", "m.sc", "msc"]):
        score = 0.8
    elif any(k in text for k in ["bachelor", "b.tech", "b.sc", "bsc"]):
        score = 0.6
    elif text.strip():
        score = 0.4
    else:
        score = 0.2

    # Slight boost if category appears compatible (heuristic)
    if (job_category or "").lower() in text:
        score = min(1.0, score + 0.1)
    return float(score)


def compute_features(resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Compute match features using a deterministic feature set.

    Expected features:
      - skill_overlap_count
      - skill_overlap_ratio
      - experience_gap
      - education_score
      - location_match
      - category_match
      - title_relevance
      - description_length
      - skills_count_resume
      - skills_count_job

    Args:
        resume_data: Parsed resume fields.
        job_data: Parsed job fields.

    Returns:
        Feature dict ready to be aligned with training columns.
    """
    resume_skills = [s.lower() for s in (resume_data.get("skills") or [])]
    job_skills = [s.lower() for s in (job_data.get("required_skills") or [])]

    overlap = set(resume_skills).intersection(set(job_skills))
    overlap_count = float(len(overlap))
    overlap_ratio = float(len(overlap)) / float(len(job_skills) or 1)

    resume_exp = float(resume_data.get("experience_years") or 0.0)
    job_salary_min = job_data.get("salary_min")
    _ = job_salary_min  # not used; keep signature parity

    # Experience gap (lower is better); turn into a 0..1-ish score later
    job_exp_target = 0.0
    if "experience_years" in job_data:
        job_exp_target = float(job_data.get("experience_years") or 0.0)
    elif "experience_min_years" in job_data:
        job_exp_target = float(job_data.get("experience_min_years") or 0.0)

    experience_gap = float(abs(resume_exp - job_exp_target))

    education_score = _education_score(
        str(resume_data.get("education") or ""),
        str(job_data.get("category") or ""),
    )

    resume_location = str(resume_data.get("location") or "").lower()
    job_location = str(job_data.get("location") or "").lower()
    location_match = 1.0 if resume_location and job_location and (resume_location == job_location) else 0.0

    resume_category = str(resume_data.get("category") or "").lower()
    job_category = str(job_data.get("category") or "").lower()
    category_match = 1.0 if resume_category and job_category and (resume_category == job_category) else 0.0

    title = str(job_data.get("title") or "").lower()
    description = str(job_data.get("description") or "").lower()
    title_tokens = set(title.split())
    resume_tokens = set(str(resume_data.get("candidate_name") or "").lower().split())
    title_relevance = float(len(title_tokens.intersection(resume_tokens)) / float(len(title_tokens) or 1))

    description_length = float(len(description))
    skills_count_resume = float(len(resume_skills))
    skills_count_job = float(len(job_skills))

    # convert experience gap to score in [0,1] using diminishing penalty
    experience_gap_score = float(np.exp(-experience_gap / 5.0))

    features: Dict[str, float] = {
        _SKILL_OVERLAP_COUNT_KEY: overlap_count,
        _SKILL_OVERLAP_RATIO_KEY: overlap_ratio,
        _EXPERIENCE_GAP_KEY: experience_gap_score,
        _EDUCATION_SCORE_KEY: float(education_score),
        _LOCATION_MATCH_KEY: float(location_match),
        _CATEGORY_MATCH_KEY: float(category_match),
        _TITLE_RELEVANCE_KEY: float(title_relevance),
        _DESCRIPTION_LENGTH_KEY: float(description_length),
        _SKILLS_COUNT_RESUME_KEY: float(skills_count_resume),
        _SKILLS_COUNT_JOB_KEY: float(skills_count_job),
    }
    return features


def score_match(resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> float:
    """
    Score how well a resume matches a job.

    Uses:
      - XGBoost model on computed features
    Fallback:
      - cosine similarity between simple TF-IDF-like vectors built from skills

    Args:
        resume_data: Resume dict.
        job_data: Job dict.

    Returns:
        Probability score in [0.0, 1.0]
    """
    try:
        model = _load_model()
        feature_dict = compute_features(resume_data, job_data)
        assert _FEATURE_COLUMNS is not None

        row = [feature_dict.get(col, 0.0) for col in _FEATURE_COLUMNS]
        x = np.array([row], dtype=float)

        # XGBoost predict_proba if available, else predict then squash
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(x)[0]
            if isinstance(proba, (list, tuple, np.ndarray)) and len(proba) >= 2:
                score = float(proba[1])
            else:
                score = float(proba[0])
        else:
            pred = float(model.predict(x)[0])
            score = float(1.0 / (1.0 + np.exp(-pred)))

        return float(max(0.0, min(1.0, score)))
    except Exception:
        # Fallback cosine similarity over skill overlap
        resume_skills = set([s.lower() for s in (resume_data.get("skills") or [])])
        job_skills = set([s.lower() for s in (job_data.get("required_skills") or [])])
        if not resume_skills and not job_skills:
            return 0.0
        if not resume_skills or not job_skills:
            return 0.0
        intersection = len(resume_skills.intersection(job_skills))
        union = len(resume_skills.union(job_skills))
        if union == 0:
            return 0.0
        return float(intersection / union)


def rank_matches(resume_data: Dict[str, Any], jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank jobs for a given resume.

    Args:
        resume_data: Resume dict.
        jobs: List of jobs.

    Returns:
        Top 10 match items with descending score.
    """
    scored: List[Dict[str, Any]] = []
    for job in jobs:
        score = score_match(resume_data, job)
        scored.append(
            {
                **job,
                "match_score": score,
            }
        )
    scored.sort(key=lambda x: float(x.get("match_score") or 0.0), reverse=True)
    return scored[:10]
