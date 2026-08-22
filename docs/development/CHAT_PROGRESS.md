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

## STEP-02 — Chat → Task State Integration
Date: 2026-08-22
Status: **COMPLETE**

Problem: `core/task_state.py` (JSONL-persisted RUNNING/WAITING_FOR_APPROVAL/
COMPLETED/FAILED task tracking) already existed but `chat_api()` never
called it — every chat turn, including agentic/tool-using ones, had no
state tracking at all (CHAT_CURRENT_STATE.md §3).

Fix: in `ui/panel_server.py`'s `elif use_tools:` branch (the only branch
that runs multi-step agentic work), wrapped the existing logic with:
- `task_state.start_task(...)` at the start → task moves to RUNNING.
- `task_state.finish_task(..., status="COMPLETED", answer=cevap)` on success.
- `task_state.finish_task(..., status="FAILED", answer=...)` on any
  exception (previously an unhandled exception here would 500 with no
  task record and no graceful user-facing message at all — this is also a
  §32/§37 error-recovery improvement, not just state tracking).
- `core/conversation_store.py` gained `last_task_id` (migration-safe
  `ALTER TABLE`, verified against a simulated pre-migration DB with no data
  loss) plus `set_last_task_id`/`get_last_task_id`, so a conversation now
  links to the task_state task_id run on its behalf.
- API response now includes `task_id` and `task_status`.

Explicitly NOT done this STEP (deferred, see CHAT_ISSUES.md): full
IDLE/WAITING_USER/PAUSED/CANCELLED state machine, live pause/resume from
chat, and non-tool ("chat"/"vision") turns still have no task_state entry
— only agentic turns do, since those are the ones with real multi-step
work to track. Scope kept to what spec's own Rule U warns against
overbuilding.

Verification: 3 new tests (`tests/test_chat_task_state.py`), all passing,
using a fake local Ollama HTTP server (same pattern as
`test_phase3_ollama_simulation.py` — no real Ollama needed). One test
confirms the chat-created task_id is readable from a genuinely separate OS
process (not just a fresh Python object). Full suite: 450 passed, 5 failed
— same 5 pre-existing failures as STEP-01, zero new failures, 3 more tests
passing than STEP-01's baseline (the 3 new task-state tests).

Next: STEP-03 candidates per user's FAZ list — Task Manager / Task Planner
integration, or the mixed-attachment bug fix (smaller, isolated). Awaiting
direction.

## STEP-03 — Task Manager: Conversation → Task Listing
Date: 2026-08-22
Status: **COMPLETE**

Problem: `task_state.py`'s `list_tasks()` returns the latest event per
task_id globally, with no conversation/workspace filter — and worse,
`finish_task()` doesn't record `workspace` at all, so even the latest
event for a completed task has no conversation to filter by. STEP-02
already links a conversation to its *most recent* task_id
(`conversation_store.get_last_task_id`), but not to *all* of its tasks.

Investigation before coding (per this STEP's required "inspect first"
phase): confirmed via direct source read that `workspace` is present on
`start`, `checkpoint`, `waiting_for_approval`, and `resume` events but
absent from `finish` events — this is why a naive "latest event" filter
doesn't work and a scan is required.

Fix:
- `core/task_state.py`: new `list_tasks_for_workspace(workspace, limit)` —
  scans the full JSONL log once, merges all events per task_id (latest
  status/step wins, workspace/request/model carried forward from
  whichever earlier event had them), then filters by workspace. No new
  storage — reuses task_state's existing log as the single source of
  conversation↔task truth (see CHAT_DECISIONS.md for why a second table
  was rejected).
- `ui/panel_server.py`: new `GET /api/chat/tasks?session_id=...&limit=...`
  route, read-only, returns `{"session_id": ..., "tasks": [...]}`.

Explicitly not done (per this STEP's own "kapsam dışı" list): no frontend
UI rendering of the task list — kept to the API layer only, since wiring
`panel.html` would require touching UI code well beyond "smallest possible
change" and this STEP's spec explicitly forbids big UI redesign. Flagged
in CHAT_ISSUES.md as the natural next small addition.

Verification: 11 new tests (`tests/test_task_manager.py`) covering all 9
functional scenarios from the STEP-03 spec's test list (one conversation
w/ 1, 2, 3+ tasks; two independent conversations; status transitions;
completed/failed/pending-running visibility; unknown conversation → empty
list) plus 2 end-to-end tests against the real `chat_api()` → task_state
pipeline via the fake-Ollama-server pattern. All pass.

