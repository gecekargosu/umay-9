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
