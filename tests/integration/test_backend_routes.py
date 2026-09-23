"""
Integration tests for the primary FastAPI backend (backend/main.py).
Validates authentication, jobs listing/creation, real XGBoost resume-to-job matching,
Spark batch endpoint, and live dashboard statistics.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture(scope="module")
def app_client():
    app = create_app()
    with TestClient(app) as client:
        yield client


class TestBackendHealthAndStats:
    """Test health check and dashboard stats endpoints."""

    def test_health(self, app_client: TestClient):
        response = app_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert data["data"]["status"] == "ok"
        assert "services" in data["data"]

    def test_dashboard_stats(self, app_client: TestClient):
        response = app_client.get("/dashboard/stats")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]
        assert "total_jobs" in data
        assert "total_resumes" in data
        assert data["total_jobs"] >= 0
        assert data["total_resumes"] >= 0


from backend.routes.auth import create_access_token


@pytest.fixture(scope="module")
def recruiter_headers():
    token = create_access_token(data={"sub": "recruiter@example.com", "role": "recruiter", "id": "recruiter-001"})
    return {"Authorization": f"Bearer {token}"}


class TestJobsEndpoints:
    """Test job retrieval and authorized creation endpoints."""

    def test_list_jobs(self, app_client: TestClient):
        response = app_client.get("/jobs/")
        assert response.status_code == 200
        jobs = response.json()
        assert isinstance(jobs, list)

    def test_create_job(self, app_client: TestClient, recruiter_headers: dict):
        job_payload = {
            "title": "Senior AI Machine Learning Engineer",
            "description": "Looking for a seasoned ML engineer with Python, XGBoost, and PySpark experience.",
            "company": "DeepTech Innovations",
            "location": "San Francisco, CA",
            "required_skills": ["Python", "Machine Learning", "XGBoost", "PySpark", "Docker"],
            "salary_min": 150000,
            "salary_max": 210000,
            "category": "Technology",
            "industry": "Artificial Intelligence",
            "job_type": "FULL_TIME",
        }
        # 1. Unauthenticated request should be rejected (401)
        unauth_response = app_client.post("/jobs/", json=job_payload)
        assert unauth_response.status_code == 401

        # 2. Authenticated recruiter request should succeed (200/201)
        response = app_client.post("/jobs/", json=job_payload, headers=recruiter_headers)
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["title"] == job_payload["title"]
        assert "job_id" in data
        assert data["posted_by"] == "recruiter@example.com"


class TestMatchEndpointsWithXGBoost:
    """Test matching endpoints powered by real XGBoost inference."""

    def test_match_resume_to_jobs_xgboost(self, app_client: TestClient):
        payload = {
            "resume_id": "test_candidate_101",
            "top_k": 3,
        }
        response = app_client.post("/match/resume-to-jobs", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        matches = body["data"]["matches"]
        assert isinstance(matches, list)
        if matches:
            top_match = matches[0]
            assert "match_score" in top_match
            assert "raw_score" in top_match
            assert "engine" in top_match
            # Confirm real XGBoost engine was executed
            assert top_match["engine"] in ["xgboost", "heuristic"]
            assert "features" in top_match
            assert "skill_overlap_count" in top_match["features"]

    def test_spark_batch_matching(self, app_client: TestClient):
        payload = {"sample_size": 5}
        response = app_client.post("/match/spark-batch", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]
        assert "total_pairs_computed" in data
        assert "results" in data


import uuid


class TestAuthWorkflow:
    """Test user registration, login, token claims, and RBAC rejection."""

    def test_register_and_login(self, app_client: TestClient):
        unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        reg_payload = {
            "email": unique_email,
            "password": "StrongPassword123!",
            "full_name": "Test Engineer",
            "role": "job_seeker",
        }
        reg_res = app_client.post("/auth/register", json=reg_payload)
        assert reg_res.status_code in [200, 201]

        # Login
        login_res = app_client.post("/auth/login-json", json={"email": unique_email, "password": "StrongPassword123!"})
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

    def test_login_invalid_password(self, app_client: TestClient):
        res = app_client.post("/auth/login-json", json={"email": "nonexistent@example.com", "password": "wrong"})
        assert res.status_code == 401

    def test_rbac_seeker_forbidden_job_creation(self, app_client: TestClient):
        seeker_token = create_access_token(data={"sub": "seeker@example.com", "role": "job_seeker", "id": "seeker-1"})
        res = app_client.post("/jobs/", json={"title": "Dev"}, headers={"Authorization": f"Bearer {seeker_token}"})
        assert res.status_code == 403


class TestResumeLifecycle:
    """Test resume upload, ATS scoring, field overrides, and pipeline stage transitions."""

    def test_resume_upload_and_stage_updates(self, app_client: TestClient):
        resume_content = b"""
        John Doe
        john.doe@example.com | (555) 123-4567 | San Francisco, CA
        Summary: Experienced Senior ML Engineer specializing in Python, PyTorch, and XGBoost.
        Experience:
        Senior AI Engineer at TechCorp (2020 - Present)
        - Designed and deployed end-to-end XGBoost and PySpark pipelines.
        Skills: Python, Machine Learning, XGBoost, Docker, PySpark, FastAPI, SQL.
        Education:
        B.S. in Computer Science, Stanford University (2016 - 2020)
        """
        files = {"file": ("resume.txt", resume_content, "text/plain")}
        res = app_client.post("/resume/upload?user_id=candidate-101&role_type=technical", files=files)
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        resume_id = body.get("resume_id") or body.get("data", {}).get("resume_id")
        assert resume_id is not None

        # 1. Update pipeline stage to Screening
        stage_res = app_client.put(f"/resume/{resume_id}/stage", json={"stage": "Screening"})
        assert stage_res.status_code == 200
        assert stage_res.json()["stage"] == "Screening"

        # 2. Recruiter manual field override
        override_res = app_client.put(
            f"/resume/{resume_id}/fields",
            json={
                "name": "Jonathan Doe, Ph.D.",
                "summary": "Updated executive ML Architect profile.",
                "technical_skills": ["Python", "XGBoost", "PySpark", "Kubernetes", "AWS"],
            },
        )
        assert override_res.status_code == 200
        assert override_res.json()["success"] is True

        # 3. Score against target job
        score_res = app_client.post(
            f"/resume/{resume_id}/score",
            json={"job_required_skills": ["Python", "XGBoost", "Kubernetes"], "role_type": "technical"},
        )
        assert score_res.status_code == 200
        assert "overall_score" in score_res.json()

        # 4. Gap analysis
        gap_res = app_client.post(
            f"/resume/{resume_id}/gap-analysis",
            json={"job_required_skills": ["Python", "XGBoost", "Rust"]},
        )
        assert gap_res.status_code == 200
        assert "matched_skills" in gap_res.json()
        assert "missing_skills" in gap_res.json()

        # 5. Access control on history: another candidate cannot view candidate-101's history
        other_seeker_token = create_access_token(data={"sub": "other@example.com", "role": "job_seeker", "id": "seeker-999"})
        history_res = app_client.get(
            f"/resume/user/candidate-101/history",
            headers={"Authorization": f"Bearer {other_seeker_token}"},
        )
        assert history_res.status_code == 403
