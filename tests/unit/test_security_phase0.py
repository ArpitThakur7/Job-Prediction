"""Security fixes: password change, auth rate limiting, offline-role fallback, upload cap, job scoring route."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from backend.config import settings
from backend.main import app
from backend.routes import auth as auth_routes
from backend.services.rate_limit import SlidingWindowLimiter, auth_limiter


@pytest.fixture()
def client(monkeypatch):
    # In-memory users only: never touch the real MongoDB.
    monkeypatch.setattr(auth_routes, "get_collection", lambda name: None)
    auth_routes._IN_MEMORY_USERS.clear()
    auth_limiter.reset()
    yield TestClient(app)
    auth_routes._IN_MEMORY_USERS.clear()
    auth_limiter.reset()


def _register(client, email="jane@example.com", password="correct-horse-1"):
    r = client.post("/auth/register", json={"email": email, "full_name": "Jane Doe", "role": "job_seeker", "password": password})
    assert r.status_code == 200, r.text


def test_password_change_requires_current_password(client):
    _register(client)
    r = client.post("/auth/reset-password", json={"email": "jane@example.com", "current_password": "wrong", "new_password": "new-password-2"})
    assert r.status_code == 401
    # The old password still works
    assert client.post("/auth/login-json", json={"email": "jane@example.com", "password": "correct-horse-1"}).status_code == 200


def test_password_change_without_current_password_is_rejected(client):
    _register(client)
    r = client.post("/auth/reset-password", json={"email": "jane@example.com", "new_password": "new-password-2"})
    assert r.status_code == 422


def test_password_change_does_not_reveal_which_emails_exist(client):
    _register(client)
    unknown = client.post("/auth/reset-password", json={"email": "nobody@example.com", "current_password": "x", "new_password": "new-password-2"})
    wrong = client.post("/auth/reset-password", json={"email": "jane@example.com", "current_password": "x", "new_password": "new-password-2"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_password_change_with_current_password_works(client):
    _register(client)
    r = client.post("/auth/reset-password", json={"email": "jane@example.com", "current_password": "correct-horse-1", "new_password": "new-password-2"})
    assert r.status_code == 200
    assert client.post("/auth/login-json", json={"email": "jane@example.com", "password": "new-password-2"}).status_code == 200


def test_login_is_rate_limited(client):
    codes = [client.post("/auth/login-json", json={"email": "a@example.com", "password": "nope"}).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_sliding_window_frees_up_after_the_window():
    now = [0.0]
    lim = SlidingWindowLimiter(max_requests=2, window_seconds=10, clock=lambda: now[0])
    assert lim.hit(("ip", "/x")) is None
    assert lim.hit(("ip", "/x")) is None
    assert lim.hit(("ip", "/x")) is not None
    assert lim.hit(("other-ip", "/x")) is None  # limits are per client
    now[0] = 10.5
    assert lim.hit(("ip", "/x")) is None


def test_offline_db_never_upgrades_role():
    token = jwt.encode({"sub": "seeker@example.com", "role": "job_seeker"}, settings.SECRET_KEY, algorithm="HS256")
    original = auth_routes.get_collection
    auth_routes.get_collection = lambda name: None
    try:
        user = asyncio.run(auth_routes._get_current_user(token))
    finally:
        auth_routes.get_collection = original
    assert user["role"] == "job_seeker"


def test_resume_upload_rejects_oversized_files(client):
    big = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024 + 10)
    r = client.post("/api/resume/upload", files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413


def test_score_job_requires_a_title(client):
    assert client.post("/match/score-job", json={"description": "Python"}).status_code == 422
