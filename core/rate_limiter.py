"""UMAY Rate Limiter — operational safety limits.

Prevents runaway automation by limiting:
- Hourly email sends
- Daily email sends
- API call rates
- Tool execution rates

Usage:
    from core.rate_limiter import check_rate_limit, record_usage
"""
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateLimit:
    """A single rate limit rule."""
    name: str
    max_count: int
    window_seconds: int
    description: str = ""


# Default limits
DEFAULT_LIMITS = [
    RateLimit("email_hourly", 5, 3600, "Max 5 emails per hour"),
    RateLimit("email_daily", 20, 86400, "Max 20 emails per day"),
    RateLimit("tool_calls_minute", 30, 60, "Max 30 tool calls per minute"),
    RateLimit("api_chat_minute", 20, 60, "Max 20 chat API calls per minute"),
    RateLimit("web_search_minute", 10, 60, "Max 10 web searches per minute"),
]


class RateLimiter:
    """Thread-safe in-memory rate limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        self._usage: dict[str, list[float]] = defaultdict(list)
        self._limits: dict[str, RateLimit] = {l.name: l for l in DEFAULT_LIMITS}

    def check(self, limit_name: str) -> dict:
        """Check if an operation is allowed under the rate limit.
        
        Returns:
            {"allowed": bool, "remaining": int, "retry_after": float|None, "limit": RateLimit}
        """
        limit = self._limits.get(limit_name)
        if not limit:
            return {"allowed": True, "remaining": 999, "retry_after": None, "limit": None}

        now = time.time()
        cutoff = now - limit.window_seconds

        with self._lock:
            # Clean old entries
            self._usage[limit_name] = [
                t for t in self._usage[limit_name] if t > cutoff
            ]
            count = len(self._usage[limit_name])
            remaining = max(0, limit.max_count - count)

            if count >= limit.max_count:
                # Find when the oldest entry in window will expire
                oldest = min(self._usage[limit_name])
                retry_after = oldest + limit.window_seconds - now
                return {
                    "allowed": False,
                    "remaining": 0,
                    "retry_after": round(retry_after, 1),
                    "limit": limit,
                }

            return {
                "allowed": True,
                "remaining": remaining,
                "retry_after": None,
                "limit": limit,
            }

    def record(self, limit_name: str) -> None:
        """Record that an operation was performed."""
        with self._lock:
            self._usage[limit_name].append(time.time())

    def add_limit(self, limit: RateLimit) -> None:
        """Add or update a rate limit rule."""
        self._limits[limit.name] = limit

    def get_status(self) -> dict:
        """Get current status of all limits."""
        now = time.time()
        status = {}
        for name, limit in self._limits.items():
            cutoff = now - limit.window_seconds
            with self._lock:
                count = len([t for t in self._usage[name] if t > cutoff])
            status[name] = {
                "used": count,
                "max": limit.max_count,
                "window": limit.window_seconds,
                "description": limit.description,
            }
        return status


# Global singleton
_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def check_rate_limit(limit_name: str) -> dict:
    """Check if an operation is allowed."""
    return get_rate_limiter().check(limit_name)


def record_usage(limit_name: str) -> None:
    """Record that an operation was performed."""
    get_rate_limiter().record(limit_name)


def is_blocked(limit_name: str) -> bool:
    """Quick check: is this operation blocked?"""
    return not check_rate_limit(limit_name)["allowed"]
