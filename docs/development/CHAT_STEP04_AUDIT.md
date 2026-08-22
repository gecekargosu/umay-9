# CHAT_STEP04_AUDIT — Token / Context Budget & Attachment Architecture

Date: 2026-08-22
Status: **AUDIT ONLY — no code changed this session.**
Scope: STEP-04.0 per "UMAY 9 — STEP-04 GELİŞTİRME TALİMATI". Base: the
STEP-01+02+03 FULL package (already applied in this working copy — not a
fresh extraction, but verified against the delivered zip's contents, which
were themselves independently re-tested before delivery).

Method: every claim below is from direct source reads this session
(files/line ranges noted), not from the prior Phase-0 audit's memory —
re-verified per this STEP's own "dokümanda yazana körü körüne güvenme"
instruction.

---

## 1. Token counting — **does not exist anywhere in the chat path**

Checked: `core/engine.py: chat()`, `core/model_providers.py`
(`OllamaProvider.chat()`, and the other two provider classes at lines 43
and 205), `ui/panel_server.py: chat_api()`.

- Ollama's non-streaming `/api/chat` response includes `prompt_eval_count`
  and `eval_count` (real token usage) in its JSON body. Confirmed by
  reading `OllamaProvider.chat()` (`core/model_providers.py` lines 105–131):
  it calls `r.json()`, then extracts **only** `message.content` and
  `message.tool_calls` — `prompt_eval_count`/`eval_count` are read off the
  response dict and then discarded. The real number the spec asks for
  ("provider-reported usage") is already arriving over the wire and is
  being thrown away, not merely uncomputed.
- `core/engine.py: chat()` (lines 184–260+) passes through whatever
  `provider.chat()` returns — since that never included token counts, none
  propagate further.
- `chat_api()` in `panel_server.py` only tracks wall-clock `latency`
  (`t_start`/`t_router`/`t_model_start` etc.) — no token field anywhere in
  its JSON response or in what it stores.

**Classification: P0.** This is exactly spec §25/R17, already flagged P0 in
the Phase-0 audit — now confirmed with the exact code location and, new
information this session: fixing it is cheaper than assumed, because real
usage data already exists in the Ollama response and just needs to be
plumbed through instead of computed/estimated from scratch.

## 2. Context assembly — one flat string, no component-level budget

Checked: `ui/panel_server.py: chat_api()` lines 475–486 (message building),
`core/attachment_engine.py: build_chat_context()` (lines 277–301),
`core/identity.py` (system prompt).

Current assembly for a normal (non-vision) turn:
```
messages = [
    {"role": "system", "content": UMAY_SYSTEM},      # ~4,960 chars, ~1,240 est. tokens, sent on EVERY request unchanged
    *history,                                          # up to 40 messages (STEP-01's max_pairs=20), each un-token-bounded
    {"role": "user", "content": att_context}           # user text + ALL attachments concatenated into one string
]
```
- `build_chat_context()` concatenates every attachment's extracted content
  with no total-budget check — it relies entirely on
  `attachment_engine.py`'s **per-file** `MAX_TEXT_CONTENT = 15000` chars
  cap (confirmed at `core/attachment_engine.py` line 27, applied at lines
  146/197/237/272). Per-file, not per-message: a turn with 3 large text
  attachments can still produce a ~45,000-char user message with no
  aggregate check.
- Conversation history (`core/conversation_store.py: get_history()`,
  STEP-01) trims by **message-pair count** (`max_pairs=20`, i.e. up to 40
  messages), not by character or token count. A history where several of
  those 40 messages themselves contain large `att_context` blobs (attachments
  from earlier turns) is not accounted for at all — STEP-01's trim was
  designed to bound message *count* for readability, not token budget; it
  was never intended as a token-safety mechanism, and this audit confirms
  it currently is the *only* mechanism doing that job.
- Tool results are the one component with a real, already-enforced ceiling:
  `core/agent.py: MAX_TOOL_RESULT_CHARS = 18_000` (line 67), applied in
  `_bounded_tool_result()` (line 146). **This one already works and should
  be reused/extended, not replaced** (spec Rule 0).
- System prompt: sent in full, identically, on **every** request (both the
  `use_tools`/plain branch at line 482 and the vision branch at line 513) —
  no caching, no conditional shortening. Confirmed real but scoped as P2/P3
  here (spec §51 caching is FAZ-10 per `CHAT_ROADMAP.md`, not this STEP's
  job) — noted for completeness, not proposed for fixing in STEP-04.

