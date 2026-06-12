from __future__ import annotations

"""
predict.py
==========
Inference script for the XGBoost job-candidate matcher.

Three calling modes
-------------------
1. Single pair  — score one resume against one job interactively.
2. Batch CSV    — score every row in a CSV file, write results CSV.
3. Imported     — call score_pair() or score_batch() from another module
                  (FastAPI, Celery worker, Jupyter, etc.).

Usage
-----
    # Score a single pair (prompted interactively)
    python ml/predict.py --mode single

    # Score a CSV of pairs
    python ml/predict.py --mode batch --input data/sample/sample_features.csv

    # Score a CSV and save results to a custom path
    python ml/predict.py --mode batch --input pairs.csv --output results.csv

    # Use optimal threshold from tune_threshold.py instead of 0.5
    python ml/predict.py --mode batch --input pairs.csv --use-optimal-threshold

    # Also emit per-prediction SHAP explanations alongside scores
    python ml/predict.py --mode batch --input pairs.csv --explain

Outputs (batch mode)
--------------------
    <input_stem>_predictions.csv   — original columns + match_probability,
                                     predicted_match, verdict, confidence
    ml/plots/shap_waterfall_*.png  — one waterfall per row (if --explain)
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PredictConfig:
    model_path: Path        = Path("ml/model/xgb_matcher.pkl")
    feature_cols_path: Path = Path("ml/model/feature_columns.json")
    threshold_path: Path    = Path("ml/model/optimal_threshold.json")
    plots_dir: Path         = Path("ml/plots")
    default_threshold: float = 0.5


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


# ---------------------------------------------------------------------------
# Model + config loading
# ---------------------------------------------------------------------------

def load_model(cfg: PredictConfig):
    """Load the trained XGBClassifier from disk."""
    logger.info("Loading model from %s", cfg.model_path)
    return joblib.load(cfg.model_path)


def load_feature_cols(cfg: PredictConfig) -> list[str]:
    """Load the ordered feature column list saved during training."""
    with cfg.feature_cols_path.open("r", encoding="utf-8") as f:
        cols = json.load(f)
    logger.info("Feature columns (%d): %s", len(cols), cols)
    return cols


def load_threshold(cfg: PredictConfig, use_optimal: bool) -> float:
    """
    Return the classification threshold to use.

    Args:
        cfg:         PredictConfig.
        use_optimal: If True, load from optimal_threshold.json; else use default.

    Returns:
        Threshold float.
    """
    if use_optimal:
        if not cfg.threshold_path.exists():
            logger.warning(
                "optimal_threshold.json not found at %s — falling back to %.1f. "
                "Run ml/tune_threshold.py first to generate it.",
                cfg.threshold_path, cfg.default_threshold,
            )
            return cfg.default_threshold
        with cfg.threshold_path.open("r", encoding="utf-8") as f:
            t = float(json.load(f)["optimal_threshold"])
        logger.info("Using optimal threshold: %.4f", t)
        return t
    logger.info("Using default threshold: %.1f", cfg.default_threshold)
    return cfg.default_threshold


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_input(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """
    Checks that all required feature columns are present and numeric.
    Fills missing values with 0 and warns per column.

    Args:
        df:           Input DataFrame.
        feature_cols: Expected feature column names.

    Returns:
        DataFrame with all feature columns present and numeric.

    Raises:
        ValueError: If a required column is entirely absent.
    """
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"Input is missing required feature columns: {missing}\n"
            f"Expected: {feature_cols}\n"
            f"Got:      {df.columns.tolist()}"
        )

    for col in feature_cols:
        null_count = df[col].isna().sum()
        if null_count:
            logger.warning(
                "Column '%s' has %d null value(s) — filling with 0.", col, null_count
            )
            df[col] = df[col].fillna(0)

        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.warning(
                "Column '%s' is non-numeric (%s) — attempting cast to float.",
                col, df[col].dtype,
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


# ---------------------------------------------------------------------------
# Confidence band
# ---------------------------------------------------------------------------

def _confidence_label(prob: float, threshold: float) -> str:
    """
    Returns a human-readable confidence label based on distance from threshold.

    Bands (distance from threshold):
        ≥ 0.25  → High
        ≥ 0.10  → Medium
        < 0.10  → Low

    Args:
        prob:      Predicted probability for class 1.
        threshold: Classification threshold.

    Returns:
        One of 'High', 'Medium', 'Low'.
    """
    distance = abs(prob - threshold)
    if distance >= 0.25:
        return "High"
    elif distance >= 0.10:
        return "Medium"
    else:
        return "Low"


# ---------------------------------------------------------------------------
# Core scoring functions
# ---------------------------------------------------------------------------

def score_pair(
    feature_values: dict[str, Any],
    model=None,
    feature_cols: list[str] | None = None,
    threshold: float = 0.5,
    cfg: PredictConfig | None = None,
    explain: bool = False,
) -> dict:
    """
    Score a single resume/job pair.

    Args:
        feature_values: Dict mapping feature name -> value.
                        Must contain all keys in feature_cols.
        model:          Pre-loaded XGBClassifier. Loaded from disk if None.
        feature_cols:   Ordered feature column list. Loaded from disk if None.
        threshold:      Classification threshold.
        cfg:            PredictConfig (used only when loading from disk).
        explain:        If True, append SHAP contributions to the result.

    Returns:
        Dict with keys:
            match_probability  — float, model's confidence this is a match
            predicted_match    — int (0 or 1)
            verdict            — 'MATCH' or 'NO MATCH'
            confidence         — 'High', 'Medium', or 'Low'
            threshold_used     — float
            shap_contributions — list of dicts (only if explain=True)

    Example
    -------
        result = score_pair(
            feature_values={
                "skill_overlap_count":  4,
                "skill_overlap_ratio":  0.57,
                "experience_gap":      -1,
                "education_score":      2,
                "location_match":       1,
                "skills_count_resume":  7,
            },
            threshold=0.7232,
        )
        print(result["verdict"], result["match_probability"])
    """
    cfg = cfg or PredictConfig()
    if model is None:
        model = load_model(cfg)
    if feature_cols is None:
        feature_cols = load_feature_cols(cfg)

    row = pd.DataFrame([{col: feature_values[col] for col in feature_cols}])
    row = validate_input(row, feature_cols)

    X = row[feature_cols].to_numpy(dtype=float)
    prob      = float(model.predict_proba(X)[0, 1])
    predicted = int(prob >= threshold)

    result = {
        "match_probability": round(prob, 4),
        "predicted_match":   predicted,
        "verdict":           "MATCH" if predicted else "NO MATCH",
        "confidence":        _confidence_label(prob, threshold),
        "threshold_used":    threshold,
    }

    if explain:
        try:
            from explain import explain_pair
            shap_result = explain_pair(
                model=model,
                feature_values=feature_values,
                feature_cols=feature_cols,
                threshold=threshold,
            )
            result["shap_contributions"] = shap_result["contributions"]
        except ImportError:
            logger.warning("explain.py not found — skipping SHAP. Place it in ml/.")

    return result


def score_batch(
    df: pd.DataFrame,
    model=None,
    feature_cols: list[str] | None = None,
    threshold: float = 0.5,
    cfg: PredictConfig | None = None,
    explain: bool = False,
) -> pd.DataFrame:
    """
    Score a DataFrame of resume/job pairs.

    Args:
        df:           DataFrame with at least the feature columns.
                      Extra columns (resume_id, job_id, etc.) are preserved.
        model:        Pre-loaded XGBClassifier. Loaded from disk if None.
        feature_cols: Ordered feature column list. Loaded from disk if None.
        threshold:    Classification threshold.
        cfg:          PredictConfig (used when loading from disk).
        explain:      If True, run SHAP on every row and save waterfall plots.

    Returns:
        Input DataFrame with four new columns appended:
            match_probability, predicted_match, verdict, confidence
    """
    cfg = cfg or PredictConfig()
    if model is None:
        model = load_model(cfg)
    if feature_cols is None:
        feature_cols = load_feature_cols(cfg)

    df = df.copy()
    df = validate_input(df, feature_cols)

    logger.info("Scoring %d pairs ...", len(df))

    X       = df[feature_cols].to_numpy(dtype=float)
    probas  = model.predict_proba(X)[:, 1]
    preds   = (probas >= threshold).astype(int)

    df["match_probability"] = np.round(probas, 4)
    df["predicted_match"]   = preds
    df["verdict"]           = np.where(preds == 1, "MATCH", "NO MATCH")
    df["confidence"]        = [_confidence_label(p, threshold) for p in probas]

    n_match    = int(preds.sum())
    n_no_match = len(preds) - n_match
    logger.info(
        "Results — MATCH: %d (%.1f%%) | NO MATCH: %d (%.1f%%)",
        n_match,    n_match    / len(preds) * 100,
        n_no_match, n_no_match / len(preds) * 100,
    )

    # Confidence breakdown
    for band in ("High", "Medium", "Low"):
        count = int((df["confidence"] == band).sum())
        logger.info("  %-6s confidence: %d pairs", band, count)

    if explain:
        _run_batch_shap(model, df, feature_cols, threshold, cfg.plots_dir)

    return df


# ---------------------------------------------------------------------------
# Batch SHAP helper
# ---------------------------------------------------------------------------

def _run_batch_shap(model, df, feature_cols, threshold, plots_dir):
    """Run SHAP waterfall on every row in df and save plots."""
    try:
        from explain import explain_single_prediction
    except ImportError:
        logger.warning("explain.py not found — skipping SHAP. Place it in ml/.")
        return

    logger.info("Running SHAP on %d rows — this may take a moment ...", len(df))
    for i, (idx, row) in enumerate(df[feature_cols].iterrows()):
        explain_single_prediction(
            model=model,
            row=row,
            y_true=None,
            threshold=threshold,
            plots_dir=plots_dir,
            row_index=int(idx),
        )
    logger.info("SHAP waterfall plots saved to %s", plots_dir)


# ---------------------------------------------------------------------------
# Interactive single-pair mode
# ---------------------------------------------------------------------------

def _prompt_feature_values(feature_cols: list[str]) -> dict[str, float]:
    """
    Prompts the user to enter each feature value on the command line.

    Args:
        feature_cols: List of feature names to prompt for.

    Returns:
        Dict of feature name -> float value.
    """
    print("\nEnter feature values for the resume/job pair.")
    print("Press Enter to use 0 as the default.\n")
    values = {}
    for col in feature_cols:
        while True:
            raw = input(f"  {col}: ").strip()
            if raw == "":
                values[col] = 0.0
                break
            try:
                values[col] = float(raw)
                break
            except ValueError:
                print(f"    ✗ '{raw}' is not a number — try again.")
    return values


def run_single_interactive(cfg: PredictConfig, use_optimal: bool, explain: bool) -> None:
    """Interactive single-pair scoring loop."""
    model        = load_model(cfg)
    feature_cols = load_feature_cols(cfg)
    threshold    = load_threshold(cfg, use_optimal)

    while True:
        feature_values = _prompt_feature_values(feature_cols)
        result = score_pair(
            feature_values=feature_values,
            model=model,
            feature_cols=feature_cols,
            threshold=threshold,
            cfg=cfg,
            explain=explain,
        )

        print(f"\n{'=' * 44}")
        print(f"  Verdict     : {result['verdict']}")
        print(f"  Probability : {result['match_probability']:.4f}  "
              f"(threshold: {threshold:.4f})")
        print(f"  Confidence  : {result['confidence']}")

        if explain and "shap_contributions" in result:
            print(f"\n  {'Feature':<28}  {'Value':>7}  {'SHAP':>8}  Direction")
            print(f"  {'-'*28}  {'-'*7}  {'-'*8}  ---------")
            for c in result["shap_contributions"]:
                print(f"  {c['feature']:<28}  {c['value']:>7.3f}  "
                      f"{c['shap']:>+8.4f}  {c['direction']}")

        print(f"{'=' * 44}\n")

        again = input("Score another pair? [y/N]: ").strip().lower()
        if again != "y":
            break


# ---------------------------------------------------------------------------
# Batch CSV mode
# ---------------------------------------------------------------------------

def run_batch(
    cfg: PredictConfig,
    input_path: Path,
    output_path: Path | None,
    use_optimal: bool,
    explain: bool,
) -> None:
    """
    Load a CSV, score every row, save results.

    Args:
        cfg:         PredictConfig.
        input_path:  Path to input CSV.
        output_path: Path to write results CSV. Auto-generated if None.
        use_optimal: Use optimal threshold if True.
        explain:     Run SHAP on every row if True.
    """
    logger.info("Loading input: %s", input_path)
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    logger.info("Input shape: %s | columns: %s", df.shape, df.columns.tolist())

    model        = load_model(cfg)
    feature_cols = load_feature_cols(cfg)
    threshold    = load_threshold(cfg, use_optimal)

    results_df = score_batch(
        df=df,
        model=model,
        feature_cols=feature_cols,
        threshold=threshold,
        cfg=cfg,
        explain=explain,
    )

    # Determine output path
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_predictions.csv"

    results_df.to_csv(output_path, index=False)
    logger.info("Results saved -> %s", output_path)

    # Print a preview of top matches
    matches = results_df[results_df["predicted_match"] == 1].sort_values(
        "match_probability", ascending=False
    )
    if not matches.empty:
        preview_cols = ["match_probability", "verdict", "confidence"]
        id_cols = [c for c in ("resume_id", "job_id") if c in results_df.columns]
        preview_cols = id_cols + preview_cols

        print(f"\nTop matches (threshold: {threshold:.4f}):")
        print(matches[preview_cols].head(10).to_string(index=False))
    else:
        print(f"\nNo matches found at threshold {threshold:.4f}.")
        print("Consider lowering the threshold or checking your input data.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Inference script — XGBoost job-candidate matcher"
    )
    parser.add_argument(
        "--mode", choices=["single", "batch"], default="batch",
        help="'single' for interactive single-pair scoring, "
             "'batch' to score a CSV file (default: batch).",
    )
    parser.add_argument(
        "--input", type=Path, default=None,
        help="Path to input CSV (required for batch mode).",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Path to write results CSV. "
             "Defaults to <input_stem>_predictions.csv.",
    )
    parser.add_argument(
        "--use-optimal-threshold", action="store_true",
        help="Use threshold from optimal_threshold.json (0.7232) "
             "instead of the default 0.5.",
    )
    parser.add_argument(
        "--explain", action="store_true",
        help="Attach SHAP explanations to each prediction. "
             "Requires explain.py in ml/.",
    )
    args = parser.parse_args()

    cfg = PredictConfig()

    if args.mode == "single":
        run_single_interactive(
            cfg=cfg,
            use_optimal=args.use_optimal_threshold,
            explain=args.explain,
        )
    else:
        if args.input is None:
            parser.error("--input is required for batch mode.")
        run_batch(
            cfg=cfg,
            input_path=args.input,
            output_path=args.output,
            use_optimal=args.use_optimal_threshold,
            explain=args.explain,
        )


if __name__ == "__main__":
    main()
