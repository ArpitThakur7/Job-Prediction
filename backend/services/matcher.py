from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path when running standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.database import get_database
from backend.services.embedder import generate_embedding
from backend.services.rag_vector_store import query_rag_context

logger = logging.getLogger("backend.matcher")

# Lazy-loaded XGBoost model & feature columns cache
_xgb_model = None
_xgb_feature_cols: Optional[List[str]] = None
_xgb_threshold: float = 0.5
_xgb_loaded = False


def _get_xgb_scorer():
    """Lazy load the trained XGBoost model and configuration."""
    global _xgb_model, _xgb_feature_cols, _xgb_threshold, _xgb_loaded
    if not _xgb_loaded:
        _xgb_loaded = True
        try:
            from pathlib import Path
            from ml.predict import load_model, load_feature_cols, load_threshold, PredictConfig
            root = Path(__file__).resolve().parents[2]
            cfg = PredictConfig(
                model_path=root / "ml" / "model" / "xgb_matcher.pkl",
                feature_cols_path=root / "ml" / "model" / "feature_columns.json",
                threshold_path=root / "ml" / "model" / "optimal_threshold.json",
            )
            if cfg.model_path.exists() and cfg.feature_cols_path.exists():
                _xgb_model = load_model(cfg)
                _xgb_feature_cols = load_feature_cols(cfg)
                _xgb_threshold = load_threshold(cfg, use_optimal=True)
                logger.info("Successfully loaded real XGBoost matcher model (threshold=%.4f)", _xgb_threshold)
            else:
                logger.warning("XGBoost model files not found at %s. Using heuristic scoring fallback.", cfg.model_path)
        except Exception as e:
            logger.warning("Could not initialize XGBoost matcher: %s. Using heuristic fallback.", e)
    return _xgb_model, _xgb_feature_cols, _xgb_threshold


EDUCATION_SCORE_MAP = {
    "phd": 5, "doctorate": 5,
    "masters": 4, "master": 4, "mba": 4, "m.tech": 4, "m.s.": 4, "msc": 4,
    "bachelors": 3, "bachelor": 3, "b.tech": 3, "b.s.": 3, "b.e.": 3, "bsc": 3,
    "associate": 2, "diploma": 2,
    "high school": 1, "secondary": 1,
}


def _extract_pair_features(
    resume_data: Dict[str, Any],
    job_data: Dict[str, Any],
    semantic_sim: float = 0.5,
) -> Dict[str, Any]:
    """Extract all 9 feature columns expected by XGBoost classifier."""
    # 1. Skills extraction & overlap
    r_skills_raw = resume_data.get("skills") or []
    if isinstance(r_skills_raw, str):
        r_skills = [s.strip().lower() for s in r_skills_raw.split(",") if s.strip()]
    elif isinstance(r_skills_raw, list):
        r_skills = [str(s).strip().lower() for s in r_skills_raw if str(s).strip()]
    else:
        r_skills = []

    j_skills_raw = job_data.get("required_skills") or []
    if isinstance(j_skills_raw, str):
        j_skills = [s.strip().lower() for s in j_skills_raw.split(",") if s.strip()]
    elif isinstance(j_skills_raw, list):
        j_skills = [str(s).strip().lower() for s in j_skills_raw if str(s).strip()]
    else:
        j_skills = []

    r_set = set(r_skills)
    j_set = set(j_skills)
    overlap_count = len(r_set & j_set)
    overlap_ratio = overlap_count / max(len(j_set), 1)

    # 2. Experience gap
    r_exp = float(resume_data.get("experience_years") or 0.0)
    j_exp = float(job_data.get("experience_years") or job_data.get("min_experience") or 2.0)
    exp_gap = float(max(-10.0, min(10.0, r_exp - j_exp)))

    # 3. Education score
    r_edu = str(resume_data.get("education") or "").lower()
    edu_score = 3  # default bachelor
    for edu_key, score in EDUCATION_SCORE_MAP.items():
        if edu_key in r_edu:
            edu_score = score
            break

    # 4. Location match
    r_loc = str(resume_data.get("location") or "Remote").lower()
    j_loc = str(job_data.get("location") or "Remote").lower()
    r_parts = set(r_loc.replace(",", " ").split())
    j_parts = set(j_loc.replace(",", " ").split())
    location_match = 1 if ("remote" in j_loc or "remote" in r_loc or bool(r_parts & j_parts)) else 0

    # 5. Category match
    r_cat = str(resume_data.get("category") or "").strip().lower()
    j_cat = str(job_data.get("category") or "").strip().lower()
    category_match = 1 if (r_cat and j_cat and r_cat == j_cat) else 0

    # 6. Title relevance
    j_title_words = [w for w in str(job_data.get("title") or "").lower().split() if len(w) > 3]
    r_full_text = f"{resume_data.get('raw_text', '')} {resume_data.get('title', '')} {resume_data.get('summary', '')}".lower()
    title_relevance = 1 if any(w in r_full_text for w in j_title_words) else 0

    return {
        "skill_overlap_count": overlap_count,
        "skill_overlap_ratio": round(overlap_ratio, 4),
        "experience_gap": exp_gap,
        "education_score": edu_score,
        "location_match": location_match,
        "category_match": category_match,
        "title_relevance": title_relevance,
        "semantic_similarity": round(float(semantic_sim), 4),
        "skills_count_resume": len(r_set),
    }


