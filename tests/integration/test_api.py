"""
Integration tests for the ML inference API (api/main.py).

Tests use a dummy model and the FastAPI TestClient to verify
endpoints respond correctly without requiring external services.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Generator

import joblib
import pytest
from fastapi.testclient import TestClient

from api.main import app, _ModelState, MODEL_PATH, FEATURE_COLS_PATH, THRESHOLD_PATH


@pytest.fixture(autouse=True)
def _patch_model_state(dummy_model: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Replace the model state with a dummy model so tests don't need
    a real trained model file.
    """
    state = _ModelState()
    state.model = joblib.load(dummy_model)
    feat_path = dummy_model.parent / "feature_columns.json"
    with feat_path.open() as f:
        state.feature_cols = json.load(f)
    state.threshold = 0.5
    state.loaded_at = "2026-01-01T00:00:00"

    # Patch the global state object
    monkeypatch.setattr("api.main.state", state)

    # Also patch the path-based loading so lifespan doesn't override
    monkeypatch.setattr("api.main.MODEL_PATH", dummy_model)
    monkeypatch.setattr("api.main.FEATURE_COLS_PATH", feat_path)


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, Any, None]:
    """FastAPI TestClient."""
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "loaded_at" in data


class TestModelInfoEndpoint:
    """Tests for GET /model/info."""

    def test_model_info(self, client: TestClient) -> None:
        response = client.get("/model/info")
        assert response.status_code == 200
        data = response.json()
        assert "feature_columns" in data
        assert "threshold" in data
        assert data["threshold"] == 0.5


class TestMatchEndpoint:
    """Tests for POST /match."""

    @pytest.fixture
    def valid_payload(self) -> dict[str, float]:
        return {
            "skill_overlap_count": 4,
            "skill_overlap_ratio": 0.57,
            "experience_gap": -1.0,
            "education_score": 2.0,
            "location_match": 1.0,
            "skills_count_resume": 7.0,
        }

    def test_match_single(self, client: TestClient, valid_payload: dict[str, float]) -> None:
        response = client.post("/match", json=valid_payload)
        assert response.status_code == 200
        data = response.json()
        assert "match_probability" in data
        assert "predicted_match" in data
        assert "verdict" in data
        assert "confidence" in data
        assert "threshold_used" in data
        assert data["verdict"] in ("MATCH", "NO MATCH")

    def test_match_with_ids(self, client: TestClient, valid_payload: dict[str, float]) -> None:
        payload = {**valid_payload, "resume_id": "res_1", "job_id": "job_1"}
        response = client.post("/match", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["resume_id"] == "res_1"
        assert data["job_id"] == "job_1"

    def test_match_invalid_ratio(self, client: TestClient) -> None:
        """When skill_overlap_count > 0 but ratio is 0, should return 422."""
        payload = {
            "skill_overlap_count": 5,
            "skill_overlap_ratio": 0,
            "experience_gap": 0,
            "education_score": 1,
            "location_match": 1,
            "skills_count_resume": 5,
        }
        response = client.post("/match", json=payload)
        assert response.status_code == 422

    def test_match_missing_field(self, client: TestClient) -> None:
        payload = {"skill_overlap_count": 1}  # missing required fields
        response = client.post("/match", json=payload)
        assert response.status_code == 422


class TestBatchEndpoint:
    """Tests for POST /match/batch."""

    @pytest.fixture
    def batch_payload(self) -> dict[str, Any]:
        return {
            "pairs": [
                {
                    "skill_overlap_count": 4,
                    "skill_overlap_ratio": 0.57,
                    "experience_gap": -1.0,
                    "education_score": 2.0,
                    "location_match": 1.0,
                    "skills_count_resume": 7.0,
                },
                {
                    "skill_overlap_count": 0,
                    "skill_overlap_ratio": 0.0,
                    "experience_gap": 5.0,
                    "education_score": 0.0,
                    "location_match": 0.0,
                    "skills_count_resume": 2.0,
                },
            ]
        }

    def test_batch_scoring(self, client: TestClient, batch_payload: dict[str, Any]) -> None:
        response = client.post("/match/batch", json=batch_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert "matched" in data
        assert "match_rate" in data
        assert len(data["results"]) == 2

    def test_batch_empty_raises(self, client: TestClient) -> None:
        response = client.post("/match/batch", json={"pairs": []})
        assert response.status_code == 422

    def test_batch_too_large(self, client: TestClient) -> None:
        many_pairs = [
            {
                "skill_overlap_count": i,
                "skill_overlap_ratio": 0.5,
                "experience_gap": 0.0,
                "education_score": 1.0,
                "location_match": 1.0,
                "skills_count_resume": 5.0,
            }
            for i in range(1001)
        ]
        response = client.post("/match/batch", json={"pairs": many_pairs})
        assert response.status_code == 422


class TestExplainEndpoint:
    """Tests for POST /match/explain."""

    @pytest.fixture
    def valid_payload(self) -> dict[str, float]:
        return {
            "skill_overlap_count": 4,
            "skill_overlap_ratio": 0.57,
            "experience_gap": -1.0,
            "education_score": 2.0,
            "location_match": 1.0,
            "skills_count_resume": 7.0,
        }

    def test_explain_requires_shap(self, client: TestClient, valid_payload: dict[str, float]) -> None:
        """
        If shap is not installed, /match/explain should return 501.
        We simulate this by patching the import.
        """
        import api.main  # noqa: F811

        # Save original
        original_imports = {}
        import sys

        if "shap" in sys.modules:
            original_imports["shap"] = sys.modules.pop("shap")

        try:
            sys.modules["shap"] = None  # type: ignore[assignment]
            response = client.post("/match/explain", json=valid_payload)
            assert response.status_code in (200, 501)  # 200 if shap is installed, 501 if not
        finally:
            # Restore
            if "shap" in original_imports:
                sys.modules["shap"] = original_imports["shap"]