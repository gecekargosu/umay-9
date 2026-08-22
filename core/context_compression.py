"""UMAY Context Compression — proactive context size management.

STEP-04.4: When the token budget approaches or exceeds the context limit,
compress older conversation history into a summary while preserving recent
messages and critical information.

Design principles (from STEP-04 audit §5 and roadmap):
- Compression is ONLY triggered when budget check indicates WARNING/EXCEEDED
- Never compress system prompt or current user message
- Preserve recent messages (last N pairs) in full
- Summarize older messages into a compact summary
- The summary replaces old messages in the model-facing context
- Full history is NEVER modified — compression is a model-facing view only
- Conversation Store (SQLite) is untouched — all original messages remain on disk
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.token_budget import (
    estimate_messages_tokens,
    estimate_usage,
    check_budget,
    DEFAULT_CONTEXT_LIMIT_TOKENS,
    DEFAULT_WARNING_RATIO,
    STATUS_OK,
    STATUS_WARNING,
    STATUS_EXCEEDED,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# How many recent message pairs to ALWAYS keep (never compress these)
RECENT_PAIRS_KEEP = 4

# Threshold ratio at which compression triggers (same as budget warning)
COMPRESSION_TRIGGER_RATIO = DEFAULT_WARNING_RATIO  # 0.8

# Maximum chars for the summary block (keeps it compact for the model)
MAX_SUMMARY_CHARS = 2000


# ---------------------------------------------------------------------------
# Compression result
# ---------------------------------------------------------------------------

@dataclass
class CompressionResult:
    """Result of a context compression operation."""
    compressed_messages: list[dict[str, Any]]
    original_count: int
    compressed_count: int
    summary_text: str
    tokens_saved_estimate: int
    was_compressed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "was_compressed": self.was_compressed,
            "original_count": self.original_count,
            "compressed_count": self.compressed_count,
            "summary_text": self.summary_text[:200] + "..." if len(self.summary_text) > 200 else self.summary_text,
            "tokens_saved_estimate": self.tokens_saved_estimate,
        }


# ---------------------------------------------------------------------------
# Summary generation (lightweight — no model call)
# ---------------------------------------------------------------------------

def _summarize_messages(messages: list[dict[str, Any]]) -> str:
    """Create a lightweight summary of older messages without calling a model.

    This is a keyword/extraction-based summary — fast, deterministic, and
    never fails. A model-based summary would be more natural but adds latency
    and a failure mode during the very situation we're trying to recover from
    (context overflow).
    """
    if not messages:
        return ""

    user_msgs = []
    assistant_msgs = []
    topics = set()

    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        if not isinstance(content, str) or not content.strip():
            continue

        # Extract first sentence as topic indicator
        first_sentence = content.split(".")[0].split("\n")[0].strip()[:150]

        if role == "user":
            user_msgs.append(first_sentence)
            # Extract potential keywords (Turkish + English)
            for word in content.split():
                if len(word) > 4 and word.isalpha():
                    topics.add(word.lower())
        elif role == "assistant":
            assistant_msgs.append(first_sentence)

    parts = []

    if user_msgs:
        parts.append(f"Konuşma özeti ({len(user_msgs)} kullanıcı mesajı):")
        # Include up to 5 most recent user messages' first sentences
        for msg in user_msgs[-5:]:
            parts.append(f"  - {msg}")

    if assistant_msgs:
        parts.append(f"Yanıtlar ({len(assistant_msgs)} mesaj):")
        for msg in assistant_msgs[-3:]:
            parts.append(f"  - {msg}")

    if topics:
        # Top keywords by frequency-like selection
        key_topics = sorted(topics, key=lambda t: -sum(1 for m in messages if t in m.get("content", "").lower()))[:10]
        parts.append(f"Anahtar kelimeler: {', '.join(key_topics)}")

    summary = "\n".join(parts)

    # Enforce max length
    if len(summary) > MAX_SUMMARY_CHARS:
        summary = summary[:MAX_SUMMARY_CHARS] + "\n[Özet kısaltıldı]"

    return summary


# ---------------------------------------------------------------------------
# Core compression function
# ---------------------------------------------------------------------------

def compress_context(
    messages: list[dict[str, Any]],
    limit_tokens: int = DEFAULT_CONTEXT_LIMIT_TOKENS,
    warning_ratio: float = COMPRESSION_TRIGGER_RATIO,
    recent_pairs_keep: int = RECENT_PAIRS_KEEP,
) -> CompressionResult:
    """Analyze message context and compress if needed.

    This function:
    1. Estimates current token usage
    2. Checks against budget
    3. If WARNING/EXCEEDED: compresses older messages into a summary
    4. Returns compressed message list (or original if no compression needed)

    The system prompt (first message) and recent messages are ALWAYS preserved.
    Only older user/assistant pairs are summarized.

    Args:
        messages: Full message list (system + history + user)
        limit_tokens: Context window limit
        warning_ratio: Threshold for triggering compression
        recent_pairs_keep: Number of recent pairs to preserve in full

    Returns:
        CompressionResult with compressed messages and metadata
    """
    original_count = len(messages)

    # Always keep: system prompt (index 0) + recent messages
    # System prompt is always first
    if not messages:
        return CompressionResult(
            compressed_messages=messages,
            original_count=0, compressed_count=0,
            summary_text="", tokens_saved_estimate=0,
            was_compressed=False,
        )

    system_msg = messages[0]
    non_system = messages[1:]  # everything after system prompt

    # Check if compression is needed
    usage = estimate_usage(messages)
    check = check_budget(usage, limit_tokens=limit_tokens, warning_ratio=warning_ratio)

    if check.status == STATUS_OK:
        # No compression needed
        return CompressionResult(
            compressed_messages=messages,
            original_count=original_count,
            compressed_count=original_count,
            summary_text="",
            tokens_saved_estimate=0,
            was_compressed=False,
        )

    # Compression needed — split into "keep" and "compress" portions
    max_recent_messages = recent_pairs_keep * 2  # pairs → individual messages

    if len(non_system) <= max_recent_messages:
        # Not enough old messages to compress — keep everything
        # (this shouldn't normally happen if budget is exceeded, but defensive)
        return CompressionResult(
            compressed_messages=messages,
            original_count=original_count,
            compressed_count=original_count,
            summary_text="",
            tokens_saved_estimate=0,
            was_compressed=False,
        )

    # Split: old messages to summarize, recent messages to keep
    old_messages = non_system[:-max_recent_messages]
    recent_messages = non_system[-max_recent_messages:]

    # Generate summary of old messages
    summary_text = _summarize_messages(old_messages)

    # Build compressed context: system + summary + recent
    summary_msg = {
        "role": "system",
        "content": f"[Önceki konuşma özeti — {len(old_messages)} mesaj özetlendi]\n{summary_text}\n[Özet sonu — son {recent_pairs_keep} çift mesaj aşağıda]"
    }

    compressed_messages = [system_msg, summary_msg] + recent_messages

    # Estimate tokens saved
    old_tokens = estimate_messages_tokens(old_messages)
    summary_tokens = estimate_messages_tokens([summary_msg])
    tokens_saved = max(0, old_tokens - summary_tokens)

    compressed_count = len(compressed_messages)

    return CompressionResult(
        compressed_messages=compressed_messages,
        original_count=original_count,
        compressed_count=compressed_count,
        summary_text=summary_text,
        tokens_saved_estimate=tokens_saved,
        was_compressed=True,
    )