def _predict_pair_score(features: Dict[str, Any]) -> Dict[str, Any]:
    """Score a pair using XGBoost if available, else calibrate a weighted feature score."""
    model, cols, threshold = _get_xgb_scorer()
    if model is not None and cols is not None:
        try:
            from ml.predict import score_pair
            res = score_pair(
                feature_values=features,
                model=model,
                feature_cols=cols,
                threshold=threshold,
            )
            return {
                "match_probability": res["match_probability"],
                "predicted_match": res["predicted_match"],
                "verdict": res["verdict"],
                "confidence": res["confidence"],
                "engine": "xgboost",
            }
        except Exception as e:
            logger.warning("XGBoost prediction failed on pair: %s. Using heuristic.", e)

    # Heuristic fallback if model unavailable
    prob = (
        features["skill_overlap_ratio"] * 0.35 +
        features["semantic_similarity"] * 0.30 +
        (max(0, features["experience_gap"] + 5) / 10.0) * 0.15 +
        (features["education_score"] / 5.0) * 0.10 +
        features["category_match"] * 0.05 +
        features["location_match"] * 0.05
    )
    prob = round(max(0.05, min(0.99, prob)), 4)
    pred = 1 if prob >= threshold else 0
    return {
        "match_probability": prob,
        "predicted_match": pred,
        "verdict": "MATCH" if pred == 1 else "NO MATCH",
        "confidence": "High" if abs(prob - threshold) > 0.2 else "Medium",
        "engine": "heuristic",
    }


def _load_fallback_jobs_from_csv() -> List[Dict[str, Any]]:
    import pandas as pd
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "jobs_clean.csv"))
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path).head(50)
            jobs = []
            for _, row in df.iterrows():
                req_skills = [s.strip() for s in str(row.get("required_skills", "")).split(",") if s.strip()]
                jobs.append({
                    "job_id": str(row.get("job_id", "")),
                    "title": str(row.get("title", "")),
                    "company": str(row.get("company", "")),
                    "location": str(row.get("location", "")),
                    "required_skills": req_skills,
                    "salary_min": int(row["salary_min"]) if not pd.isna(row.get("salary_min")) else None,
                    "salary_max": int(row["salary_max"]) if not pd.isna(row.get("salary_max")) else None,
                    "category": str(row.get("category", "")),
                })
            return jobs
        except Exception as e:
            logger.warning("Failed to load fallback jobs CSV: %s", e)
    return []


