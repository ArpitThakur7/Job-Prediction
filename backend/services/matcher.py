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
from ml.skills import canonical_skill_set

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


def _resume_text(resume_data: Dict[str, Any]) -> str:
    """Full resume text if stored, else a best-effort composition of its fields."""
    raw = resume_data.get("raw_text")
    if isinstance(raw, str) and raw.strip():
        return raw
    skills = resume_data.get("skills") or []
    if isinstance(skills, list):
        skills = ", ".join(str(s) for s in skills)
    parts = [resume_data.get("title"), resume_data.get("summary"), resume_data.get("education"), skills]
    return " ".join(str(p) for p in parts if p)


def _active_semantic_backend() -> str:
    """'minilm' or 'tfidf' — how the ACTIVE model's semantic_similarity was trained."""
    try:
        from ml.registry import load_active_meta
        return str(load_active_meta().get("semantic_backend", "tfidf"))
    except Exception:
        return "tfidf"


def compute_semantic_pair(
    resume_text: str,
    job_text: str,
) -> Dict[str, Optional[float]]:
    """
    semantic_similarity + tfidf_similarity for one pair, computed exactly as in
    scripts/prepare_dataset.py (ml/semantic.py). Values are None when not computable.
    """
    from ml.semantic import minilm_similarity, tfidf_similarity
    from pathlib import Path
    tfidf_path = Path(__file__).resolve().parents[2] / "ml" / "model" / "tfidf_vectorizer.pkl"
    tf = tfidf_similarity(resume_text, job_text, path=tfidf_path)
    if _active_semantic_backend() == "minilm":
        sem = minilm_similarity(resume_text, job_text)
        if sem is None:
            sem = tf
    else:
        sem = tf
    return {"semantic_similarity": sem, "tfidf_similarity": tf}


