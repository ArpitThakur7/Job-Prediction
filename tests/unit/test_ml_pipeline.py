"""
Unit tests for the ML pipeline components.

Tests cover:
- Feature column extraction
- Model loading and inference
- Confidence label computation
- Input validation
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from ml.predict import (
    PredictConfig,
    _confidence_label,
    load_feature_cols,
    load_model,
    load_threshold,
    score_pair,
    validate_input,
)


class TestConfidenceLabel:
    """Tests for the _confidence_label helper."""

    @pytest.mark.parametrize(
        ("prob", "threshold", "expected"),
        [
            (0.95, 0.5, "High"),    # distance 0.45 ≥ 0.25
            (0.75, 0.5, "High"),    # distance 0.25 ≥ 0.25
            (0.65, 0.5, "Medium"),  # distance 0.15 ≥ 0.10
            (0.55, 0.5, "Low"),     # distance 0.05 < 0.10
            (0.50, 0.5, "Low"),     # distance 0.00 < 0.10
            (0.10, 0.5, "High"),    # distance 0.40 ≥ 0.25 (below threshold)
            (0.35, 0.5, "Medium"),  # distance 0.15 ≥ 0.10 (below threshold)
            (0.45, 0.5, "Low"),     # distance 0.05 < 0.10 (below threshold)
        ],
    )
    def test_confidence_bands(self, prob: float, threshold: float, expected: str) -> None:
        assert _confidence_label(prob, threshold) == expected


class TestValidateInput:
    """Tests for the validate_input function."""

    def test_valid_input(self, sample_feature_cols: list[str]) -> None:
        df = pd.DataFrame(
            [{col: 1.0 for col in sample_feature_cols}]
        )
        result = validate_input(df, sample_feature_cols)
        assert result is not None
        assert list(result.columns) == sample_feature_cols

    def test_missing_column_raises(self, sample_feature_cols: list[str]) -> None:
        df = pd.DataFrame({"skill_overlap_count": [1.0]})
        with pytest.raises(ValueError, match="missing required feature columns"):
            validate_input(df, sample_feature_cols)

    def test_null_filled_with_zero(self, sample_feature_cols: list[str]) -> None:
        df = pd.DataFrame(
            [{col: None for col in sample_feature_cols}]
        )
        result = validate_input(df, sample_feature_cols)
        assert result[sample_feature_cols[0]].iloc[0] == 0.0

    def test_non_numeric_cast_to_float(self, sample_feature_cols: list[str]) -> None:
        df = pd.DataFrame(
            [{col: "5" for col in sample_feature_cols}]
        )
        result = validate_input(df, sample_feature_cols)
        assert result[sample_feature_cols[0]].dtype in (np.float64, np.float32)


class TestModelLoading:
    """Tests for model and artifact loading."""

    def test_load_model(self, dummy_model: Path) -> None:
        cfg = PredictConfig(model_path=dummy_model)
        model = load_model(cfg)
        assert hasattr(model, "predict")
        assert hasattr(model, "predict_proba")

    def test_load_feature_cols(self, dummy_model: Path) -> None:
        feat_path = dummy_model.parent / "feature_columns.json"
        cfg = PredictConfig(feature_cols_path=feat_path)
        cols = load_feature_cols(cfg)
        assert isinstance(cols, list)
        assert len(cols) > 0

    def test_load_threshold_default(self) -> None:
        cfg = PredictConfig()
        t = load_threshold(cfg, use_optimal=False)
        assert t == 0.5

    def test_load_threshold_optimal_missing(self, tmp_path: Path) -> None:
        cfg = PredictConfig(threshold_path=tmp_path / "nonexistent.json")
        t = load_threshold(cfg, use_optimal=True)
        assert t == 0.5  # fallback to default

    def test_load_threshold_optimal(self, tmp_path: Path) -> None:
        threshold_path = tmp_path / "optimal_threshold.json"
        with threshold_path.open("w") as f:
            json.dump({"optimal_threshold": 0.7232}, f)
        cfg = PredictConfig(threshold_path=threshold_path)
        t = load_threshold(cfg, use_optimal=True)
        assert t == pytest.approx(0.7232)


class TestScorePair:
    """Tests for the score_pair function."""

    def test_score_pair_returns_expected_keys(self, dummy_model: Path) -> None:
        model = joblib.load(dummy_model)
        feat_path = dummy_model.parent / "feature_columns.json"
        with feat_path.open() as f:
            feature_cols = json.load(f)

        feature_values = {col: 1.0 for col in feature_cols}
        result = score_pair(
            feature_values=feature_values,
            model=model,
            feature_cols=feature_cols,
            threshold=0.5,
        )

        assert "match_probability" in result
        assert "predicted_match" in result
        assert "verdict" in result
        assert "confidence" in result
        assert "threshold_used" in result
        assert result["threshold_used"] == 0.5
        assert result["verdict"] in ("MATCH", "NO MATCH")
        assert 0.0 <= result["match_probability"] <= 1.0

    def test_score_pair_high_probability(self, dummy_model: Path) -> None:
        """With all features set to high values, probability should be high."""
        model = joblib.load(dummy_model)
        feat_path = dummy_model.parent / "feature_columns.json"
        with feat_path.open() as f:
            feature_cols = json.load(f)

        feature_values = {col: 999.0 for col in feature_cols}
        result = score_pair(
            feature_values=feature_values,
            model=model,
            feature_cols=feature_cols,
            threshold=0.5,
        )

        # With extreme feature values, model should predict match
        assert result["predicted_match"] == 1
        assert result["verdict"] == "MATCH"