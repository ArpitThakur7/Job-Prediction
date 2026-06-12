from __future__ import annotations

from typing import Any, Optional

from pymongo import MongoClient
from pymongo.database import Database

from backend.config import settings

_mongo_client: Optional[MongoClient] = None


def get_db() -> Database:
    """
    Get a MongoDB database instance.

    Returns:
        pymongo.database.Database: Database handle configured via settings.

    Raises:
        RuntimeError: If MongoDB connection cannot be established.
    """
    global _mongo_client
    if _mongo_client is None:
        try:
            _mongo_client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
            # Validate connection early
            _mongo_client.admin.command("ping")
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Failed to connect to MongoDB: {exc}") from exc

    return _mongo_client[settings.DB_NAME]


def get_collection(name: str) -> Any:
    """
    Get a collection from the configured database.

    Args:
        name: Collection name.

    Returns:
        pymongo.collection.Collection: Collection handle.
    """
    return get_db()[name]


def ping_db() -> bool:
    """
    Ping the MongoDB server.

    Returns:
        bool: True if reachable, otherwise False.
    """
    try:
        db = get_db()
        db.command("ping")
        return True
    except Exception:
        return False
