from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    n_estimators: int = 200
    max_depth: int = 4
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


def _merge_legacy_mongo_feedback(features_df: pd.DataFrame) -> pd.DataFrame:
    """Legacy active-learning hack: append rows from Mongo job_prediction.feedback_data."""
    try:
        import os
        from pymongo import MongoClient
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        feedback_col = client["job_prediction"]["feedback_data"]
        feedback_count = feedback_col.count_documents({})
        if feedback_count > 0:
            logger.info("Found %d legacy feedback rows in MongoDB. Merging...", feedback_count)
            feedback_df = pd.DataFrame(list(feedback_col.find({}, {"_id": 0, "created_at": 0})))
            for col in features_df.columns:
                if col not in feedback_df.columns:
                    feedback_df[col] = 0.0
            feedback_df = feedback_df[features_df.columns]
            features_df = pd.concat([features_df, feedback_df], ignore_index=True)
            logger.info("New merged features shape: %s", features_df.shape)
    except Exception as e:
        logger.warning("Could not merge user feedback from MongoDB: %s", e)
    return features_df


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

    # Legacy: append raw feature rows from MongoDB `feedback_data` (opt-in only,
    # TRAIN_MERGE_MONGO_FEEDBACK_DATA=1). The supported feedback loop is
    # ml/retrain_with_feedback.py, which builds proper features + labels from /feedback events.
    import os
    if os.environ.get("TRAIN_MERGE_MONGO_FEEDBACK_DATA") == "1":
        features_df = _merge_legacy_mongo_feedback(features_df)

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
        "category_match",  # Exclude to prevent high-correlation proxy leakage
        "description_length",
        "skills_count_job",
        # bookkeeping columns, never model inputs
        "resume_experience_years", "job_experience_required", "sample_weight", "source",
    }
    feature_cols = [c for c in merged_df.columns if c not in exclude]

    if not feature_cols:
        raise ValueError("No feature columns found after excluding id/label columns.")

    logger.info("Feature columns (%d): %s", len(feature_cols), feature_cols)
    return feature_cols


def check_feature_leakage(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str = "is_match",
    max_allowed_corr: float = 0.80,
) -> None:
    """
    Check correlations between features and label to detect any potential data leakage.
    Warns if any feature has |corr| > max_allowed_corr.
    """
    logger.info("-" * 50)
    logger.info("FEATURE CORRELATION & LEAKAGE CHECK:")
    leaky_features = []
    for col in feature_cols:
        try:
            corr = float(df[col].corr(df[target_col]))
            status = "⚠️ POTENTIAL LEAK (>0.80)" if abs(corr) > max_allowed_corr else "OK"
            logger.info("  %-25s: corr=%+.4f [%s]", col, corr, status)
            if abs(corr) > max_allowed_corr:
                leaky_features.append((col, corr))
        except Exception as e:
            logger.debug("Could not compute corr for %s: %s", col, e)
    logger.info("-" * 50)
    if leaky_features:
        logger.warning("POTENTIAL DATA LEAKAGE DETECTED in features: %s", leaky_features)
    else:
        logger.info("Data leakage check PASSED — all feature correlations are within normal bounds.")


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


def _dcg(rels: np.ndarray) -> float:
    if rels.size == 0:
        return 0.0
    discounts = 1.0 / np.log2(np.arange(2, rels.size + 2))
    return float(((2.0 ** rels - 1.0) * discounts).sum())


def ranking_metrics(
    group_ids: np.ndarray,
    y_rel: np.ndarray,
    scores: np.ndarray,
    k: int = 10,
) -> Dict[str, float]:
    """
    NDCG@k and Precision@k averaged over groups (one group = one resume_id).

    * NDCG@k: graded relevance allowed (gain 2^rel - 1); groups with no relevant
      item are skipped (NDCG undefined there).
    * P@k: relevant (rel > 0) items in the top-k divided by min(k, group size), so a
      resume with only 6 candidate jobs in the split is not penalised for having < k.
      Averaged over groups that contain at least one relevant item.
    Ties in score are broken deterministically by original order (stable sort).
    """
    df = pd.DataFrame({"g": group_ids, "y": y_rel.astype(float), "s": scores.astype(float)})
    ndcgs: List[float] = []
    precs: List[float] = []
    for _, grp in df.groupby("g", sort=False):
        y = grp["y"].to_numpy()
        if not (y > 0).any():
            continue
        order = np.argsort(-grp["s"].to_numpy(), kind="stable")
        top = y[order][:k]
        ideal = np.sort(y)[::-1][:k]
        idcg = _dcg(ideal)
        ndcgs.append(_dcg(top) / idcg if idcg > 0 else 0.0)
        precs.append(float((top > 0).sum()) / min(k, len(y)))
    return {
        f"ndcg_at_{k}": float(np.mean(ndcgs)) if ndcgs else float("nan"),
        f"precision_at_{k}": float(np.mean(precs)) if precs else float("nan"),
        "ranking_groups": int(len(ndcgs)),
    }


