"""
ml/retrain_with_feedback.py — simple online-learning loop from real user feedback.

1. Load feedback events (MongoDB `feedback` collection + data/feedback.jsonl fallback),
   keep the latest event per job_url.
2. Labels: apply / save / interview / offer -> 1 ; dismiss / reject -> 0.
   Graded relevance for NDCG: offer 3, interview 2, apply 1, save 1, dismiss/reject 0.
3. Features for each event against the user's resume (data/resume/resume.md),
   computed with the SAME function as training (ml.feature_engineering.compute_pair_features).
4. Shadow comparison on the feedback events:
     active model   -> NDCG@10 of its scores on all events (features built the way the
                       active model expects, see its model_meta.json)
     candidate      -> out-of-fold NDCG@10: K-fold over the events, each fold trained on
                       synthetic data + the other folds' feedback (up-weighted)
5. Train the final candidate (synthetic train split + all feedback, up-weighted), save it
   as a new registry version, and ACTIVATE it only if its NDCG@10 is not worse than the
   active model's. Otherwise it is registered but left inactive.

Exits 0 with a message when there is too little feedback.

Usage:
    python ml/retrain_with_feedback.py
    python ml/retrain_with_feedback.py --min-events 20 --feedback-weight 100
    python ml/retrain_with_feedback.py --feedback-file my.jsonl --no-mongo --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.feature_engineering import (  # noqa: E402
    compute_pair_features,
    estimate_min_experience_from_title,
    extract_education,
    extract_experience_years,
)
from ml.registry import (  # noqa: E402
    MODEL_DIR, activate_version, load_active_meta, load_registry, next_version, register_version,
)
from ml.skills import extract_skills  # noqa: E402
from ml.text_utils import strip_html  # noqa: E402
from ml import semantic  # noqa: E402
from ml.train import (  # noqa: E402
    TrainConfig, build_model, compute_scale_pos_weight, evaluate_metrics,
    find_optimal_threshold, get_feature_columns, load_and_merge, load_feature_meta, ranking_metrics,
)

logger = logging.getLogger("ml.retrain_with_feedback")

POSITIVE = {"apply", "save", "interview", "offer"}
NEGATIVE = {"dismiss", "reject"}
GRADE = {"offer": 3, "interview": 2, "apply": 1, "save": 1, "dismiss": 0, "reject": 0}
DEFAULT_FEEDBACK_FILE = ROOT / "data" / "feedback.jsonl"
DEFAULT_RESUME = ROOT / "data" / "resume" / "resume.md"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_feedback(feedback_file: Path, use_mongo: bool = True) -> pd.DataFrame:
    events: List[Dict[str, Any]] = []
    if use_mongo:
        try:
            from backend.database import get_database
            db = get_database()
            if db is not None:
                events.extend(db["feedback"].find({}, {"_id": 0}))
                logger.info("Loaded %d feedback events from MongoDB", len(events))
        except Exception as exc:
            logger.warning("MongoDB feedback unavailable: %s", exc)
    if feedback_file.exists():
        n0 = len(events)
        with feedback_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        logger.info("Loaded %d feedback events from %s", len(events) - n0, feedback_file)
    if not events:
        return pd.DataFrame(columns=["job_url", "title", "company", "action", "description", "created_at"])
    df = pd.DataFrame(events)
    for c in ("job_url", "title", "company", "action", "description", "created_at"):
        if c not in df.columns:
            df[c] = None
    df["action"] = df["action"].astype(str).str.lower()
    df = df[df["action"].isin(POSITIVE | NEGATIVE)]
    df = df[df["job_url"].astype(str).str.len() > 0]
    # latest event per job wins (e.g. save -> reject is a negative)
    df = df.sort_values("created_at", na_position="first").drop_duplicates("job_url", keep="last")
    df["label"] = df["action"].isin(POSITIVE).astype(int)
    df["grade"] = df["action"].map(GRADE).astype(int)
    return df.reset_index(drop=True)


def load_resume(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    plain = strip_html(text)
    return {
        "raw_text": plain,
        "skills": extract_skills(plain),
        "experience_years": extract_experience_years(plain),
        "education": extract_education(plain),
        "location": "",
    }


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

def event_job(ev: pd.Series) -> Dict[str, Any]:
    desc = str(ev.get("description") or "")
    title = str(ev.get("title") or "")
    exp = extract_experience_years(desc) if desc else 0
    return {
        "title": title,
        "description": desc,
        "required_skills": extract_skills(strip_html(f"{title}. {desc}")),
        "location": "Remote",
        "category": "INFORMATION-TECHNOLOGY",
        "experience_years": float(exp) if exp else estimate_min_experience_from_title(title),
    }


def build_feedback_features(events: pd.DataFrame, resume: Dict[str, Any],
                            semantic_backend: str, tfidf_path: Path) -> pd.DataFrame:
    """Feature rows for every event, built the way a model with ``semantic_backend`` expects."""
    vec = semantic.load_tfidf(tfidf_path)
    jobs = [event_job(ev) for _, ev in events.iterrows()]
    job_texts = [j["description"] or j["title"] for j in jobs]
    tf = [semantic.tfidf_similarity(resume["raw_text"], t, vectorizer=vec) for t in job_texts]
    if semantic_backend == "minilm":
        sem = semantic.minilm_similarity_many(resume["raw_text"], job_texts)
        sem = [s if s is not None else t for s, t in zip(sem, tf)]
    else:
        sem = tf
    rows = []
    for job, s, t in zip(jobs, sem, tf):
        rows.append(compute_pair_features(resume, job, semantic_similarity=s or 0.0, tfidf_similarity=t or 0.0))
    return pd.DataFrame(rows)


def ndcg_single(grades: np.ndarray, scores: np.ndarray, k: int = 10) -> float:
    r = ranking_metrics(np.zeros(len(grades)), grades.astype(float), scores, k=k)
    return float(r[f"ndcg_at_{k}"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    import os
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    os.chdir(ROOT)  # TrainConfig / feature_meta paths are project-relative

    events = load_feedback(Path(args.feedback_file), use_mongo=not args.no_mongo)
    n = len(events)
    n_pos = int(events["label"].sum()) if n else 0
    n_neg = n - n_pos
    if n < args.min_events or n_pos < args.min_per_class or n_neg < args.min_per_class:
        print(f"Not enough feedback to retrain yet: {n} usable events "
              f"({n_pos} positive, {n_neg} negative); need >= {args.min_events} events and "
              f">= {args.min_per_class} of each class. Keep using /feedback and try again later.")
        return 0

    resume_path = Path(args.resume)
    if not resume_path.exists():
        print(f"Resume not found at {resume_path}; cannot compute feedback features.")
        return 0
    resume = load_resume(resume_path)
    grades = events["grade"].to_numpy()
    y_fb = events["label"].to_numpy()

    # ---- active model on feedback (features as IT expects them) ----
    reg = load_registry()
    active = reg.get("active")
    active_meta = load_active_meta()
    active_model = joblib.load(MODEL_DIR / "xgb_matcher.pkl")
    active_cols = json.loads((MODEL_DIR / "feature_columns.json").read_text(encoding="utf-8"))
    fb_active = build_feedback_features(events, resume, active_meta.get("semantic_backend", "tfidf"),
                                        MODEL_DIR / "tfidf_vectorizer.pkl")
    active_scores = active_model.predict_proba(fb_active[active_cols].to_numpy(dtype=float))[:, 1]
    active_ndcg = ndcg_single(grades, active_scores)
    logger.info("Active model %s: feedback NDCG@10 = %.4f", active, active_ndcg)

    # ---- candidate: synthetic data (current features.csv) + feedback ----
    cfg = TrainConfig()
    syn = load_and_merge(cfg.features_path, cfg.labels_path)
    feat_cols = get_feature_columns(syn)
    feature_meta = load_feature_meta()
    cand_tfidf = Path("data/processed/tfidf_vectorizer.pkl")
    if not (ROOT / cand_tfidf).exists():
        cand_tfidf = MODEL_DIR / "tfidf_vectorizer.pkl"
    fb_cand = build_feedback_features(events, resume, feature_meta.get("semantic_backend", "tfidf"), ROOT / cand_tfidf)
    X_fb = fb_cand[feat_cols].to_numpy(dtype=float)

    from sklearn.model_selection import StratifiedKFold, train_test_split
    X_syn = syn[feat_cols].to_numpy(dtype=float)
    y_syn = syn["is_match"].to_numpy(dtype=int)
    idx_tr, idx_te = train_test_split(np.arange(len(y_syn)), test_size=cfg.test_size,
                                      random_state=cfg.random_state, stratify=y_syn)
    spw = compute_scale_pos_weight(y_syn[idx_tr])
    w = float(args.feedback_weight)

    def fit(fb_idx: np.ndarray):
        X = np.vstack([X_syn[idx_tr], X_fb[fb_idx]])
        y = np.concatenate([y_syn[idx_tr], y_fb[fb_idx]])
        sw = np.concatenate([np.ones(len(idx_tr)), np.full(len(fb_idx), w)])
        m = build_model(cfg, spw)
        m.fit(X, y, sample_weight=sw)
        return m

    k = int(min(5, n_pos, n_neg))
    oof = np.zeros(n)
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=cfg.random_state)
    for fold, (tr, te) in enumerate(skf.split(X_fb, y_fb)):
        oof[te] = fit(tr).predict_proba(X_fb[te])[:, 1]
        logger.info("  shadow fold %d/%d done", fold + 1, k)
    cand_ndcg = ndcg_single(grades, oof)
    logger.info("Candidate (out-of-fold): feedback NDCG@10 = %.4f", cand_ndcg)

    final = fit(np.arange(n))
    proba = final.predict_proba(X_syn[idx_te])[:, 1]
    metrics: Dict[str, Any] = evaluate_metrics(y_syn[idx_te], (proba >= 0.5).astype(int), proba)
    metrics.update(ranking_metrics(syn["resume_id"].astype(str).to_numpy()[idx_te], y_syn[idx_te], proba))
    thr = find_optimal_threshold(y_syn[idx_te], proba)
    metrics["optimal_threshold"] = thr["optimal_threshold"]
    metrics["feedback_events"] = n
    metrics["feedback_ndcg_at_10_candidate_oof"] = cand_ndcg
    metrics["feedback_ndcg_at_10_active"] = active_ndcg
    metrics["feedback_active_version"] = active
    metrics["feedback_weight"] = w

    promote = cand_ndcg >= active_ndcg - 1e-9
    print(json.dumps({"active": active, "active_feedback_ndcg@10": round(active_ndcg, 4),
                      "candidate_feedback_ndcg@10_oof": round(cand_ndcg, 4),
                      "promote": promote, "events": n}, indent=2))
    if args.dry_run:
        print("--dry-run: nothing saved.")
        return 0

    version = next_version(reg)
    vdir = MODEL_DIR / version
    vdir.mkdir(parents=True, exist_ok=True)
    joblib.dump(final, vdir / "xgb_matcher.pkl")
    (vdir / "feature_columns.json").write_text(json.dumps(feat_cols, indent=2), encoding="utf-8")
    (vdir / "train_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (vdir / "optimal_threshold.json").write_text(json.dumps(thr, indent=2), encoding="utf-8")
    import shutil
    shutil.copy2(ROOT / cand_tfidf, vdir / "tfidf_vectorizer.pkl")
    meta = {
        "version": version,
        "semantic_backend": feature_meta.get("semantic_backend", "tfidf"),
        "skill_extractor": feature_meta.get("skill_extractor", "unknown"),
        "feature_columns": feat_cols,
        "trained_on": "synthetic features.csv (train split) + feedback events",
        "parent": active,
    }
    (vdir / "model_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    reg_metrics = {kk: metrics[kk] for kk in (
        "auc_roc", "f1", "ndcg_at_10", "precision_at_10", "optimal_threshold", "feedback_events",
        "feedback_ndcg_at_10_candidate_oof", "feedback_ndcg_at_10_active") if kk in metrics}
    register_version(
        version, reg_metrics, meta=meta,
        notes=(f"Feedback retrain on {n} events (weight {w}). Shadow NDCG@10 on feedback: "
               f"candidate {cand_ndcg:.4f} vs active {active} {active_ndcg:.4f} -> "
               f"{'activated' if promote else 'NOT activated'}."),
        activate=promote,
    )
    print(f"Saved {version} -> {vdir} ({'ACTIVE' if promote else 'inactive; active stays ' + str(active)})")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Retrain the matcher with real user feedback")
    ap.add_argument("--feedback-file", default=str(DEFAULT_FEEDBACK_FILE))
    ap.add_argument("--no-mongo", action="store_true", help="Only read --feedback-file")
    ap.add_argument("--resume", default=str(DEFAULT_RESUME))
    ap.add_argument("--min-events", type=int, default=20)
    ap.add_argument("--min-per-class", type=int, default=5)
    ap.add_argument("--feedback-weight", type=float, default=100.0,
                    help="sample_weight of each feedback row (synthetic rows weigh 1)")
    ap.add_argument("--dry-run", action="store_true", help="Run the comparison but save nothing")
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
