from __future__ import annotations

"""
explain.py
==========
SHAP explainability for the XGBoost job-candidate matcher.

Two modes
---------
1. Global  — beeswarm + bar summary plots over the full test set.
2. Per-pair — waterfall plot + console summary for a single resume/job pair.

Usage
-----
    # Global summary (beeswarm + bar)
    python ml/explain.py

    # Explain a specific row by its index in features.csv
    python ml/explain.py --row 42

    # Explain with a custom threshold loaded from optimal_threshold.json
    python ml/explain.py --row 42 --use-optimal-threshold

Outputs
-------
    ml/plots/shap_beeswarm.png          — global feature impact (beeswarm)
    ml/plots/shap_bar.png               — global mean |SHAP| bar chart
    ml/plots/shap_waterfall_row{N}.png  — per-pair waterfall (when --row used)
"""

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExplainConfig:
    features_path: Path     = Path("data/processed/features.csv")
    labels_path: Path       = Path("data/processed/match_labels.csv")
    model_path: Path        = Path("ml/model/xgb_matcher.pkl")
    feature_cols_path: Path = Path("ml/model/feature_columns.json")
    threshold_path: Path    = Path("ml/model/optimal_threshold.json")
    plots_dir: Path         = Path("ml/plots")
    test_size: float        = 0.2
    random_state: int       = 42
    # Max samples to run SHAP on globally (keeps runtime under ~10 s)
    max_global_samples: int = 2000


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _read_csv_or_raise(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Required file not found: {path}") from exc


def load_merged(cfg: ExplainConfig) -> pd.DataFrame:
    """
    Mirrors the merge logic from train.py so the row indices stay consistent.
    Returns the full merged DataFrame (all rows, not just test split).
    """
    features_df = _read_csv_or_raise(cfg.features_path)
    labels_df   = _read_csv_or_raise(cfg.labels_path)

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
    return merged


def load_feature_cols(cfg: ExplainConfig) -> list[str]:
    with cfg.feature_cols_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_optimal_threshold(cfg: ExplainConfig) -> float:
    with cfg.threshold_path.open("r", encoding="utf-8") as f:
        return float(json.load(f)["optimal_threshold"])


def get_test_split(cfg: ExplainConfig) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """
    Returns (X_test_df, y_test, original_indices) using the same split as train.py.
    original_indices lets you map a test-set row back to its position in features.csv.
    """
    from sklearn.model_selection import train_test_split

    merged = load_merged(cfg)
    feature_cols = load_feature_cols(cfg)

    X = merged[feature_cols]
    y = merged["is_match"].to_numpy(dtype=int)

    idx = np.arange(len(merged))
    _, X_test, _, y_test, _, orig_idx = train_test_split(
        X, y, idx,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
        stratify=y,
    )
    return X_test, y_test, orig_idx


# ---------------------------------------------------------------------------
# SHAP computation
# ---------------------------------------------------------------------------

def compute_shap_values(
    model,
    X: pd.DataFrame,
    max_samples: int = 2000,
) -> shap.Explanation:
    """
    Computes SHAP values using the fast TreeExplainer.

    Args:
        model:       Trained XGBClassifier.
        X:           Feature DataFrame (column names preserved for plots).
        max_samples: Subsample size for global analysis. Set to None for full data.

    Returns:
        shap.Explanation for class 1 (match probability).
    """
    if max_samples and len(X) > max_samples:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(X), size=max_samples, replace=False)
        X_sample = X.iloc[idx]
        logger.info("Subsampled to %d rows for SHAP computation", max_samples)
    else:
        X_sample = X

    logger.info("Computing SHAP values (TreeExplainer) ...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_sample)

    # shap_values has shape (n_samples, n_features, n_classes) for classifiers.
    # Slice class 1 (match) to get a 2D Explanation object.
    if shap_values.values.ndim == 3:
        sv = shap.Explanation(
            values       = shap_values.values[:, :, 1],
            base_values  = shap_values.base_values[:, 1],
            data         = shap_values.data,
            feature_names= shap_values.feature_names,
        )
    else:
        sv = shap_values

    logger.info("SHAP values computed — shape: %s", sv.values.shape)
    return sv


# ---------------------------------------------------------------------------
# Global plots
# ---------------------------------------------------------------------------

def plot_beeswarm(shap_exp: shap.Explanation, plots_dir: Path) -> None:
    """
    Saves a beeswarm plot: each dot is one sample, position = SHAP value,
    colour = feature value (high=red, low=blue).

    Args:
        shap_exp:  SHAP Explanation for class 1.
        plots_dir: Output directory.
    """
    plots_dir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 6))
    shap.plots.beeswarm(shap_exp, show=False, max_display=10)
    plt.title("SHAP beeswarm — feature impact on match probability", fontsize=13, pad=12)
    plt.tight_layout()
    out = plots_dir / "shap_beeswarm.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    logger.info("Saved beeswarm -> %s", out)


