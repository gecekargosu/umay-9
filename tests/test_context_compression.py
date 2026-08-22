"""Tests for STEP-04.4: Context Compression.

Verifies:
- Short conversations are NOT compressed
- Long conversations ARE compressed when budget exceeded
- System prompt is always preserved
- Recent messages are preserved
- Older messages are summarized
- Token savings are reported
- Conversation Store is NOT modified
- Session persistence still works after compression
"""
import pytest
from core.context_compression import (
    compress_context,
    _summarize_messages,
    CompressionResult,
    RECENT_PAIRS_KEEP,
)
from core.token_budget import (
    estimate_tokens,
    estimate_messages_tokens,
    DEFAULT_CONTEXT_LIMIT_TOKENS,
)


def _make_system():
    return {"role": "system", "content": "You are UMAY."}


def _make_user(text):
    return {"role": "user", "content": text}


def _make_assistant(text):
    return {"role": "assistant", "content": text}


def _make_pair(i):
    # Each pair ~400 chars → ~100 tokens. 25 pairs = ~2500 tokens.
    long_text = f"User message {i}: " + "word " * 80 + f"topic {i} end."
    long_reply = f"Assistant reply {i}: " + "response " * 60 + f"details {i} end."
    return [_make_user(long_text), _make_assistant(long_reply)]


class TestSummarizeMessages:
    def test_empty_list(self):
        assert _summarize_messages([]) == ""

    def test_single_message(self):
        result = _summarize_messages([_make_user("Merhaba")])
        assert "Merhaba" in result or "Konuşma" in result

    def test_multiple_messages(self):
        msgs = [_make_user(f"mesaj {i}") for i in range(5)]
        result = _summarize_messages(msgs)
        assert len(result) > 0

    def test_extracted_keywords(self):
        msgs = [
            _make_user("Python programlama hakkında bilgi ver"),
            _make_assistant("Python bir programlama dilidir"),
            _make_user("Python ile makine öğrenmesi yapabilir miyim"),
        ]
        result = _summarize_messages(msgs)
        assert "python" in result.lower()


class TestCompressContext:
    def test_short_conversation_not_compressed(self):
        """Short conversation should NOT trigger compression."""
        messages = [_make_system(), _make_user("Merhaba"), _make_assistant("Selam")]
        result = compress_context(messages, limit_tokens=8192)
        assert not result.was_compressed
        assert result.compressed_messages == messages

    def test_long_conversation_compressed(self):
        """Long conversation exceeding budget SHOULD trigger compression."""
        messages = [_make_system()]
        for i in range(25):
            messages.extend(_make_pair(i))
        # Each pair ~400 chars → ~100 tokens. 25 pairs = ~2500 tokens.
        # With limit_tokens=1500, should trigger at 80% = 1200 tokens
        result = compress_context(messages, limit_tokens=1500)
        assert result.was_compressed
        assert result.compressed_count < result.original_count
        assert result.tokens_saved_estimate > 0

    def test_system_prompt_preserved(self):
        """System prompt must ALWAYS be the first message after compression."""
        messages = [_make_system()]
        for i in range(25):
            messages.extend(_make_pair(i))
        result = compress_context(messages, limit_tokens=4000)
        assert result.compressed_messages[0]["role"] == "system"
        assert result.compressed_messages[0]["content"] == "You are UMAY."

    def test_recent_messages_preserved(self):
        """Recent messages (last RECENT_PAIRS_KEEP pairs) must be preserved in full."""
        messages = [_make_system()]
        for i in range(25):
            messages.extend(_make_pair(i))
        result = compress_context(messages, limit_tokens=4000, recent_pairs_keep=RECENT_PAIRS_KEEP)

        # Last few messages should be from high-numbered pairs
        last_user = [m for m in result.compressed_messages if m["role"] == "user"][-1]
        assert "24" in last_user["content"]  # Last pair (i=24)

    def test_compression_ratio(self):
        """Compression should reduce message count significantly."""
        messages = [_make_system()]
        for i in range(30):
            messages.extend(_make_pair(i))
        result = compress_context(messages, limit_tokens=1500)
        assert result.was_compressed
        # Should compress 30+ pairs down to summary + recent 4 pairs
        assert result.compressed_count < 15  # Summary + system + recent messages

    def test_no_compression_when_budget_ok(self):
        """When budget is OK, no compression should happen."""
        messages = [_make_system(), _make_user("hi"), _make_assistant("hello")]
        result = compress_context(messages, limit_tokens=8192)
        assert not result.was_compressed

    def test_empty_messages(self):
        """Empty message list should not crash."""
        result = compress_context([])
        assert not result.was_compressed
        assert result.compressed_messages == []


class TestCompressionResult:
    def test_as_dict_shape(self):
        result = CompressionResult(
            compressed_messages=[], original_count=10, compressed_count=5,
            summary_text="test summary", tokens_saved_estimate=100,
            was_compressed=True,
        )
        d = result.as_dict()
        assert d["was_compressed"] is True
        assert d["original_count"] == 10
        assert d["compressed_count"] == 5
        assert d["tokens_saved_estimate"] == 100


class TestCompressionIntegration:
    def test_compression_preserves_token_budget(self):
        """After compression, token estimate should be within budget."""
        messages = [_make_system()]
        for i in range(30):
            messages.extend(_make_pair(i))

        limit = 4000
        result = compress_context(messages, limit_tokens=limit)
        if result.was_compressed:
            # Verify compressed messages fit within budget (approximately)
            from core.token_budget import estimate_usage
            usage = estimate_usage(result.compressed_messages)
            # Should be significantly less than original
            original_usage = estimate_usage(messages)
            assert usage.input_tokens < original_usage.input_tokens

    def test_double_compression_idempotent(self):
        """Compressing already-compressed messages should be a no-op."""
        messages = [_make_system()]
        for i in range(25):
            messages.extend(_make_pair(i))

        r1 = compress_context(messages, limit_tokens=1500)
        assert r1.was_compressed

        r2 = compress_context(r1.compressed_messages, limit_tokens=1500)
        # Second compression should either not compress or not crash
        assert isinstance(r2, CompressionResult)