Baseline re-verified before claiming any regression count (per this
STEP's explicit "don't blindly trust the STEP-02 numbers" instruction):
ran the full suite fresh this session — pre-STEP-03 state (STEP-02's own
final state) was 450 passed / 5 failed, confirmed by re-running before
touching any code. Post-STEP-03: 461 passed / 5 failed — same 5 failures,
same causes, zero new failures.

Next: STEP-04 (Live Task Progress — multi-step, not just single-shot) or
STEP-05 (Pause/Resume, largest FAZ-1 item) per CHAT_ROADMAP.md.

## STEP-04.0 — Context/Token Audit (no code changed)
Date: 2026-08-22
Status: **COMPLETE (audit-only, per instruction to stop before STEP-04.1)**

Read directly (not from prior docs alone): `ui/panel_server.py` chat_api()
both branches, `core/attachment_engine.py`, `core/engine.py`,
`core/model_providers.py` (all 3 providers), `core/agent.py`,
`core/conversation_store.py`, `core/identity.py`.

Key findings (full detail in `CHAT_STEP04_AUDIT.md`):
- P0: Ollama already returns real `prompt_eval_count`/`eval_count` token
  usage in its response — the code reads the response and discards these
  fields without capturing them. Fixing this is cheaper than building an
  estimator from scratch.
- P0: no aggregate context-size budget anywhere — only per-file
  (`MAX_TEXT_CONTENT=15000` chars) and per-tool-result
  (`MAX_TOOL_RESULT_CHARS=18000` chars) caps exist; nothing bounds the
  total assembled message.
- P0: mixed-attachment bug re-confirmed with exact root cause — vision
  branch in `chat_api()` uses raw `soru` instead of the already-computed
  `att_context`, one-line fix, isolated.
- P0: no proactive overflow warning before a model call.
- P1: no summarization/compression mechanism (expected — gated behind
  budget mechanism existing first, per STEP-04's own instructions).
- UNKNOWN (honestly flagged, not guessed): actual Ollama behavior when a
  real context window is exceeded — no live Ollama in this sandbox.

Proposed order (deviates slightly from the instruction's default,
reasoned in the audit doc): 04.1 (token budget, capture real usage first)
→ 04.5 (mixed-attachment fix, moved earlier — small/isolated/already
diagnosed) → 04.3 (integration) → 04.4 (compression) → 04.6 (recovery) →
04.7 (regression).

**Per explicit instruction, stopping here for approval before STEP-04.1
code changes begin.**

## STEP-04.5 — Mixed-Attachment Bug Fix
Date: 2026-08-22
Status: **COMPLETE**

Verification before fixing (per instruction: "önce mevcut davranışı
doğrula"): ran `core.attachment_engine.build_chat_context()` directly with
an image+PDF attachment pair — confirmed it correctly produces a combined
string with BOTH the image placeholder and the PDF content. Then read
`ui/panel_server.py`'s vision branch again and confirmed it builds
`vision_msgs` from raw `soru`, never referencing `att_context` — so the
already-correct combined context was being computed and then discarded.
Bug re-confirmed exactly as the STEP-04.0 audit described, before writing
any test or fix.

Root cause: `ui/panel_server.py`, vision branch (`if has_image and
vision_image:`), built:
```python
vision_msgs = [..., {"role": "user", "content": soru, "images": [vision_image]}]
```
instead of using `att_context` (already computed earlier in the same
function from ALL attachments, not just the image).

Fix: one-line change — `"content": soru` → `"content": att_context`. No
other logic touched.

Test-first discipline: before finalizing the 5 new regression tests, ran
them against the **pre-fix** code by temporarily reverting the one-line
change — confirmed 4/5 failed exactly as expected (image+PDF, image+code,
image+text, image+multiple-attachments all failed; image-only correctly
still passed, proving it's unaffected). Restored the fix, re-ran — all 5
passed. This proves the tests actually catch the bug, not just that they
pass on the fixed code by coincidence.

Files changed: `ui/panel_server.py` (1 line), `tests/test_mixed_attachment_fix.py` (new, 5 tests).

Full suite: 466 passed, 5 failed — same 5 pre-existing failures as
STEP-01/02/03 (identical test names, identical causes), zero new
failures. 466 = 461 (STEP-03 end state) + 5 (new mixed-attachment tests).

Per explicit instruction: **stopping here.** Not proceeding to STEP-04.1
or any other STEP-04 subtask without approval.
