from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.database import get_collection
from backend.models.job import JobCreate, JobResponse
from backend.services.embedder import generate_embedding as _generate_embedding
from backend.services.vector_store import upsert_vector

logger = logging.getLogger("backend.routes.jobs")

router = APIRouter()


def _job_response_from_doc(doc: Dict[str, Any]) -> JobResponse:
    """
    Convert MongoDB job document to JobResponse safely.
    """
    return JobResponse(
        job_id=str(doc.get("job_id")),
        title=str(doc.get("title") or "Position"),
        description=str(doc.get("description") or ""),
        company=str(doc.get("company") or "Company"),
        location=str(doc.get("location") or "Remote"),
        required_skills=doc.get("required_skills") or [],
        salary_min=int(doc.get("salary_min") or 80000),
        salary_max=int(doc.get("salary_max") or 150000),
        job_type=str(doc.get("job_type") or "FULL_TIME"),
        category=str(doc.get("category") or "Engineering"),
        industry=str(doc.get("industry") or "Technology"),
        posted_by=str(doc.get("posted_by") or "admin"),
        created_at=doc.get("created_at") or datetime.utcnow(),
        is_active=bool(doc.get("is_active", True)),
    )


from backend.routes.auth import require_role


@router.post("/jobs/", response_model=JobResponse)
async def create_job(
    payload: JobCreate,
    current_user: Dict[str, Any] = Depends(require_role(["recruiter", "admin"])),
) -> JobResponse:
    """
    Create a job, store in MongoDB, generate embedding and upsert to Pinecone.
    Requires authenticated user with 'recruiter' or 'admin' role.
    """
    try:
        jobs_col = get_collection("jobs")
        job_id = str(uuid.uuid4())
        posted_by = current_user.get("email") or "recruiter"
        now = datetime.utcnow()

        job_doc: Dict[str, Any] = {
            "job_id": job_id,
            "posted_by": posted_by,
            "created_at": now,
            "is_active": True,
            **payload.model_dump(),
        }

        if jobs_col is not None:
            jobs_col.insert_one(job_doc)

        # Embedding text for retrieval
        embed_text = f"{payload.title}\n{payload.company}\n{payload.location}\n{payload.description}"
        vector = _generate_embedding(embed_text)

        metadata = {
            "type": "job",
            "job_id": job_id,
            "text": json.dumps(
                {
                    "title": payload.title,
                    "company": payload.company,
                    "location": payload.location,
                    "description": payload.description[:2000],
                    "required_skills": payload.required_skills,
                    "category": payload.category,
                }
            ),
        }
        upsert_vector(id=f"job:{job_id}", vector=vector, metadata=metadata)

        # Stream job event to Apache Kafka
        try:
            from backend.services.kafka_producer import publish_job_event
            publish_job_event(
                job_id=job_id,
                title=payload.title,
                company=payload.company,
                required_skills=payload.required_skills,
                location=payload.location,
            )
        except Exception as k_err:
            logger.debug("Kafka job event publish skipped: %s", k_err)

        return _job_response_from_doc(job_doc)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("create_job failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create job") from exc


@router.get("/jobs/", response_model=List[JobResponse])
async def list_jobs(
    location: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    salary_min: Optional[int] = Query(default=None),
    salary_max: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
) -> List[JobResponse]:
    """
    List jobs with optional filters and safe pagination (default limit 50, max 200).
    Cache results in Redis (TTL 300s).
    """
    from backend.redis_client import cache_get, cache_set

    cache_key = f"jobs:list:{location or ''}:{category or ''}:{salary_min or ''}:{salary_max or ''}:{limit}:{skip}"
    cached = cache_get(cache_key)
    if cached:
        try:
            decoded = json.loads(cached)
            return [JobResponse(**x) for x in decoded]
        except Exception:
            pass

    try:
        jobs_col = get_collection("jobs")
        query: Dict[str, Any] = {"is_active": {"$ne": False}}

        if location:
            query["location"] = location
        if category:
            query["category"] = category
        if salary_min is not None:
            query["salary_min"] = {"$gte": int(salary_min)}
        if salary_max is not None:
            query["salary_max"] = {"$lte": int(salary_max)}

        docs = list(jobs_col.find(query).skip(skip).limit(limit))
        results = [_job_response_from_doc(d) for d in docs]

        # mode="json" makes datetimes JSON-serializable (ISO strings).
        cache_set(cache_key, json.dumps([r.model_dump(mode="json") for r in results]), ttl=300)
        return results
    except Exception as exc:
        logger.exception("list_jobs failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list jobs") from exc


# NOTE: /jobs/search must be declared BEFORE /jobs/{job_id},
# otherwise "search" is captured as a job_id path parameter.
@router.get("/jobs/search", response_model=List[JobResponse])
async def search_jobs(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> List[JobResponse]:
    """
    Search jobs by title or description with a safe response cap.
    """
    try:
        jobs_col = get_collection("jobs")
        needle = q.strip()
        cursor = jobs_col.find(
            {
                "is_active": True,
                "$or": [
                    {"title": {"$regex": needle, "$options": "i"}},
                    {"description": {"$regex": needle, "$options": "i"}},
                ],
            }
        ).limit(limit)
        docs = list(cursor)
        return [_job_response_from_doc(d) for d in docs]
    except Exception as exc:
        logger.exception("search_jobs failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to search jobs") from exc


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """
    Get a single job by job_id.
    """
    try:
        jobs_col = get_collection("jobs")
        doc = jobs_col.find_one({"job_id": job_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Job not found")
        return _job_response_from_doc(doc)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_job failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch job") from exc


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str) -> JSONResponse:
    """
    Delete job from MongoDB and Pinecone vector store.
    """
    from backend.services.vector_store import delete_vector

    try:
        jobs_col = get_collection("jobs")
        doc = jobs_col.find_one({"job_id": job_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Job not found")

        jobs_col.delete_one({"job_id": job_id})
        delete_vector(f"job:{job_id}")

        return JSONResponse(
            content={"success": True, "data": {"job_id": job_id}, "message": "Job deleted successfully"}
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("delete_job failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to delete job") from exc
