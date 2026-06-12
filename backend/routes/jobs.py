from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.database import get_collection
from backend.embedder import generate_embedding  # type: ignore[attr-defined]
from backend.models.job import JobBase, JobCreate, JobFilter, JobResponse
from backend.services.embedder import generate_embedding as _generate_embedding
from backend.services.vector_store import upsert_vector

logger = logging.getLogger("backend.routes.jobs")

router = APIRouter()


def _job_response_from_doc(doc: Dict[str, Any]) -> JobResponse:
    """
    Convert MongoDB job document to JobResponse.
    """
    return JobResponse(
        job_id=str(doc.get("job_id")),
        title=doc.get("title"),
        description=doc.get("description"),
        company=doc.get("company"),
        location=doc.get("location"),
        required_skills=doc.get("required_skills") or [],
        salary_min=int(doc.get("salary_min") or 0),
        salary_max=int(doc.get("salary_max") or 0),
        job_type=doc.get("job_type"),
        category=doc.get("category"),
        industry=doc.get("industry"),
        posted_by=str(doc.get("posted_by") or ""),
        created_at=doc.get("created_at") or datetime.utcnow(),
        is_active=bool(doc.get("is_active", True)),
    )


@router.post("/jobs/", response_model=JobResponse)
async def create_job(payload: JobCreate) -> JobResponse:
    """
    Create a job, store in MongoDB, generate embedding and upsert to Pinecone.
    """
    try:
        jobs_col = get_collection("jobs")
        job_id = str(uuid.uuid4())
        posted_by = "unknown"  # In future, extract from JWT. For now, keep deterministic.
        now = datetime.utcnow()

        job_doc: Dict[str, Any] = {
            "job_id": job_id,
            "posted_by": posted_by,
            "created_at": now,
            "is_active": True,
            **payload.model_dump(),
        }

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
) -> List[JobResponse]:
    """
    List all jobs with optional filters.
    Cache results in Redis (TTL 300s).
    """
    from backend.redis_client import cache_get, cache_set

    cache_key = f"jobs:list:{location or ''}:{category or ''}:{salary_min or ''}:{salary_max or ''}"
    cached = cache_get(cache_key)
    if cached:
        try:
            decoded = json.loads(cached)
            return [JobResponse(**x) for x in decoded]
        except Exception:
            pass

    try:
        jobs_col = get_collection("jobs")
        query: Dict[str, Any] = {"is_active": True}

        if location:
            query["location"] = location
        if category:
            query["category"] = category
        if salary_min is not None:
            query["salary_min"] = {"$gte": int(salary_min)}
        if salary_max is not None:
            query["salary_max"] = {"$lte": int(salary_max)}

        docs = list(jobs_col.find(query))
        results = [_job_response_from_doc(d) for d in docs]

        cache_set(cache_key, json.dumps([r.model_dump() for r in results]), ttl=300)
        return results
    except Exception as exc:
        logger.exception("list_jobs failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list jobs") from exc


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


@router.get("/jobs/search")
async def search_jobs(q: str = Query(..., min_length=1)) -> List[JobResponse]:
    """
    Search jobs by title or description.
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
        )
        docs = list(cursor)
        return [_job_response_from_doc(d) for d in docs]
    except Exception as exc:
        logger.exception("search_jobs failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to search jobs") from exc
