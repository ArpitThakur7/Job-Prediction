from __future__ import annotations

import pytest
from backend.services.matcher import (
    _load_salvo_live_jobs,
    _predict_pair_score,
    match_resume_to_jobs,
)


def test_load_salvo_live_jobs():
    """Verify that only live Salvo pipeline positions are loaded, and no Kaggle CSV jobs."""
    jobs = _load_salvo_live_jobs()
    assert len(jobs) > 0, "Expected live Salvo jobs to be loaded"

    # Verify no fast food or Del Taco jobs exist
    companies = [j.get("company", "").lower() for j in jobs]
    assert not any("del taco" in c for c in companies), "Del Taco should never appear in Salvo live jobs"

    # Verify live companies are present
    assert any("enveritas" in c or "weekday" in c or "xentovia" in c or "vortizo" in c for c in companies)


def test_domain_gating_unrelated_job():
    """Verify that jobs with zero skill overlap and no title relevance are gated strictly below 12%."""
    features = {
        "skill_overlap_count": 0,
        "skill_overlap_ratio": 0.0,
        "experience_gap": 0.0,
        "education_score": 3,
        "location_match": 1,
        "title_relevance": 0,
        "semantic_similarity": 0.5,
        "is_entry_level_job": 1,
        "project_keyword_count": 5,
        "internship_mentions": 2,
        "certification_count": 1,
        "education_field_match": 0,
        "experience_adequacy": 1.0,
        "skill_recency_score": 0.8,
        "resume_experience_years": 1.0,
        "job_experience_required": 1.0,
        "job_title": "Shift Manager Fast Food",
    }

    pred = _predict_pair_score(features, r_exp=1.0, j_exp=1.0, job_title="Shift Manager Fast Food")
    assert pred["match_probability"] <= 0.12, f"Expected out-of-domain match to be <= 0.12, got {pred['match_probability']}"
    assert pred["verdict"] == "NO MATCH"


def test_internship_and_fresher_calibration():
    """Verify candidate with 1.0y internship experience is realistically calibrated to ~75-85% for internships, and <= 48% for senior roles."""
    intern_features = {
        "skill_overlap_count": 3,
        "skill_overlap_ratio": 0.6,
        "experience_gap": 1.0,
        "education_score": 3,
        "location_match": 1,
        "title_relevance": 1,
        "semantic_similarity": 0.72,
        "is_entry_level_job": 1,
        "project_keyword_count": 4,
        "internship_mentions": 3,
        "certification_count": 1,
        "education_field_match": 1,
        "experience_adequacy": 1.0,
        "skill_recency_score": 0.9,
        "resume_experience_years": 1.0,
        "job_experience_required": 0.0,
        "job_title": "Software Engineer Internship",
    }

    intern_pred = _predict_pair_score(intern_features, r_exp=1.0, j_exp=0.0, job_title="Software Engineer Internship")
    assert 0.74 <= intern_pred["match_probability"] <= 0.85, f"Expected internship match between 0.74 and 0.85, got {intern_pred['match_probability']}"
    assert intern_pred["verdict"] == "MATCH"

    # Now test senior role with same candidate skills but 5+ year experience requirement
    senior_features = dict(intern_features)
    senior_features["experience_gap"] = -4.0
    senior_features["is_entry_level_job"] = 0
    senior_features["job_experience_required"] = 6.0
    senior_features["job_title"] = "Senior Lead Cloud Architect"

    senior_pred = _predict_pair_score(senior_features, r_exp=1.0, j_exp=6.0, job_title="Senior Lead Cloud Architect")
    assert senior_pred["match_probability"] <= 0.48, f"Expected senior role for intern to be <= 0.48, got {senior_pred['match_probability']}"
    assert senior_pred["verdict"] == "NO MATCH"


def test_match_resume_to_jobs_returns_salvo_jobs():
    """Verify match_resume_to_jobs returns live pipeline jobs."""
    results = match_resume_to_jobs(resume_id="test_intern_candidate", top_k=5)
    assert len(results) > 0
    for r in results:
        assert "Del Taco" not in r["company"]
        assert r["raw_score"] <= 0.86, f"Intern score should be calibrated <= 0.86, got {r['raw_score']}"
