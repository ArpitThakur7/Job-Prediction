from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class JobBase(BaseModel):
    """
    Base job fields.
    """

    title: str
    description: str
    company: str
    location: str

    required_skills: List[str] = Field(default_factory=list)

    salary_min: int
    salary_max: int

    job_type: str
    category: str
    industry: str


class JobCreate(JobBase):
    """
    Payload for creating a job.
    """

    pass


class JobInDB(JobBase):
    """
    Job model persisted in MongoDB.
    """

    job_id: str
    posted_by: str
    created_at: datetime
    is_active: bool = True


class JobResponse(JobInDB):
    """
    Response schema for returning jobs to clients.
    """

    pass


class JobFilter(BaseModel):
    """
    Optional filters used when listing jobs.
    """

    location: Optional[str] = None
    category: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    job_type: Optional[str] = None