def _load_fallback_resumes_from_csv() -> List[Dict[str, Any]]:
    import pandas as pd
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "resumes_clean.csv"))
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path).head(20)
            resumes = []
            for _, row in df.iterrows():
                skills = [s.strip() for s in str(row.get("skills", "")).split(",") if s.strip()]
                resumes.append({
                    "resume_id": str(row.get("resume_id", "")),
                    "candidate_name": str(row.get("name", "Candidate")),
                    "email": str(row.get("email", "")),
                    "skills": skills,
                    "experience_years": float(row["experience_years"]) if not pd.isna(row.get("experience_years")) else 0.0,
                    "education": str(row.get("education", "Bachelors")),
                    "category": str(row.get("category", "General")),
                })
            return resumes
        except Exception as e:
            logger.warning("Failed to load fallback resumes CSV: %s", e)
    return []


def match_resume_to_jobs(resume_id: str, top_k: int = 10, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Given a resume ID, score all candidate jobs using the real XGBoost classifier
    and return top ranked matches with probabilities and feature attributions.
    """
    db = get_database()
    resume_doc = None

    if db is not None:
        try:
            resume_doc = db["resumes"].find_one({"resume_id": resume_id})
        except Exception as e:
            logger.warning("MongoDB find_one failed for resume_id %s: %s", resume_id, e)

    if not resume_doc:
        # Check CSV fallback for resume
        csv_resumes = _load_fallback_resumes_from_csv()
        for r in csv_resumes:
            if r.get("resume_id") == resume_id:
                resume_doc = r
                break

    if not resume_doc:
        resume_doc = {"resume_id": resume_id, "skills": [], "category": "Technology"}

    skills = resume_doc.get("skills") or []
    category = resume_doc.get("category") or "General"
    skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
    query_text = f"Category: {category} | Skills: {skills_str} | Education: {resume_doc.get('education', '')} | Summary: {resume_doc.get('raw_text', resume_doc.get('resume_text', ''))[:400]}"

    # Search RAG vector store / Pinecone 'jobs' for nearest candidates
    raw_matches = query_rag_context(query_text, top_k=top_k * 3, api_key=api_key)

    candidate_ids = []
    vector_sim_map: Dict[str, float] = {}
    for m in raw_matches:
        meta = m.get("metadata") or {}
        m_id = str(m.get("id") or "")
        if meta.get("type") == "job" or meta.get("namespace") == "jobs" or "title" in meta or m_id.startswith("job"):
            clean_id = m_id.replace("job_", "").replace("job:", "")
            candidate_ids.append(clean_id)
            vector_sim_map[clean_id] = float(m.get("score", 0.5))

    full_jobs_map: Dict[str, Dict[str, Any]] = {}
    if db is not None and candidate_ids:
        try:
            cursor = db["jobs"].find({"$or": [{"job_id": {"$in": candidate_ids}}, {"_id": {"$in": candidate_ids}}]})
            for doc in cursor:
                jid_str = str(doc.get("job_id") or doc.get("_id") or "")
                if jid_str:
                    full_jobs_map[jid_str] = doc
        except Exception as e:
            logger.warning("Batch jobs Mongo lookup warning: %s", e)

    # If vector search yielded fewer than top_k, supplement from MongoDB or CSV
    if len(full_jobs_map) < top_k:
        db_jobs = []
        if db is not None:
            try:
                db_jobs = list(db["jobs"].find({"is_active": {"$ne": False}}).limit(top_k * 2))
            except Exception:
                db_jobs = []
        if not db_jobs:
            db_jobs = _load_fallback_jobs_from_csv()
        for j in db_jobs:
            jid = str(j.get("job_id") or j.get("_id") or "")
            if jid and jid not in full_jobs_map:
                full_jobs_map[jid] = j

    scored_jobs = []
    for jid, job in full_jobs_map.items():
        sim = vector_sim_map.get(jid, 0.5)
        features = _extract_pair_features(resume_doc, job, semantic_sim=sim)
        pred = _predict_pair_score(features)

        prob = pred["match_probability"]
        scored_jobs.append({
            "job_id": jid,
            "match_score": f"{prob * 100:.1f}%",
            "raw_score": prob,
            "predicted_match": pred["predicted_match"],
            "verdict": pred["verdict"],
            "confidence": pred["confidence"],
            "engine": pred["engine"],
            "title": job.get("title", "Software Engineer"),
            "company": job.get("company", "Enterprise Tech"),
            "location": job.get("location", "Remote"),
            "required_skills": job.get("required_skills") or [],
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "features": features,
        })

    # Sort descending by real match probability
    scored_jobs.sort(key=lambda x: x["raw_score"], reverse=True)
    return scored_jobs[:top_k]


def match_job_to_resumes(job_id: str, top_k: int = 10, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Given a job ID, score all candidate resumes using the real XGBoost classifier
    (Recruiter Candidate Sourcing view).
    """
    db = get_database()
    job_doc = None

    if db is not None:
        try:
            job_doc = db["jobs"].find_one({"job_id": job_id})
        except Exception as e:
            logger.warning("MongoDB find_one failed for job_id %s: %s", job_id, e)

    if not job_doc:
        csv_jobs = _load_fallback_jobs_from_csv()
        for j in csv_jobs:
            if j.get("job_id") == job_id:
                job_doc = j
                break

    if not job_doc:
        job_doc = {"job_id": job_id, "title": "Software Engineer", "required_skills": []}

    job_skills = job_doc.get("required_skills") or []
    skills_str = ", ".join(job_skills) if isinstance(job_skills, list) else str(job_skills)
    query_text = f"Job Title: {job_doc.get('title', '')} | Required Skills: {skills_str} | Description: {job_doc.get('description', '')[:400]}"

    raw_matches = query_rag_context(query_text, top_k=top_k * 3, api_key=api_key)

    candidate_res_ids = []
    vector_sim_map: Dict[str, float] = {}
    for m in raw_matches:
        meta = m.get("metadata") or {}
        m_id = str(m.get("id") or "")
        if meta.get("type") == "resume" or meta.get("namespace") == "resumes" or "name" in meta or m_id.startswith("resume"):
            clean_id = m_id.replace("resume_", "").replace("resume:", "")
            candidate_res_ids.append(clean_id)
            vector_sim_map[clean_id] = float(m.get("score", 0.5))

    full_res_map: Dict[str, Dict[str, Any]] = {}
    if db is not None and candidate_res_ids:
        try:
            cursor = db["resumes"].find({"$or": [{"resume_id": {"$in": candidate_res_ids}}, {"_id": {"$in": candidate_res_ids}}]})
            for doc in cursor:
                rid_str = str(doc.get("resume_id") or doc.get("_id") or "")
                if rid_str:
                    full_res_map[rid_str] = doc
        except Exception as e:
            logger.warning("Batch resumes Mongo lookup warning: %s", e)

    if len(full_res_map) < top_k:
        db_resumes = []
        if db is not None:
            try:
                db_resumes = list(db["resumes"].find().limit(top_k * 2))
            except Exception:
                db_resumes = []
        if not db_resumes:
            db_resumes = _load_fallback_resumes_from_csv()
        for r in db_resumes:
            rid = str(r.get("resume_id") or r.get("_id") or "")
            if rid and rid not in full_res_map:
                full_res_map[rid] = r

    scored_candidates = []
    for rid, rdoc in full_res_map.items():
        sim = vector_sim_map.get(rid, 0.5)
        features = _extract_pair_features(rdoc, job_doc, semantic_sim=sim)
        pred = _predict_pair_score(features)

        prob = pred["match_probability"]
        scored_candidates.append({
            "candidate_id": rid,
            "resume_id": rid,
            "candidate_name": rdoc.get("candidate_name") or rdoc.get("name") or "Candidate",
            "email": rdoc.get("email") or "candidate@example.com",
            "match_score": f"{prob * 100:.1f}%",
            "raw_score": prob,
            "predicted_match": pred["predicted_match"],
            "verdict": pred["verdict"],
            "confidence": pred["confidence"],
            "engine": pred["engine"],
            "skills": rdoc.get("skills") or [],
            "experience_years": rdoc.get("experience_years", 0),
            "education": rdoc.get("education", "Bachelors"),
            "category": rdoc.get("category", "General"),
            "features": features,
        })

    scored_candidates.sort(key=lambda x: x["raw_score"], reverse=True)
    return scored_candidates[:top_k]
