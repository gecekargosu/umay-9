"""UMAY Token / Context Budget— central estimator and budget-check
abstraction.

STEP-04.1 (see docs/development/CHAT_STEP04_AUDIT.md and CHAT_ROADMAP.md).

Scope discipline (explicit user instruction for this STEP): this module
only builds the reusable estimator/budget abstraction. It is deliberately
**not** wired into `ui/panel_server.py: chat_api()` or
`core/model_providers.py` yet — that integration is STEP-04.3's job.
Nothing outside this file is touched by STEP-04.1.

Key finding from the STEP-04.0 audit: Ollama's non-streaming `/api/chat`
response already includes real `prompt_eval_count` / `eval_count` fields —
genuine provider-reported usage, not an estimate. `core/model_providers.py`
currently reads that response and discards those two fields (confirmed by
direct source read in the audit). `usage_from_ollama_response()` below is
built to capture that real data once STEP-04.3 wires it in. For anything
where no real usage exists yet (most importantly: a *pre-flight* check
before a model call, so a warning can fire before the call happens), the
`estimate_*` functions provide a clearly-labeled ESTIMATE — never presented
as exact, per spec's own "tahmini gerçek kullanım gibi gösterme" rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Estimation (used only when real usage isn't available yet)
# ---------------------------------------------------------------------------

# Rough chars-per-token heuristic. Not model- or tokenizer-specific — good
# enough for a pre-flight ESTIMATE, never presented as exact. Turkish and
# other non-English text may tokenize somewhat differently than a fixed
# ratio assumes; that's a documented limitation of this estimate, not a
# silently-ignored one.
CHARS_PER_TOKEN_ESTIMATE = 4


def estimate_tokens(text: str) -> int:
    """Rough token estimate for a single string. Callers must treat this as
    an ESTIMATE (see TokenUsage.estimated), never as real usage."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough total token estimate across a list of chat messages (system +
    history + user, etc). Sums each message's `content` string.

    Does NOT attempt to account for an `images` payload (base64 image
    tokens are provider/model-specific and out of scope for a
    text-length heuristic) — a message carrying an image will therefore be
    under-estimated. This is a known, documented gap, not a silent
    assumption that images cost zero tokens; STEP-04.3 (chat integration)
    should account for this explicitly if/when image turns need budgeting.
    """
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
    return total


# ---------------------------------------------------------------------------
# Usage — real (provider-reported) or estimated, always distinguishable
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    """A token usage figure, tagged with where it came from. `estimated`
    must always be checked before treating `input_tokens`/`output_tokens`
    as ground truth."""
    input_tokens: int
    output_tokens: int = 0
    cached_tokens: int = 0
    source: str = "estimate"  # "ollama" | "estimate"
    estimated: bool = True

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "total_tokens": self.total_tokens,
            "source": self.source,
            "estimated": self.estimated,
        }


def usage_from_ollama_response(response: dict[str, Any]) -> TokenUsage | None:
    """Extract REAL token usage from a raw Ollama `/api/chat` JSON response.

    Ollama's non-streaming response includes `prompt_eval_count` (input)
    and `eval_count` (output) when available. Returns `None` if neither
    field is present (e.g. a malformed or mocked response, or a provider
    other than Ollama) — callers should fall back to `estimate_usage()` in
    that case. Returning `None` makes that fallback an explicit caller
    decision rather than silently reporting a fabricated zero as real
    usage.
    """
    if not isinstance(response, dict):
        return None
    prompt_tokens = response.get("prompt_eval_count")
    output_tokens = response.get("eval_count")
    if prompt_tokens is None and output_tokens is None:
        return None
    return TokenUsage(
        input_tokens=prompt_tokens or 0,
        output_tokens=output_tokens or 0,
        cached_tokens=0,  # Ollama does not report a separate cached-token count
        source="ollama",
        estimated=False,
    )


def estimate_usage(messages: list[dict[str, Any]], reserved_output_tokens: int = 1024) -> TokenUsage:
    """Pre-flight ESTIMATE for use before a model call (e.g. STEP-04.3's
    warning path), when no real usage exists yet.

    `reserved_output_tokens` is a budgeted allowance for the anticipated
    reply, not a measurement — defaults to 1024, overridable per call.
    """
    return TokenUsage(
        input_tokens=estimate_messages_tokens(messages),
        output_tokens=reserved_output_tokens,
        cached_tokens=0,
        source="estimate",
        estimated=True,
    )


# ---------------------------------------------------------------------------
# Budget check
# ---------------------------------------------------------------------------

# Conservative default context-window size. NOT verified against any
# specific installed model's real limit — the STEP-04.0 audit flagged
# actual Ollama context-window behavior as UNKNOWN / REQUIRES LIVE
# VERIFICATION (no Ollama instance was available in this sandbox). Callers
# with better per-model information should pass an explicit `limit_tokens`
# rather than relying on this default for a specific model.
DEFAULT_CONTEXT_LIMIT_TOKENS = 8192

# Fraction of the limit at which callers should warn before it's reached.
DEFAULT_WARNING_RATIO = 0.8

STATUS_OK = "OK"
STATUS_WARNING = "WARNING"
STATUS_EXCEEDED = "EXCEEDED"


@dataclass
class BudgetCheck:
    status: str  # STATUS_OK | STATUS_WARNING | STATUS_EXCEEDED
    used_tokens: int
    limit_tokens: int
    ratio: float
    usage: TokenUsage

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "used_tokens": self.used_tokens,
            "limit_tokens": self.limit_tokens,
            "ratio": round(self.ratio, 3),
            "usage": self.usage.as_dict(),
        }


def check_budget(
    usage: TokenUsage,
    limit_tokens: int = DEFAULT_CONTEXT_LIMIT_TOKENS,
    warning_ratio: float = DEFAULT_WARNING_RATIO,
) -> BudgetCheck:
    """Compare a TokenUsage (real or estimated) against a context limit.

    Returns OK / WARNING / EXCEEDED. Never raises, never silently drops
    data — callers (STEP-04.3) decide what action to take for each status;
    this function only classifies.
    """
    used = usage.total_tokens
    limit_tokens = max(1, limit_tokens)
    ratio = used / limit_tokens
    if used > limit_tokens:
        status = STATUS_EXCEEDED
    elif ratio >= warning_ratio:
        status = STATUS_WARNING
    else:
        status = STATUS_OK
    return BudgetCheck(
        status=status, used_tokens=used, limit_tokens=limit_tokens,
        ratio=ratio, usage=usage,
    )
