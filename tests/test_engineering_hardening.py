"""Tests for engineering hardening modules: rate_limiter, idempotency, audit_timeline."""
import time
import pytest


class TestRateLimiter:
    """Rate limiter tests."""

    def test_check_within_limit(self):
        from core.rate_limiter import RateLimiter
        rl = RateLimiter()
        result = rl.check("tool_calls_minute")
        assert result["allowed"] is True
        assert result["remaining"] > 0

    def test_exceed_limit(self):
        from core.rate_limiter import RateLimiter
        from core.rate_limiter import RateLimit
        rl = RateLimiter()
        rl.add_limit(RateLimit("test_limit", 3, 60, "test"))
        
        # Use up all allowed
        rl.record("test_limit")
        rl.record("test_limit")
        rl.record("test_limit")
        
        # Should be blocked now
        result = rl.check("test_limit")
        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert result["retry_after"] > 0

    def test_unknown_limit_always_allowed(self):
        from core.rate_limiter import RateLimiter
        rl = RateLimiter()
        result = rl.check("nonexistent_limit")
        assert result["allowed"] is True

    def test_get_status(self):
        from core.rate_limiter import RateLimiter
        rl = RateLimiter()
        status = rl.get_status()
        assert "email_hourly" in status
        assert status["email_hourly"]["max"] == 5


class TestIdempotency:
    """Idempotency guard tests."""

    def test_first_operation_allowed(self):
        from core.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        assert guard.check("op_001") is False  # Not duplicate

    def test_duplicate_blocked(self):
        from core.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        guard.register("op_002")
        assert guard.check("op_002") is True  # Duplicate

    def test_different_keys_allowed(self):
        from core.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        guard.register("op_a")
        assert guard.check("op_b") is False  # Different key

    def test_clear(self):
        from core.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        guard.register("op_c")
        guard.clear()
        assert guard.check("op_c") is False  # Cleared


class TestAuditTimeline:
    """Audit timeline tests."""

    def test_empty_timeline(self):
        from core.audit_timeline import get_timeline, format_timeline
        events = get_timeline(task_id="nonexistent_task_xyz")
        assert events == []
        assert "No events found" in format_timeline(events)

    def test_format_timeline(self):
        from core.audit_timeline import format_timeline
        events = [
            {"time": 1700000000, "action": "test_start", "status": "RUNNING", "tool": "", "detail": "started", "task_id": "t1", "source": "test"},
            {"time": 1700000001, "action": "test_end", "status": "COMPLETED", "tool": "", "detail": "done", "task_id": "t1", "source": "test"},
        ]
        result = format_timeline(events)
        assert "test_start" in result
        assert "test_end" in result
        assert "Total: 2 events" in result
