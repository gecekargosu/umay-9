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
