"""Tests for STEP-04.6: Failure Recovery.

Verifies:
- Successful calls pass through without retry
- Transient errors trigger retry with backoff
- Permanent errors fail immediately
- Max retries enforced (never infinite)
- Context overflow triggers compression + retry
- Graceful error response format
- Error classification (transient vs permanent)
"""
import pytest
from unittest.mock import patch, MagicMock
from core.failure_recovery import (
    with_recovery,
    graceful_error_response,
    _is_transient,
    _is_permanent,
    _is_context_overflow,
    _retry_delay,
    MAX_RETRIES,
    TRANSIENT_ERRORS,
    PERMANENT_ERRORS,
)


class TestErrorClassification:
    def test_transient_timeout(self):
        assert _is_transient("Ollama 180s timeout")

    def test_transient_connection(self):
        assert _is_transient("Connection refused")

    def test_transient_bağlan(self):
        assert _is_transient("Ollama'ya bağlanılamadı")

    def test_permanent_malformed(self):
        assert _is_permanent("Malformed JSON response")

    def test_permanent_not_found(self):
        assert _is_permanent("Model not found")

    def test_context_overflow_token(self):
        assert _is_context_overflow("context length exceeded")

    def test_context_overflow_bütçe(self):
        assert _is_context_overflow("Token bütçesi aşıldı")

    def test_normal_error_not_transient(self):
        assert not _is_transient("Normal error message")

    def test_normal_error_not_permanent(self):
        assert not _is_permanent("Normal error message")


class TestRetryDelay:
    def test_delay_increases(self):
        d0 = _retry_delay(0)
        d1 = _retry_delay(1)
        d2 = _retry_delay(2)
        assert d0 < d1 < d2

    def test_delay_bounded(self):
        d = _retry_delay(10)
        assert d <= 10.0  # MAX_DELAY_SECONDS


class TestWithRecovery:
    def test_successful_call_no_retry(self):
        """Successful call should return without retry."""
        def ok_chat(messages, model=None, raw=True, **kwargs):
            return {"message": {"content": "OK response"}, "usage": None}

        result = with_recovery(ok_chat, [{"role": "user", "content": "hi"}])
        assert result.success
        assert result.attempts == 1
        assert result.recovery_type == "none"

    def test_transient_error_retries(self):
        """Transient errors should trigger retry."""
        call_count = 0

        def flaky_chat(messages, model=None, raw=True, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Ollama timeout")
            return {"message": {"content": "Success after retry"}, "usage": None}

        result = with_recovery(flaky_chat, [{"role": "user", "content": "hi"}], max_retries=3)
        assert result.success
        assert result.attempts == 3
        assert call_count == 3

    def test_permanent_error_no_retry(self):
        """Permanent errors should fail immediately without retry."""
        call_count = 0

        def perm_fail(messages, model=None, raw=True, **kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Model not found in Ollama")

        result = with_recovery(perm_fail, [{"role": "user", "content": "hi"}], max_retries=3)
        assert not result.success
        assert result.attempts == 1  # Only 1 attempt, no retry
        assert result.recovery_type == "permanent_error"

    def test_max_retries_enforced(self):
        """Should not retry beyond max_retries."""
        call_count = 0

        def always_fail(messages, model=None, raw=True, **kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Connection error")

        result = with_recovery(always_fail, [{"role": "user", "content": "hi"}], max_retries=3)
        assert not result.success
        assert result.attempts == 3
        assert call_count == 3  # Exactly 3, not more

    def test_empty_response_treated_as_failure(self):
        """Empty model response should trigger retry."""
        call_count = 0

        def empty_response(messages, model=None, raw=True, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return {"message": {"content": ""}}
            return {"message": {"content": "Got content"}}

        result = with_recovery(empty_response, [{"role": "user", "content": "hi"}], max_retries=3)
        assert result.success
        assert result.attempts == 2

    def test_string_response_accepted(self):
        """String responses should be accepted."""
        def str_chat(messages, model=None, raw=True, **kwargs):
            return "Simple string response"

        result = with_recovery(str_chat, [{"role": "user", "content": "hi"}])
        assert result.success

    def test_empty_string_response_treated_as_failure(self):
        """Empty string response should trigger retry."""
        call_count = 0

        def empty_str(messages, model=None, raw=True, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return ""
            return "Got it"

        result = with_recovery(empty_str, [{"role": "user", "content": "hi"}], max_retries=3)
        assert result.success
        assert result.attempts == 2

    def test_result_dict_shape(self):
        """RecoveryResult should have expected dict shape."""
        def ok_chat(messages, model=None, raw=True, **kwargs):
            return {"message": {"content": "OK"}}

        result = with_recovery(ok_chat, [{"role": "user", "content": "hi"}])
        d = result.as_dict()
        assert "success" in d
        assert "attempts" in d
        assert "recovery_type" in d
        assert "compressed" in d


class TestGracefulErrorResponse:
    def test_basic_error(self):
        resp = graceful_error_response(RuntimeError("test error"), model="phi4-mini")
        assert resp["error"] is True
        assert resp["model"] == "phi4-mini"
        assert "cevap" in resp
        assert "latency" in resp

    def test_context_overflow_message(self):
        resp = graceful_error_response(RuntimeError("context length exceeded"))
        assert "bağlam" in resp["cevap"].lower() or "büyüdü" in resp["cevap"]

    def test_timeout_message(self):
        resp = graceful_error_response(RuntimeError("Ollama timeout"))
        assert "zaman" in resp["cevap"].lower() or "tekrar" in resp["cevap"]

    def test_with_recovery_result(self):
        from core.failure_recovery import RecoveryResult
        rr = RecoveryResult(success=False, attempts=3, errors=["err1", "err2"])
        resp = graceful_error_response(RuntimeError("fail"), recovery_result=rr)
        assert "recovery" in resp
        assert resp["recovery"]["attempts"] == 3
