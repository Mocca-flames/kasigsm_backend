import time
from collections import defaultdict
from fastapi import Request, HTTPException
from app.config import settings


class InMemoryRateLimiter:
    def __init__(self):
        self._requests = defaultdict(list)  # key: (identifier, window_key)
        self._lock = False

    def is_allowed(self, identifier: str, limit: int, window_seconds: int) -> tuple[bool, dict]:
        now = time.time()
        cutoff = now - window_seconds
        key = (identifier, int(now // window_seconds))
        self._requests[identifier] = [t for t in self._requests[identifier] if t > cutoff]
        self._requests[identifier].append(now)
        # bucket by window
        window_key = int(now // window_seconds)
        key = (identifier, window_key)
        bucket = [t for t in self._requests.get(key, []) if t > cutoff]
        self._requests[key] = bucket
        count = len(bucket)
        allowed = count <= limit
        meta = {"limit": limit, "remaining": max(0, limit - count), "reset": cutoff + window_seconds}
        return allowed, meta


# single shared instance
auth_rate_limiter = InMemoryRateLimiter()
