# CHAT_PROGRESS

## STEP-01 — Persistent Conversation Storage
Date: 2026-08-22
Status: **COMPLETE**

Problem: `ui/panel_server.py` kept all chat history in a module-level Python
dict (`_chat_sessions`). Every process restart erased all conversation
history — confirmed as a live bug (see CHAT_CURRENT_STATE.md §2), not a
guess, via a real two-process restart test before the fix (process A wrote
history and exited; process B, a fresh Python process, could not see it).

Fix: `core/conversation_store.py` — a SQLite-backed store (stdlib
`sqlite3`, no new dependency) with `get_history`, `add_message`,
`clear_conversation`, `list_conversations`. `ui/panel_server.py`'s three
existing helper functions (`_get_session_history`, `_add_to_history`,
`_clear_session`) were rewired to delegate to it, keeping their exact
original signatures and call sites unchanged — no other file needed to
change.

Verification: restart test now passes (process A writes, process B — a
genuinely separate OS process — reads back the same history). Full test
suite run: 447 passed, 5 failed, all 5 pre-existing/unrelated (see
CHAT_TESTS.md for the exact failures and why each is out of scope for this
STEP).

Next: STEP-02 — wire `chat_api()` to `core/task_state.py` (explicit
conversation/task state, currently absent from the live chat path).
