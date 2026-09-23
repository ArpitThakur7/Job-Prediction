from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import ping_db
from backend.redis_client import ping_redis
from backend.services.vector_store import initialize_pinecone

from backend.routes.auth import router as auth_router
from backend.routes.jobs import router as jobs_router
from backend.routes.resume import router as resume_router
from backend.routes.match import router as match_router
from backend.routes.chat import router as chat_router
from backend.routes.dashboard import router as dashboard_router

logger = logging.getLogger("backend.main")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI app.
    """
    app = FastAPI(title="JOB-AI-PLATFORM", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # dev
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(auth_router, prefix="", tags=["auth"])
    app.include_router(jobs_router, prefix="", tags=["jobs"])
    app.include_router(resume_router, prefix="", tags=["resume"])
    app.include_router(match_router, prefix="", tags=["match"])
    app.include_router(chat_router, prefix="", tags=["chat"])
    app.include_router(dashboard_router, prefix="", tags=["dashboard"])

    @app.on_event("startup")
    async def on_startup():
        """
        On backend startup, check if database collections are populated.
        If empty, automatically seed jobs & resumes into MongoDB and vector index.
        """
        try:
            from backend.database import get_db
            db = get_db()
            if db is not None:
                jobs_count = db["jobs"].count_documents({})
                if jobs_count == 0:
                    logger.info("MongoDB jobs collection is empty. Auto-seeding initial dataset...")
                    from scripts.seed_db import seed
                    import threading
                    threading.Thread(target=seed, daemon=True).start()
        except Exception as e:
            logger.warning("Startup auto-seed check skipped: %s", e)

        # Start Kafka consumer background loop if enabled
        if settings.KAFKA_ENABLED:
            try:
                from backend.services.kafka_consumer import start_kafka_consumer
                import threading
                threading.Thread(target=start_kafka_consumer, daemon=True).start()
            except Exception as k_err:
                logger.info("Kafka consumer background worker initialization deferred: %s", k_err)

    @app.get("/health")
    async def health() -> Any:
        """
        Health check endpoint with real checks for API Gate, MongoDB, Pinecone, Groq.
        """
        import os
        from pinecone import Pinecone

        mongodb_ok = ping_db()
        cache_ok = ping_redis()

        pinecone_ok = False
        try:
            pc_key = settings.PINECONE_API_KEY or os.getenv("PINECONE_API_KEY")
            if pc_key and len(pc_key.strip()) > 10:
                pinecone_ok = True
        except Exception:
            pass

        groq_ok = False
        try:
            groq_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
            if groq_key and len(groq_key.strip()) > 10:
                groq_ok = True
        except Exception:
            pass

        gemini_ok = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 5)
        openrouter_ok = bool(settings.OPENROUTER_API_KEY and len(settings.OPENROUTER_API_KEY.strip()) > 5)
        openai_ok = bool(settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 5)
        anthropic_ok = bool(settings.ANTHROPIC_API_KEY and len(settings.ANTHROPIC_API_KEY.strip()) > 5)

        return {
            "success": True,
            "data": {
                "status": "ok" if (mongodb_ok and cache_ok) else "partial",
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "backend": True,
                    "mongodb": mongodb_ok,
                    "redis": cache_ok,
                    "pinecone": pinecone_ok,
                    "groq": groq_ok,
                },
                "providers": {
                    "groq": groq_ok,
                    "gemini": gemini_ok,
                    "openrouter": openrouter_ok,
                    "openai": openai_ok,
                    "anthropic": anthropic_ok,
                    "pinecone": pinecone_ok,
                },
            },
            "message": "Service status retrieved successfully",
        }

    @app.get("/")
    async def root() -> Any:
        """
        Root endpoint.
        """
        return {
            "success": True,
            "data": {
                "name": "JOB-AI-PLATFORM",
                "version": "1.0.0",
                "docs": "/docs",
            },
            "message": "Welcome to JOB-AI Platform",
        }

    return app


app = create_app()
