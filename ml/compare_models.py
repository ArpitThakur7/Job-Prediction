import json
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, roc_curve
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("compare_models")

def main():
    features_path = Path("data/processed/features.csv")
    labels_path = Path("data/processed/match_labels.csv")
    plots_dir = Path("ml/plots")
    model_dir = Path("ml/model")

    plots_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

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
    logger.info("Features: %s", feature_cols)

    X = merged_df[feature_cols].to_numpy(dtype=float)
    y = merged_df["is_match"].to_numpy(dtype=int)

    # Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Class imbalance weight for XGBoost
    scale_pos_weight = float((len(y_train) - y_train.sum()) / y_train.sum())

    # 2. Define classifiers
    classifiers = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1),
        "HistGradientBoosting": HistGradientBoostingClassifier(max_iter=100, max_depth=6, random_state=42),
        "XGBoost (Champion)": xgb.XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
            random_state=42, scale_pos_weight=scale_pos_weight, n_jobs=-1
        )
    }

    results = []

    plt.figure(figsize=(10, 8))
    plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")

    for name, clf in classifiers.items():
        logger.info("Training %s...", name)
        clf.fit(X_train, y_train)

        # Predict
        y_proba = clf.predict_proba(X_test)[:, 1]
        y_pred = (y_proba >= 0.5).astype(int)

        # Metrics
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)

        logger.info("  %s Metrics -> AUC: %.4f | F1: %.4f", name, auc, f1)

        results.append({
            "Model": name,
            "Accuracy": round(acc, 4),
            "Precision": round(prec, 4),
            "Recall": round(rec, 4),
            "F1-Score": round(f1, 4),
            "AUC-ROC": round(auc, 4)
        })

        # Plot ROC curve
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        plt.plot(fpr, tpr, lw=2, label=f"{name} (AUC = {auc:.4f})")

    # 3. Save comparison metrics
    comparison_df = pd.DataFrame(results)
    comparison_df.to_csv(model_dir / "comparison_metrics.csv", index=False)
    
    with open(model_dir / "comparison_metrics.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info("Saved comparison metrics -> %s", model_dir / "comparison_metrics.csv")

    # 4. Finish and save plot
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Model Comparison - Receiver Operating Characteristic (ROC)")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(plots_dir / "model_comparison.png", dpi=200)
    plt.close()
    logger.info("Saved model comparison plot -> %s", plots_dir / "model_comparison.png")

    # Print comparison table
    print("\n" + "=" * 80)
    print("  MODEL COMPARISON SUMMARY TABLE")
    print("=" * 80)
    print(comparison_df.to_string(index=False))
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
