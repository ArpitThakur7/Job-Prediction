"""
Real-feedback capture for the ML matcher (online-learning loop).

    POST /feedback        {job_url, title, company, action, description?, relevance_score?, prediction_score?}
                          -> {"ok": true}
    GET  /feedback/stats  -> {"total": int, "by_action": {action: count}}

Events go to MongoDB collection ``feedback`` (backend's existing connection,
settings.DB_NAME). If MongoDB is unavailable they are appended to
``data/feedback.jsonl`` instead. ml/retrain_with_feedback.py reads both.

CORS is handled by the app-wide CORSMiddleware in backend/main.py (same as every
other route), so the Next.js dev server on localhost:3000 can call these.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.database import get_database, run_async_db

logger = logging.getLogger("backend.routes.feedback")

router = APIRouter()

FEEDBACK_COLLECTION = "feedback"
FEEDBACK_JSONL = Path(__file__).resolve().parents[2] / "data" / "feedback.jsonl"
FEEDBACK_ACTIONS = ("apply", "save", "dismiss", "interview", "offer", "reject")
_jsonl_lock = threading.Lock()

FeedbackAction = Literal["apply", "save", "dismiss", "interview", "offer", "reject"]


class FeedbackEvent(BaseModel):
    job_url: str = Field(..., min_length=1, max_length=2048)
    title: str = Field(..., max_length=500)
    company: str = Field(..., max_length=300)
    action: FeedbackAction
    description: Optional[str] = Field(default=None, max_length=50_000)
    relevance_score: Optional[float] = None
    prediction_score: Optional[float] = None


def _append_jsonl(doc: Dict[str, Any]) -> None:
    FEEDBACK_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with _jsonl_lock:
        with FEEDBACK_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")


def _read_jsonl() -> List[Dict[str, Any]]:
    if not FEEDBACK_JSONL.exists():
        return []
    out: List[Dict[str, Any]] = []
    with _jsonl_lock:
        with FEEDBACK_JSONL.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def store_feedback(doc: Dict[str, Any]) -> str:
    """Insert into Mongo `feedback`; fall back to data/feedback.jsonl. Returns the store used."""
    db = get_database()
    if db is not None:
        try:
            db[FEEDBACK_COLLECTION].insert_one(dict(doc))  # copy: insert_one adds _id
            return "mongodb"
        except Exception as exc:
            logger.warning("Mongo feedback insert failed (%s); writing to %s", exc, FEEDBACK_JSONL)
    _append_jsonl(doc)
    return "jsonl"


def feedback_stats() -> Dict[str, Any]:
    by_action: Dict[str, int] = {a: 0 for a in FEEDBACK_ACTIONS}
    db = get_database()
    if db is not None:
        try:
            for row in db[FEEDBACK_COLLECTION].aggregate([{"$group": {"_id": "$action", "n": {"$sum": 1}}}]):
                by_action[str(row["_id"])] = by_action.get(str(row["_id"]), 0) + int(row["n"])
        except Exception as exc:
            logger.warning("Mongo feedback stats failed: %s", exc)
    # Events that landed in the JSONL fallback count too.
    for ev in _read_jsonl():
        a = str(ev.get("action", ""))
        by_action[a] = by_action.get(a, 0) + 1
    return {"total": int(sum(by_action.values())), "by_action": by_action}


@router.post("/feedback")
async def post_feedback(event: FeedbackEvent) -> Dict[str, Any]:
    doc = event.model_dump() if hasattr(event, "model_dump") else event.dict()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    try:
        store = await run_async_db(store_feedback, doc)
    except Exception as exc:
        logger.exception("Failed to store feedback: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to store feedback") from exc
    logger.info("feedback %s for %s stored in %s", doc["action"], doc["job_url"], store)
    return {"ok": True}


@router.get("/feedback/stats")
async def get_feedback_stats() -> Dict[str, Any]:
    return await run_async_db(feedback_stats)
