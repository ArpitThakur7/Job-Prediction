from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from backend.redis_client import cache_delete
from backend.services.llm_chain import ask_question, _DualLayerConversationMemory

logger = logging.getLogger("backend.routes.chat")

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    session_id: str
    primary_provider: Optional[str] = "groq"
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    pinecone_api_key: Optional[str] = None


@router.post("/chat/", response_model=Dict[str, Any])
async def chat(
    payload: ChatRequest,
    x_groq_api_key: Optional[str] = Header(None),
    x_openrouter_api_key: Optional[str] = Header(None),
    x_pinecone_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Accept: {question: str, session_id: str, primary_provider: str, ...}
    Run multi-provider auto-fallback RAG chain with Groq, Gemini, OpenRouter, OpenAI, or Anthropic.
    Retains continuous context memory per session.
    """
    try:
        question = (payload.question or "").strip()
        session_id = (payload.session_id or "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        result = ask_question(
            question=question,
            session_id=session_id,
            groq_api_key=x_groq_api_key or payload.groq_api_key,
            openai_api_key=payload.openai_api_key,
            anthropic_api_key=payload.anthropic_api_key,
            gemini_api_key=payload.gemini_api_key,
            openrouter_api_key=x_openrouter_api_key or payload.openrouter_api_key,
            primary_provider=payload.primary_provider,
            pinecone_api_key=x_pinecone_api_key or payload.pinecone_api_key
        )

        return {
            "success": True,
            "data": {
                "answer": result.get("answer") or "",
                "session_id": session_id,
                "sources": result.get("sources") or [],
                "provider_used": result.get("provider_used") or "Local RAG Engine",
                "fallback_triggered": result.get("fallback_triggered") or False,
            },
            "message": f"Chat response generated via {result.get('provider_used')}",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("chat failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate chat response") from exc


@router.delete("/chat/{session_id}")
async def clear_chat(session_id: str) -> Dict[str, Any]:
    """
    Clear conversation memory history for the session from both Redis and memory fallback.
    """
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        # Clear dual-layer memory
        mem = _DualLayerConversationMemory(session_id=session_id)
        mem.clear()

        return {"success": True, "data": {"session_id": session_id}, "message": "Chat history cleared"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("clear_chat failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to clear chat") from exc
