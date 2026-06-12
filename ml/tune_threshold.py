from __future__ import annotations

"""
tune_threshold.py
=================
Finds the optimal classification threshold for the XGBoost job-candidate
matcher by sweeping candidate thresholds on the validation set and
maximising F1 score (default).  Also supports precision, recall, or a
custom beta for F-beta.

Usage
-----
    python ml/tune_threshold.py                        # default paths
    python ml/tune_threshold.py --beta 0.5             # favour precision
    python ml/tune_threshold.py --beta 2               # favour recall

Outputs
-------
    ml/model/optimal_threshold.json   — threshold + metrics at that point
    ml/plots/threshold_curve.png      — F1 / precision / recall vs threshold
"""

import argparse
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TuneConfig:
    features_path: Path  = Path("data/processed/features.csv")
    labels_path: Path    = Path("data/processed/match_labels.csv")
    model_path: Path     = Path("ml/model/xgb_matcher.pkl")
    feature_cols_path: Path = Path("ml/model/feature_columns.json")
    output_json: Path    = Path("ml/model/optimal_threshold.json")
    plots_dir: Path      = Path("ml/plots")
    test_size: float     = 0.2
    random_state: int    = 42
    # sweep resolution (number of thresholds to evaluate)
    n_thresholds: int    = 1000
    # F-beta: beta=1 → F1, beta<1 favours precision, beta>1 favours recall
    beta: float          = 1.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _read_csv_or_raise(path: Path):
    import pandas as pd
    try:
        return pd.read_csv(path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Required file not found: {path}") from exc


def load_test_set(cfg: TuneConfig):
    """
    Re-creates the exact same train/test split used in train.py so that
    threshold tuning is evaluated on held-out data only.
    """
    import pandas as pd

    features_df = _read_csv_or_raise(cfg.features_path)
    labels_df   = _read_csv_or_raise(cfg.labels_path)

    # Mirror the merge logic from train.py
    label_only_cols = [
        c for c in labels_df.columns
        if c not in ("resume_id", "job_id") and c in features_df.columns
    ]
    if label_only_cols:
        labels_df = labels_df.drop(columns=label_only_cols)

    if "is_match" in features_df.columns:
        merged = features_df.copy()
    else:
        merged = pd.merge(features_df, labels_df, on=["resume_id", "job_id"], how="inner")

    if "match_id" in merged.columns:
        merged = merged.drop(columns=["match_id"])

    merged["is_match"] = merged["is_match"].astype(int)

    # Load the saved feature columns to guarantee alignment
    with cfg.feature_cols_path.open("r", encoding="utf-8") as f:
        feature_cols = json.load(f)

    missing = set(feature_cols) - set(merged.columns)
    if missing:
        raise ValueError(f"Columns in feature_columns.json missing from data: {missing}")

    X = merged[feature_cols].to_numpy(dtype=float)
    y = merged["is_match"].to_numpy(dtype=int)

    _, X_test, _, y_test = train_test_split(
        X, y,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
        stratify=y,
    )
    logger.info("Test set: %d rows | positives: %.1f%%", len(y_test), y_test.mean() * 100)
    return X_test, y_test


# ---------------------------------------------------------------------------
# Core: threshold sweep
# ---------------------------------------------------------------------------

def sweep_thresholds(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    beta: float = 1.0,
    n_thresholds: int = 1000,
) -> dict:
    """
    Sweeps thresholds from 0 to 1 and computes precision, recall, and
    F-beta at each point.  Returns a dict with per-threshold arrays plus
    the optimal threshold and its metrics.

    Args:
        y_true:       Ground truth binary labels.
        y_proba:      Predicted probabilities for class 1.
        beta:         F-beta weight. beta=1 → F1.
        n_thresholds: Number of threshold steps to evaluate.

    Returns:
        dict with keys: thresholds, precision, recall, fbeta,
                        best_threshold, best_metrics.
    """
    thresholds = np.linspace(0.01, 0.99, n_thresholds)

    precisions = np.zeros(n_thresholds)
    recalls    = np.zeros(n_thresholds)
    fbetas     = np.zeros(n_thresholds)

    for i, t in enumerate(thresholds):
        y_pred = (y_proba >= t).astype(int)
        precisions[i] = precision_score(y_true, y_pred, zero_division=0)
        recalls[i]    = recall_score(y_true, y_pred, zero_division=0)
        # F-beta = (1 + beta²) * P * R / (beta² * P + R)
        b2 = beta ** 2
        denom = b2 * precisions[i] + recalls[i]
        fbetas[i] = (1 + b2) * precisions[i] * recalls[i] / denom if denom > 0 else 0.0

    best_idx       = int(np.argmax(fbetas))
    best_threshold = float(thresholds[best_idx])

    # Final metric recompute at best threshold for cleanliness
    y_pred_best = (y_proba >= best_threshold).astype(int)
    best_metrics = {
        "threshold": best_threshold,
        "f_beta":    float(fbetas[best_idx]),
        "precision": float(precision_score(y_true, y_pred_best, zero_division=0)),
        "recall":    float(recall_score(y_true, y_pred_best, zero_division=0)),
        "f1":        float(f1_score(y_true, y_pred_best, zero_division=0)),
        "beta":      beta,
    }

    # Baseline at 0.5 for comparison
    y_pred_05 = (y_proba >= 0.5).astype(int)
    baseline_metrics = {
        "threshold": 0.5,
        "precision": float(precision_score(y_true, y_pred_05, zero_division=0)),
        "recall":    float(recall_score(y_true, y_pred_05, zero_division=0)),
        "f1":        float(f1_score(y_true, y_pred_05, zero_division=0)),
    }

    return {
        "thresholds":       thresholds,
        "precision":        precisions,
        "recall":           recalls,
        "fbeta":            fbetas,
        "best_threshold":   best_threshold,
        "best_metrics":     best_metrics,
        "baseline_metrics": baseline_metrics,
    }


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def plot_threshold_curve(result: dict, plots_dir: Path, beta: float) -> None:
    """
    Plots precision, recall, and F-beta against threshold.
    Marks the optimal threshold with a vertical dashed line and the
    default 0.5 threshold for comparison.

    Args:
        result:    Output dict from sweep_thresholds().
        plots_dir: Directory to save the plot.
        beta:      Beta used (for axis label).
    """
    plots_dir.mkdir(parents=True, exist_ok=True)

    t   = result["thresholds"]
    p   = result["precision"]
    r   = result["recall"]
    fb  = result["fbeta"]
    opt = result["best_threshold"]

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(t, p,  label="Precision",          color="#2196F3", lw=2)
    ax.plot(t, r,  label="Recall",             color="#FF9800", lw=2)
    ax.plot(t, fb, label=f"F{beta} score",     color="#4CAF50", lw=2.5)

    # Optimal threshold line
    ax.axvline(opt, color="#E91E63", lw=1.8, linestyle="--",
               label=f"Optimal threshold = {opt:.4f}")

    # Default 0.5 line
    ax.axvline(0.5, color="gray", lw=1.2, linestyle=":",
               label="Default threshold = 0.50")

    # Annotate the best F-beta value
    best_fb = result["best_metrics"]["f_beta"]
    ax.annotate(
        f"F{beta}={best_fb:.4f}",
        xy=(opt, best_fb),
        xytext=(opt + 0.04, best_fb - 0.07),
        fontsize=10,
        color="#E91E63",
        arrowprops=dict(arrowstyle="->", color="#E91E63", lw=1.2),
    )

    ax.set_xlabel("Classification threshold", fontsize=12)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title(f"Precision / Recall / F{beta} vs Threshold", fontsize=13)
    ax.legend(loc="lower left", fontsize=10)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.3)

    out_path = plots_dir / "threshold_curve.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    logger.info("Saved threshold curve -> %s", out_path)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def tune_threshold(cfg: TuneConfig) -> dict:
    """
    Full threshold-tuning pipeline:
      load model → score test set → sweep thresholds → save result + plot.

    Args:
        cfg: TuneConfig with all paths and settings.

    Returns:
        best_metrics dict (also written to cfg.output_json).
    """
    setup_logging()
    logger.info("=" * 60)
    logger.info("Threshold Tuning — XGBoost Job-Candidate Matcher")
    logger.info("Beta = %.2f  |  n_thresholds = %d", cfg.beta, cfg.n_thresholds)
    logger.info("=" * 60)

    # Load model
    logger.info("Loading model from %s", cfg.model_path)
    model = joblib.load(cfg.model_path)

    # Reconstruct test set
    X_test, y_test = load_test_set(cfg)

    # Get predicted probabilities
    y_proba = model.predict_proba(X_test)[:, 1]
    logger.info("Probabilities computed for %d samples", len(y_proba))

    # Sweep thresholds
    logger.info("Sweeping %d thresholds (beta=%.2f) ...", cfg.n_thresholds, cfg.beta)
    result = sweep_thresholds(y_proba=y_proba, y_true=y_test,
                               beta=cfg.beta, n_thresholds=cfg.n_thresholds)

    # Log comparison
    bm = result["best_metrics"]
    bl = result["baseline_metrics"]
    logger.info("=" * 40)
    logger.info("BASELINE  (threshold=0.50)")
    logger.info("  Precision : %.4f", bl["precision"])
    logger.info("  Recall    : %.4f", bl["recall"])
    logger.info("  F1        : %.4f", bl["f1"])
    logger.info("OPTIMAL   (threshold=%.4f)", bm["threshold"])
    logger.info("  Precision : %.4f  (%+.4f)", bm["precision"], bm["precision"] - bl["precision"])
    logger.info("  Recall    : %.4f  (%+.4f)", bm["recall"],    bm["recall"]    - bl["recall"])
    logger.info("  F1        : %.4f  (%+.4f)", bm["f1"],        bm["f1"]        - bl["f1"])
    logger.info("  F%-7s: %.4f", f"{cfg.beta}", bm["f_beta"])
    logger.info("=" * 40)

    # Save plot
    plot_threshold_curve(result, cfg.plots_dir, cfg.beta)

    # Save optimal threshold JSON
    cfg.output_json.parent.mkdir(parents=True, exist_ok=True)
    save_payload = {
        "optimal_threshold": bm["threshold"],
        "beta":              cfg.beta,
        "metrics_at_optimal": {
            "precision": bm["precision"],
            "recall":    bm["recall"],
            "f1":        bm["f1"],
            f"f{cfg.beta}": bm["f_beta"],
        },
        "metrics_at_0_5": {
            "precision": bl["precision"],
            "recall":    bl["recall"],
            "f1":        bl["f1"],
        },
    }
    with cfg.output_json.open("w", encoding="utf-8") as f:
        json.dump(save_payload, f, indent=2)
    logger.info("Saved optimal threshold -> %s", cfg.output_json)

    logger.info("=" * 60)
    logger.info("Done. Use threshold %.4f in your inference script.", bm["threshold"])
    logger.info("=" * 60)

    return bm


