"""UMAY Failure Recovery — controlled retry and graceful degradation.

STEP-04.6: When model calls fail, recover gracefully instead of crashing.
Supports retry with exponential backoff, context overflow recovery via
compression, and graceful degradation on permanent failures.

Design principles (from STEP-04 audit §6 and blueprint §22/§23):
- Retry with bounded attempts (NEVER infinite loop)
- Exponential backoff between retries
- Context overflow → compress → retry (unique recovery path)
- Transient errors (timeout, connection) → retry
- Permanent errors (malformed response, auth) → graceful failure
- Never crash the application
- Always return a useful response to the user
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from core.token_budget import (
    estimate_usage,
    check_budget,
    DEFAULT_CONTEXT_LIMIT_TOKENS,
    STATUS_EXCEEDED,
    STATUS_WARNING,
)
from core.utils.logger import log

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 10.0
BACKOFF_MULTIPLIER = 2.0

# Error classification
TRANSIENT_ERRORS = (
    "timeout",
    "connection",
    "连接",
    "bağlan",
    "Timeout",
    "timeout",
)

PERMANENT_ERRORS = (
    "malformed",
    "invalid",
    "unauthorized",
    "permission",
    "not found",
)


# ---------------------------------------------------------------------------
# Recovery result
# ---------------------------------------------------------------------------

@dataclass
class RecoveryResult:
    """Result of a failure recovery attempt."""
    success: bool
    result: Any = None
    attempts: int = 0
    recovery_type: str = ""  # "retry" | "compress_retry" | "fallback" | "none"
    errors: list[str] = field(default_factory=list)
    compressed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "attempts": self.attempts,
            "recovery_type": self.recovery_type,
            "compressed": self.compressed,
            "errors": self.errors[:3],  # Limit for response size
        }


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

def _is_transient(error_msg: str) -> bool:
    """Check if an error is likely transient (worth retrying)."""
    msg_lower = error_msg.lower()
    return any(term.lower() in msg_lower for term in TRANSIENT_ERRORS)


def _is_permanent(error_msg: str) -> bool:
    """Check if an error is permanent (not worth retrying)."""
    msg_lower = error_msg.lower()
    return any(term.lower() in msg_lower for term in PERMANENT_ERRORS)


def _is_context_overflow(error_msg: str) -> bool:
    """Check if error indicates context window overflow."""
    msg_lower = error_msg.lower()
    overflow_terms = [
        "context", "token", "length", "too long", "exceed",
        "bütçe", "limit", "overflow", "truncat",
    ]
    return any(term in msg_lower for term in overflow_terms)


# ---------------------------------------------------------------------------
# Retry delay calculation
# ---------------------------------------------------------------------------

def _retry_delay(attempt: int) -> float:
    """Calculate exponential backoff delay for a given attempt number."""
    delay = BASE_DELAY_SECONDS * (BACKOFF_MULTIPLIER ** attempt)
    return min(delay, MAX_DELAY_SECONDS)


# ---------------------------------------------------------------------------
# Core recovery function
# ---------------------------------------------------------------------------

def with_recovery(
    chat_fn: Callable[..., Any],
    messages: list[dict[str, Any]],
    model: str | None = None,
    limit_tokens: int = DEFAULT_CONTEXT_LIMIT_TOKENS,
    max_retries: int = MAX_RETRIES,
    **kwargs,
) -> RecoveryResult:
    """Execute a chat function with automatic retry and failure recovery.

    Recovery strategy:
    1. Try the chat function
    2. On failure:
       a. If context overflow → compress messages → retry
       b. If transient error → retry with backoff
       c. If permanent error → return graceful failure
    3. Max retries enforced — never infinite loop

    Args:
        chat_fn: The function to call (e.g., engine.chat)
        messages: Message list (may be compressed on context overflow)
        model: Model name to use
        limit_tokens: Context window limit for overflow detection
        max_retries: Maximum number of retry attempts
        **kwargs: Additional arguments passed to chat_fn

    Returns:
        RecoveryResult with success status, result, and metadata
    """
    errors = []
    compressed = False
    current_messages = list(messages)  # Don't mutate original

    for attempt in range(max_retries):
        try:
            log(f"[RECOVERY] Attempt {attempt + 1}/{max_retries}")

            result = chat_fn(current_messages, model=model, raw=True, **kwargs)

            # Validate result is usable
            if isinstance(result, dict):
                content = result.get("message", {}).get("content", "")
                if not content:
                    raise RuntimeError("Model boş cevap döndürdü.")
            elif isinstance(result, str):
                if not result.strip():
                    raise RuntimeError("Model boş cevap döndürdü.")
            else:
                raise RuntimeError(f"Beklenmeyen model yanıtı tipi: {type(result)}")

            recovery_type = "retry" if attempt > 0 else ("compress_retry" if compressed else "none")

            return RecoveryResult(
                success=True,
                result=result,
                attempts=attempt + 1,
                recovery_type=recovery_type,
                errors=errors,
                compressed=compressed,
            )

        except Exception as exc:
            error_msg = str(exc)
            errors.append(error_msg)
            log(f"[RECOVERY] Attempt {attempt + 1} failed: {error_msg[:100]}")

            # Check if this is a permanent error — don't retry
            if _is_permanent(error_msg):
                log("[RECOVERY] Permanent error detected, not retrying")
                return RecoveryResult(
                    success=False,
                    attempts=attempt + 1,
                    recovery_type="permanent_error",
                    errors=errors,
                    compressed=compressed,
                )

            # Check if context overflow — try compression
            if _is_context_overflow(error_msg) and not compressed:
                log("[RECOVERY] Context overflow detected, attempting compression")
                from core.context_compression import compress_context

                compression = compress_context(current_messages, limit_tokens=limit_tokens)
                if compression.was_compressed:
                    current_messages = compression.compressed_messages
                    compressed = True
                    log(f"[RECOVERY] Compressed {compression.original_count} → {compression.compressed_count} messages, "
                        f"saved ~{compression.tokens_saved_estimate} tokens")
                    # Don't wait on compression — retry immediately
                    continue
                else:
                    log("[RECOVERY] Compression not possible or not needed")

            # For transient errors, wait before retry
            if attempt < max_retries - 1:
                delay = _retry_delay(attempt)
                log(f"[RECOVERY] Waiting {delay:.1f}s before retry")
                time.sleep(delay)

    # All retries exhausted
    return RecoveryResult(
        success=False,
        attempts=max_retries,
        recovery_type="exhausted",
        errors=errors,
        compressed=compressed,
    )


# ---------------------------------------------------------------------------
# Graceful error response
# ---------------------------------------------------------------------------

def graceful_error_response(
    error: Exception,
    model: str | None = None,
    recovery_result: RecoveryResult | None = None,
) -> dict[str, Any]:
    """Create a user-friendly error response that never crashes the API.

    Returns a dict matching the normal chat_api() response format so the
    frontend can render it without special handling.
    """
    error_msg = str(error)

    # User-friendly messages based on error type
    if _is_context_overflow(error_msg):
        friendly = "Konuşma bağlamı çok büyüdü. Yeni bir sohbet başlatmayı deneyin."
    elif _is_transient(error_msg):
        friendly = "Geçici bağlantı sorunu. Lütfen tekrar deneyin."
    elif _is_permanent(error_msg):
        friendly = "Model hatası oluştu. Lütfen daha sonra tekrar deneyin."
    elif "timeout" in error_msg.lower():
        friendly = "Model zaman aşımına uğradı. Daha kısa bir mesaj göndermeyi deneyin."
    elif "boş cevap" in error_msg.lower():
        friendly = "Model yanıt üretemedi. Lütfen sorunuzu yeniden ifade edin."
    else:
        friendly = "Bir hata oluştu. Lütfen tekrar deneyin."

    result = {
        "cevap": friendly,
        "model": model or "unknown",
        "gorev": "chat",
        "latency": {"total": 0, "router": 0, "model": 0},
        "error": True,
        "error_type": type(error).__name__,
    }

    if recovery_result:
        result["recovery"] = recovery_result.as_dict()

    return result