def plot_bar(shap_exp: shap.Explanation, plots_dir: Path) -> None:
    """
    Saves a bar chart of mean |SHAP| values — global feature importance.

    Args:
        shap_exp:  SHAP Explanation for class 1.
        plots_dir: Output directory.
    """
    plots_dir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    shap.plots.bar(shap_exp, show=False, max_display=10)
    plt.title("Mean |SHAP| — global feature importance", fontsize=13, pad=12)
    plt.tight_layout()
    out = plots_dir / "shap_bar.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    logger.info("Saved bar chart -> %s", out)


# ---------------------------------------------------------------------------
# Per-prediction explanation
# ---------------------------------------------------------------------------

def explain_single_prediction(
    model,
    row: pd.Series,
    y_true: int | None,
    threshold: float,
    plots_dir: Path,
    row_index: int,
) -> dict:
    """
    Explains a single resume/job pair:
      - Waterfall plot saved to disk.
      - Structured dict returned (and logged) for console inspection.

    Args:
        model:      Trained XGBClassifier.
        row:        Feature values for the single pair (pd.Series).
        y_true:     Ground truth label (None if unknown).
        threshold:  Classification threshold.
        plots_dir:  Output directory for the waterfall plot.
        row_index:  Row number (used in filename and logging).

    Returns:
        Dict with prediction, probability, threshold, verdict, and
        per-feature SHAP contributions sorted by absolute impact.
    """
    X_single = row.to_frame().T.reset_index(drop=True)

    explainer  = shap.TreeExplainer(model)
    shap_vals  = explainer(X_single)

    # Slice class 1
    if shap_vals.values.ndim == 3:
        sv_single = shap.Explanation(
            values       = shap_vals.values[:, :, 1],
            base_values  = shap_vals.base_values[:, 1],
            data         = shap_vals.data,
            feature_names= shap_vals.feature_names,
        )
    else:
        sv_single = shap_vals

    # Waterfall plot
    plots_dir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(9, 5))
    shap.plots.waterfall(sv_single[0], show=False)
    plt.title(f"SHAP waterfall — row {row_index}", fontsize=13, pad=12)
    plt.tight_layout()
    out = plots_dir / f"shap_waterfall_row{row_index}.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    logger.info("Saved waterfall -> %s", out)

    # Probability and verdict
    proba     = float(model.predict_proba(X_single)[0, 1])
    predicted = int(proba >= threshold)
    verdict   = "MATCH" if predicted == 1 else "NO MATCH"

    # Per-feature contributions
    feature_names = list(sv_single.feature_names)
    shap_contribs = sv_single.values[0]
    feature_values = sv_single.data[0]

    contributions = sorted(
        [
            {
                "feature":    name,
                "value":      float(feature_values[i]),
                "shap":       float(shap_contribs[i]),
                "direction":  "↑ match" if shap_contribs[i] > 0 else "↓ match",
            }
            for i, name in enumerate(feature_names)
        ],
        key=lambda x: abs(x["shap"]),
        reverse=True,
    )

    result = {
        "row_index":    row_index,
        "probability":  round(proba, 4),
        "threshold":    threshold,
        "predicted":    predicted,
        "verdict":      verdict,
        "ground_truth": y_true,
        "correct":      (predicted == y_true) if y_true is not None else None,
        "base_value":   round(float(sv_single.base_values[0]), 4),
        "contributions": contributions,
    }

    # Pretty console output
    logger.info("=" * 52)
    logger.info("PREDICTION EXPLANATION — row %d", row_index)
    logger.info("  Probability : %.4f  (threshold: %.4f)", proba, threshold)
    logger.info("  Verdict     : %s", verdict)
    if y_true is not None:
        logger.info("  Ground truth: %s  |  Correct: %s",
                    "MATCH" if y_true else "NO MATCH",
                    "YES" if result["correct"] else "NO")
    logger.info("  Base value  : %.4f  (avg model output)", result["base_value"])
    logger.info("-" * 52)
    logger.info("  %-28s  %8s  %8s", "Feature", "Value", "SHAP")
    logger.info("  %-28s  %8s  %8s", "-" * 28, "-" * 8, "-" * 8)
    for c in contributions:
        logger.info("  %-28s  %8.3f  %+8.4f  %s",
                    c["feature"], c["value"], c["shap"], c["direction"])
    logger.info("=" * 52)

    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_global(cfg: ExplainConfig) -> None:
    """Compute and save global SHAP summary plots over the test set."""
    logger.info("=" * 60)
    logger.info("SHAP Global Explainability")
    logger.info("=" * 60)

    model        = joblib.load(cfg.model_path)
    X_test, _, _ = get_test_split(cfg)

    shap_exp = compute_shap_values(model, X_test, max_samples=cfg.max_global_samples)
    plot_beeswarm(shap_exp, cfg.plots_dir)
    plot_bar(shap_exp, cfg.plots_dir)

    logger.info("Global SHAP done. Plots saved to %s", cfg.plots_dir)


