from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class EvaluationPaths:
    """
    Resolve default evaluation paths relative to project root.
    """

    model_path: Path
    feature_columns_path: Path
    features_path: Path
    labels_path: Path
    plots_dir: Path

    def __init__(
        self,
        model_path: Path = Path("ml/model/xgb_matcher.pkl"),
        feature_columns_path: Path = Path("ml/model/feature_columns.json"),
        features_path: Path = Path("data/processed/features.csv"),
        labels_path: Path = Path("data/processed/match_labels.csv"),
        plots_dir: Path = Path("ml/plots"),
    ) -> None:
        self.model_path = model_path
        self.feature_columns_path = feature_columns_path
        self.features_path = features_path
        self.labels_path = labels_path
        self.plots_dir = plots_dir


def setup_logging() -> None:
    """
    Configure Python logging.

    Returns:
        None
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _read_csv_or_raise(path: Path) -> pd.DataFrame:
    """
    Read CSV file into DataFrame with clear error message.

    Args:
        path: CSV path.

    Returns:
        DataFrame.

    Raises:
        FileNotFoundError: If file missing.
    """
    try:
        return pd.read_csv(path)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Required data file not found: {path}. "
            f"Place it in the path relative to the project root."
        ) from e


def load_feature_columns(feature_columns_path: Path) -> List[str]:
    """
    Load feature column names saved during training.

    Args:
        feature_columns_path: Path to feature_columns.json.

    Returns:
        List of feature column names.

    Raises:
        FileNotFoundError: If feature columns file missing.
        ValueError: If JSON is invalid or not a list of strings.
    """
    try:
        with feature_columns_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Required feature columns file not found: {feature_columns_path}. "
            f"Run training first to generate it."
        ) from e

    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise ValueError(f"Invalid feature columns JSON format in {feature_columns_path}. Expected list[str].")

    return data


def load_model(model_path: Path) -> xgb.XGBClassifier:
    """
    Load trained XGBoost model from joblib.

    Args:
        model_path: Path to xgb_matcher.pkl.

    Returns:
        Loaded model.

    Raises:
        FileNotFoundError: If model missing.
    """
    try:
        model = joblib.load(model_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Required model file not found: {model_path}. Run training first to generate it."
        ) from e
    return model


def load_and_prepare_eval_dataframe(features_path: Path, labels_path: Path) -> pd.DataFrame:
    """
    Load features and labels and merge on resume_id + job_id.

    Args:
        features_path: Path to features.csv.
        labels_path: Path to match_labels.csv.

    Returns:
        Merged DataFrame.
    """
    features_df = _read_csv_or_raise(features_path)
    labels_df = _read_csv_or_raise(labels_path)

    required_feature_cols = {"resume_id", "job_id"}
    required_label_cols = {"resume_id", "job_id", "is_match"}

    missing_features = required_feature_cols - set(features_df.columns)
    missing_labels = required_label_cols - set(labels_df.columns)

    if missing_features:
        raise ValueError(f"features.csv missing columns: {sorted(missing_features)}")
    if missing_labels:
        raise ValueError(f"match_labels.csv missing columns: {sorted(missing_labels)}")

    merged = pd.merge(features_df, labels_df, on=["resume_id", "job_id"], how="inner")
    if merged.empty:
        raise ValueError("Merged dataset is empty. Check resume_id/job_id keys consistency.")

    merged["is_match"] = merged["is_match"].astype(int)
    return merged


def save_confusion_matrix_png(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    plots_dir: Path,
) -> Path:
    """
    Save confusion matrix to PNG.

    Args:
        y_true: Ground truth labels.
        y_pred: Predicted labels.
        plots_dir: Directory to save plots.

    Returns:
        Path to saved confusion matrix PNG.
    """
    plots_dir.mkdir(parents=True, exist_ok=True)
    cm = confusion_matrix(y_true, y_pred)

    plt.figure(figsize=(7, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Confusion Matrix")
    out_path = plots_dir / "confusion_matrix_eval.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return out_path


def plot_feature_importances_top_n(
    model: xgb.XGBClassifier,
    feature_cols: List[str],
    plots_dir: Path,
    top_n: int = 20,
) -> Path:
    """
    Plot top-n feature importances.

    Args:
        model: Trained model.
        feature_cols: Feature column names aligned with model feature importance array.
        plots_dir: Output directory.
        top_n: Number of features to plot.

    Returns:
        Path to saved feature importance PNG.
    """
    plots_dir.mkdir(parents=True, exist_ok=True)

    importances = model.feature_importances_
    if len(importances) != len(feature_cols):
        raise ValueError(
            f"Feature importances length ({len(importances)}) does not match feature columns length ({len(feature_cols)})."
        )

    fi = pd.DataFrame({"feature": feature_cols, "importance": importances})
    fi = fi.sort_values("importance", ascending=False).head(top_n)

    plt.figure(figsize=(10, 7))
    sns.barplot(data=fi, x="importance", y="feature", orient="h")
    plt.title(f"Top {top_n} Feature Importances")
    out_path = plots_dir / "feature_importance_top20_eval.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return out_path


def evaluate() -> None:
    """
    Evaluate trained model on held-out test set.

    Returns:
        None
    """
    setup_logging()

    paths = EvaluationPaths()
    logger.info("Loading model from %s", paths.model_path)
    model = load_model(paths.model_path)

    logger.info("Loading feature column names from %s", paths.feature_columns_path)
    feature_cols = load_feature_columns(paths.feature_columns_path)

    logger.info("Loading evaluation data (features + labels)")
    merged_df = load_and_prepare_eval_dataframe(paths.features_path, paths.labels_path)

    missing = [c for c in feature_cols if c not in merged_df.columns]
    if missing:
        raise ValueError(
            f"Evaluation dataset is missing expected feature columns from training: {missing}. "
            f"Check that data/processed/features.csv has the same engineered features."
        )

    X = merged_df[feature_cols].to_numpy(dtype=float)
    y = merged_df["is_match"].to_numpy(dtype=int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    logger.info("Running predictions on held-out test set")
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)

    report = classification_report(y_test, y_pred, digits=6, zero_division=0)
    logger.info("Sklearn classification_report (held-out test):\n%s", report)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc_roc = roc_auc_score(y_test, y_proba)

    logger.info(
        "Eval metrics: Accuracy=%.6f Precision=%.6f Recall=%.6f F1=%.6f AUC-ROC=%.6f",
        float(accuracy),
        float(precision),
        float(recall),
        float(f1),
        float(auc_roc),
    )

    # Confusion matrix
    cm_path = save_confusion_matrix_png(y_true=y_test, y_pred=y_pred, plots_dir=paths.plots_dir)
    logger.info("Saved confusion matrix to %s", cm_path)

    # Feature importances
    fi_path = plot_feature_importances_top_n(model=model, feature_cols=feature_cols, plots_dir=paths.plots_dir, top_n=20)
    logger.info("Saved feature importances to %s", fi_path)


def main() -> None:
    """
    Entry point for model evaluation.

    Returns:
        None
    """
    evaluate()


if __name__ == "__main__":
    main()
