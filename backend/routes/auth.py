from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

from bcrypt import checkpw, gensalt, hashpw
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
try:
    from jose import JWTError, jwt
except ImportError:
    import jwt
    try:
        from jwt.exceptions import PyJWTError as JWTError
    except ImportError:
        JWTError = Exception  # type: ignore

from backend.config import settings
from backend.database import get_collection
from backend.models.user import Token, UserCreate, UserResponse, LoginRequest, ResetPasswordRequest

logger = logging.getLogger("backend.routes.auth")

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _create_password_hash(password: str) -> str:
    hashed = hashpw(password.encode("utf-8"), gensalt())
    return hashed.decode("utf-8")


def _verify_password(password: str, hashed_password: str) -> bool:
    try:
        return checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def _create_access_token(email: str, expires_delta: timedelta) -> str:
    return create_access_token({"sub": email}, expires_delta)


def _find_user_by_email(users_col, email: str):
    """Case-insensitive email lookup in MongoDB."""
    clean = email.strip()
    return users_col.find_one({"email": {"$regex": f"^{re.escape(clean)}$", "$options": "i"}})


def _build_user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user.get("id") or user.get("_id")),
        email=user["email"],
        full_name=user.get("full_name", ""),
        role=user.get("role", "job_seeker"),
        created_at=user.get("created_at") or datetime.utcnow(),
    )


def _build_token_response(user: dict) -> Token:
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = _create_access_token(user["email"], expires)
    # Cache session in Redis (best-effort)
    try:
        from backend.redis_client import cache_set
        token_payload = {"email": user["email"], "token": access_token, "exp": (datetime.utcnow() + expires).isoformat()}
        cache_set(f"session:{user['email']}", json.dumps(token_payload), ttl=int(expires.total_seconds()))
    except Exception:
        pass
    return Token(access_token=access_token, token_type="bearer", user=_build_user_response(user))


oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def _get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        users_col = get_collection("users")
        if users_col is None:
            # Local in-memory mock user if MongoDB is offline in local dev
            return {"id": "local_dev_user", "email": email, "role": "recruiter"}
        user = users_col.find_one({"email": email})
        if not user:
            if "role" in payload:
                return {
                    "id": payload.get("id", str(uuid.uuid4())),
                    "email": email,
                    "full_name": payload.get("full_name", email.split("@")[0]),
                    "role": payload.get("role", "job_seeker"),
                }
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


get_current_user = _get_current_user


async def get_optional_user(token: Optional[str] = Depends(oauth2_scheme_optional)) -> Optional[Dict[str, Any]]:
    """Return authenticated user if Bearer token present, else None."""
    if not token:
        return None
    try:
        return await _get_current_user(token)
    except Exception:
        return None


def require_role(allowed_roles: List[str]):
    """FastAPI dependency requiring user to have one of the specified roles."""
    async def role_checker(current_user: Dict[str, Any] = Depends(_get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "job_seeker")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{user_role}' not authorized. Requires one of: {allowed_roles}",
            )
        return current_user
    return role_checker


# ─── REGISTER ───────────────────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate) -> UserResponse:
    try:
        users_col = get_collection("users")
        existing = _find_user_by_email(users_col, user.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered. Please sign in.")

        now = datetime.utcnow()
        created = {
            "id": str(uuid.uuid4()),
            "email": user.email.strip().lower(),
            "full_name": user.full_name.strip(),
            "role": user.role,
            "hashed_password": _create_password_hash(user.password),
            "created_at": now,
        }
        users_col.insert_one(dict(created))

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


# ─── LOGIN (OAuth2 form-data) ───────────────────────────────────────────────
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    try:
        users_col = get_collection("users")
        user = _find_user_by_email(users_col, form_data.username)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if not _verify_password(form_data.password, user.get("hashed_password") or ""):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        return _build_token_response(user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("login failed: %s", exc)
        raise HTTPException(status_code=500, detail="Login failed") from exc


# ─── LOGIN-JSON (JSON body) ─────────────────────────────────────────────────
@router.post("/login-json", response_model=Token)
async def login_json(payload: LoginRequest) -> Token:
    try:
        users_col = get_collection("users")
        user = _find_user_by_email(users_col, payload.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if not _verify_password(payload.password, user.get("hashed_password") or ""):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        return _build_token_response(user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("login_json failed: %s", exc)
        raise HTTPException(status_code=500, detail="Login failed") from exc


# ─── RESET PASSWORD ─────────────────────────────────────────────────────────
@router.post("/reset-password", response_model=Token)
async def reset_password(payload: ResetPasswordRequest) -> Token:
    try:
        users_col = get_collection("users")
        user = _find_user_by_email(users_col, payload.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account registered with this email.")
        new_hash = _create_password_hash(payload.new_password)
        users_col.update_one({"_id": user["_id"]}, {"$set": {"hashed_password": new_hash}})
        return _build_token_response(user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("reset_password failed: %s", exc)
        raise HTTPException(status_code=500, detail="Password update failed") from exc


# ─── ME (authenticated) ─────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
async def me(current_user: Dict[str, Any] = Depends(_get_current_user)) -> UserResponse:
    return _build_user_response(current_user)
