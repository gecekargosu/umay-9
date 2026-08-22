# CHAT_CURRENT_STATE — UMAY 9 Chat Subsystem Audit

Date: 2026-08-22
Auditor: Claude (Phase 0 — Discover/Analyze, per UMAY CHAT — MASTER ENGINEERING SPECIFICATION)
Base: repository "UMAY 9" (matches prior blueprint dated 2026-08-21, status "COMPLETED",
80 Python files / ~20,119 lines / 55 tools / 457 tests claimed passing — see
`docs/blueprint/00_MASTER_BLUEPRINT.md`). This document focuses specifically on the
Chat subsystem, cross-checked directly against source, not just prior reports.

---

## 1. Entry points — TWO separate, divergent chat implementations exist

### 1a. `core/chat.py` — legacy CLI chat (124 lines)
- Standalone terminal REPL (`python core/chat.py` style, `run()` loop with `input()`).
- Loads a fixed Turkish system prompt (identity: "UMAY", built by Cengiz Kılıç).
- Loads a static knowledge base by concatenating files under `knowledge/*.md|*.txt`
  (cap: 4000 chars total, naive truncation, no chunking/relevance ranking).
- History: single flat file `memory/history.json` (list of `{tarih, soru, cevap, model}`),
  full read/write on every turn, last 4 exchanges re-injected into context.
- Model selection via `core/router.py: model_sec()`.
- No tool calling, no attachments, no multimodal, no task state.
- **Status: functional but effectively a separate, unmaintained prototype.** Not used by
  the web UI. Real usage path is 1b.

### 1b. `ui/panel_server.py: /api/chat` — the actual production chat endpoint (~240 lines,
lines 406–645)
- Flask + Flask-SocketIO app (`ui/panel_server.py`, 988 lines total) serves a single-page
  panel UI (`ui/templates/panel.html`) plus this JSON endpoint.
- Per-request flow:
  1. Emit SocketIO `task_status` "thinking" event.
  2. If any attachment is an image → route straight to a vision model via direct Ollama
     `/api/chat` call (bypasses `core/engine.py`, bypasses tool calling).
  3. Otherwise call `core/router.py: model_sec(soru)` to pick a model + a task label
     (`gorev`) — a keyword/heuristic classifier, not an LLM-based intent classifier.
  4. `use_tools = gorev in ("coding", "agent")` — tools are enabled ONLY for those two
     task labels; everything else ("chat", etc.) never sees the tool registry.
  5. Attachments are flattened into one big text blob via
     `core/attachment_engine.py: build_chat_context()` and appended to the user message.
  6. Session history is read via `_get_session_history(session_id)`.
  7. `core/engine.py: chat()` is called once; if tool calls come back, exactly ONE round
     of tool execution is performed (`core/agent.py` helpers), the tool result is stuffed
     back as a message, and a hand-written string is produced from it — the model is
     **not** called again to compose a natural-language answer from the tool result in
     most branches (see §3 below).
  8. Response + latency breakdown returned as JSON; SocketIO status events fired
     throughout for UI feedback.

---

## 2. Conversation state & persistence — **P0 gap**

- `_chat_sessions: dict[str, list[dict]]` in `ui/panel_server.py` (module-level Python
  dict) is the **only** store for web-chat conversation history.
- Consequence: **all conversation history is lost on process restart** — there is no
  database, no file, no persistence layer for the actual product chat. This directly
  contradicts spec §11 ("History must survive application restart").
- No conversation IDs beyond a client-supplied `session_id` string; no title, no
  created/updated metadata, no per-conversation record at all — just a raw message list.
- Trimming: last 20 pairs (40 messages) kept, oldest silently dropped — no summarization
  (spec §9 requires SUMMARY + RELEVANT RETRIEVED CONTEXT, not just truncation).
- No conversation list, rename, delete, archive, restore, or search endpoints exist
  anywhere in `panel_server.py`'s route table (`/api/chat/clear` only clears one session's
  in-memory list — see §1's route dump).
