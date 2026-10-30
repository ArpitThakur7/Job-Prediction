"""
ml/compare_versions.py — evaluate registered model versions side by side.

For each version we reproduce its own held-out test split (same
train_test_split(test_size=0.2, random_state=42, stratify=is_match) that
ml/train.py uses) on the dataset it was trained on and report:

1. Synthetic-label metrics (AUC, F1@0.5, NDCG@10, P@10 by resume_id).
   NOT comparable across versions whose datasets were regenerated: the label
   formula in scripts/prepare_dataset.py itself uses skill overlap, so fixing
   skill extraction changes the labels.

2. A label-formula-INDEPENDENT proxy ("category agreement"): relevance = 1 when
   the resume's human-assigned Kaggle category equals the job's category
   (derived from the job title). Neither is an input to the synthetic label
   formula, so this is the fairest like-for-like comparison available without
   real outcomes. It is a weak/noisy proxy (job categories come from a keyword
   map that defaults to INFORMATION-TECHNOLOGY).

Usage:
    python ml/compare_versions.py                       # v1 vs active
    python ml/compare_versions.py --versions v1 v2 --data v1=data/processed/v1 v2=data/processed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.train import ranking_metrics  # noqa: E402


def evaluate_version(version: str, data_dir: Path) -> Dict[str, float]:
    vdir = ROOT / "ml" / "model" / version
    model = joblib.load(vdir / "xgb_matcher.pkl")
    cols = json.loads((vdir / "feature_columns.json").read_text(encoding="utf-8"))

    feats = pd.read_csv(data_dir / "features.csv")
    y = feats["is_match"].astype(int).to_numpy()
    _, idx_test = train_test_split(np.arange(len(y)), test_size=0.2, random_state=42, stratify=y)
    test = feats.iloc[idx_test].reset_index(drop=True)
    proba = model.predict_proba(test[cols].to_numpy(dtype=float))[:, 1]
    y_test = y[idx_test]

    out: Dict[str, float] = {
        "synthetic_auc": float(roc_auc_score(y_test, proba)),
        "synthetic_f1_at_0.5": float(f1_score(y_test, (proba >= 0.5).astype(int))),
        "positive_rate": float(y.mean()),
    }
    r = ranking_metrics(test["resume_id"].astype(str).to_numpy(), y_test, proba, k=10)
    out["synthetic_ndcg_at_10"] = r["ndcg_at_10"]
    out["synthetic_precision_at_10"] = r["precision_at_10"]

    # ---- category-agreement proxy (independent of the label formula) ----
    jobs = pd.read_csv(data_dir / "jobs_clean.csv", usecols=["job_id", "category"])
    res = pd.read_csv(data_dir / "resumes_clean.csv", usecols=["resume_id", "category"])
    jobs["job_cat"] = jobs["category"].astype(str).str.strip().str.upper()
    res["res_cat"] = res["category"].astype(str).str.strip().str.upper()
    t = test[["resume_id", "job_id"]].copy()
    t["resume_id"] = t["resume_id"].astype(str)
    res["resume_id"] = res["resume_id"].astype(str)
    t["score"] = proba
    t = t.merge(jobs[["job_id", "job_cat"]], on="job_id", how="left").merge(
        res[["resume_id", "res_cat"]], on="resume_id", how="left")
    rel = (t["job_cat"] == t["res_cat"]).astype(int).to_numpy()
    out["category_proxy_positive_rate"] = float(rel.mean())
    out["category_proxy_auc"] = float(roc_auc_score(rel, t["score"])) if 0 < rel.sum() < len(rel) else float("nan")
    r2 = ranking_metrics(t["resume_id"].to_numpy(), rel, t["score"].to_numpy(), k=10)
    out["category_proxy_ndcg_at_10"] = r2["ndcg_at_10"]
    out["category_proxy_precision_at_10"] = r2["precision_at_10"]
    out["n_test"] = int(len(idx_test))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", nargs="+", default=["v1", "v2"])
    ap.add_argument("--data", nargs="*", default=["v1=data/processed/v1", "v2=data/processed"],
                    help="version=dataset_dir pairs")
    ap.add_argument("--out", default=str(ROOT / "ml" / "model" / "version_comparison.json"))
    args = ap.parse_args(argv)
    data_map = dict(d.split("=", 1) for d in args.data)
    results = {}
    for v in args.versions:
        d = ROOT / data_map.get(v, "data/processed")
        results[v] = evaluate_version(v, d)
        print(v, json.dumps(results[v], indent=2))
    Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("saved ->", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
