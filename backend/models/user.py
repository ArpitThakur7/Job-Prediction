from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """
    Base fields for a user.
    """

    email: EmailStr
    full_name: str
    role: Literal["job_seeker", "recruiter"]


class UserCreate(UserBase):
    """
    User creation schema. Includes a plaintext password which will be hashed server-side.
    """

    password: str = Field(min_length=8, max_length=256)


class UserInDB(UserBase):
    """
    User representation as stored in MongoDB.
    """

    id: str
    hashed_password: str
    created_at: datetime


class UserResponse(UserBase):
    """
    Safe user representation returned to clients (no passwords).
    """

    id: str
    created_at: datetime


class Token(BaseModel):
    """
    JWT token response.
    """

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Decoded token data.
    """

    email: EmailStr
