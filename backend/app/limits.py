"""A small per-process rate limiter (sliding window), used as FastAPI dependencies.

Counters live in memory, so with several worker processes each one counts separately.
That is fine at this size; use Redis if you ever need exact global limits.
"""
import threading
import time
from collections import deque

from fastapi import HTTPException

UNITS = {"second": 1, "minute": 60, "hour": 3600}


def parse_rate(rate: str):
    """'20/minute' -> (20, 60 seconds)."""
    count, _, unit = rate.partition("/")
    return int(count), UNITS[unit.strip().lower()]


class SlidingWindowLimiter:
    def __init__(self, max_keys: int = 20000):
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def check(self, key: str, rate: str) -> None:
        """Count one request for this key, or raise HTTP 429 if it is over the rate."""
        limit, window = parse_rate(rate)
        now = time.monotonic()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] >= window:
                q.popleft()
            if len(q) >= limit:
                retry = max(1, int(window - (now - q[0])) + 1)
                raise HTTPException(429, "Too many requests. Please slow down.", headers={"Retry-After": str(retry)})
            q.append(now)
            if len(self._hits) > self._max_keys:          # bound memory if someone sprays many IPs
                self._evict(now)

    def _evict(self, now: float) -> None:
        stale = [k for k, q in self._hits.items() if not q or now - q[-1] > 3600]
        for k in stale:
            del self._hits[k]
        if len(self._hits) > self._max_keys:               # still too many: drop the least recently used half
            for k in sorted(self._hits, key=lambda k: self._hits[k][-1])[: len(self._hits) // 2]:
                del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()
