from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrainConfig:
    """Training configuration for the XGBoost matcher."""

    features_path: Path = Path("data/processed/features.csv")
    labels_path: Path = Path("data/processed/match_labels.csv")
    model_dir: Path = Path("ml/model")
    plots_dir: Path = Path("ml/plots")
    test_size: float = 0.2
    random_state: int = 42
    n_splits: int = 5
    n_estimators: int = 300
    max_depth: int = 6
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    eval_metric: str = "logloss"


def setup_logging() -> None:
    """Configure Python logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _read_csv_or_raise(path: Path) -> pd.DataFrame:
    """
    Read a CSV file into a DataFrame with a clear error message.

    Args:
        path: Path to the CSV file.

    Returns:
        DataFrame.

    Raises:
        FileNotFoundError: If the file is missing.
    """
    try:
        return pd.read_csv(path)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Required data file not found: {path}. "
            f"Place it in the path relative to the project root."
        ) from e


def load_and_merge(features_path: Path, labels_path: Path) -> pd.DataFrame:
    """
    Load features and match labels and merge on resume_id + job_id.

    Handles the case where features.csv already contains is_match
    and match_score columns — skips redundant merge in that case.

    Args:
        features_path: Path to features.csv.
        labels_path: Path to match_labels.csv.

    Returns:
        Merged DataFrame with feature columns and labels.
    """
    # ============================
    # DATASET REQUIRED
    # ============================
    # Place files in: data/processed/
    # features.csv columns expected:
    #   resume_id, job_id, skill_overlap_count, skill_overlap_ratio,
    #   experience_gap, education_score, location_match, category_match,
    #   title_relevance, description_length, skills_count_resume,
    #   skills_count_job, is_match, match_score
    # match_labels.csv columns expected:
    #   match_id, resume_id, job_id, is_match (0 or 1), match_score (0.0-1.0)
    # ============================

    logger.info("Loading features from %s", features_path)
    features_df = _read_csv_or_raise(features_path)

    logger.info("Loading labels from %s", labels_path)
    labels_df = _read_csv_or_raise(labels_path)

    logger.info("features.csv shape: %s | columns: %s", features_df.shape, features_df.columns.tolist())
    logger.info("match_labels.csv shape: %s | columns: %s", labels_df.shape, labels_df.columns.tolist())

    # Drop duplicate label columns already present in features_df
    label_only_cols = [
        c for c in labels_df.columns
        if c not in ("resume_id", "job_id") and c in features_df.columns
    ]
    if label_only_cols:
        logger.info("Dropping duplicate cols from labels before merge: %s", label_only_cols)
        labels_df = labels_df.drop(columns=label_only_cols)

    # Validate required columns
    required_feature_cols = {"resume_id", "job_id"}
    missing_features = required_feature_cols - set(features_df.columns)
    if missing_features:
        raise ValueError(f"features.csv missing columns: {sorted(missing_features)}")

    # If is_match already in features_df — skip merge entirely
    if "is_match" in features_df.columns:
        logger.info(
            "is_match already present in features.csv — "
            "skipping merge, using features_df directly (%d rows)",
            len(features_df),
        )
        merged = features_df.copy()
    else:
        merged = pd.merge(features_df, labels_df, on=["resume_id", "job_id"], how="inner")
        if merged.empty:
            raise ValueError(
                "Merged dataset is empty. Check resume_id/job_id key consistency."
            )

    # Drop match_id — not a feature, not a label
    if "match_id" in merged.columns:
        merged = merged.drop(columns=["match_id"])

    # Validate is_match exists after merge
    if "is_match" not in merged.columns:
        raise ValueError(
            "is_match column missing after merge. "
            "Ensure match_labels.csv contains an is_match column."
        )

    merged["is_match"] = merged["is_match"].astype(int)

    pos_pct = merged["is_match"].mean() * 100
    logger.info(
        "Dataset ready — rows: %d | columns: %d | positive matches: %.1f%%",
        len(merged),
        len(merged.columns),
        pos_pct,
    )
    return merged


def get_feature_columns(merged_df: pd.DataFrame) -> List[str]:
    """
    Determine feature columns for model training.

    Excludes all ID, label, metadata, and leaky columns.

    Excluded columns and reasons:
      - resume_id, job_id, match_id : identifiers, not features
      - is_match, match_score       : labels (match_score was used to generate is_match — leakage)
      - title_relevance             : binary column perfectly correlated with is_match — leakage
      - category_match              : NaN / constant — zero variance
      - description_length          : zero correlation with is_match
      - skills_count_job            : zero correlation with is_match

    Args:
        merged_df: Merged DataFrame.

    Returns:
        List of feature column names.
    """
    exclude = {
        "resume_id", "job_id", "match_id",
        "is_match", "match_score",
        "title_relevance",
        "category_match",
        "description_length",
        "skills_count_job",
    }
    feature_cols = [c for c in merged_df.columns if c not in exclude]

    if not feature_cols:
        raise ValueError("No feature columns found after excluding id/label columns.")

    logger.info("Feature columns (%d): %s", len(feature_cols), feature_cols)
    return feature_cols


def plot_roc_curve(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    plots_dir: Path,
) -> None:
    """
    Plot and save ROC curve.

    Args:
        y_true: Ground truth labels.
        y_proba: Predicted probabilities for class 1.
        plots_dir: Output directory.

    Returns:
        None
    """
    plots_dir.mkdir(parents=True, exist_ok=True)
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    auc = roc_auc_score(y_true, y_proba)

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC curve (AUC = {auc:.4f})")
    plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Receiver Operating Characteristic (ROC)")
    plt.legend(loc="lower right")
    out_path = plots_dir / "roc_curve.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    logger.info("Saved ROC curve -> %s", out_path)


def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    plots_dir: Path,
) -> None:
    """
    Plot and save confusion matrix heatmap.

    Args:
        y_true: Ground truth labels.
        y_pred: Predicted class labels.
        plots_dir: Output directory.

    Returns:
        None
    """
    plots_dir.mkdir(parents=True, exist_ok=True)
    cm = confusion_matrix(y_true, y_pred)

    plt.figure(figsize=(7, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Confusion Matrix")
    out_path = plots_dir / "confusion_matrix.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    logger.info("Saved confusion matrix -> %s", out_path)


def plot_feature_importance(
    model: xgb.XGBClassifier,
    feature_cols: List[str],
    plots_dir: Path,
    top_n: int = 20,
) -> None:
    """
    Plot and save feature importance bar chart.

    Args:
        model: Trained XGBoost model.
        feature_cols: Feature column names aligned to model features.
        plots_dir: Output directory.
        top_n: Number of top features to display.

    Returns:
        None
    """
    plots_dir.mkdir(parents=True, exist_ok=True)
    importances = model.feature_importances_

    if len(importances) != len(feature_cols):
        raise ValueError(
            f"Feature importances length ({len(importances)}) does not match "
            f"feature columns length ({len(feature_cols)})."
        )

    fi = pd.DataFrame({"feature": feature_cols, "importance": importances})
    fi = fi.sort_values("importance", ascending=False).head(top_n)

    plt.figure(figsize=(10, 7))
    sns.barplot(data=fi, x="importance", y="feature", orient="h")
    plt.title(f"Top {top_n} Feature Importances")
    plt.tight_layout()
    out_path = plots_dir / "feature_importance.png"
    plt.savefig(out_path, dpi=200)
    plt.close()
    logger.info("Saved feature importance -> %s", out_path)


def compute_scale_pos_weight(y: np.ndarray) -> float:
    """
    Compute scale_pos_weight for XGBoost class imbalance handling.

    scale_pos_weight = count(negatives) / count(positives)

    Args:
        y: Binary labels array.

    Returns:
        scale_pos_weight float value.
    """
    y_int = y.astype(int)
    count_0 = int((y_int == 0).sum())
    count_1 = int((y_int == 1).sum())

    if count_1 == 0:
        raise ValueError(
            "Cannot compute scale_pos_weight: no positive examples (is_match=1) found."
        )

    ratio = count_0 / count_1
    logger.info(
        "Class balance — negatives: %d | positives: %d | scale_pos_weight: %.4f",
        count_0, count_1, ratio,
    )
    return ratio


def evaluate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
) -> Dict[str, float]:
    """
    Compute all classification metrics.

    Args:
        y_true: Ground truth labels.
        y_pred: Predicted binary labels.
        y_proba: Predicted probability for class 1.

    Returns:
        Dictionary of metric name -> float value.
    """
    return {
        "accuracy":  float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall":    float(recall_score(y_true, y_pred, zero_division=0)),
        "f1":        float(f1_score(y_true, y_pred, zero_division=0)),
        "auc_roc":   float(roc_auc_score(y_true, y_proba)),
    }


def train_and_evaluate(config: TrainConfig) -> None:
    """
    Full XGBoost training pipeline:
    load -> merge -> split -> cross-validate -> train -> evaluate -> save.

    Args:
        config: TrainConfig with all paths and hyperparameters.

    Returns:
        None
    """
    setup_logging()
    logger.info("=" * 60)
    logger.info("Starting XGBoost Job-Candidate Matching Training Pipeline")
    logger.info("=" * 60)

    # Load & prepare data
    merged_df = load_and_merge(config.features_path, config.labels_path)
    feature_cols = get_feature_columns(merged_df)

    X = merged_df[feature_cols].to_numpy(dtype=float)
    y = merged_df["is_match"].to_numpy(dtype=int)

    logger.info("X shape: %s | y shape: %s", X.shape, y.shape)

    # Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=config.test_size,
        random_state=config.random_state,
        stratify=y,
    )
    logger.info(
        "Split — train: %d rows | test: %d rows",
        len(X_train), len(X_test),
    )

    # Class imbalance weight
    scale_pos_weight = compute_scale_pos_weight(y_train)

    # Build model
    model = xgb.XGBClassifier(
        n_estimators=config.n_estimators,
        max_depth=config.max_depth,
        learning_rate=config.learning_rate,
        subsample=config.subsample,
        colsample_bytree=config.colsample_bytree,
        eval_metric=config.eval_metric,
        random_state=config.random_state,
        scale_pos_weight=scale_pos_weight,
        n_jobs=-1,
        verbosity=0,
    )

    # Cross-validation
    logger.info("Running %d-fold stratified cross-validation (scoring=roc_auc) ...", config.n_splits)
    cv = StratifiedKFold(
        n_splits=config.n_splits,
        shuffle=True,
        random_state=config.random_state,
    )
    cv_scores = cross_val_score(
        model, X_train, y_train,
        cv=cv,
        scoring="roc_auc",
        n_jobs=-1,
    )
    logger.info(
        "CV ROC-AUC — mean: %.6f | std: %.6f | scores: %s",
        float(cv_scores.mean()),
        float(cv_scores.std()),
        [round(s, 4) for s in cv_scores.tolist()],
    )

    # Final fit on full training set
    logger.info("Fitting final model on full training set ...")
    model.fit(X_train, y_train)

    # Predict on test set
    logger.info("Evaluating on test set ...")
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred  = (y_proba >= 0.5).astype(int)

    metrics = evaluate_metrics(y_test, y_pred, y_proba)
    logger.info("=" * 40)
    logger.info("TEST RESULTS:")
    for k, v in metrics.items():
        logger.info("  %-12s: %.6f", k.upper(), v)
    logger.info("=" * 40)

    # Save plots
    plot_roc_curve(y_true=y_test, y_proba=y_proba, plots_dir=config.plots_dir)
    plot_confusion_matrix(y_true=y_test, y_pred=y_pred, plots_dir=config.plots_dir)
    plot_feature_importance(
        model=model,
        feature_cols=feature_cols,
        plots_dir=config.plots_dir,
        top_n=min(20, len(feature_cols)),
    )

    # Save model
    config.model_dir.mkdir(parents=True, exist_ok=True)
    model_path = config.model_dir / "xgb_matcher.pkl"
    joblib.dump(model, model_path)
    logger.info("Saved trained model -> %s", model_path)

    # Save feature columns (critical for inference alignment)
    feature_cols_path = config.model_dir / "feature_columns.json"
    with feature_cols_path.open("w", encoding="utf-8") as f:
        json.dump(feature_cols, f, indent=2)
    logger.info("Saved feature columns -> %s", feature_cols_path)

    # Save metrics
    metrics_path = config.model_dir / "train_metrics.json"
    metrics["cv_auc_mean"] = float(cv_scores.mean())
    metrics["cv_auc_std"]  = float(cv_scores.std())
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Saved metrics -> %s", metrics_path)

    logger.info("=" * 60)
    logger.info("Training complete. Model saved to %s", model_path)
    logger.info("=" * 60)


def main() -> None:
    """Entry point for XGBoost training pipeline."""
    train_and_evaluate(TrainConfig())


if __name__ == "__main__":
    main()