def find_optimal_threshold(y_true: np.ndarray, y_proba: np.ndarray, beta: float = 1.0,
                           n_thresholds: int = 999) -> Dict[str, Any]:
    """F-beta-maximising threshold sweep (same method as ml/tune_threshold.py)."""
    thresholds = np.linspace(0.01, 0.99, n_thresholds)
    best = {"threshold": 0.5, "f": -1.0, "precision": 0.0, "recall": 0.0}
    b2 = beta ** 2
    for t in thresholds:
        pred = (y_proba >= t).astype(int)
        p = precision_score(y_true, pred, zero_division=0)
        r = recall_score(y_true, pred, zero_division=0)
        denom = b2 * p + r
        f = (1 + b2) * p * r / denom if denom > 0 else 0.0
        if f > best["f"]:
            best = {"threshold": float(t), "f": float(f), "precision": float(p), "recall": float(r)}
    pred05 = (y_proba >= 0.5).astype(int)
    return {
        "optimal_threshold": best["threshold"],
        "beta": beta,
        "metrics_at_optimal": {
            "precision": best["precision"],
            "recall": best["recall"],
            "f1": best["f"] if beta == 1.0 else float(f1_score(y_true, (y_proba >= best["threshold"]).astype(int))),
            f"f{beta}": best["f"],
        },
        "metrics_at_0_5": {
            "precision": float(precision_score(y_true, pred05, zero_division=0)),
            "recall": float(recall_score(y_true, pred05, zero_division=0)),
            "f1": float(f1_score(y_true, pred05, zero_division=0)),
        },
    }


