"""
Phase 7 — Enterprise API Surface for Resume Analyzer & ATS Scoring Service
Provides FastAPI endpoints for document upload, structured parsing, 5-category ATS scoring,
recruiter manual field overrides, hiring pipeline stage movements, and version history.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from backend.database import get_collection
from backend.services.ats_scorer import score_resume_ats, ATSScoreResult
from backend.services.gap_analyzer import perform_skill_gap_analysis, SkillGapAnalysisResult
from backend.services.resume_storage import store_resume_document, get_resume_history_by_user
from backend.services.structured_extractor import extract_structured_resume, StructuredResumeSchema, ContactInfo, SkillsCategorized
from backend.services.text_extractor import extract_resume_text

logger = logging.getLogger("backend.routes.resume")

router = APIRouter()


class ScoreRequest(BaseModel):
    job_id: Optional[str] = None
    job_description: Optional[str] = None
    job_required_skills: Optional[List[str]] = Field(default_factory=list)
    role_type: str = "technical"


class GapAnalysisRequest(BaseModel):
    job_id: Optional[str] = None
    job_description: Optional[str] = None
    job_required_skills: Optional[List[str]] = Field(default_factory=list)


class FieldsOverrideRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None
    technical_skills: Optional[List[str]] = None
    soft_skills: Optional[List[str]] = None
    tools: Optional[List[str]] = None


class PipelineStageUpdate(BaseModel):
    stage: str = "New"  # New, Screening, Interview, Offer, Hired


from backend.routes.auth import get_optional_user


@router.post("/resume/upload")
@router.post("/api/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Query("default_user"),
    role_type: str = Query("technical"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    x_groq_api_key: Optional[str] = Header(None),
    x_pinecone_api_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Intake PDF/DOCX/TXT file -> Robust Text Extraction -> Structured Groq Parsing -> ATS Scoring -> Storage.
    Automatically binds document to authenticated user if session active.
    """
    effective_user_id = (current_user.get("id") or current_user.get("email")) if current_user else (user_id or "default_user")
    try:
        file_bytes = await file.read()
        extracted = extract_resume_text(file_bytes, file.filename or "resume.pdf")

        structured: StructuredResumeSchema = extract_structured_resume(
            raw_text=extracted["raw_text"],
            groq_api_key=x_groq_api_key,
        )

        ats_result: ATSScoreResult = score_resume_ats(
            structured=structured,
            raw_text=extracted["raw_text"],
            role_type=role_type,
        )

        doc = store_resume_document(
            user_id=effective_user_id,
            raw_text=extracted["raw_text"],
            content_hash=extracted["content_hash"],
            structured=structured,
            ats_score=ats_result,
            filename=file.filename or "resume.pdf",
            pinecone_api_key=x_pinecone_api_key,
        )

        # Default stage set to New
        resumes_col = get_collection("resumes")
        if resumes_col is not None:
            resumes_col.update_one({"resume_id": doc["resume_id"]}, {"$set": {"pipeline_stage": "New"}})

        # Publish event to Apache Kafka streaming bus
        try:
            from backend.services.kafka_producer import publish_resume_event
            all_skills = list(structured.skills.technical) + list(structured.skills.tools)
            publish_resume_event(
                resume_id=doc["resume_id"],
                filename=file.filename or "resume.pdf",
                skills=all_skills,
                candidate_name=structured.contact.name,
                experience_years=len(structured.experience),
            )
        except Exception as k_err:
            logger.debug("Kafka resume event publish skipped: %s", k_err)

        return {
            "success": True,
            "message": "Resume uploaded and parsed successfully",
            "resume_id": doc["resume_id"],
            "version": doc.get("version", 1),
            "is_cached": doc.get("is_cached", False),
            "filename": doc.get("filename"),
            "pipeline_stage": "New",
            "candidate_name": structured.contact.name,
            "email": structured.contact.email,
            "structured": structured.dict(),
            "ats_score": ats_result.dict(),
        }

    except ValueError as ve:
        logger.warning("Resume upload validation error: %s", ve)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.exception("Resume upload pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to parse and store resume") from exc


