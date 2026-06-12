from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ResumeBase(BaseModel):
    """
    Base resume fields.
    """

    candidate_name: str
    email: str
    phone: str
    skills: List[str] = Field(default_factory=list)
    experience_years: float
    education: str
    category: str


class ResumeCreate(ResumeBase):
    """
    Payload for resume upload/creation. Includes raw extracted text.
    """

    raw_text: str


class ResumeInDB(ResumeBase):
    """
    Resume stored in MongoDB.
    """

    resume_id: str
    user_id: str
    created_at: datetime
    file_url: str


class ResumeResponse(ResumeInDB):
    """
    Response schema for returning resumes.
    """

    pass


class MatchResult(BaseModel):
    """
    Match result for a resume-job pair.
    """

    resume_id: str
    job_id: str
    match_score: float
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    rank: int
