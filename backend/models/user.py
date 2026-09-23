from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

try:
    import email_validator  # noqa: F401
    from pydantic import EmailStr
except ImportError:
    EmailStr = str  # type: ignore


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
    user: UserResponse | None = None


class LoginRequest(BaseModel):
    """
    JSON Login Request Payload.
    """

    email: EmailStr
    password: str


class ResetPasswordRequest(BaseModel):
    """
    Reset Password Request Payload.
    """

    email: EmailStr
    new_password: str = Field(min_length=8, max_length=256)


class TokenData(BaseModel):
    """
    Decoded token data.
    """

    email: EmailStr
