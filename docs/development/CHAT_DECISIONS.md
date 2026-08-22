# CHAT_DECISIONS

## STEP-01 — Persistent Conversation Storage

**Decision:** Use SQLite (stdlib `sqlite3`), not a new dependency or service.

**Reason:** Rule U ("KESİNLİKLE YAPMA") explicitly forbids adding a new
database or duplicate infrastructure without first checking the existing
solution. The rest of UMAY already persists state as local files:
`core/task_state.py` and `core/approval_manager.py` use JSONL,
`core/memory/memory_manager.py` uses JSON, `rag/chroma_manager.py` uses
ChromaDB for vectors. None of those fit a relational, queryable,
append-heavy message log well (JSONL has no update-in-place / indexed
lookup by conversation id without scanning; a second JSON blob would
re-create the exact "giant single file" problem spec §28 warns against).
SQLite is the smallest addition that fits the existing "local file, no
external service" pattern and needs zero new pip dependency.

**Decision:** Keep the existing function signatures
(`_get_session_history`, `_add_to_history`, `_clear_session`) in
`ui/panel_server.py` instead of introducing a new API surface for callers.

**Reason:** Rule 0 ("Mevcut bir interface varsa onu koru") — every other
line in `chat_api()` already calls these three functions; changing their
signatures would mean touching every call site for no functional benefit.
Swapping only their internal implementation is the minimum safe change.

**Decision:** Trim to the last N pairs at **read** time
(`get_history(..., max_pairs=...)`), not at write time.

**Reason:** The old in-memory implementation trimmed at write time,
permanently discarding older messages. That's acceptable for RAM but wrong
for a persistent store — deleting history from disk on every turn would
make the "History Search" (spec §5/R5) and "Project Library" (§6/R6)
requirements impossible to satisfy later, since the data would already be
gone. Storing everything and windowing only what's sent to the model is
consistent with spec §9 ("Recent Messages + Summary + Relevant Historical
Messages...") — the full history now exists to be summarized/retrieved
from in a later STEP; it just isn't yet.

**Decision:** `list_conversations()` was added to the store now, but no new
route/endpoint was added to expose it.

**Reason:** The schema needed to support it costs nothing extra to add
today (conversations already need an id/title/timestamps row for messages
to reference). Adding it now avoids a schema migration later. But wiring it
into a UI/route is scope creep for a STEP whose stated purpose was fixing
persistence — deferred to the History/Search STEP per the roadmap (Phase 2
in CHAT_CHECKPOINT.md).

**No breaking changes.** `_chat_sessions` dict is removed (dead code —
nothing else referenced it, confirmed via grep before deletion), but no
external behavior changed: same function names, same call sites, same
input/output shapes, same trim window (20 pairs).

## STEP-02 — Chat → Task State Integration

**Decision:** Only the `use_tools` (agentic/"coding"/"agent" task label)
branch of `chat_api()` gets a task_state entry; plain chat and vision turns
do not.

**Reason:** `task_state.py`'s own purpose (per its docstring: "long UMAY
agent jobs") and the FAZ-1 list item text ("Her uzun/agentic görevin
state'i olmalı" — every long/agentic task should have state) both scope
this to agentic work specifically. Giving every single chat turn a task_id
would be state-tracking overhead with no payoff (a one-line chat reply
isn't a task to pause/resume/checkpoint) and contradicts spec Rule U
("gereksiz refactor yapma" / don't build unneeded machinery).

**Decision:** `finish_task(..., status="FAILED", ...)` was added inside a
new `except Exception` around the tool-calling logic, where previously
there was no broad exception handling in that branch at all.

**Reason:** This wasn't explicitly asked for in FAZ-1's "Chat → Task State
entegrasyonu" bullet, but leaving task_state started-but-never-finished on
an exception would produce a permanently RUNNING task in the JSONL log —
worse than the "no tracking at all" state before this STEP. Finishing the
task on failure is a one-line consequence of adding start_task in the
first place, not scope creep.

**Decision:** Did not build the full state machine (IDLE / WAITING_USER /
PAUSED / CANCELLED) this STEP — only RUNNING → COMPLETED/FAILED.

**Reason:** `task_state.py`'s existing API (`start_task`, `finish_task`,
`checkpoint`, `waiting_for_approval`, `resume_task`) already supports the
richer states, but chat_api() currently runs each tool turn synchronously
to completion in one request — there's no live "mid-task" moment yet to
be PAUSED from. Wiring PAUSED/WAITING_USER without a running task to pause
would be dead code. Deferred to the Pause/Resume STEP (FAZ-1, later item),
which needs the agentic loop to run across multiple requests first.

## STEP-03 — Task Manager: Conversation → Task Listing

**Decision:** No new database table for conversation↔task association.
`list_tasks_for_workspace()` scans `task_state.py`'s existing JSONL log
and filters by the `workspace` field already written on `start_task()`.

**Reason:** `workspace` already equals `session_id`/`conversation_id` at
every call site in this codebase (verified by reading `chat_api()` in
STEP-02, not assumed). Adding a `conversation_tasks` SQL table would be a
second system recording the same relationship `task_state.py` already
records — exactly what the master spec's Rule U ("aynı işi yapan ikinci
bir sistem oluşturma") forbids. Scanning the log is O(n) in total event
count; acceptable at this project's scale (JSONL, single-machine, local
tool), and can be revisited if `logs/tasks.jsonl` grows large enough to
matter — not a premature optimization worth making now.

**Decision:** An unknown/nonexistent `session_id` passed to
`GET /api/chat/tasks` returns `200` with an empty `tasks: []` list, not a
`404`.

**Reason:** Conversations in this system are free-form string keys, not
objects that must be explicitly created before use (`conversation_store`
itself auto-creates a conversation row on first message via
`_ensure_conversation`). Treating "no tasks yet for this key" as an error
would be inconsistent with how the rest of the chat system already
treats unknown session_ids (e.g. `_get_session_history` for a brand-new
session_id also just returns `[]`, not an error).

**Decision:** No frontend/UI changes this STEP — API only.

**Reason:** Explicit instruction in the STEP-03 spec's "kapsam dışı"
section ("büyük UI redesign yapma") plus this STEP's own scope
("mevcut frontend mimarisine uyuyorsa basit bir liste oluştur" — but
`ui/templates/panel.html` was not read/modified this STEP, so no attempt
was made to guess what "fits" without inspecting it first, per Rule 0).
Logged as a deferred small addition in CHAT_ISSUES.md rather than
guessed at.
