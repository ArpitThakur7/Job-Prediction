from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.services.matcher import match_resume_to_jobs, match_job_to_resumes

logger = logging.getLogger("backend.routes.match")

router = APIRouter()


class ResumeMatchRequest(BaseModel):
    resume_id: str
    top_k: int = 10
    pinecone_api_key: Optional[str] = None


@router.post("/match/resume-to-jobs", response_model=Dict[str, Any])
async def post_match_resume_to_jobs(payload: ResumeMatchRequest) -> Dict[str, Any]:
    """
    POST /match/resume-to-jobs  — JSON body alias for resume-to-job matching.
    Accepts: {resume_id: str, top_k: int}
    """
    try:
        if not payload.resume_id:
            raise HTTPException(status_code=400, detail="resume_id is required")

        matches = match_resume_to_jobs(
            resume_id=payload.resume_id,
            top_k=payload.top_k,
            api_key=payload.pinecone_api_key,
        )

        # Stream match event to Apache Kafka
        if matches:
            try:
                from backend.services.kafka_producer import publish_match_event
                top_m = matches[0]
                publish_match_event(
                    candidate_id=payload.resume_id,
                    job_id=top_m.get("job_id", ""),
                    score=top_m.get("raw_score", 0.0),
                    metadata={"title": top_m.get("title", ""), "engine": top_m.get("engine", "xgboost")},
                )
            except Exception as k_err:
                logger.debug("Kafka match event publish skipped: %s", k_err)

        return {
            "success": True,
            "data": {
                "resume_id": payload.resume_id,
                "matches": matches,
                "total_matches": len(matches),
            },
            "message": f"Successfully retrieved top {len(matches)} job matches",
        }
    except Exception as exc:
        logger.exception("post_match_resume_to_jobs failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to calculate job matches") from exc


class SparkBatchRequest(BaseModel):
    sample_size: int = 50


@router.post("/match/spark-batch", response_model=Dict[str, Any])
async def post_spark_batch_matching(payload: Optional[SparkBatchRequest] = None) -> Dict[str, Any]:
    """
    Trigger distributed Apache Spark / PySpark batch candidate matching across
    jobs and candidate profiles in the database or sample data.
    """
    try:
        from backend.database import get_database
        from backend.services.spark_processor import trigger_spark_batch_matching
        from backend.services.matcher import _load_fallback_jobs_from_csv, _load_fallback_resumes_from_csv

        db = get_database()
        limit = payload.sample_size if payload else 50

        jobs = []
        resumes = []
        if db is not None:
            try:
                jobs = list(db["jobs"].find({"is_active": {"$ne": False}}).limit(limit))
                resumes = list(db["resumes"].find().limit(limit))
            except Exception:
                pass

        if not jobs:
            jobs = _load_fallback_jobs_from_csv()[:limit]
        if not resumes:
            resumes = _load_fallback_resumes_from_csv()[:limit]

        result = trigger_spark_batch_matching(jobs=jobs, resumes=resumes)
        return {
            "success": True,
            "data": result,
            "message": f"Successfully computed distributed batch scoring for {result.get('total_pairs_computed', 0)} pairs via {result.get('spark_master')}",
        }
    except Exception as exc:
        logger.exception("Spark batch matching failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to execute Spark batch compute") from exc


@router.get("/match/resume/{resume_id}", response_model=Dict[str, Any])
async def get_jobs_for_resume(
    resume_id: str,
    top_k: int = Query(10, ge=1, le=50),
    x_pinecone_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Match candidate resume against jobs database.
    GET /api/match/resume/:id
    """
    try:
        if not resume_id:
            raise HTTPException(status_code=400, detail="resume_id is required")

        matches = match_resume_to_jobs(resume_id=resume_id, top_k=top_k, api_key=x_pinecone_api_key)
        return {
            "success": True,
            "data": {
                "resume_id": resume_id,
                "matches": matches,
                "total_matches": len(matches),
            },
            "message": f"Successfully retrieved top {len(matches)} job matches for resume {resume_id}",
        }
    except Exception as exc:
        logger.exception("match_resume failed for id %s: %s", resume_id, exc)
        raise HTTPException(status_code=500, detail="Failed to calculate job matches") from exc


@router.get("/match/job/{job_id}", response_model=Dict[str, Any])
async def get_resumes_for_job(
    job_id: str,
    top_k: int = Query(10, ge=1, le=50),
    x_pinecone_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Match job posting against candidate resumes database (Candidate Sourcing view).
    GET /api/match/job/:id
    """
    try:
        if not job_id:
            raise HTTPException(status_code=400, detail="job_id is required")

        matches = match_job_to_resumes(job_id=job_id, top_k=top_k, api_key=x_pinecone_api_key)
        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "candidates": matches,
                "total_candidates": len(matches),
            },
            "message": f"Successfully retrieved top {len(matches)} candidate matches for job {job_id}",
        }
    except Exception as exc:
        logger.exception("match_job failed for id %s: %s", job_id, exc)
        raise HTTPException(status_code=500, detail="Failed to calculate candidate matches") from exc

