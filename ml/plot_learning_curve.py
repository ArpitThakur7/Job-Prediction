import logging
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("learning_curve")

def main():
    features_path = Path("data/processed/features.csv")
    plots_dir = Path("ml/plots")

    plots_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    logger.info("Loading features and labels...")
    merged_df = pd.read_csv(features_path)
    
    exclude = {
        "resume_id", "job_id", "match_id",
        "is_match", "match_score",
        "description_length",
        "skills_count_job",
    }
    feature_cols = [c for c in merged_df.columns if c not in exclude]

    X = merged_df[feature_cols].to_numpy(dtype=float)
    y = merged_df["is_match"].to_numpy(dtype=int)

    # Define training sizes (10% to 100%)
    train_sizes = np.linspace(0.1, 1.0, 7)
    train_scores_mean = []
    val_scores_mean = []

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    logger.info("Computing learning curves over %d training sizes...", len(train_sizes))

    for fraction in train_sizes:
        logger.info("Processing train size fraction: %.2f", fraction)
        train_fold_scores = []
        val_fold_scores = []

        for train_idx, val_idx in cv.split(X, y):
            X_cv_train, X_cv_val = X[train_idx], X[val_idx]
            y_cv_train, y_cv_val = y[train_idx], y[val_idx]

            # Sample subset of the training fold based on fraction
            n_sub = int(len(X_cv_train) * fraction)
            X_sub = X_cv_train[:n_sub]
            y_sub = y_cv_train[:n_sub]

            # Train fold model
            scale_pos_weight = float((len(y_sub) - y_sub.sum()) / y_sub.sum())
            clf = xgb.XGBClassifier(
                n_estimators=100, max_depth=5, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
                random_state=42, scale_pos_weight=scale_pos_weight, n_jobs=-1,
                verbosity=0
            )
            clf.fit(X_sub, y_sub)

            # Train score
            y_train_proba = clf.predict_proba(X_sub)[:, 1]
            train_fold_scores.append(roc_auc_score(y_sub, y_train_proba))

            # Val score
            y_val_proba = clf.predict_proba(X_cv_val)[:, 1]
            val_fold_scores.append(roc_auc_score(y_cv_val, y_val_proba))

        train_scores_mean.append(np.mean(train_fold_scores))
        val_scores_mean.append(np.mean(val_fold_scores))
        logger.info("  Train AUC: %.4f | Val AUC: %.4f", train_scores_mean[-1], val_scores_mean[-1])

    # Plot
    plt.figure(figsize=(8, 6))
    plt.plot(train_sizes * 100, train_scores_mean, "o-", color="r", label="Training score")
    plt.plot(train_sizes * 100, val_scores_mean, "o-", color="g", label="Cross-validation score")
    plt.xlabel("Training Set Size (%)")
    plt.ylabel("ROC-AUC Score")
    plt.title("XGBoost Matching Model Learning Curve")
    plt.legend(loc="lower right")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(plots_dir / "learning_curve.png", dpi=200)
    plt.close()
    logger.info("Saved learning curve plot -> %s", plots_dir / "learning_curve.png")

if __name__ == "__main__":
    main()
