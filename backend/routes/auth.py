from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from bcrypt import hashpw, gensalt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

from backend.config import settings
from backend.database import get_collection
from backend.models.user import Token, TokenData, UserCreate, UserResponse

logger = logging.getLogger("backend.routes.auth")

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _create_password_hash(password: str) -> str:
    """
    Hash a plaintext password.

    Args:
        password: plaintext password

    Returns:
        bcrypt hash (utf-8 string)
    """
    hashed = hashpw(password.encode("utf-8"), gensalt())
    return hashed.decode("utf-8")


def _verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against stored bcrypt hash.

    Args:
        password: plaintext password
        hashed_password: stored bcrypt hash

    Returns:
        True if valid, else False
    """
    try:
        return hashpw(password.encode("utf-8"), hashed_password.encode("utf-8")) == hashed_password.encode("utf-8")
    except Exception:
        return False


def _create_access_token(email: str, expires_delta: timedelta) -> str:
    """
    Create JWT access token.

    Args:
        email: user email
        expires_delta: token expiry duration

    Returns:
        JWT token string
    """
    to_encode = {"sub": email, "exp": datetime.utcnow() + expires_delta}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


async def _get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Resolve user from JWT token.

    Returns:
        User document
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        users_col = get_collection("users")
        user = users_col.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate) -> UserResponse:
    """
    Register a new user.

    Args:
        user: UserCreate

    Returns:
        UserResponse
    """
    try:
        users_col = get_collection("users")
        existing = users_col.find_one({"email": user.email})
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        now = datetime.utcnow()
        created = {
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "hashed_password": _create_password_hash(user.password),
            "created_at": now,
            "id": str(existing.get("id") if existing else now.timestamp()),
        }
        # More reliable id:
        created["id"] = created["id"] = f"{int(now.timestamp() * 1000)}"
        users_col.insert_one(created)

        created["id"] = str(created["id"])
        return UserResponse(
            id=created["id"],
            email=created["email"],
            full_name=created["full_name"],
            role=created["role"],
            created_at=created["created_at"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("register failed: %s", exc)
        raise HTTPException(status_code=500, detail="Registration failed") from exc


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """
    Login and return JWT token.

    Also caches session token in Redis.

    Args:
        form_data: OAuth2PasswordRequestForm

    Returns:
        Token
    """
    try:
        users_col = get_collection("users")
        user = users_col.find_one({"email": form_data.username})
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if not _verify_password(form_data.password, user.get("hashed_password") or ""):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = _create_access_token(user["email"], expires)
        token_payload = {"email": user["email"], "token": access_token, "exp": (datetime.utcnow() + expires).isoformat()}

        # Cache session in Redis (best-effort)
        try:
            from backend.redis_client import cache_set

            cache_set(f"session:{user['email']}", json.dumps(token_payload), ttl=int(expires.total_seconds()))
        except Exception:
            pass

        return Token(access_token=access_token, token_type="bearer")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("login failed: %s", exc)
        raise HTTPException(status_code=500, detail="Login failed") from exc


@router.get("/me", response_model=UserResponse)
async def me(current_user: Dict[str, Any] = Depends(_get_current_user)) -> UserResponse:
    """
    Get the current authenticated user.

    Args:
        current_user: from JWT dependency

    Returns:
        UserResponse
    """
    return UserResponse(
        id=str(current_user.get("id")),
        email=current_user["email"],
        full_name=current_user.get("full_name") or "",
        role=current_user.get("role") or "job_seeker",
        created_at=current_user.get("created_at") or datetime.utcnow(),
    )
