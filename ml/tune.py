from __future__ import annotations

"""
tune.py
=======
Optuna hyperparameter tuning for the XGBoost job-candidate matcher.

Runs N trials of Bayesian optimisation over the XGBoost search space,
evaluates each trial with stratified cross-validation (ROC-AUC), and
writes the best parameters to ml/model/best_params.json so that train.py
can pick them up on the next run.

Usage
-----
    # Default: 50 trials, 5-fold CV
    python ml/tune.py

    # Custom trial count
    python ml/tune.py --trials 100

    # Quick smoke-test (5 trials)
    python ml/tune.py --trials 5

    # Tune then immediately retrain with best params
    python ml/tune.py --trials 50 --retrain

Outputs
-------
    ml/model/best_params.json     — best hyperparameters found
    ml/plots/optuna_history.png   — objective value per trial
    ml/plots/optuna_importance.png— hyperparameter importance ranking

Integration with train.py
--------------------------
    After tuning, train.py automatically loads best_params.json if it
    exists, overriding the defaults in TrainConfig.  No code change needed.

    To ignore best_params.json and use TrainConfig defaults:
        python ml/train.py --ignore-tuned-params
"""

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import optuna
from optuna.samplers import TPESampler
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.model_selection import train_test_split
import xgboost as xgb

logger = logging.getLogger(__name__)

optuna.logging.set_verbosity(optuna.logging.WARNING)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TuneConfig:
    features_path: Path     = Path("data/processed/features.csv")
    labels_path: Path       = Path("data/processed/match_labels.csv")
    feature_cols_path: Path = Path("ml/model/feature_columns.json")
    output_params: Path     = Path("ml/model/best_params.json")
    plots_dir: Path         = Path("ml/plots")
    n_trials: int           = 50
    n_splits: int           = 5
    test_size: float        = 0.2
    random_state: int       = 42
    scoring: str            = "roc_auc"
    # Timeout per trial in seconds (None = no limit)
    trial_timeout: int | None = None


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


# ---------------------------------------------------------------------------
# Data loading  (mirrors train.py exactly)
# ---------------------------------------------------------------------------

