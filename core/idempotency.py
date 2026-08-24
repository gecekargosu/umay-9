"""UMAY Idempotency Guard — prevents duplicate operations.

Ensures that the same operation (e.g., sending an email) is not
performed twice, even if retried due to network timeout or crash.

Usage:
    from core.idempotency import check_duplicate, register_operation
    
    # Before sending
    op_key = f"email:{to}:{subject_hash}"
    if check_duplicate(op_key):
        return {"error": "Duplicate operation blocked", "idempotent": True}
    
    # After successful send
    register_operation(op_key)
"""
import time
import threading
from typing import Optional


class IdempotencyGuard:
    """Thread-safe in-memory idempotency guard.
    
    Operations are tracked by key for a configurable TTL (default 1 hour).
    """

    def __init__(self, ttl_seconds: int = 3600):
        self._lock = threading.Lock()
        self._operations: dict[str, float] = {}
        self._ttl = ttl_seconds

    def check(self, key: str) -> bool:
        """Check if this operation was already performed.
        
        Returns True if duplicate (should be blocked).
        """
        now = time.time()
        with self._lock:
            self._cleanup(now)
            if key in self._operations:
                age = now - self._operations[key]
                if age < self._ttl:
                    return True  # Duplicate
                else:
                    # Expired — allow
                    del self._operations[key]
        return False

    def register(self, key: str) -> None:
        """Register that an operation was successfully performed."""
        with self._lock:
            self._operations[key] = time.time()

    def _cleanup(self, now: float) -> None:
        """Remove expired entries."""
        expired = [k for k, t in self._operations.items() if now - t > self._ttl]
        for k in expired:
            del self._operations[k]

    def clear(self) -> None:
        """Clear all tracked operations."""
        with self._lock:
            self._operations.clear()

    def status(self) -> dict:
        """Get current status."""
        with self._lock:
            self._cleanup(time.time())
            return {"tracked_operations": len(self._operations)}


# Global singleton
_guard: Optional[IdempotencyGuard] = None


def get_idempotency_guard() -> IdempotencyGuard:
    global _guard
    if _guard is None:
        _guard = IdempotencyGuard()
    return _guard


def check_duplicate(key: str) -> bool:
    """Check if this operation is a duplicate."""
    return get_idempotency_guard().check(key)


def register_operation(key: str) -> None:
    """Register a successful operation."""
    get_idempotency_guard().register(key)
