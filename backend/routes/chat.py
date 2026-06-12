from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.redis_client import cache_delete
from backend.services.llm_chain import ask_question

logger = logging.getLogger("backend.routes.chat")

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    session_id: str


@router.post("/chat/", response_model=Dict[str, Any])
async def chat(payload: ChatRequest) -> Dict[str, Any]:
    """
    Accept: {question: str, session_id: str}
    Run RAG chain with Groq LLM, cache conversation in Redis.
    """
    try:
        question = (payload.question or "").strip()
        session_id = (payload.session_id or "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        result = ask_question(question=question, session_id=session_id)

        return {
            "success": True,
            "data": {
                "answer": result.get("answer") or "",
                "session_id": session_id,
                "sources": result.get("sources") or [],
            },
            "message": "Chat response generated",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("chat failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate chat response") from exc


@router.delete("/chat/{session_id}")
async def clear_chat(session_id: str) -> Dict[str, Any]:
    """
    Clear conversation history from Redis for the session.
    """
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        # Our llm_chain memory stores under: chat:{session_id}:history
        cache_delete(f"chat:{session_id}:history")

        return {"success": True, "data": {"session_id": session_id}, "message": "Chat history cleared"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("clear_chat failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to clear chat") from exc
