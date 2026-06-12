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
    app.include_router(jobs_router, prefix="", tags=["jobs"])
    app.include_router(resume_router, prefix="", tags=["resume"])
    app.include_router(match_router, prefix="", tags=["match"])
    app.include_router(chat_router, prefix="", tags=["chat"])

    @app.get("/health")
    async def health() -> Any:
        """
        Health check endpoint.
        """
        return {
            "success": True,
            "data": {
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
            },
            "message": "Service is healthy",
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
            "message": "Welcome",
        }

    return app


app = create_app()


@app.on_event("startup")
async def startup_event() -> None:
    """
    Application startup: connect MongoDB/Redis, initialize Pinecone, validate spaCy availability.
    """
    # MongoDB
    try:
        if not ping_db():
            logger.warning("MongoDB ping failed (startup will continue).")
        else:
            logger.info("MongoDB OK")
    except Exception:
        logger.exception("MongoDB startup check failed")

    # Redis
    try:
        if not ping_redis():
            logger.warning("Redis ping failed (startup will continue).")
        else:
            logger.info("Redis OK")
    except Exception:
        logger.exception("Redis startup check failed")

    # Pinecone
    try:
        initialize_pinecone()
        logger.info("Pinecone OK")
    except Exception:
        logger.exception("Pinecone initialization failed")

    # spaCy model load happens inside nlp_extractor module as best-effort.
    # We still import it here to trigger loading.
    try:
        import backend.services.nlp_extractor  # noqa: F401

        logger.info("spaCy OK (best-effort)")
    except Exception:
        logger.exception("spaCy startup load failed (best-effort)")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Application shutdown hook.
    """
    logger.info("Shutting down JOB-AI-PLATFORM backend.")
