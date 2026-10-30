"""
Small in-memory sliding-window rate limiter for sensitive routes (login, register,
password change). Per client IP, per route. Good enough for a single local process;
swap for Redis if the API is ever run with multiple workers.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Callable, Deque, Dict, Tuple

from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.max_requests = max_requests
        self.window = window_seconds
        self.clock = clock
        self._hits: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: Tuple[str, str]) -> float | None:
        """Record a request. Returns seconds to wait if over the limit, else None."""
        now = self.clock()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.max_requests:
                return self.window - (now - q[0])
            q.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# 10 attempts per 5 minutes per IP per route.
auth_limiter = SlidingWindowLimiter(max_requests=10, window_seconds=300)


async def limit_auth(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    wait = auth_limiter.hit((client, request.url.path))
    if wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again in a few minutes.",
            headers={"Retry-After": str(int(wait) + 1)},
        )