- `core/archive.py` (267 lines) DOES implement `search_by_topic`, `search_by_date`,
  `search_keywords` — but it is a **separate subsystem** (looks unrelated to live chat
  session storage; needs confirmation whether/how it's populated from chat turns).
  **UNKNOWN — REQUIRES INVESTIGATION**: is `core/archive.py` ever invoked from
  `panel_server.py`? A grep of `panel_server.py` for `archive` should be done before
  assuming it is or isn't wired in.

## 3. Conversation state machine — missing

- `core/task_state.py` (156 lines) implements a real, JSONL-persisted task/checkpoint
  system (`start_task`, `waiting_for_approval`, statuses including `RUNNING`,
  `WAITING_FOR_APPROVAL`) — this is a solid P0 building block per spec §10/§24.
- **However, `chat_api()` never calls into `task_state.py` at all.** Chat turns have no
  state machine — no IDLE/THINKING/PLANNING/EXECUTING/WAITING_USER/PAUSED states
  attached to a conversation. `task_state.py` is currently only used by the
  planner/agent/approval flows that run outside the chat endpoint.
- `core/orchestrator.py` (268 lines) defines `AgentRole` / `AgentStatus` enums for a
  multi-agent orchestrator, but `chat_api()` never calls it either — the "PARTIAL" status
  in the prior blueprint is consistent with what's in the code: real dataclasses/enums
  exist, integration into the live chat path does not.

## 4. Tool / agent routing

- `core/router.py` (27 lines) does simple keyword-based task classification
  (`model_sec()`), not a real intent/task classifier per spec §20.
- Tool calling is gated by task label, single-shot (one tool call round, no multi-step
  tool chains inside `/api/chat`), and the composed answer after a tool call is built by
  hand-parsing the tool's JSON rather than asking the model to synthesize a reply — this
  will break for any tool whose result shape doesn't match the one hard-coded case
  (`status == "OK"` with a `lines` field) around line ~575 of `panel_server.py`.
- `core/planner.py` (988 lines) is a much more capable-looking reasoning/planning engine
  (ReasoningEngine → TaskDecomposer → ToolRouter → ExecutionEngine → SelfVerifier →
  RetryManager per its own docstring) but per the prior blueprint is "CODE ONLY" (no
  live-fire test) and, like the orchestrator, is **not called from `chat_api()`**.

## 5. Attachments / multimodal

- `core/attachment_engine.py` (348 lines): supports text/code passthrough, PDF (pypdf),
  DOCX (python-docx), XLSX/CSV (openpyxl/csv), images (base64 for vision models).
  `MAX_FILE_SIZE = 20MB`, `MAX_TEXT_CONTENT = 15000 chars`, `MAX_TABLE_ROWS = 100` — real,
  concrete limits already defined (good — matches spec §14's "define limits, don't
  copy another platform's").
- Multimodal orchestration is minimal: images take a hard fork to a direct vision-model
  Ollama call; every other attachment type is flattened into one text blob and appended
  to the user message — no per-type specialized processor pipeline
  (CLASSIFICATION → ROUTING → SPECIALIZED PROCESSING → SYNTHESIS per spec §16). A request
  mixing e.g. an image + a PDF + code in one turn will not be handled as a unified task —
  only the image path will fire, and if it fires the PDF/code content that was appended to
  `soru`/`att_context` never reaches the vision call (which sends only `soru` + the raw
  image, not `att_context` — see lines around "vision_msgs" in `panel_server.py`). This is
  a likely **bug**, not just a gap.

## 6. Memory

- `core/memory/memory_bridge.py` + `core/memory/memory_manager.py` (JSON-backed) and
  `rag/memory_manager.py` + `rag/chroma_manager.py` (ChromaDB, bge-m3 embeddings) exist
  and were previously verified (learn/recall/context test results cited in
  `docs/blueprint/09_MEMORY.md`).
- `chat_api()` does not appear to call memory recall/learn at all in the code read so far
  — session history is the only "memory" active in the live chat path.
  **UNKNOWN — REQUIRES INVESTIGATION**: confirm via grep whether `memory_bridge` is
  imported anywhere in `panel_server.py` or `core/engine.py`'s chat path.
- No separation of user/conversation/project/decision/procedural/knowledge/preference
  memory categories in the chat path specifically (spec §28) — what exists is one
  JSON store + one vector store, not category-separated.

## 7. Token / context budget

- No token/context budget tracking visible in `chat_api()`. `core/engine.py` return
  value is used only for `.message.content`; no usage/token accounting is surfaced to
  the user or logged per-turn in the chat path. Spec §25 (P0/high-priority) is
  effectively unimplemented for chat specifically.

## 8. Verification / testing

- `tests/test_panel_endpoints.py` and `tests/test_phase3_ollama_simulation.py` reference
  the chat API/endpoints (grep-confirmed). Existing test coverage for `chat_api()` itself
  has not yet been read in detail — **UNKNOWN — REQUIRES INVESTIGATION** (need to read
  these two files to know what's actually asserted before claiming any behavior is
  "tested").

## 9. Other spec areas relevant to Chat, not yet inspected in this pass

Flagged as **UNKNOWN — REQUIRES INVESTIGATION** rather than guessed:
- Voice (STT/TTS/barge-in) — no evidence found or looked for yet in the chat path.
- Live activity feed — partially present (SocketIO `task_status` events with
  icon/message/phase are already emitted throughout `chat_api()` — this is a real,
  working partial implementation of spec §40, worth reusing rather than replacing).
- Quick notes / post-its — not found in route table; likely missing.
- Notifications — not found in route table for chat specifically.
- Artifact management — no dedicated artifact store found; attachments upload dir
  (`uploads/`) exists but generated-output artifacts (vs. user uploads) not yet confirmed.
- Computer control / permissions / sandbox — `core/terminal_agent.py` (678 lines) and
  `core/approval_manager.py` (564 lines, JSONL-persisted, channel-agnostic
  WAITING_FOR_APPROVAL flow) both exist and look substantial, but again are not called
  from `chat_api()` — same integration gap pattern as planner/orchestrator/memory.

---

## 10. Cross-cutting pattern observed

The single biggest theme in this audit: **UMAY already has real, independently
substantial subsystems for nearly every spec requirement** (task_state, approval_manager,
orchestrator, planner, memory_bridge, archive) — but the live web chat endpoint
(`chat_api()` in `panel_server.py`) is a monolithic ~240-line function that talks
directly to `core/engine.py` and a couple of helpers, and does **not** call most of these
subsystems. The gap is integration/wiring and conversation persistence, not a lack of
underlying capability. This matches spec §7's warning against "a giant monolithic Chat
component" — that is close to the current state of `chat_api()` itself, even though the
surrounding codebase is not monolithic.

This reframes the likely safest implementation order: prioritize (1) conversation
persistence and (2) decomposing `chat_api()` to call the existing task_state /
orchestrator / memory subsystems that already work, before building any new subsystem
from scratch.