@router.put("/resume/{resume_id}/fields")
@router.put("/api/resume/{resume_id}/fields")
async def override_resume_fields(
    resume_id: str,
    payload: FieldsOverrideRequest,
) -> Dict[str, Any]:
    """
    Recruiter Field Override: Allows recruiters to manually correct parsed fields.
    Recalculates ATS score instantly and saves changes to MongoDB.
    """
    resumes_col = get_collection("resumes")
    doc = resumes_col.find_one({"resume_id": resume_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")

    structured_dict = doc.get("structured", {})
    structured = StructuredResumeSchema(**structured_dict)

    if payload.name is not None:
        structured.contact.name = payload.name
    if payload.email is not None:
        structured.contact.email = payload.email
    if payload.phone is not None:
        structured.contact.phone = payload.phone
    if payload.summary is not None:
        structured.summary = payload.summary
    if payload.technical_skills is not None:
        structured.skills.technical = payload.technical_skills
    if payload.soft_skills is not None:
        structured.skills.soft = payload.soft_skills
    if payload.tools is not None:
        structured.skills.tools = payload.tools

    raw_text = doc.get("raw_text", "")
    ats_result = score_resume_ats(
        structured=structured,
        raw_text=raw_text,
    )

    resumes_col.update_one(
        {"resume_id": resume_id},
        {
            "$set": {
                "structured": structured.dict(),
                "ats_score": ats_result.dict(),
                "last_edited_at": datetime.utcnow(),
            }
        },
    )

    return {
        "success": True,
        "message": "Resume fields updated and ATS score re-calculated successfully",
        "resume_id": resume_id,
        "structured": structured.dict(),
        "ats_score": ats_result.dict(),
    }


@router.post("/resume/{resume_id}/score")
@router.post("/api/resume/{resume_id}/score")
async def score_resume(
    resume_id: str,
    payload: ScoreRequest = ScoreRequest(),
) -> Dict[str, Any]:
    """
    ATS scoring against a target job posting or job description.
    """
    resumes_col = get_collection("resumes")
    doc = resumes_col.find_one({"resume_id": resume_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")

    raw_text = doc.get("raw_text", "")
    structured_dict = doc.get("structured", {})
    structured = StructuredResumeSchema(**structured_dict)

    req_skills = payload.job_required_skills or []
    job_desc = payload.job_description or ""

    if payload.job_id:
        jobs_col = get_collection("jobs")
        job_doc = jobs_col.find_one({"job_id": payload.job_id})
        if job_doc:
            job_desc = job_doc.get("description") or job_desc
            req_skills = job_doc.get("required_skills") or req_skills

    ats_result = score_resume_ats(
        structured=structured,
        raw_text=raw_text,
        job_description=job_desc,
        job_required_skills=req_skills,
        role_type=payload.role_type or "technical",
    )

    return {
        "success": True,
        "resume_id": resume_id,
        "overall_score": ats_result.overall_score,
        "parse_confidence_score": ats_result.parse_confidence_score,
        "breakdown": ats_result.breakdown.dict(),
        "issues": [i.dict() for i in ats_result.issues],
        "matched_keywords": ats_result.matched_keywords,
        "missing_keywords": ats_result.missing_keywords,
    }


@router.put("/resume/{resume_id}/fields")
@router.put("/api/resume/{resume_id}/fields")
async def override_resume_fields(
    resume_id: str,
    payload: FieldsOverrideRequest,
) -> Dict[str, Any]:
    """
    Recruiter manual override of extracted candidate fields.
    """
    resumes_col = get_collection("resumes")
    doc = resumes_col.find_one({"resume_id": resume_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")

    structured = doc.get("structured", {})
    contact = structured.get("contact", {})
    skills = structured.get("skills", {})

    if payload.name is not None:
        contact["name"] = payload.name
    if payload.email is not None:
        contact["email"] = payload.email
    if payload.phone is not None:
        contact["phone"] = payload.phone
    if payload.summary is not None:
        structured["summary"] = payload.summary
    if payload.technical_skills is not None:
        skills["technical"] = payload.technical_skills
    if payload.soft_skills is not None:
        skills["soft"] = payload.soft_skills
    if payload.tools is not None:
        skills["tools"] = payload.tools

    structured["contact"] = contact
    structured["skills"] = skills

    resumes_col.update_one(
        {"resume_id": resume_id},
        {"$set": {"structured": structured, "updated_at": datetime.utcnow()}}
    )
    return {"success": True, "resume_id": resume_id, "structured": structured}


@router.post("/resume/{resume_id}/gap-analysis")
@router.post("/api/resume/{resume_id}/gap-analysis")
async def resume_gap_analysis(
    resume_id: str,
    payload: GapAnalysisRequest = GapAnalysisRequest(),
    x_groq_api_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Skill gap analysis, adjacent skill matching, and bullet rewrites against target job.
    """
    resumes_col = get_collection("resumes")
    doc = resumes_col.find_one({"resume_id": resume_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")

    structured_dict = doc.get("structured", {})
    structured = StructuredResumeSchema(**structured_dict)

    req_skills = payload.job_required_skills or []
    if payload.job_id:
        jobs_col = get_collection("jobs")
        job_doc = jobs_col.find_one({"job_id": payload.job_id})
        if job_doc:
            req_skills = job_doc.get("required_skills") or req_skills

    if not req_skills:
        req_skills = ["Python", "SQL", "Docker", "REST APIs", "AWS", "Git"]

    gap_result: SkillGapAnalysisResult = perform_skill_gap_analysis(
        structured=structured,
        job_required_skills=req_skills,
        groq_api_key=x_groq_api_key,
    )

    return {
        "success": True,
        "resume_id": resume_id,
        "matched_skills": gap_result.matched_skills,
        "missing_skills": gap_result.missing_skills,
        "adjacent_skills": [a.dict() for a in gap_result.adjacent_skills],
        "bullet_rewrites": [b.dict() for b in gap_result.bullet_rewrites],
        "learning_tracks": [l.dict() for l in gap_result.learning_tracks],
    }


@router.get("/resume/pipeline/stages")
@router.get("/api/resume/pipeline/stages")
async def get_pipeline_stages() -> Dict[str, Any]:
    """
    Get candidates grouped by recruiter Kanban pipeline stages.
    """
    resumes_col = get_collection("resumes")
    docs = list(resumes_col.find().limit(200))

    stages: Dict[str, List[Dict[str, Any]]] = {
        "New": [],
        "Screening": [],
        "Interview": [],
        "Offer": [],
        "Hired": [],
    }

    for d in docs:
        stg = d.get("pipeline_stage") or "New"
        if stg not in stages:
            stg = "New"

        ats = d.get("ats_score") or {}
        struct = d.get("structured") or {}
        contact = struct.get("contact") or {}

        stages[stg].append({
            "resume_id": d.get("resume_id"),
            "candidate_name": contact.get("name") or "Candidate",
            "email": contact.get("email") or "",
            "filename": d.get("filename", "resume.pdf"),
            "overall_score": ats.get("overall_score", 0),
            "parse_confidence": ats.get("parse_confidence_score", 100),
            "created_at": d.get("created_at"),
            "stage": stg,
        })

    return {"success": True, "stages": stages}


@router.put("/resume/{resume_id}/stage")
@router.put("/api/resume/{resume_id}/stage")
async def update_pipeline_stage(
    resume_id: str,
    payload: PipelineStageUpdate,
) -> Dict[str, Any]:
    """
    Move candidate between recruiter Kanban pipeline stages.
    """
    resumes_col = get_collection("resumes")
    result = resumes_col.update_one({"resume_id": resume_id}, {"$set": {"pipeline_stage": payload.stage}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Resume not found")

    return {"success": True, "resume_id": resume_id, "stage": payload.stage}


@router.get("/resume/{resume_id}")
@router.get("/api/resume/{resume_id}")
async def get_resume(resume_id: str) -> Dict[str, Any]:
    """Get full structured resume document by ID."""
    resumes_col = get_collection("resumes")
    doc = resumes_col.find_one({"resume_id": resume_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")

    doc["_id"] = str(doc.get("_id"))
    return {"success": True, "data": doc}


@router.get("/resume/user/{user_id}/history")
@router.get("/api/resume/{user_id}/history")
async def get_resume_history(
    user_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Get version history deltas for a user with authorization check."""
    if current_user:
        curr_id = str(current_user.get("id") or current_user.get("email") or "")
        curr_role = current_user.get("role", "job_seeker")
        # Enforce that candidates cannot access another candidate's private resume history
        if curr_role not in ["recruiter", "admin"] and user_id != curr_id and user_id != current_user.get("email"):
            raise HTTPException(status_code=403, detail="Forbidden: You cannot access another candidate's private history")

    history = get_resume_history_by_user(user_id)
    return {"success": True, "user_id": user_id, "history": history}
