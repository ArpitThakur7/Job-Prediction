"""
Pytest configuration and shared fixtures for JOB-AI-PLATFORM tests.

Run with: pytest
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pytest
from xgboost import XGBClassifier


# ---------------------------------------------------------------------------
# Fixtures: ML pipeline test data
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def sample_feature_cols() -> list[str]:
    """Feature columns expected by the model."""
    return [
        "skill_overlap_count",
        "skill_overlap_ratio",
        "experience_gap",
        "education_score",
        "location_match",
        "category_match",
        "title_relevance",
        "semantic_similarity",
        "skills_count_resume",
    ]


@pytest.fixture(scope="session")
def sample_features_csv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a synthetic features CSV for batch inference testing."""
    n = 20
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "resume_id": [f"res_{i}" for i in range(n)],
            "job_id": [f"job_{i}" for i in range(n)],
            "skill_overlap_count": rng.integers(0, 10, n),
            "skill_overlap_ratio": rng.uniform(0, 1, n),
            "experience_gap": rng.uniform(-5, 10, n),
            "education_score": rng.uniform(0, 3, n),
            "location_match": rng.integers(0, 2, n),
            "category_match": rng.integers(0, 2, n),
            "title_relevance": rng.integers(0, 2, n),
            "semantic_similarity": rng.uniform(0, 1, n),
            "skills_count_resume": rng.integers(2, 20, n),
            "is_match": rng.integers(0, 2, n),
        }
    )
    path = tmp_path_factory.mktemp("data") / "sample_features.csv"
    df.to_csv(path, index=False)
    return path


@pytest.fixture(scope="session")
def dummy_model(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Train a tiny XGBoost model on synthetic data and return its path."""
    rng = np.random.default_rng(42)
    n = 100
    X = pd.DataFrame(
        {
            "skill_overlap_count": rng.integers(0, 10, n),
            "skill_overlap_ratio": rng.uniform(0, 1, n),
            "experience_gap": rng.uniform(-5, 10, n),
            "education_score": rng.uniform(0, 3, n),
            "location_match": rng.integers(0, 2, n),
            "category_match": rng.integers(0, 2, n),
            "title_relevance": rng.integers(0, 2, n),
            "semantic_similarity": rng.uniform(0, 1, n),
            "skills_count_resume": rng.integers(2, 20, n),
        }
    )
    y = rng.integers(0, 2, n)

    model = XGBClassifier(
        n_estimators=5,
        max_depth=2,
        random_state=42,
        verbosity=0,
        n_jobs=1,
    )
    model.fit(X, y)

    model_dir = tmp_path_factory.mktemp("model")
    model_path = model_dir / "xgb_matcher.pkl"
    joblib.dump(model, model_path)

    # Save feature columns
    import json

    feat_path = model_dir / "feature_columns.json"
    with feat_path.open("w") as f:
        json.dump(list(X.columns), f)

    return model_path