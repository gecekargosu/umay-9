"""Tests for core/token_budget.py — STEP-04.1.

This module is deliberately standalone this STEP (not wired into
chat_api()/model_providers.py — that's STEP-04.3), so these tests only
import core.token_budget and exercise it directly.
"""
from core import token_budget as tb


class TestEstimateTokens:
    def test_empty_string_is_zero(self):
        assert tb.estimate_tokens("") == 0

    def test_short_string_is_at_least_one(self):
        assert tb.estimate_tokens("hi") == 1

    def test_scales_with_length(self):
        short = tb.estimate_tokens("a" * 40)
        long = tb.estimate_tokens("a" * 400)
        assert long > short
        assert long == pytest_approx_ratio(short, 10)


def pytest_approx_ratio(base, factor):
    # helper: 400 chars / 4 == 100, 40 chars / 4 == 10 -> ratio 10
    return base * factor


class TestEstimateMessagesTokens:
    def test_empty_list(self):
        assert tb.estimate_messages_tokens([]) == 0

    def test_sums_across_messages(self):
        messages = [
            {"role": "system", "content": "x" * 40},
            {"role": "user", "content": "x" * 40},
        ]
        total = tb.estimate_messages_tokens(messages)
        assert total == tb.estimate_tokens("x" * 40) * 2

    def test_ignores_non_string_content_without_crashing(self):
        messages = [{"role": "user", "content": {"weird": "structure"}}]
        # Should not raise; non-string content contributes 0
        assert tb.estimate_messages_tokens(messages) == 0

    def test_missing_content_key_does_not_crash(self):
        messages = [{"role": "user"}]
        assert tb.estimate_messages_tokens(messages) == 0


class TestUsageFromOllamaResponse:
    def test_real_usage_extracted(self):
        response = {
            "message": {"content": "cevap"},
            "prompt_eval_count": 120,
            "eval_count": 45,
        }
        usage = tb.usage_from_ollama_response(response)
        assert usage is not None
        assert usage.input_tokens == 120
        assert usage.output_tokens == 45
        assert usage.source == "ollama"
        assert usage.estimated is False
        assert usage.total_tokens == 165

    def test_returns_none_when_fields_absent(self):
        response = {"message": {"content": "cevap"}}
        assert tb.usage_from_ollama_response(response) is None

    def test_returns_none_for_non_dict_input(self):
        assert tb.usage_from_ollama_response("not a dict") is None
        assert tb.usage_from_ollama_response(None) is None

    def test_partial_fields_still_extracted(self):
        # Only prompt_eval_count present (e.g. a streamed/partial response)
        response = {"prompt_eval_count": 50}
        usage = tb.usage_from_ollama_response(response)
        assert usage is not None
        assert usage.input_tokens == 50
        assert usage.output_tokens == 0
        assert usage.estimated is False


class TestEstimateUsage:
    def test_marks_as_estimated(self):
        messages = [{"role": "user", "content": "merhaba"}]
        usage = tb.estimate_usage(messages)
        assert usage.estimated is True
        assert usage.source == "estimate"

    def test_default_reserved_output(self):
        usage = tb.estimate_usage([])
        assert usage.output_tokens == 1024

    def test_custom_reserved_output(self):
        usage = tb.estimate_usage([], reserved_output_tokens=200)
        assert usage.output_tokens == 200

    def test_input_tokens_reflect_messages(self):
        messages = [{"role": "user", "content": "x" * 400}]
        usage = tb.estimate_usage(messages)
        assert usage.input_tokens == 100  # 400 / 4


class TestTokenUsageDataclass:
    def test_total_tokens_property(self):
        usage = tb.TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150

    def test_as_dict_shape(self):
        usage = tb.TokenUsage(input_tokens=10, output_tokens=5, source="ollama", estimated=False)
        d = usage.as_dict()
        assert d == {
            "input_tokens": 10,
            "output_tokens": 5,
            "cached_tokens": 0,
            "total_tokens": 15,
            "source": "ollama",
            "estimated": False,
        }


class TestCheckBudget:
    def test_ok_status_when_well_under_limit(self):
        usage = tb.TokenUsage(input_tokens=100, output_tokens=50)
        result = tb.check_budget(usage, limit_tokens=8192)
        assert result.status == tb.STATUS_OK

    def test_warning_status_at_threshold(self):
        # 80% of 1000 = 800
        usage = tb.TokenUsage(input_tokens=800, output_tokens=0)
        result = tb.check_budget(usage, limit_tokens=1000, warning_ratio=0.8)
        assert result.status == tb.STATUS_WARNING

    def test_ok_status_just_under_threshold(self):
        usage = tb.TokenUsage(input_tokens=799, output_tokens=0)
        result = tb.check_budget(usage, limit_tokens=1000, warning_ratio=0.8)
        assert result.status == tb.STATUS_OK

    def test_exceeded_status_over_limit(self):
        usage = tb.TokenUsage(input_tokens=1200, output_tokens=0)
        result = tb.check_budget(usage, limit_tokens=1000)
        assert result.status == tb.STATUS_EXCEEDED

    def test_exceeded_at_exactly_limit_is_not_exceeded(self):
        # used == limit should be WARNING (at capacity), not EXCEEDED
        # (EXCEEDED means over, not at)
        usage = tb.TokenUsage(input_tokens=1000, output_tokens=0)
        result = tb.check_budget(usage, limit_tokens=1000)
        assert result.status == tb.STATUS_WARNING
        assert result.status != tb.STATUS_EXCEEDED

    def test_default_limit_used_when_not_specified(self):
        usage = tb.TokenUsage(input_tokens=10, output_tokens=10)
        result = tb.check_budget(usage)
        assert result.limit_tokens == tb.DEFAULT_CONTEXT_LIMIT_TOKENS

    def test_never_raises_on_zero_limit(self):
        usage = tb.TokenUsage(input_tokens=10, output_tokens=0)
        result = tb.check_budget(usage, limit_tokens=0)
        assert result.status == tb.STATUS_EXCEEDED
        assert result.limit_tokens == 1  # clamped to avoid division by zero

    def test_as_dict_shape(self):
        usage = tb.TokenUsage(input_tokens=10, output_tokens=5)
        result = tb.check_budget(usage, limit_tokens=100)
        d = result.as_dict()
        assert set(d.keys()) == {"status", "used_tokens", "limit_tokens", "ratio", "usage"}
        assert d["usage"]["input_tokens"] == 10

    def test_end_to_end_real_ollama_usage_through_budget_check(self):
        """Realistic flow: a captured Ollama response -> real usage -> budget check."""
        response = {"prompt_eval_count": 7000, "eval_count": 500}
        usage = tb.usage_from_ollama_response(response)
        result = tb.check_budget(usage, limit_tokens=8192)
        assert result.usage.source == "ollama"
        assert result.usage.estimated is False
        assert result.used_tokens == 7500
        assert result.status == tb.STATUS_WARNING  # 7500/8192 ≈ 0.915 >= 0.8