**Classification: P0** (aggregate budget missing is the STEP-04 mandate
itself) with **P2 sub-note** (system-prompt caching — out of this STEP's
scope, belongs to the caching STEP per the roadmap).

## 3. Context overflow handling — **none**

No code path in `chat_api()`, `core/engine.py`, or the three provider
`chat()` implementations checks message/content size against any model
context-window limit before sending. If a real Ollama model's context
window is exceeded:
- Ollama's own behavior (silently drop oldest context vs. error) was not
  testable in this sandbox (no live Ollama instance available — same
  environment limitation noted in STEP-01/02/03's `CHAT_TESTS.md`), so
  this is marked **UNKNOWN — REQUIRES LIVE VERIFICATION**, not assumed.
- What IS confirmed from source: UMAY's own code has no proactive check
  or warning before the call, and no handling specific to an
  overflow/truncation response after the call — `chat_api()`'s only
  `except Exception` (added in STEP-02, `panel_server.py` around the
  `use_tools` branch) catches connection/HTTP errors generically, and would
  treat a context-overflow error from Ollama (if it errors rather than
  truncates) the same as any other failure: mark the task_state entry
  FAILED and return a generic message. That's a safe fallback (no crash,
  no silent data loss) but not the specific, actionable warning spec §25
  asks for ("BÜYÜK İŞE BAŞLAMA... risk uyarısı").

