# CHAT_CHANGELOG

## STEP-01 — 2026-08-22 — Persistent Conversation Storage

**Added**
- `core/conversation_store.py` — SQLite-backed conversation/message store
  (`memory/conversations.db`, created on first use).
- `tests/test_conversation_store.py` — 8 tests, including a real two-process
  restart-persistence regression test.
- `docs/development/{CHAT_PROGRESS,CHAT_DECISIONS,CHAT_TESTS,CHAT_ISSUES,CHAT_CHANGELOG}.md`.

**Changed**
- `ui/panel_server.py`: `_get_session_history`, `_add_to_history`,
  `_clear_session` now delegate to `core/conversation_store.py` instead of
  an in-memory dict. Signatures and call sites unchanged.

**Removed**
- `ui/panel_server.py`: module-level `_chat_sessions: dict[str, list[dict]]`
  (dead code after the above — confirmed no other references via grep
  before removal).

**Fixed**
- Chat history no longer lost on process/server restart.

**Not changed / explicitly out of scope for this STEP**
- Conversation titles, project association, task-state wiring, history
  search/list UI, the mixed-attachment vision-branch bug (see
  CHAT_ISSUES.md) — all deferred to later STEPs per the roadmap.

## STEP-02 — 2026-08-22 — Chat → Task State Integration

**Added**
- `core/conversation_store.py`: `last_task_id` column (migrated in place),
  `set_last_task_id()`, `get_last_task_id()`.
- `tests/test_chat_task_state.py` — 3 tests.

**Changed**
- `ui/panel_server.py`: `chat_api()`'s `use_tools` branch now calls
  `core/task_state.py`'s `start_task()`/`finish_task()`; wrapped in
  try/except so tool/model failures end the task as FAILED instead of
  crashing with no record. JSON response gains `task_id` and
  `task_status` fields.

**Fixed**
- Agentic chat turns previously had zero persistent state tracking despite
  `task_state.py` already existing in the codebase for this purpose.
- Unhandled exceptions in the tool-calling path previously produced an
  unhandled 500 with no task record; now caught, logged as FAILED, and
  returned as a normal JSON error response.

**Not changed / explicitly out of scope for this STEP**
- Plain chat/vision turns still have no task_state entry (by design — see
  CHAT_DECISIONS.md).
- No PAUSED/WAITING_USER/CANCELLED states yet — deferred to the
  Pause/Resume STEP.

## STEP-03 — 2026-08-22 — Task Manager: Conversation → Task Listing

**Added**
- `core/task_state.py`: `list_tasks_for_workspace(workspace, limit)`.
- `ui/panel_server.py`: `GET /api/chat/tasks?session_id=...&limit=...`.
- `tests/test_task_manager.py` — 11 tests.

**Changed**
- Nothing existing modified — purely additive (new function, new route).

**Not changed / explicitly out of scope**
- No frontend rendering of the task list (API-only this STEP, see
  CHAT_ISSUES.md for the deferred UI item).

## STEP-04.5 — 2026-08-22 — Mixed-Attachment Bug Fix

**Fixed**
- `ui/panel_server.py`: vision branch of `chat_api()` now sends
  `att_context` (built from ALL attachments) to the Ollama vision API
  instead of raw `soru` (which only ever contained the user's typed
  question, not any attached PDF/code/text content). One-line change.

**Added**
- `tests/test_mixed_attachment_fix.py` — 5 tests (image+PDF, image+code,
  image+text, image+multiple-attachments, image-only regression check).
  Verified to fail against the pre-fix code before being finalized.

**Not changed**
- No other logic in the vision branch touched. No refactor.
  `core/attachment_engine.py: build_vision_message()` (the unused helper
  noted in the STEP-04.0 audit) was left as-is — adopting it instead of
  inline construction was flagged as an open decision, not required for
  this fix, and out of scope per "gereksiz refactor yapma."
