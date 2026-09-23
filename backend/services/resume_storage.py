"""
Phase 6 — Dense Embedding & Persistent Storage - JOB-AI Platform
Generates dense text embeddings from structured resume fields, manages version history per user,
and syncs documents across MongoDB and Pinecone vector namespaces.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.database import get_collection
from backend.services.ats_scorer import ATSScoreResult
from backend.services.embedder import generate_embedding
from backend.services.structured_extractor import StructuredResumeSchema
from backend.services.vector_store import upsert_vector

logger = logging.getLogger("backend.services.resume_storage")


def generate_dense_resume_embedding_text(structured: StructuredResumeSchema) -> str:
    """
    Build dense embedding string from structured attributes (skills, titles, education, top bullets).
    """
    parts = []

    if structured.contact.name:
        parts.append(f"Candidate Name: {structured.contact.name}")

    all_skills = structured.skills.technical + structured.skills.soft + structured.skills.tools
    if all_skills:
        parts.append(f"Skills: {', '.join(all_skills)}")

    titles = [exp.title for exp in structured.experience if exp.title]
    if titles:
        parts.append(f"Roles: {', '.join(titles)}")

    top_bullets = []
    for exp in structured.experience[:3]:
        top_bullets.extend(exp.bullets[:2])
    if top_bullets:
        parts.append(f"Key Accomplishments: {' | '.join(top_bullets)}")

    degrees = [edu.degree for edu in structured.education if edu.degree]
    if degrees:
        parts.append(f"Education: {', '.join(degrees)}")

    return "\n".join(parts)


def store_resume_document(
    user_id: str,
    raw_text: str,
    content_hash: str,
    structured: StructuredResumeSchema,
    ats_score: ATSScoreResult,
    filename: str = "resume.pdf",
    pinecone_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Store structured resume + ATS score in MongoDB with version history,
    and upsert dense embedding to Pinecone `resumes` namespace.
    """
    resumes_col = get_collection("resumes")
    now = datetime.utcnow()

    # 1. Check for duplicate content hash for caching / re-upload detection
    existing_by_hash = resumes_col.find_one({"user_id": user_id, "content_hash": content_hash})
    if existing_by_hash:
        logger.info("Found exact duplicate content hash (%s) for user %s. Returning cached resume document.", content_hash, user_id)
        existing_by_hash["is_cached"] = True
        return existing_by_hash

    # 2. Version history tracking
    user_resumes = list(resumes_col.find({"user_id": user_id}).sort("version", -1).limit(1))
    next_version = 1
    parent_id = None
    if user_resumes:
        next_version = user_resumes[0].get("version", 1) + 1
        parent_id = user_resumes[0].get("resume_id")

    resume_id = str(uuid.uuid4())

    # 3. Generate dense vector embedding
    dense_text = generate_dense_resume_embedding_text(structured)
    embedding_vector = generate_embedding(dense_text)

    # 4. Prepare MongoDB Document
    doc: Dict[str, Any] = {
        "resume_id": resume_id,
        "user_id": user_id or "anonymous",
        "version": next_version,
        "parent_resume_id": parent_id,
        "filename": filename,
        "content_hash": content_hash,
        "raw_text": raw_text,
        "structured": structured.dict(),
        "ats_score": ats_score.dict(),
        "created_at": now,
        "is_cached": False,
    }

    resumes_col.insert_one(doc)

    # 5. Pinecone Vector Upsert
    try:
        metadata = {
            "type": "resume",
            "resume_id": resume_id,
            "user_id": user_id or "anonymous",
            "version": next_version,
            "overall_score": ats_score.overall_score,
            "skills": ", ".join(structured.skills.technical[:8]),
        }
        upsert_vector(
            id=f"resume:{resume_id}",
            vector=embedding_vector,
            metadata=metadata,
            api_key=pinecone_api_key,
        )
    except Exception as exc:
        logger.warning("Pinecone vector upsert skipped: %s", exc)

    return doc


def get_resume_history_by_user(user_id: str) -> List[Dict[str, Any]]:
    """Retrieve version history of resumes for a given user sorted by version."""
    resumes_col = get_collection("resumes")
    docs = list(resumes_col.find({"user_id": user_id}).sort("version", -1).limit(50))
    history = []
    for d in docs:
        ats = d.get("ats_score") or {}
        history.append({
            "resume_id": d.get("resume_id"),
            "version": d.get("version", 1),
            "filename": d.get("filename", "resume.pdf"),
            "overall_score": ats.get("overall_score", 0),
            "created_at": d.get("created_at"),
            "breakdown": ats.get("breakdown", {}),
        })
    return history