**Classification: P0** for the missing proactive warning;
**existing partial safety net** (STEP-02's try/except) already prevents
the worst outcome (crash / permanently-RUNNING task) even though it wasn't
built for this specific failure mode.

## 4. Mixed-attachment bug — confirmed again, exact fix now scoped

This was flagged in the Phase-0 audit and logged in
`CHAT_ISSUES.md` (#1) after STEP-01, and the STEP-04 instructions
explicitly ask to re-verify and fix it in STEP-04.5. Re-confirmed this
session by reading the current code directly (`ui/panel_server.py` lines
486–519):

- `att_context = build_chat_context(attachments, soru)` (line 476) is
  computed **once**, up front, and correctly includes every attachment
  (image placeholder text + all non-image attachments' extracted content).
- The plain/tool-calling branch uses `att_context` correctly
  (`{"role": "user", "content": att_context}`, line 485).
- The vision branch (lines 505–519, `if has_image and vision_image:`)
  builds its own separate `vision_msgs` using **raw `soru`**, not
  `att_context`:
  ```python
  vision_msgs = [
      {"role": "system", "content": UMAY_SYSTEM},
      {"role": "user", "content": soru, "images": [vision_image]}
  ]
  ```
  Any PDF/code/text attachment sent alongside an image in the same turn is
  silently dropped from what the vision model sees — confirmed, not
  inferred; `att_context` is computed but never referenced again after
  line 476 anywhere in the vision branch.
- Root cause is a single missing substitution (`soru` → `att_context`) at
  one call site — the fix is small and isolated, exactly as the STEP-04
  instructions anticipated. No architectural change needed for this one;
  it's a targeted STEP-04.5 fix, not a redesign.
- Separately, `core/attachment_engine.py: build_vision_message()`
  (line 304) — an existing helper that is **not currently called from
  `chat_api()` at all** (the vision branch builds `vision_msgs` inline
  instead of using it) — has the same limitation baked in: it only accepts
  one `attachment` + `question`, no provision for other attachments' text.
  Worth deciding in STEP-04.5 whether to fix inline construction in
  `panel_server.py` (smaller diff) or to fix+adopt `build_vision_message()`
  (removes near-duplicate logic, more consistent with Rule 0's
  "extend, don't duplicate") — flagged as an open decision for STEP-04.5,
  not decided here since STEP-04.0 is audit-only.

**Classification: P0** (confirmed live bug, real data loss, already
flagged twice, now with an exact one-line root cause identified).

## 5. Summarization / compression — does not exist

Grepped `chat_api()` and `core/conversation_store.py` for any
summarization call — none found. `get_history()`'s trimming (STEP-01)
discards older messages from the *model-facing view* but never summarizes
them; nothing preserves "conversation identity / açık görevler / kararlar"
from trimmed-off history per spec §25/STEP-04.4's requirement. This is
real but explicitly gated by STEP-04's own instructions ("Eğer STEP-04
auditinde gerekli olduğu doğrulanırsa") — classification below reflects
that it's only needed once budget pressure is real, not for its own sake.

**Classification: P1** — needed to make STEP-04.2/04.3's budget warnings
actionable (a warning with no compression option is just a dead end for
the user), but not P0 on its own; can follow the token/budget mechanism
rather than precede it.

## 6. Failure-mode coverage (STEP-04.6 scope) — partially covered already

| Failure mode | Current handling | Verified how |
|---|---|---|
| Model/provider connection failure | Caught, `finish_task(...FAILED...)`, graceful JSON response | Read STEP-02's try/except in `chat_api()` |
| Oversized single attachment | Per-file `MAX_FILE_SIZE=20MB` check in `attachment_engine.py: process_upload()` | Read directly, confirmed real (Phase-0 audit already noted this; re-confirmed) |
| Oversized combined attachments in one turn | **Not handled** — no aggregate check | Confirmed absent (see §2) |
| Token estimation failure | N/A — no estimation exists yet to fail | — |
| Model context limit exceeded | **UNKNOWN — REQUIRES LIVE VERIFICATION** (no Ollama in this sandbox) | Not testable here |
| Malformed conversation / missing state | `_ensure_conversation()` auto-creates a row on any conversation_id (STEP-01) — no "missing" state is possible by construction | Read `core/conversation_store.py` |
| Summarization failure | N/A — no summarization exists yet | — |
| Response truncation | Not distinguished from a normal short response anywhere | Confirmed absent |

---

## Priority summary

| Priority | Items |
|---|---|
| **P0** | Token usage capture (real Ollama fields discarded, §1); aggregate context budget check before model calls (§2); proactive overflow warning (§3); mixed-attachment bug fix (§4) |
| **P1** | Context compression/summarization once budget pressure exists (§5); aggregate-attachment-size check (§6) |
| **P2** | System-prompt caching (§2, belongs to the caching STEP, not this one) |
| **P3** | — |
| **UNKNOWN** | Actual behavior when a real Ollama model's context window is exceeded (§3, §6) — needs live verification once a real Ollama instance is available; do not guess or fabricate this |

---

## Proposed STEP-04 sub-task order (adjusted from the instructions' default
order based on what this audit actually found)

1. **STEP-04.1 — Token Budget Abstraction.** Build the estimator/budget
   module. Because §1 found that Ollama already returns real
   `prompt_eval_count`/`eval_count`, this STEP should capture and surface
   *real* usage first (cheap, no estimation needed for Ollama calls) and
   only fall back to a clearly-labeled `ESTIMATE` for providers/paths that
   don't return real numbers (e.g. before a call, for the warning
   mechanism in 04.3). Reuses `core/agent.py: MAX_TOOL_RESULT_CHARS`'s
   existing pattern as precedent rather than inventing a new bounding
   convention.
2. **STEP-04.5 — Mixed-attachment bug fix.** Moved earlier than the
   instructions' default order deliberately: it's a small, isolated, already
   fully-diagnosed P0 fix with a one-line root cause (§4) — no reason to
   make it wait behind the larger budget-abstraction work, and fixing it
   first removes a confound from later attachment-budget testing in
   STEP-04.3.
3. **STEP-04.3 — Chat Context Budget Integration.** Wire the STEP-04.1
   estimator into `chat_api()`'s message assembly; add the pre-call warning
   path (§3).
4. **STEP-04.4 — Context Compression.** Only once 04.3's warning threshold
   exists to trigger it (per the instructions' own gating condition).
5. **STEP-04.6 — Failure recovery.** Extend STEP-02's existing try/except
   rather than replace it; add the model-context-limit-exceeded case
   specifically once real Ollama behavior can be verified (flagged UNKNOWN
   above — may need to stay partially speculative/defensive-coded if no
   live Ollama becomes available).
6. **STEP-04.7 — Full regression.**

First concrete code change if approved: **STEP-04.5 (mixed-attachment fix)
or STEP-04.1 (token budget module)** — both are ready to implement without
further investigation; recommend STEP-04.5 first since it's smaller,
fully isolated, and already caused real reported problems.

---

## Files read this session (for this audit)
`ui/panel_server.py` (chat_api, both branches), `core/attachment_engine.py`
(build_chat_context, build_vision_message, MAX_* constants),
`core/engine.py` (chat()), `core/model_providers.py` (all three chat()
implementations), `core/agent.py` (MAX_TOOL_RESULT_CHARS,
_bounded_tool_result), `core/conversation_store.py` (get_history),
`core/identity.py` (UMAY_SYSTEM size), `docs/development/CHAT_ISSUES.md`,
`CHAT_CHECKPOINT.md`, `CHAT_ROADMAP.md` (cross-checked, not blindly
trusted — every claim above traces to a source read this session, not to
the prior documents' claims alone).
