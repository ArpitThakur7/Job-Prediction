from __future__ import annotations

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, List, Any

from backend.database import get_collection, ping_db

logger = logging.getLogger("backend.redis")

class MongoRedisAdapter:
    """
    MongoDB-backed adapter mimicking standard Redis client operations
    for caching and list operations (chat history).
    """
    def __init__(self) -> None:
        logger.warning("Initializing MongoDB-backed Redis Adapter (no Redis server required).")

    def ping(self) -> bool:
        return ping_db()

    def set(self, name: str, value: str, ex: Optional[int] = None) -> bool:
        try:
            col = get_collection("cache")
            expires_at = None
            if ex:
                expires_at = datetime.utcnow() + timedelta(seconds=ex)
            col.update_one(
                {"_id": name},
                {"$set": {"value": value, "expires_at": expires_at}},
                upsert=True
            )
            return True
        except Exception as exc:
            logger.error(f"MongoCache set error: {exc}")
            return False

    def get(self, name: str) -> Optional[str]:
        try:
            col = get_collection("cache")
            doc = col.find_one({"_id": name})
            if not doc:
                return None
            
            # Check expiration (lazy deletion)
            expires_at = doc.get("expires_at")
            if expires_at and expires_at < datetime.utcnow():
                col.delete_one({"_id": name})
                return None
                
            return doc.get("value")
        except Exception as exc:
            logger.error(f"MongoCache get error: {exc}")
            return None

    def delete(self, *names: str) -> int:
        try:
            col_cache = get_collection("cache")
            col_chat = get_collection("chat_history")
            count = 0
            for name in names:
                # Delete cache entry
                res1 = col_cache.delete_one({"_id": name})
                count += res1.deleted_count
                
                # Delete chat history if matching 'chat:{session_id}:history'
                if name.startswith("chat:") and name.endswith(":history"):
                    parts = name.split("chat:")
                    if len(parts) > 1:
                        session_id = parts[1].split(":history")[0]
                        res2 = col_chat.delete_many({"session_id": session_id})
                        count += res2.deleted_count
            return count
        except Exception as exc:
            logger.error(f"MongoCache delete error: {exc}")
            return 0

    # Redis List methods for _RedisConversationMemory
    def lrange(self, key: str, start: int, end: int) -> List[str]:
        try:
            parts = key.split("chat:")
            if len(parts) <= 1:
                return []
            session_id = parts[1].split(":history")[0]
            col = get_collection("chat_history")
            docs = list(col.find({"session_id": session_id}).sort("created_at", 1))
            raw_list = [json.dumps({"role": d["role"], "content": d["content"]}) for d in docs]
            
            length = len(raw_list)
            if start < 0:
                start = max(0, length + start)
            if end < 0:
                end = length + end
            else:
                end = min(length - 1, end)
                
            if start > end or start >= length:
                return []
            return raw_list[start:end+1]
        except Exception as exc:
            logger.error(f"MongoCache lrange error: {exc}")
            return []

    def rpush(self, key: str, *values: str) -> int:
        try:
            parts = key.split("chat:")
            if len(parts) <= 1:
                return 0
            session_id = parts[1].split(":history")[0]
            col = get_collection("chat_history")
            inserted = 0
            for val in values:
                obj = json.loads(val)
                col.insert_one({
                    "session_id": session_id,
                    "role": obj.get("role"),
                    "content": obj.get("content"),
                    "created_at": datetime.utcnow()
                })
                inserted += 1
            return inserted
        except Exception as exc:
            logger.error(f"MongoCache rpush error: {exc}")
            return 0

    def ltrim(self, key: str, start: int, end: int) -> bool:
        try:
            parts = key.split("chat:")
            if len(parts) <= 1:
                return False
            session_id = parts[1].split(":history")[0]
            col = get_collection("chat_history")
            docs = list(col.find({"session_id": session_id}).sort("created_at", 1))
            length = len(docs)
            if length == 0:
                return True
                
            if start < 0:
                start = max(0, length + start)
            if end < 0:
                end = length + end
            else:
                end = min(length - 1, end)
                
            keep_docs = docs[start:end+1]
            keep_ids = [d["_id"] for d in keep_docs]
            
            col.delete_many({"session_id": session_id, "_id": {"$nin": keep_ids}})
            return True
        except Exception as exc:
            logger.error(f"MongoCache ltrim error: {exc}")
            return False

    def expire(self, key: str, time: int) -> bool:
        return True


_redis_client = MongoRedisAdapter()

def get_redis() -> MongoRedisAdapter:
    """
    Get the MongoDB-backed Redis client adapter.
    """
    return _redis_client

def is_fake_redis() -> bool:
    """
    Returns False as we are now using a real database client.
    """
    return False

def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    try:
        get_redis().set(name=key, value=value, ex=ttl)
    except Exception:
        return

def cache_get(key: str) -> Optional[str]:
    try:
        return get_redis().get(name=key)
    except Exception:
        return None

def cache_delete(key: str) -> None:
    try:
        get_redis().delete(key)
    except Exception:
        return

def ping_redis() -> bool:
    """
    Ping Redis. Returns True if MongoDB is online.
    """
    return ping_db()

