from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.database import get_collection
from backend.models.resume import MatchResult
from backend.services.embedder import generate_embedding as _generate_embedding
from backend.services.matcher import rank_matches, score_match
from backend.services.report_generator import generate_match_report
from backend.services.vector_store import query_similar

logger = logging.getLogger("backend.routes.match")

router = APIRouter()


def _get_resume_doc(resume_id: str) -> Dict[str, Any]:
    resumes_col = get_collection("resumes")
    doc = resumes_col.find_one({"resume_id": resume_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    return doc


def _get_job_doc(job_id: str) -> Dict[str, Any]:
    jobs_col = get_collection("jobs")
    doc = jobs_col.find_one({"job_id": job_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return doc


def _resume_data_from_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "skills": doc.get("skills") or [],
        "experience_years": float(doc.get("experience_years") or 0.0),
        "education": doc.get("education") or "Unknown",
        "location": doc.get("location") or "Unknown",
        "category": doc.get("category") or "unknown",
        "candidate_name": doc.get("candidate_name") or "",
    }


def _job_data_from_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_id": doc.get("job_id"),
        "title": doc.get("title") or "",
        "description": doc.get("description") or "",
        "company": doc.get("company") or "",
        "location": doc.get("location") or "",
        "required_skills": doc.get("required_skills") or [],
        "salary_min": doc.get("salary_min"),
        "salary_max": doc.get("salary_max"),
        "job_type": doc.get("job_type") or "",
        "category": doc.get("category") or "",
        "industry": doc.get("industry") or "",
    }


def _matched_skill_sets(resume_skills: List[str], job_skills: List[str]) -> tuple[List[str], List[str]]:
    resume_set = set(resume_skills or [])
    job_set = set(job_skills or [])
    matched = resume_set.intersection(job_set)
    missing = job_set.difference(matched)
    return sorted(list(matched)), sorted(list(missing))


@router.post("/match/resume-to-jobs", response_model=List[MatchResult])
async def resume_to_jobs(payload: Dict[str, Any]) -> List[MatchResult]:
    """
    Accept: {resume_id: str, top_k: int = 10}
    Get resume from MongoDB, query Pinecone, re-rank with XGBoost, return sorted MatchResults.
    """
    try:
        resume_id = str(payload.get("resume_id") or "")
        top_k = int(payload.get("top_k") or 10)
        if not resume_id:
            raise HTTPException(status_code=400, detail="resume_id is required")

        resume_doc = _get_resume_doc(resume_id)
        resume_data = _resume_data_from_doc(resume_doc)

        resume_text_for_embedding = json.dumps(resume_data, ensure_ascii=False)
        query_vec = _generate_embedding(resume_text_for_embedding)

        pinecone_matches = query_similar(query_vec, top_k=top_k)

        # Retrieve actual jobs by IDs (metadata job_id preferred)
        jobs_col = get_collection("jobs")
        job_ids: List[str] = []
        for m in pinecone_matches:
            meta = m.get("metadata") or {}
            jid = meta.get("job_id")
            if jid:
                job_ids.append(str(jid))

        # Fallback: parse id from Pinecone id like "job:{job_id}"
        if not job_ids:
            for m in pinecone_matches:
                mid = str(m.get("id") or "")
                if mid.startswith("job:"):
                    job_ids.append(mid.split("job:", 1)[1])

        job_docs: List[Dict[str, Any]] = []
        for jid in job_ids[:top_k]:
            doc = jobs_col.find_one({"job_id": jid})
            if doc:
                job_docs.append(doc)

        job_data_list = [_job_data_from_doc(d) for d in job_docs]

        ranked = rank_matches(resume_data, job_data_list)

        results: List[MatchResult] = []
        resume_skills = resume_data.get("skills") or []
        for idx, item in enumerate(ranked[:10], start=1):
            job_skills = item.get("required_skills") or []
            matched_skills, missing_skills = _matched_skill_sets(resume_skills, job_skills)

            results.append(
                MatchResult(
                    resume_id=resume_id,
                    job_id=str(item.get("job_id")),
                    match_score=float(item.get("match_score") or 0.0),
                    matched_skills=matched_skills,
                    missing_skills=missing_skills,
                    rank=idx,
                )
            )

        return results
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("resume_to_jobs failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to match resume to jobs") from exc


@router.post("/match/job-to-candidates", response_model=List[MatchResult])
async def job_to_candidates(payload: Dict[str, Any]) -> List[MatchResult]:
    """
    Accept: {job_id: str, top_k: int = 10}
    Get job from MongoDB, query Pinecone, re-rank with XGBoost, return sorted MatchResults.
    """
    try:
        job_id = str(payload.get("job_id") or "")
        top_k = int(payload.get("top_k") or 10)
        if not job_id:
            raise HTTPException(status_code=400, detail="job_id is required")

        job_doc = _get_job_doc(job_id)
        job_data = _job_data_from_doc(job_doc)

        job_text_for_embedding = json.dumps(job_data, ensure_ascii=False)
        query_vec = _generate_embedding(job_text_for_embedding)

        pinecone_matches = query_similar(query_vec, top_k=top_k)

        resumes_col = get_collection("resumes")
        resume_ids: List[str] = []
        for m in pinecone_matches:
            meta = m.get("metadata") or {}
            rid = meta.get("resume_id")
            if rid:
                resume_ids.append(str(rid))

        # Fallback: parse id from Pinecone id like "resume:{resume_id}"
        if not resume_ids:
            for m in pinecone_matches:
                mid = str(m.get("id") or "")
                if mid.startswith("resume:"):
                    resume_ids.append(mid.split("resume:", 1)[1])

        resume_docs: List[Dict[str, Any]] = []
        for rid in resume_ids[:top_k]:
            doc = resumes_col.find_one({"resume_id": rid})
            if doc:
                resume_docs.append(doc)

        # Re-rank: score resume against the single job
        results: List[MatchResult] = []
        job_skills = job_data.get("required_skills") or []
        for idx, rdoc in enumerate(resume_docs, start=1):
            resume_data = _resume_data_from_doc(rdoc)
            sc = score_match(resume_data, job_data)

            resume_skills = resume_data.get("skills") or []
            matched_skills, missing_skills = _matched_skill_sets(resume_skills, job_skills)

            results.append(
                MatchResult(
                    resume_id=str(rdoc.get("resume_id")),
                    job_id=str(job_id),
                    match_score=float(sc),
                    matched_skills=matched_skills,
                    missing_skills=missing_skills,
                    rank=idx,  # will be corrected after sorting
                )
            )

        results.sort(key=lambda x: float(x.match_score or 0.0), reverse=True)
        for i, r in enumerate(results[:10], start=1):
            r.rank = i

        return results[:10]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("job_to_candidates failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to match job to candidates") from exc


@router.get("/match/report/{resume_id}/{job_id}")
async def match_report(resume_id: str, job_id: str) -> Any:
    """
    Generate PDF match report and return it.
    """
    try:
        resume_doc = _get_resume_doc(resume_id)
        job_doc = _get_job_doc(job_id)

        resume_data = _resume_data_from_doc(resume_doc)
        job_data = _job_data_from_doc(job_doc)

        # Compute top skill overlap for report
        resume_skills = resume_data.get("skills") or []
        job_skills = job_data.get("required_skills") or []
        matched_skills, missing_skills = _matched_skill_sets(resume_skills, job_skills)

        score = score_match(resume_data, job_data)

        candidate = {
            "candidate_name": resume_doc.get("candidate_name") or resume_data.get("candidate_name") or "Unknown",
            "email": resume_doc.get("email") or "Unknown",
            "experience_years": resume_doc.get("experience_years") or 0.0,
            "education": resume_doc.get("education") or "Unknown",
        }
        job = {
            "title": job_doc.get("title") or "Unknown",
            "company": job_doc.get("company") or "Unknown",
            "location": job_doc.get("location") or "Unknown",
            "salary_min": job_doc.get("salary_min"),
            "salary_max": job_doc.get("salary_max"),
        }

        pdf_bytes = generate_match_report(
            candidate=candidate,
            job=job,
            score=float(score),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
        )

        # Write to a temporary file? FastAPI FileResponse requires a path.
        # We'll use a NamedTemporaryFile approach.
        import tempfile
        import os

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        try:
            tmp.write(pdf_bytes)
            tmp.flush()
            tmp.close()
            filename = f"match_report_{resume_id}_{job_id}.pdf"
            os.replace(tmp.name, tmp.name)  # no-op but ensures file exists
            return FileResponse(
                path=tmp.name,
                media_type="application/pdf",
                filename=filename,
            )
        except Exception:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
            raise
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("match_report failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate match report") from exc
