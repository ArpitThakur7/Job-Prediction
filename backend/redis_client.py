from __future__ import annotations

from typing import Optional

from redis import Redis

from backend.config import settings

_redis_client: Optional[Redis] = None


def get_redis() -> Redis:
    """
    Get a Redis client instance.

    Returns:
        redis.Redis: Redis client configured via settings.

    Raises:
        RuntimeError: If Redis cannot be instantiated/connected.
    """
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Validate connection early
            _redis_client.ping()
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Failed to connect to Redis: {exc}") from exc
    return _redis_client


def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    """
    Cache a string value in Redis.

    Args:
        key: Redis key.
        value: String value to cache.
        ttl: Time to live in seconds.
    """
    try:
        redis_client = get_redis()
        redis_client.set(name=key, value=value, ex=ttl)
    except Exception:
        # Cache failures should not break core API functionality
        return


def cache_get(key: str) -> Optional[str]:
    """
    Fetch a cached value from Redis.

    Args:
        key: Redis key.

    Returns:
        Cached string value or None.
    """
    try:
        redis_client = get_redis()
        val = redis_client.get(name=key)
        return val
    except Exception:
        return None


def cache_delete(key: str) -> None:
    """
    Delete a cached key.

    Args:
        key: Redis key.
    """
    try:
        redis_client = get_redis()
        redis_client.delete(key)
    except Exception:
        return


def ping_redis() -> bool:
    """
    Ping Redis.

    Returns:
        True if reachable, otherwise False.
    """
    try:
        get_redis().ping()
        return True
    except Exception:
        return False
