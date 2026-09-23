import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("eda")

def main():
    features_path = Path("data/processed/features.csv")
    plots_dir = Path("ml/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    logger.info("Loading feature matrix...")
    df = pd.read_csv(features_path)

    # Set styling
    sns.set_theme(style="darkgrid")
    plt.rcParams.update({
        "font.size": 12,
        "axes.labelsize": 14,
        "axes.titlesize": 16,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "figure.titlesize": 18
    })

    # Plot 1: Class Imbalance
    logger.info("Generating Plot 1: Class Imbalance...")
    plt.figure(figsize=(6, 6))
    counts = df["is_match"].value_counts()
    plt.pie(counts, labels=["No Match (0)", "Match (1)"], autopct="%1.1f%%", startangle=140, colors=["#ff4757", "#2ed573"], explode=(0, 0.05))
    plt.title("Class Balance (is_match)")
    plt.tight_layout()
    plt.savefig(plots_dir / "eda_class_balance.png", dpi=200)
    plt.close()

    # Plot 2: Correlation Heatmap
    logger.info("Generating Plot 2: Correlation Heatmap...")
    exclude = {"resume_id", "job_id", "match_id"}
    corr_cols = [c for c in df.columns if c not in exclude]
    corr_matrix = df[corr_cols].corr()
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", cbar=True, square=True, linewidths=0.5)
    plt.title("Feature Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(plots_dir / "eda_correlation_heatmap.png", dpi=200)
    plt.close()

    # Plot 3: Experience Gap by Match Status
    logger.info("Generating Plot 3: Experience Gap Distribution...")
    plt.figure(figsize=(8, 6))
    sns.kdeplot(data=df, x="experience_gap", hue="is_match", fill=True, common_norm=False, palette=["#ff4757", "#2ed573"], alpha=0.5, linewidth=2)
    plt.title("Experience Gap Distribution by Match Status")
    plt.xlabel("Experience Gap (Candidate Years - Required Years)")
    plt.ylabel("Density")
    plt.tight_layout()
    plt.savefig(plots_dir / "eda_experience_gap.png", dpi=200)
    plt.close()

    # Plot 4: Semantic Similarity by Match Status
    logger.info("Generating Plot 4: Semantic Similarity Distribution...")
    plt.figure(figsize=(8, 6))
    sns.kdeplot(data=df, x="semantic_similarity", hue="is_match", fill=True, common_norm=False, palette=["#ff4757", "#2ed573"], alpha=0.5, linewidth=2)
    plt.title("Semantic Similarity Distribution by Match Status")
    plt.xlabel("TF-IDF Cosine Similarity")
    plt.ylabel("Density")
    plt.tight_layout()
    plt.savefig(plots_dir / "eda_semantic_similarity.png", dpi=200)
    plt.close()

    logger.info("EDA completed successfully! Plots saved to ml/plots/")

if __name__ == "__main__":
    main()