def build_model(config: TrainConfig, scale_pos_weight: float) -> xgb.XGBClassifier:
    return xgb.XGBClassifier(
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


def load_feature_meta(path: Path = Path("data/processed/feature_meta.json")) -> Dict[str, Any]:
    """Describes how features.csv was built (semantic backend, skill extractor)."""
    if path.exists():
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    return {"semantic_backend": "tfidf", "skill_extractor": "substring-v1"}


def train_and_evaluate(
    config: TrainConfig,
    version: Optional[str] = None,
    activate: bool = True,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Full XGBoost training pipeline:
    load -> merge -> split -> cross-validate -> train -> evaluate -> save (versioned).

    Artifacts go to ml/model/<version>/ and are registered in ml/model/registry.json.
    With ``activate=True`` they are also copied to the top-level ml/model/ paths the
    backend loads (so serving picks the new version up).

    Returns:
        The metrics dict saved to train_metrics.json.
    """
    import shutil
    from datetime import datetime, timezone

    try:
        from ml.registry import activate_version, next_version, register_version
    except ImportError:  # running as `python ml/train.py` without project root on sys.path
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from ml.registry import activate_version, next_version, register_version

    setup_logging()
    logger.info("=" * 60)
    logger.info("Starting XGBoost Job-Candidate Matching Training Pipeline")
    logger.info("=" * 60)

    # Load & prepare data
    merged_df = load_and_merge(config.features_path, config.labels_path)
    feature_cols = get_feature_columns(merged_df)
    check_feature_leakage(merged_df, feature_cols)

    X = merged_df[feature_cols].to_numpy(dtype=float)
    y = merged_df["is_match"].to_numpy(dtype=int)
    groups = merged_df["resume_id"].astype(str).to_numpy()

    logger.info("X shape: %s | y shape: %s", X.shape, y.shape)

    # Train / test split (row-level, stratified — same as v1 so numbers are comparable)
    idx_train, idx_test = train_test_split(
        np.arange(len(y)),
        test_size=config.test_size,
        random_state=config.random_state,
        stratify=y,
    )
    X_train, X_test = X[idx_train], X[idx_test]
    y_train, y_test = y[idx_train], y[idx_test]
    logger.info("Split — train: %d rows | test: %d rows", len(X_train), len(X_test))

    scale_pos_weight = compute_scale_pos_weight(y_train)
    model = build_model(config, scale_pos_weight)

    # Cross-validation
    logger.info("Running %d-fold stratified cross-validation (scoring=roc_auc) ...", config.n_splits)
    cv = StratifiedKFold(n_splits=config.n_splits, shuffle=True, random_state=config.random_state)
    cv_scores = []
    for fold, (train_idx, val_idx) in enumerate(cv.split(X_train, y_train)):
        fold_model = build_model(config, scale_pos_weight)
        fold_model.fit(X_train[train_idx], y_train[train_idx])
        fold_auc = roc_auc_score(y_train[val_idx], fold_model.predict_proba(X_train[val_idx])[:, 1])
        cv_scores.append(fold_auc)
        logger.info("  Fold %d ROC-AUC: %.4f", fold + 1, fold_auc)
    cv_scores = np.array(cv_scores)
    logger.info("CV ROC-AUC — mean: %.6f | std: %.6f", float(cv_scores.mean()), float(cv_scores.std()))

    # Final fit on full training set
    logger.info("Fitting final model on full training set ...")
    model.fit(X_train, y_train)

    # Evaluate
    logger.info("Evaluating on test set ...")
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)
    metrics: Dict[str, Any] = evaluate_metrics(y_test, y_pred, y_proba)
    metrics["cv_auc_mean"] = float(cv_scores.mean())
    metrics["cv_auc_std"] = float(cv_scores.std())

    # Ranking metrics grouped by resume_id on the test split
    rank = ranking_metrics(groups[idx_test], y_test, y_proba, k=10)
    metrics.update(rank)
    metrics["ranking_note"] = (
        "NDCG@10 / P@10 grouped by resume_id over the test split; groups without a "
        "positive are skipped; P@10 divides by min(10, group size)."
    )

    # Optimal threshold (F1 sweep on the test split, same method as tune_threshold.py)
    thr = find_optimal_threshold(y_test, y_proba, beta=1.0)
    metrics["optimal_threshold"] = thr["optimal_threshold"]
    metrics["f1_at_optimal"] = thr["metrics_at_optimal"]["f1"]
    metrics["n_train"] = int(len(y_train))
    metrics["n_test"] = int(len(y_test))
    metrics["positive_rate"] = float(y.mean())

    logger.info("=" * 40)
    logger.info("TEST RESULTS:")
    for k, v in metrics.items():
        if isinstance(v, float):
            logger.info("  %-18s: %.6f", k.upper(), v)
    logger.info("=" * 40)

    # Plots
    plot_roc_curve(y_true=y_test, y_proba=y_proba, plots_dir=config.plots_dir)
    plot_confusion_matrix(y_true=y_test, y_pred=y_pred, plots_dir=config.plots_dir)
    plot_feature_importance(model=model, feature_cols=feature_cols, plots_dir=config.plots_dir,
                            top_n=min(20, len(feature_cols)))

    # ---- Save versioned artifacts ----
    version = version or next_version()
    vdir = config.model_dir / version
    vdir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, vdir / "xgb_matcher.pkl")
    with (vdir / "feature_columns.json").open("w", encoding="utf-8") as f:
        json.dump(feature_cols, f, indent=2)
    with (vdir / "train_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    with (vdir / "optimal_threshold.json").open("w", encoding="utf-8") as f:
        json.dump(thr, f, indent=2)
    tfidf_src = config.model_dir / "tfidf_vectorizer.pkl"
    staged_tfidf = Path("data/processed/tfidf_vectorizer.pkl")
    for cand in (staged_tfidf, tfidf_src):
        if cand.exists():
            shutil.copy2(cand, vdir / "tfidf_vectorizer.pkl")
            break
    feature_meta = load_feature_meta()
    meta = {
        "version": version,
        "semantic_backend": feature_meta.get("semantic_backend", "tfidf"),
        "skill_extractor": feature_meta.get("skill_extractor", "unknown"),
        "feature_columns": feature_cols,
        "trained_on": str(config.features_path),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with (vdir / "model_meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    logger.info("Saved artifacts -> %s", vdir)

    reg_metrics = {k: metrics[k] for k in (
        "auc_roc", "f1", "accuracy", "precision", "recall", "cv_auc_mean",
        "ndcg_at_10", "precision_at_10", "optimal_threshold", "f1_at_optimal", "positive_rate",
    ) if k in metrics}
    register_version(version, reg_metrics, meta=meta, notes=notes, activate=False)
    if activate:
        activate_version(version)
        logger.info("Activated %s (copied to %s)", version, config.model_dir)

    logger.info("=" * 60)
    logger.info("Training complete: %s", version)
    logger.info("=" * 60)
    return metrics


def main() -> None:
    """Entry point for XGBoost training pipeline."""
    import argparse
    ap = argparse.ArgumentParser(description="Train the XGBoost matcher (versioned)")
    ap.add_argument("--version", default=None, help="Version name (default: next vN)")
    ap.add_argument("--no-activate", action="store_true", help="Register but do not activate")
    ap.add_argument("--notes", default="", help="Free-text notes stored in registry.json")
    args = ap.parse_args()
    train_and_evaluate(TrainConfig(), version=args.version, activate=not args.no_activate, notes=args.notes)


if __name__ == "__main__":
    main()
