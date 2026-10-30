"""
ml/registry.py — tiny model registry for the XGBoost matcher.

Layout
------
    ml/model/<version>/            immutable artifacts of one version
        xgb_matcher.pkl, feature_columns.json, optimal_threshold.json,
        train_metrics.json, tfidf_vectorizer.pkl, model_meta.json
    ml/model/*.{pkl,json}          the ACTIVE version (what backend/ml.predict load)
    ml/model/registry.json         versions, metrics, created_at, active

CLI
---
    python ml/registry.py list
    python ml/registry.py activate v1      # roll back (copies v1 artifacts to ml/model/)
    python ml/registry.py activate v2      # roll forward again

The backend caches the loaded model in-process: restart uvicorn (or rely on
``--reload``) after activating a different version.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "ml" / "model"
REGISTRY_PATH = MODEL_DIR / "registry.json"

#: Files that make up a servable version (copied on activate).
ARTIFACT_FILES = [
    "xgb_matcher.pkl",
    "feature_columns.json",
    "optimal_threshold.json",
    "train_metrics.json",
    "tfidf_vectorizer.pkl",
    "model_meta.json",
]

ROLLBACK_HELP = (
    "Roll back / switch versions with:  python ml/registry.py activate <version>  "
    "(copies ml/model/<version>/* over the top-level ml/model/ artifacts the backend loads; "
    "restart the backend afterwards)."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_registry() -> Dict[str, Any]:
    if REGISTRY_PATH.exists():
        with REGISTRY_PATH.open(encoding="utf-8") as f:
            reg = json.load(f)
    else:
        reg = {"active": None, "versions": {}}
    reg.setdefault("versions", {})
    reg["rollback"] = ROLLBACK_HELP
    return reg


def save_registry(reg: Dict[str, Any]) -> None:
    reg["rollback"] = ROLLBACK_HELP
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)
    tmp.replace(REGISTRY_PATH)


def version_dir(version: str) -> Path:
    return MODEL_DIR / version


def next_version(reg: Optional[Dict[str, Any]] = None) -> str:
    reg = reg or load_registry()
    nums = []
    for v in reg["versions"]:
        if v.startswith("v") and v[1:].isdigit():
            nums.append(int(v[1:]))
    for p in MODEL_DIR.glob("v*"):
        if p.is_dir() and p.name[1:].isdigit():
            nums.append(int(p.name[1:]))
    return f"v{(max(nums) if nums else 0) + 1}"


def register_version(
    version: str,
    metrics: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
    notes: str = "",
    activate: bool = False,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a version whose artifacts already live in ml/model/<version>/."""
    vdir = version_dir(version)
    if not (vdir / "xgb_matcher.pkl").exists():
        raise FileNotFoundError(f"{vdir / 'xgb_matcher.pkl'} not found — save artifacts first")
    reg = load_registry()
    reg["versions"][version] = {
        "path": f"ml/model/{version}",
        "created_at": created_at or _now(),
        "metrics": metrics,
        "meta": meta or {},
        "notes": notes,
    }
    save_registry(reg)
    if activate:
        activate_version(version)
        reg = load_registry()
    return reg


def activate_version(version: str) -> None:
    """Copy ml/model/<version>/ artifacts to the top-level ml/model/ paths and mark active."""
    vdir = version_dir(version)
    if not (vdir / "xgb_matcher.pkl").exists():
        raise FileNotFoundError(f"No artifacts for {version} in {vdir}")
    for name in ARTIFACT_FILES:
        src = vdir / name
        dst = MODEL_DIR / name
        if src.exists():
            shutil.copy2(src, dst)
        elif name == "model_meta.json" and dst.exists():
            dst.unlink()  # older versions have no meta: serve with legacy defaults
    reg = load_registry()
    if version not in reg["versions"]:
        reg["versions"][version] = {"path": f"ml/model/{version}", "created_at": _now(), "metrics": {}}
    prev = reg.get("active")
    reg["active"] = version
    reg.setdefault("history", []).append({"activated": version, "previous": prev, "at": _now()})
    save_registry(reg)


def load_active_meta() -> Dict[str, Any]:
    """model_meta.json of the active artifacts (legacy default: TF-IDF semantic feature)."""
    p = MODEL_DIR / "model_meta.json"
    if p.exists():
        try:
            with p.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"semantic_backend": "tfidf", "skill_extractor": "substring-v1"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="XGBoost matcher model registry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    a = sub.add_parser("activate")
    a.add_argument("version")
    args = ap.parse_args(argv)

    if args.cmd == "list":
        reg = load_registry()
        print(f"active: {reg.get('active')}")
        for v, info in sorted(reg["versions"].items()):
            m = info.get("metrics", {})
            print(f"  {v:4s} created {info.get('created_at')}  auc={m.get('auc_roc')}  "
                  f"f1={m.get('f1')}  ndcg@10={m.get('ndcg_at_10')}  p@10={m.get('precision_at_10')}")
        return 0
    if args.cmd == "activate":
        activate_version(args.version)
        print(f"Activated {args.version}. Restart the backend to load it.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