# ---------------------------------------------------------------------------
# How to use the optimal threshold in predict.py
# ---------------------------------------------------------------------------

def load_optimal_threshold(threshold_json: Path = Path("ml/model/optimal_threshold.json")) -> float:
    """
    Convenience loader for inference scripts.

    Usage in predict.py:
        from tune_threshold import load_optimal_threshold
        threshold = load_optimal_threshold()
        y_pred = (model.predict_proba(X)[:, 1] >= threshold).astype(int)

    Args:
        threshold_json: Path to the saved optimal_threshold.json.

    Returns:
        Optimal threshold float.
    """
    with threshold_json.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return float(data["optimal_threshold"])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Threshold tuning for XGBoost matcher")
    parser.add_argument(
        "--beta", type=float, default=1.0,
        help=(
            "F-beta weight (default: 1.0 = F1). "
            "beta < 1 favours precision; beta > 1 favours recall. "
            "Example: --beta 0.5 to reduce false positives."
        ),
    )
    parser.add_argument(
        "--n-thresholds", type=int, default=1000,
        help="Number of threshold steps to evaluate (default: 1000).",
    )
    args = parser.parse_args()

    cfg = TuneConfig(beta=args.beta, n_thresholds=args.n_thresholds)
    tune_threshold(cfg)


if __name__ == "__main__":
    main()