def _extract_pair_features(
    resume_data: Dict[str, Any],
    job_data: Dict[str, Any],
    semantic_sim: Optional[float] = None,
    tfidf_sim: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Extract the XGBoost feature columns for a pair via the SAME function used to
    build the training data (ml.feature_engineering.compute_pair_features), with
    the shared token-boundary skill extractor (ml/skills.py).

    ``semantic_sim`` / ``tfidf_sim``: pass pre-computed values (e.g. batched); when
    None they are computed from the resume / job text, falling back to 0.5 when no
    text is available (legacy behaviour).
    """
    from ml.feature_engineering import compute_pair_features

    resume_text = _resume_text(resume_data)
    job_text = str(job_data.get("description") or "")

    if semantic_sim is None or tfidf_sim is None:
        sims: Dict[str, Optional[float]] = {"semantic_similarity": None, "tfidf_similarity": None}
        if resume_text.strip() and job_text.strip():
            try:
                sims = compute_semantic_pair(resume_text, job_text)
            except Exception as e:
                logger.debug("semantic pair computation failed: %s", e)
        if semantic_sim is None:
            semantic_sim = sims["semantic_similarity"]
        if tfidf_sim is None:
            tfidf_sim = sims["tfidf_similarity"]
    if semantic_sim is None:
        semantic_sim = 0.5
    if tfidf_sim is None:
        tfidf_sim = semantic_sim

    resume = {
        "skills": resume_data.get("skills") or [],
        "raw_text": resume_text,
        "experience_years": resume_data.get("experience_years") or 0.0,
        "education": resume_data.get("education") or "",
        "location": resume_data.get("location") or "",
    }
    j_exp = job_data.get("experience_years")
    if j_exp is None:
        j_exp = job_data.get("min_experience")
    job = {
        "required_skills": job_data.get("required_skills") or [],
        "description": job_text,
        "title": job_data.get("title") or "",
        "location": job_data.get("location") or "Remote",
        "category": job_data.get("category") or "INFORMATION-TECHNOLOGY",
        "experience_years": 2.0 if j_exp is None else j_exp,
    }
    feats = compute_pair_features(resume, job, semantic_similarity=semantic_sim, tfidf_similarity=tfidf_sim)
    feats["job_title"] = str(job_data.get("title") or "")
    return feats


def _predict_pair_score(
    features: Dict[str, Any],
    r_exp: Optional[float] = None,
    j_exp: Optional[float] = None,
    job_title: str = "",
) -> Dict[str, Any]:
    """
    Score a pair using XGBoost if available, with strict domain gating
    and realistic fresher/internship calibration.
    """
    model, cols, threshold = _get_xgb_scorer()
    raw_prob = 0.5
    engine = "heuristic"

    if model is not None and cols is not None:
        try:
            from ml.predict import score_pair
            res = score_pair(
                feature_values=features,
                model=model,
                feature_cols=cols,
                threshold=threshold,
            )
            raw_prob = float(res["match_probability"])
            engine = "xgboost"
        except Exception as e:
            logger.warning("XGBoost prediction failed on pair: %s. Using heuristic.", e)

    if engine == "heuristic":
        is_entry = features.get("is_entry_level_job", 0)
        if is_entry:
            fresher_boost = (
                (features.get("project_keyword_count", 0) / 10.0) * 0.08 +
                (features.get("internship_mentions", 0) / 5.0) * 0.06 +
                (features.get("certification_count", 0) / 5.0) * 0.04 +
                features.get("skill_recency_score", 0.0) * 0.02
            )
        else:
            fresher_boost = (
                features.get("skill_recency_score", 0.0) * 0.03 +
                (features.get("certification_count", 0) / 5.0) * 0.02
            )

        raw_prob = (
            features.get("skill_overlap_ratio", 0.0) * 0.35 +
            features.get("semantic_similarity", 0.0) * 0.25 +
            features.get("experience_adequacy", 0.0) * 0.15 +
            fresher_boost +
            (features.get("education_score", 3.0) / 5.0) * 0.05 +
            features.get("education_field_match", 0) * 0.05 +
            features.get("location_match", 0) * 0.05
        )

    # -----------------------------------------------------------------
    # 1. HARD DOMAIN GATING
    # If 0 skill overlap and 0 title relevance, the job is out-of-domain
    # (e.g., Del Taco Shift Manager, cashier, sales, fast food).
    # Cap strictly at < 0.12 (12%) NO MATCH.
    # -----------------------------------------------------------------
    overlap_count = int(features.get("skill_overlap_count", 0))
    title_rel = int(features.get("title_relevance", 0))
    overlap_ratio = float(features.get("skill_overlap_ratio", 0.0))

    resume_exp = r_exp if r_exp is not None else float(features.get("resume_experience_years", 0.0))
    job_req_exp = j_exp if j_exp is not None else float(features.get("job_experience_required", 2.0))
    title_str = (job_title or str(features.get("job_title", ""))).lower()

    if overlap_count == 0 and title_rel == 0:
        calibrated_prob = min(raw_prob, 0.1150)
    else:
        calibrated_prob = raw_prob

        # -------------------------------------------------------------
        # 2. FRESHER / INTERNSHIP CALIBRATION
        # When candidate has <= 1.5 years experience (internship/fresher stage)
        # Real-world scoring:
        # - Internships / Early Career Tech: 74% - 85% (Solid, realistic target)
        # - Junior Dev (1-2 yrs): 60% - 72%
        # - Senior / Lead / Architect (5+ yrs): 30% - 48% (Clear experience deficit)
        # -------------------------------------------------------------
        if resume_exp <= 1.5 or features.get("internship_mentions", 0) > 0:
            is_intern_job = (
                "intern" in title_str or
                "internship" in title_str or
                "trainee" in title_str or
                "fresher" in title_str or
                features.get("is_entry_level_job", 0) == 1 or
                job_req_exp <= 1.0
            )
            is_senior_job = (
                "senior" in title_str or
                "sr." in title_str or
                "lead" in title_str or
                "architect" in title_str or
                "principal" in title_str or
                "director" in title_str or
                job_req_exp >= 5.0
            )

            if is_intern_job:
                if overlap_count >= 2 or overlap_ratio >= 0.25:
                    calibrated_prob = round(0.75 + min(0.10, overlap_ratio * 0.12 + (overlap_count * 0.015)), 4)
                elif overlap_count == 1:
                    calibrated_prob = round(0.64 + min(0.08, overlap_ratio * 0.08), 4)
                else:
                    calibrated_prob = round(0.42 + min(0.12, features.get("semantic_similarity", 0.5) * 0.15), 4)
            elif is_senior_job:
                # 4+ year experience deficit for candidate with only internship experience
                base_senior = 0.32 + min(0.14, overlap_ratio * 0.14)
                calibrated_prob = round(min(0.46, base_senior), 4)
            else:
                # Mid-level developer role (2-4 years required)
                if overlap_count >= 2:
                    calibrated_prob = round(0.58 + min(0.12, overlap_ratio * 0.12), 4)
                else:
                    calibrated_prob = round(0.46 + min(0.10, overlap_ratio * 0.08), 4)

            # Cap maximum match score for an early-career fresher profile at 85%
            calibrated_prob = min(calibrated_prob, 0.8500)

    calibrated_prob = round(max(0.05, min(0.95, calibrated_prob)), 4)
    pred = 1 if calibrated_prob >= 0.60 else 0

    return {
        "match_probability": calibrated_prob,
        "predicted_match": pred,
        "verdict": "MATCH" if calibrated_prob >= 0.65 else ("POTENTIAL" if calibrated_prob >= 0.50 else "NO MATCH"),
        "confidence": "High" if calibrated_prob >= 0.72 or calibrated_prob < 0.35 else "Medium",
        "engine": engine,
    }


def _load_salvo_live_jobs() -> List[Dict[str, Any]]:
    """
    Load live scraped jobs strictly from Salvo pipeline files (pipeline.json & pipeline-india.json).
    Never loads offline training datasets or CSV files.
    """
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    all_jobs: List[Dict[str, Any]] = []
    seen_urls = set()

    for fname in ["pipeline.json", "pipeline-india.json"]:
        fpath = root / "data" / fname
        if not fpath.exists():
            continue
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
                for j in data.get("jobs", []):
                    url = str(j.get("url") or "")
                    if url and url in seen_urls:
                        continue
                    if url:
                        seen_urls.add(url)

                    title = str(j.get("title") or "Software Engineer")
                    desc = str(j.get("description") or "")
                    reasons = j.get("reasons") or []

                    # Extract technical skills from reasons or description
                    skills = [r.replace("+", "").replace("stack:", "").strip() for r in reasons if r.startswith("+") or r.startswith("stack:")]
                    if not skills and desc:
                        from backend.services.nlp_extractor import extract_skills_from_text
                        skills = extract_skills_from_text(desc)
                    if not skills:
                        skills = ["Python", "FastAPI", "React", "Docker", "SQL"]

                    from ml.feature_engineering import estimate_min_experience_from_title
                    min_exp = estimate_min_experience_from_title(title)

                    all_jobs.append({
                        "job_id": url or f"salvo_{len(all_jobs)}",
                        "title": title,
                        "company": str(j.get("company") or "Technology Enterprise"),
                        "location": str(j.get("location") or "Remote"),
                        "description": desc,
                        "required_skills": skills,
                        "min_experience": min_exp,
                        "experience_years": min_exp,
                        "salary_min": 85000 if min_exp >= 2.0 else 35000,
                        "salary_max": 165000 if min_exp >= 2.0 else 65000,
                        "category": "Engineering",
                        "url": url,
                        "source": str(j.get("source") or "Salvo Live Pipeline"),
                    })
        except Exception as e:
            logger.warning("Failed loading salvo pipeline %s: %s", fname, e)

    return all_jobs


def _load_fallback_jobs_from_csv() -> List[Dict[str, Any]]:
    """Legacy alias: redirected to live Salvo pipeline to avoid CSV pollution."""
    return _load_salvo_live_jobs()


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
    Given a resume ID, score all live Salvo scraped jobs using XGBoost + ATS matching,
    calibrating for candidate experience stage and returning genuine live opportunities.
    """
    db = get_database()
    resume_doc = None

    if db is not None:
        try:
            resume_doc = db["resumes"].find_one({"resume_id": resume_id})
        except Exception as e:
            logger.warning("MongoDB find_one failed for resume_id %s: %s", resume_id, e)

    if not resume_doc:
        csv_resumes = _load_fallback_resumes_from_csv()
        for r in csv_resumes:
            if r.get("resume_id") == resume_id:
                resume_doc = r
                break

    if not resume_doc:
        resume_doc = {
            "resume_id": resume_id,
            "skills": ["Python", "FastAPI", "React", "SQL", "Git"],
            "experience_years": 1.0,
            "category": "Technology",
            "education": "B.Tech",
        }

    # STRICTLY load live scraped Salvo jobs (pipeline.json & pipeline-india.json)
    salvo_jobs = _load_salvo_live_jobs()
    if not salvo_jobs:
        return []

    r_skills = resume_doc.get("skills") or []
    r_exp = float(resume_doc.get("experience_years") or 0.0)

    # Batched semantic similarity (same computation as training) when the resume has text.
    resume_text = _resume_text(resume_doc)
    sem_list: List[Optional[float]] = [None] * len(salvo_jobs)
    tfidf_list: List[Optional[float]] = [None] * len(salvo_jobs)
    if isinstance(resume_doc.get("raw_text"), str) and resume_doc["raw_text"].strip():
        try:
            from ml.semantic import minilm_similarity_many, tfidf_similarity
            from pathlib import Path
            tfidf_path = Path(__file__).resolve().parents[2] / "ml" / "model" / "tfidf_vectorizer.pkl"
            descs = [str(j.get("description") or "") for j in salvo_jobs]
            tfidf_list = [tfidf_similarity(resume_text, d, path=tfidf_path) if d else None for d in descs]
            if _active_semantic_backend() == "minilm":
                sem_list = minilm_similarity_many(resume_text, descs)
            sem_list = [s if s is not None else t for s, t in zip(sem_list, tfidf_list)]
        except Exception as e:
            logger.debug("Batched semantic similarity failed: %s", e)

    r_skill_set = canonical_skill_set(r_skills)

    scored_jobs = []
    for i, job in enumerate(salvo_jobs):
        jid = str(job.get("job_id") or "")
        j_skills = job.get("required_skills") or []
        j_exp = float(job.get("min_experience") or 2.0)
        j_title = str(job.get("title") or "")

        sim = sem_list[i]
        if sim is None:
            # No resume text: legacy heuristic proxy based on (canonical) skill overlap
            overlap_cnt = len(r_skill_set & canonical_skill_set(j_skills))
            sim = 0.68 if overlap_cnt >= 2 else (0.55 if overlap_cnt == 1 else 0.42)

        features = _extract_pair_features(resume_doc, job, semantic_sim=sim, tfidf_sim=tfidf_list[i] if tfidf_list[i] is not None else sim)
        features["resume_experience_years"] = r_exp
        features["job_experience_required"] = j_exp
        features["job_title"] = j_title

        pred = _predict_pair_score(features, r_exp=r_exp, j_exp=j_exp, job_title=j_title)
        prob = pred["match_probability"]

        scored_jobs.append({
            "job_id": jid,
            "match_score": f"{prob * 100:.1f}%",
            "raw_score": prob,
            "predicted_match": pred["predicted_match"],
            "verdict": pred["verdict"],
            "confidence": pred["confidence"],
            "engine": pred["engine"],
            "title": j_title,
            "company": job.get("company", "Tech Company"),
            "location": job.get("location", "Remote"),
            "required_skills": j_skills,
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "url": job.get("url"),
            "features": features,
        })

    # Sort descending by calibrated match score
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
        has_text = isinstance(rdoc.get("raw_text"), str) and rdoc["raw_text"].strip() and job_doc.get("description")
        # With texts available compute the trained semantic features; otherwise use the vector-store score.
        sim = None if has_text else vector_sim_map.get(rid, 0.5)
        features = _extract_pair_features(rdoc, job_doc, semantic_sim=sim, tfidf_sim=sim)
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


# ---------------------------------------------------------------------------
# Live scoring for the Salvo feed: one posting vs the user's master resume
# ---------------------------------------------------------------------------

_master_resume_cache: Dict[str, Any] = {"mtime": None, "data": None}


def _master_resume() -> Optional[Dict[str, Any]]:
    """Parse data/resume/resume.md (the same file tailoring uses). Re-read when it changes."""
    from pathlib import Path
    from ml.skills import extract_skills
    from ml.feature_engineering import extract_education, extract_experience_years

    path = Path(__file__).resolve().parents[2] / "data" / "resume" / "resume.md"
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if _master_resume_cache["mtime"] != mtime:
        text = path.read_text(encoding="utf-8")
        _master_resume_cache["data"] = {
            "raw_text": text,
            "skills": extract_skills(text),
            "experience_years": float(extract_experience_years(text) or 0),
            "education": extract_education(text),
            "location": "",
        }
        _master_resume_cache["mtime"] = mtime
    return _master_resume_cache["data"]


def score_job_for_master_resume(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score one job posting against the master resume with the real features.

    Returns both numbers so callers can choose honestly:
      model_probability — the trained model's raw output (None if no model is loaded)
      match_probability — after the hand-written domain gate and early-career bands
    """
    resume = _master_resume()
    if resume is None:
        raise FileNotFoundError("data/resume/resume.md not found — add your master resume first")

    features = _extract_pair_features(resume, job)
    model, cols, threshold = _get_xgb_scorer()
    model_prob: Optional[float] = None
    if model is not None and cols is not None:
        from ml.predict import score_pair
        model_prob = round(float(score_pair(feature_values=features, model=model, feature_cols=cols, threshold=threshold)["match_probability"]), 4)

    calibrated = _predict_pair_score(features, r_exp=resume["experience_years"], job_title=str(job.get("title") or ""))
    return {
        "model_probability": model_prob,
        "match_probability": calibrated["match_probability"],
        "engine": calibrated["engine"],
        "features": {k: v for k, v in features.items() if isinstance(v, (int, float))},
    }