def run_single(cfg: ExplainConfig, row_index: int, use_optimal_threshold: bool) -> dict:
    """
    Explain a single row from features.csv by its 0-based index.

    Args:
        cfg:                    ExplainConfig.
        row_index:              0-based index into the full features.csv.
        use_optimal_threshold:  If True, load from optimal_threshold.json; else 0.5.

    Returns:
        Explanation dict from explain_single_prediction().
    """
    logger.info("=" * 60)
    logger.info("SHAP Per-Prediction Explanation — row %d", row_index)
    logger.info("=" * 60)

    model        = joblib.load(cfg.model_path)
    feature_cols = load_feature_cols(cfg)
    merged       = load_merged(cfg)

    if row_index >= len(merged):
        raise IndexError(
            f"row_index {row_index} is out of range "
            f"(features.csv has {len(merged)} rows)."
        )

    row    = merged[feature_cols].iloc[row_index]
    y_true = int(merged["is_match"].iloc[row_index])

    threshold = load_optimal_threshold(cfg) if use_optimal_threshold else 0.5
    logger.info("Using threshold: %.4f", threshold)

    return explain_single_prediction(
        model=model,
        row=row,
        y_true=y_true,
        threshold=threshold,
        plots_dir=cfg.plots_dir,
        row_index=row_index,
    )


# ---------------------------------------------------------------------------
# Reusable helper for predict.py / API integration
# ---------------------------------------------------------------------------

def explain_pair(
    model,
    feature_values: dict,
    feature_cols: list[str],
    threshold: float = 0.5,
    plots_dir: Path | None = None,
    label: str = "pair",
) -> dict:
    """
    Explain any single resume/job pair given raw feature values as a dict.
    Designed for import from predict.py or an API endpoint — no CSV needed.

    Args:
        model:          Trained XGBClassifier (already loaded).
        feature_values: Dict mapping feature name -> value.
                        Must contain all keys in feature_cols.
        feature_cols:   Ordered list of feature column names.
        threshold:      Classification threshold (default 0.5).
        plots_dir:      If provided, saves a waterfall plot here.
        label:          String used in the waterfall plot filename.

    Returns:
        Same structured dict as explain_single_prediction().

    Example
    -------
        from explain import explain_pair
        import joblib, json

        model = joblib.load("ml/model/xgb_matcher.pkl")
        with open("ml/model/feature_columns.json") as f:
            feature_cols = json.load(f)

        result = explain_pair(
            model=model,
            feature_values={
                "skill_overlap_count":  4,
                "skill_overlap_ratio":  0.57,
                "experience_gap":      -1,
                "education_score":      2,
                "location_match":       1,
                "skills_count_resume":  7,
            },
            feature_cols=feature_cols,
            threshold=0.7232,
        )
        print(result["verdict"], result["probability"])
        for c in result["contributions"]:
            print(f"  {c['feature']:30s}  {c['shap']:+.4f}  {c['direction']}")
    """
    import pandas as pd

    row = pd.Series({col: feature_values[col] for col in feature_cols})

    return explain_single_prediction(
        model=model,
        row=row,
        y_true=None,
        threshold=threshold,
        plots_dir=plots_dir or Path("ml/plots"),
        row_index=0,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(
        description="SHAP explainability for XGBoost job-candidate matcher"
    )
    parser.add_argument(
        "--row", type=int, default=None,
        help="0-based row index in features.csv to explain. "
             "Omit for global summary plots only.",
    )
    parser.add_argument(
        "--use-optimal-threshold", action="store_true",
        help="Use threshold from optimal_threshold.json instead of 0.5.",
    )
    parser.add_argument(
        "--global-only", action="store_true",
        help="Run global plots only, even if --row is also given.",
    )
    args = parser.parse_args()

    cfg = ExplainConfig()

    if args.global_only or args.row is None:
        run_global(cfg)

    if args.row is not None and not args.global_only:
        run_global(cfg)
        run_single(cfg, row_index=args.row, use_optimal_threshold=args.use_optimal_threshold)


if __name__ == "__main__":
    main()
