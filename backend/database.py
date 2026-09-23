from __future__ import annotations

from typing import Any, Optional
import logging

from pymongo import MongoClient
from pymongo.database import Database

from backend.config import settings

logger = logging.getLogger("backend.database")
_mongo_client: Optional[MongoClient] = None


def get_db() -> Optional[Database]:
    """
    Get a MongoDB database instance. Safe fallback to None if MongoDB is offline.
    """
    global _mongo_client
    if _mongo_client is not None:
        try:
            _mongo_client.admin.command("ping")
        except Exception:
            _mongo_client = None

    if _mongo_client is None:
        uris = [settings.MONGO_URI, "mongodb://127.0.0.1:27017", "mongodb://localhost:27017"]
        for uri in uris:
            if not uri:
                continue
            try:
                client = MongoClient(uri, serverSelectionTimeoutMS=2000)
                client.admin.command("ping")
                _mongo_client = client
                break
            except Exception:
                continue

    if _mongo_client is None:
        logger.warning("MongoDB not reachable. System will use local memory fallback.")
        return None

    return _mongo_client[settings.DB_NAME]


# Alias for backward compatibility
get_database = get_db


def get_collection(name: str) -> Any:
    """
    Get a collection from the configured database.
    """
    db = get_db()
    if db is None:
        return None
    return db[name]


def ping_db() -> bool:
    """
    Ping the MongoDB server.
    """
    try:
        db = get_db()
        if db is None:
            return False
        db.command("ping")
        return True
    except Exception:
        return False


async def run_async_db(func, *args, **kwargs) -> Any:
    """
    Execute a synchronous MongoDB / I/O operation inside FastAPI's threadpool worker.
    Guarantees that PyMongo queries never block the asyncio event loop.
    """
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(func, *args, **kwargs)