def _read_csv_or_raise(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Required file not found: {path}") from exc


def load_train_data(cfg: TuneConfig) -> tuple[np.ndarray, np.ndarray]:
    """
    Loads features + labels and returns the training split only.
    Tuning must never touch test data.

    Returns:
        X_train, y_train as numpy arrays.
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

    with cfg.feature_cols_path.open("r", encoding="utf-8") as f:
        feature_cols = json.load(f)

    X = merged[feature_cols].to_numpy(dtype=float)
    y = merged["is_match"].to_numpy(dtype=int)

    X_train, _, y_train, _ = train_test_split(
        X, y,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
        stratify=y,
    )

    pos_pct = y_train.mean() * 100
    logger.info(
        "Training data — rows: %d | features: %d | positives: %.1f%%",
        len(y_train), X_train.shape[1], pos_pct,
    )
    return X_train, y_train


# ---------------------------------------------------------------------------
# Search space
# ---------------------------------------------------------------------------

def _suggest_params(trial: optuna.Trial) -> dict:
    """
    Defines the hyperparameter search space for XGBoost.

    Ranges are intentionally wide on the first run; narrow them in
    subsequent runs once you know which region works best.

    Args:
        trial: Optuna trial object.

    Returns:
        Dict of XGBoost hyperparameters.
    """
    return {
        # Tree structure
        "n_estimators":      trial.suggest_int("n_estimators", 100, 600, step=50),
        "max_depth":         trial.suggest_int("max_depth", 3, 10),
        "min_child_weight":  trial.suggest_int("min_child_weight", 1, 10),
        # Learning
        "learning_rate":     trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        # Sampling (regularise against overfitting)
        "subsample":         trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree":  trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "colsample_bylevel": trial.suggest_float("colsample_bylevel", 0.5, 1.0),
        # L1 / L2 regularisation
        "reg_alpha":         trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda":        trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        # Boosting strategy
        "gamma":             trial.suggest_float("gamma", 0.0, 5.0),
    }


# ---------------------------------------------------------------------------
# Objective
# ---------------------------------------------------------------------------

def make_objective(
    X_train: np.ndarray,
    y_train: np.ndarray,
    cfg: TuneConfig,
):
    """
    Returns an Optuna objective function closed over the training data.

    Each trial:
      1. Samples hyperparameters from the search space.
      2. Computes scale_pos_weight for class imbalance.
      3. Runs N-fold stratified CV and returns mean ROC-AUC.

    Args:
        X_train: Training features.
        y_train: Training labels.
        cfg:     TuneConfig.

    Returns:
        Callable objective(trial) -> float.
    """
    count_0 = int((y_train == 0).sum())
    count_1 = int((y_train == 1).sum())
    scale_pos_weight = count_0 / count_1

    cv = StratifiedKFold(
        n_splits=cfg.n_splits,
        shuffle=True,
        random_state=cfg.random_state,
    )

    def objective(trial: optuna.Trial) -> float:
        params = _suggest_params(trial)

        model = xgb.XGBClassifier(
            **params,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=cfg.random_state,
            n_jobs=-1,
            verbosity=0,
        )

        scores = cross_val_score(
            model, X_train, y_train,
            cv=cv,
            scoring=cfg.scoring,
            n_jobs=-1,
        )
        return float(scores.mean())

    return objective


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_optimisation_history(study: optuna.Study, plots_dir: Path) -> None:
    """
    Saves a trial-by-trial objective value plot with a running best line.

    Args:
        study:     Completed Optuna study.
        plots_dir: Output directory.
    """
    import matplotlib.pyplot as plt

    plots_dir.mkdir(parents=True, exist_ok=True)

    values   = [t.value for t in study.trials if t.value is not None]
    trials   = list(range(1, len(values) + 1))
    best_so_far = np.maximum.accumulate(values)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(trials, values, s=18, alpha=0.5, color="#7F77DD", label="Trial AUC")
    ax.plot(trials, best_so_far, color="#E91E63", lw=2, label="Best so far")
    ax.axhline(best_so_far[-1], color="#E91E63", lw=1, linestyle="--", alpha=0.4)

    ax.set_xlabel("Trial", fontsize=12)
    ax.set_ylabel(f"CV {study.metric_names[0] if study.metric_names else 'ROC-AUC'}", fontsize=12)
    ax.set_title("Optuna optimisation history", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.25)

    out = plots_dir / "optuna_history.png"
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    plt.close()
    logger.info("Saved optimisation history -> %s", out)


def plot_param_importance(study: optuna.Study, plots_dir: Path) -> None:
    """
    Saves a hyperparameter importance bar chart computed by Optuna's
    fANOVA-based estimator.

    Args:
        study:     Completed Optuna study.
        plots_dir: Output directory.
    """
    import matplotlib.pyplot as plt

    plots_dir.mkdir(parents=True, exist_ok=True)

    try:
        importance = optuna.importance.get_param_importances(study)
    except Exception as exc:
        logger.warning("Could not compute param importances: %s", exc)
        return

    names  = list(importance.keys())
    values = list(importance.values())

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(names[::-1], values[::-1], color="#5DCAA5", edgecolor="#0F6E56", lw=0.5)

    for bar, val in zip(bars, values[::-1]):
        ax.text(
            bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
            f"{val:.3f}", va="center", fontsize=10,
        )

    ax.set_xlabel("Importance (fANOVA)", fontsize=12)
    ax.set_title("Hyperparameter importance", fontsize=13)
    ax.set_xlim(0, max(values) * 1.2)
    ax.grid(axis="x", alpha=0.25)

    out = plots_dir / "optuna_importance.png"
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    plt.close()
    logger.info("Saved param importance -> %s", out)


# ---------------------------------------------------------------------------
# Results logging
# ---------------------------------------------------------------------------

def log_results(study: optuna.Study, baseline_auc: float) -> None:
    """
    Logs a clean summary of the tuning run vs the baseline.

    Args:
        study:        Completed Optuna study.
        baseline_auc: AUC from train.py with default params (for comparison).
    """
    best = study.best_trial
    delta = best.value - baseline_auc

    logger.info("=" * 60)
    logger.info("TUNING COMPLETE")
    logger.info("  Trials run       : %d", len(study.trials))
    logger.info("  Best trial       : #%d", best.number)
    logger.info("  Best CV AUC      : %.6f", best.value)
    logger.info("  Baseline AUC     : %.6f", baseline_auc)
    logger.info("  Delta            : %+.6f", delta)
    logger.info("-" * 60)
    logger.info("  Best parameters  :")
    for k, v in best.params.items():
        logger.info("    %-22s : %s", k, v)
    logger.info("=" * 60)

    if abs(delta) < 0.001:
        logger.info(
            "NOTE: Improvement is < 0.001 AUC. Your default params were "
            "already near-optimal — expected given AUC 0.996."
        )


# ---------------------------------------------------------------------------
# Save best params
# ---------------------------------------------------------------------------

def save_best_params(study: optuna.Study, cfg: TuneConfig) -> None:
    """
    Writes best params + study metadata to best_params.json.

    train.py reads this file on startup if it exists.

    Args:
        study: Completed Optuna study.
        cfg:   TuneConfig.
    """
    cfg.output_params.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "best_cv_auc":   study.best_value,
        "best_trial":    study.best_trial.number,
        "n_trials":      len(study.trials),
        "params":        study.best_params,
    }

    with cfg.output_params.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    logger.info("Saved best params -> %s", cfg.output_params)


# ---------------------------------------------------------------------------
# Main tuning pipeline
# ---------------------------------------------------------------------------

def run_tuning(cfg: TuneConfig) -> optuna.Study:
    """
    Full Optuna tuning pipeline:
      load data → create study → optimise → plot → save params.

    Args:
        cfg: TuneConfig with all paths and settings.

    Returns:
        Completed optuna.Study.
    """
    setup_logging()

    logger.info("=" * 60)
    logger.info("Optuna Hyperparameter Tuning — XGBoost Matcher")
    logger.info("Trials: %d  |  CV folds: %d  |  Scoring: %s",
                cfg.n_trials, cfg.n_splits, cfg.scoring)
    logger.info("=" * 60)

    X_train, y_train = load_train_data(cfg)

    # Baseline: what train.py gets with its default TrainConfig params
    baseline_auc = 0.996168

    objective = make_objective(X_train, y_train, cfg)

    study = optuna.create_study(
        direction="maximize",
        sampler=TPESampler(seed=cfg.random_state),
        study_name="xgb_matcher",
    )

    logger.info("Starting optimisation (%d trials) ...", cfg.n_trials)

    # Progress callback — logs every 10 trials
    def _log_callback(study: optuna.Study, trial: optuna.Trial) -> None:
        if (trial.number + 1) % 10 == 0 or trial.number == 0:
            logger.info(
                "  Trial %3d/%d — AUC: %.6f | Best so far: %.6f",
                trial.number + 1, cfg.n_trials,
                trial.value, study.best_value,
            )

    study.optimize(
        objective,
        n_trials=cfg.n_trials,
        timeout=cfg.trial_timeout,
        callbacks=[_log_callback],
        show_progress_bar=False,
    )

    log_results(study, baseline_auc)
    save_best_params(study, cfg)
    plot_optimisation_history(study, cfg.plots_dir)
    plot_param_importance(study, cfg.plots_dir)

    return study


# ---------------------------------------------------------------------------
# train.py integration patch
# ---------------------------------------------------------------------------

def load_best_params(
    params_path: Path = Path("ml/model/best_params.json"),
) -> dict | None:
    """
    Loads best params from a previous tuning run.

    Call this at the top of train.py to override TrainConfig defaults:

        from tune import load_best_params

        best = load_best_params()
        if best:
            cfg = TrainConfig(
                n_estimators      = best["n_estimators"],
                max_depth         = best["max_depth"],
                learning_rate     = best["learning_rate"],
                subsample         = best["subsample"],
                colsample_bytree  = best["colsample_bytree"],
            )
        else:
            cfg = TrainConfig()

    Args:
        params_path: Path to best_params.json.

    Returns:
        Dict of params if file exists, else None.
    """
    if not params_path.exists():
        return None
    with params_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("params", {})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Optuna hyperparameter tuning for XGBoost matcher"
    )
    parser.add_argument(
        "--trials", type=int, default=50,
        help="Number of Optuna trials (default: 50).",
    )
    parser.add_argument(
        "--retrain", action="store_true",
        help="After tuning, immediately run train.py with the best params.",
    )
    parser.add_argument(
        "--timeout", type=int, default=None,
        help="Max seconds per trial (default: no limit).",
    )
    args = parser.parse_args()

    cfg = TuneConfig(n_trials=args.trials, trial_timeout=args.timeout)
    run_tuning(cfg)

    if args.retrain:
        logger.info("--retrain flag set — launching train.py ...")
        result = subprocess.run(
            [sys.executable, "ml/train.py"],
            check=False,
        )
        if result.returncode != 0:
            logger.error("train.py exited with code %d", result.returncode)
            sys.exit(result.returncode)
        logger.info("Retraining complete.")


if __name__ == "__main__":
    main()
