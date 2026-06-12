from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.database import get_collection
from backend.models.resume import ResumeResponse
from backend.services.embedder import generate_embedding as _generate_embedding
from backend.services.nlp_extractor import extract_entities, extract_skills_from_text
from backend.services.pdf_parser import parse_resume_file
from backend.services.vector_store import upsert_vector

logger = logging.getLogger("backend.routes.resume")

router = APIRouter()


@router.post("/resume/upload", response_model=ResumeResponse)
async def upload_resume(file: UploadFile = File(...), user_id: str = "") -> ResumeResponse:
    """
    Upload a resume PDF, parse it, embed it, store it in MongoDB and upsert vector to Pinecone.
    """
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        file_bytes = await file.read()
        parsed = parse_resume_file(file_bytes)
        # Additionally run NER extraction on raw text for extra fields (best-effort).
        # We don't have raw_text from parse_resume_file; so NER uses extracted fields as-is.
        # For quality, we can also rerun by extracting text again; keep deterministic and dependency-light.
        # If you want raw text returned from pdf_parser, extend parse_resume_file accordingly.

        # upsert embedding
        resume_text_for_embedding = (
            f"{parsed.get('candidate_name','')}\n{parsed.get('skills',[])}\n{parsed.get('education','')}\n{parsed.get('email','')}\n{parsed.get('phone','')}"
        )
        embedding = _generate_embedding(resume_text_for_embedding)

        resume_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # In this simplified implementation, user_id may be empty.
        # In production, use JWT to derive current user.
        effective_user_id = user_id or "unknown"

        resumes_col = get_collection("resumes")
        resume_doc: Dict[str, Any] = {
            "resume_id": resume_id,
            "user_id": effective_user_id,
            "created_at": now,
            "file_url": "uploaded_local_or_s3_url",
            **parsed,
        }
        resumes_col.insert_one(resume_doc)

        # Vector metadata
        metadata = {
            "type": "resume",
            "resume_id": resume_id,
            "text": json.dumps(
                {
                    "candidate_name": parsed.get("candidate_name"),
                    "skills": parsed.get("skills") or [],
                    "education": parsed.get("education"),
                    "category": parsed.get("category"),
                }
            ),
        }
        upsert_vector(id=f"resume:{resume_id}", vector=embedding, metadata=metadata)

        return ResumeResponse(
            resume_id=resume_doc["resume_id"],
            user_id=resume_doc["user_id"],
            created_at=resume_doc["created_at"],
            file_url=resume_doc["file_url"],
            candidate_name=resume_doc["candidate_name"],
            email=resume_doc["email"],
            phone=resume_doc["phone"],
            skills=resume_doc["skills"] or [],
            experience_years=float(resume_doc.get("experience_years") or 0.0),
            education=resume_doc["education"],
            category=resume_doc["category"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("upload_resume failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to upload resume") from exc


@router.get("/resume/{resume_id}", response_model=ResumeResponse)
async def get_resume(resume_id: str) -> ResumeResponse:
    """
    Get resume by ID.
    """
    try:
        resumes_col = get_collection("resumes")
        doc = resumes_col.find_one({"resume_id": resume_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Resume not found")

        return ResumeResponse(
            resume_id=str(doc.get("resume_id")),
            user_id=str(doc.get("user_id")),
            created_at=doc.get("created_at") or datetime.utcnow(),
            file_url=doc.get("file_url") or "",
            candidate_name=doc.get("candidate_name") or "",
            email=doc.get("email") or "",
            phone=doc.get("phone") or "",
            skills=doc.get("skills") or [],
            experience_years=float(doc.get("experience_years") or 0.0),
            education=doc.get("education") or "Unknown",
            category=doc.get("category") or "unknown",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_resume failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch resume") from exc


@router.get("/resume/user/{user_id}", response_model=List[ResumeResponse])
async def get_user_resumes(user_id: str) -> List[ResumeResponse]:
    """
    Get all resumes for a user.
    """
    try:
        resumes_col = get_collection("resumes")
        docs = list(resumes_col.find({"user_id": user_id}))
        results: List[ResumeResponse] = []
        for doc in docs:
            results.append(
                ResumeResponse(
                    resume_id=str(doc.get("resume_id")),
                    user_id=str(doc.get("user_id")),
                    created_at=doc.get("created_at") or datetime.utcnow(),
                    file_url=doc.get("file_url") or "",
                    candidate_name=doc.get("candidate_name") or "",
                    email=doc.get("email") or "",
                    phone=doc.get("phone") or "",
                    skills=doc.get("skills") or [],
                    experience_years=float(doc.get("experience_years") or 0.0),
                    education=doc.get("education") or "Unknown",
                    category=doc.get("category") or "unknown",
                )
            )
        return results
    except Exception as exc:
        logger.exception("get_user_resumes failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch resumes") from exc
