# CHAT_REQUIREMENTS_MATRIX — UMAY 9

Date: 2026-08-22
Source spec: "UMAY CHAT — MASTER ENGINEERING SPECIFICATION" (sections 8–64)
Method: each row is graded from direct source inspection this session where possible;
rows not yet directly inspected are marked UNKNOWN rather than assumed.

Legend: EXISTING = works and is wired into live chat · PARTIAL = code exists but not
fully wired / not verified live · MISSING = no evidence found · BROKEN = code exists but
has an identified defect · UNKNOWN = not yet inspected this session.

| ID | Requirement (spec §) | Existing | Partial | Missing | Broken | Key files | Priority | Notes |
|----|---|:---:|:---:|:---:|:---:|---|---|---|
| R1 | Natural conversation, TR, markdown (§8) | ✅ | | | | `core/engine.py`, `panel_server.py` | P2 | Base chat works; no verbosity control observed |
| R2 | Context assembly: recent+summary+retrieval+task+memory (§9) | | ✅ | | | `panel_server.py` (recent only) | P0 | Only "recent" implemented; summary/retrieval/task/memory absent from chat path |
| R3 | Explicit conversation/task state machine (§10) | | ✅ | | | `core/task_state.py` (exists, not wired) | P0 | Foundation exists but disconnected from chat_api |
| R4 | Persistent conversation history, survives restart (§11) | | | | ✅ | `panel_server.py: _chat_sessions` (in-memory dict) | **P0** | Data-loss bug: all chat history lost on restart |
| R5 | History search (keyword/date/etc.) (§12) | | ✅ | | | `core/archive.py` | P1 | Exists as standalone module; unconfirmed if wired to live sessions — needs grep check |
| R6 | Project/library promotion (§13) | | | ✅ | | — | P2 | No route or model found for promoting a conversation to a project |
| R7 | Attachment system: upload/preview/limits (§14) | ✅ | | | | `core/attachment_engine.py`, `/api/chat/attach`, `/api/upload` | — | Concrete size/row/char limits already defined |
| R8 | Multimodal understanding across input types in one request (§15) | | | | ✅ | `panel_server.py` chat_api | P1 | Likely bug: vision branch sends only image+`soru`, drops other attachment context (`att_context`) built earlier in the same request |
| R9 | Multimodal orchestration (classify→route→process→synthesize) (§16) | | ✅ | | | `panel_server.py` | P2 | Only a binary image/text fork exists, not a real router |
| R10 | Code intelligence (imports/deps/call graph) (§17) | ❓ | | | | `core/code_agent.py` (743 lines, unread) | UNKNOWN | Needs inspection |
| R11 | Document intelligence w/ provenance (§18) | | ✅ | | | `core/document_reader.py` (725 lines, unread), `attachment_engine.py` | UNKNOWN | Parsing exists; provenance (page/line) unconfirmed |
| R12 | Screen understanding (§19) | ❓ | | | | `core/vision_reader.py` (580 lines, unread) | UNKNOWN | Needs inspection |
| R13 | Intent/task classification (§20) | | ✅ | | | `core/router.py: model_sec()` | P1 | Keyword heuristic, not a real classifier; adequate as a cheap first pass but not "understanding" |
| R14 | Task planning w/ explicit, revisable plan (§21) | ❓ | ✅ | | | `core/planner.py` (988 lines) | P1 | Substantial code exists ("CODE ONLY" per prior audit — unverified live); not called from chat_api |
| R15 | Live task control: pause/resume/cancel mid-task (§22–23) | | ✅ | | | `core/task_state.py`, `core/approval_manager.py` | P0 | Persistence primitives exist (WAITING_FOR_APPROVAL); not exposed in chat_api or panel UI for arbitrary tasks |
| R16 | Checkpoint & recovery (§24) | | ✅ | | | `core/task_state.py` (JSONL) | P0 | Exists for planner/agent tasks; no chat-turn-level checkpointing |
| R17 | Token/context budget manager (§25) | | | ✅ | | — | **P0** | No token accounting found in chat_api; spec explicitly flags this as high-priority |
| R18 | Model routing by task/cost/latency (§26) | ✅ | | | | `core/router.py`, `core/model_providers.py` | — | Basic version exists and works |
| R19 | Tool/agent routing, avoid unnecessary calls (§27) | | ✅ | | | `panel_server.py` (gated by `gorev in (coding, agent)`) | P1 | Gating exists but is coarse; single-shot only, no multi-tool chaining in chat |
| R20 | Categorized memory (user/conv/project/decision/procedural/knowledge/pref) (§28) | | ✅ | | | `core/memory/`, `rag/` | P1 | JSON store + vector store exist; not category-separated; not confirmed called from chat_api |
| R21 | Knowledge library w/ capture→validate→dedupe→store (§29) | ❓ | | | | `knowledge/` dir, `rag/teach_umay.py` (13 lines, unread) | UNKNOWN | `core/chat.py` legacy path loads `knowledge/*.md` with naive truncation; no validate/dedupe pipeline seen |
| R22 | Skill/procedure library, versioned (§30) | | | ✅ | | — | P3 | No evidence found |
| R23 | Lesson/experience memory w/ confidence & provenance (§31) | | | ✅ | | — | P2 | No evidence found |
| R24 | Human feedback loop (like/dislike/correction → analyzed) (§32) | | | ✅ | | — | P2 | No feedback endpoint found in route table |
| R25 | Personalization of stable preferences (§33) | | | ✅ | | — | P3 | No evidence found in chat path |
| R26 | Evaluator/critic loop for complex tasks (§34) | ❓ | | | | `core/planner.py` (SelfVerifier per docstring) | UNKNOWN | Named in planner's own architecture doc; not verified live |
| R27 | Verification/testing discipline, no false success claims (§35) | ❓ | | | | `tests/` (37 test files present) | UNKNOWN | Volume of tests is real; per-chat-feature coverage not yet confirmed |
| R28 | Observability (run/token/tool/error telemetry) (§36) | | ✅ | | | `core/audit.py` (97 lines), `logs/*.jsonl` | P1 | Audit logging infra exists (actions.jsonl, approvals.jsonl, tasks.jsonl); chat-turn-level telemetry beyond latency dict not confirmed |
| R29 | Error recovery (classify→retry→alt path→checkpoint→ask) (§37) | | | ✅ | | `panel_server.py` uses bare try/except with string fallback | P1 | chat_api has minimal error handling (single try/except around vision call only) |
| R30 | Confidence/uncertainty labeling (§38) | | | ✅ | | — | P3 | No evidence found |
| R31 | Voice: STT/TTS/barge-in (§39) | ❓ | | | | — | UNKNOWN | Not searched yet |
| R32 | Live activity indicators, no hidden CoT exposure (§40) | ✅ | | | | `panel_server.py` SocketIO `task_status` events | — | Real, working, reasonably granular — reuse this pattern rather than replace |
| R33 | Accessibility/readability, message role styling (§41, §58) | ❓ | | | | `ui/templates/panel.html` (unread) | UNKNOWN | Needs inspection |
| R34 | Quick notes / post-its (§42) | | | ✅ | | — | P3 | No route found |
| R35 | Notifications for long tasks (§43) | | ✅ | | | SocketIO channel exists generally | P2 | Transport exists (SocketIO); no dedicated notification model for completed/failed/waiting states |
| R36 | Artifact management (§44) | | | ✅ | | — | P2 | No dedicated artifact store/versioning found distinct from raw file uploads |
| R37 | Computer control (terminal/files/apps/browser) (§45) | ✅ | | | | `core/terminal_agent.py`, `agents/browser_agent.py` | — | Substantial, pre-existing; not wired into chat_api |
| R38 | Permission system (READ/WRITE/EXECUTE/DELETE/NETWORK/SYSTEM) (§46) | | ✅ | | | `core/approval_manager.py` | P0 | Approval flow exists (WAITING_FOR_APPROVAL, channel-agnostic); category granularity (R/W/X/D/N/S) not confirmed — needs inspection |
| R39 | Sandbox for code execution (§47) | ❓ | | | | `core/code_agent.py`, `docker-compose.yml` | UNKNOWN | Whole app runs in Docker per blueprint; per-execution isolation (timeout/resource limits) not confirmed |
| R40 | Offline/online mode distinction (§48) | ❓ | | | | `core/model_providers.py` | UNKNOWN | Ollama (local) vs Gemini/MiMo (cloud) both present per blueprint; explicit UI mode indicator not confirmed |
| R41 | Backup/export/restore (§49) | | | ✅ | | — | **P0** | Prior blueprint's own `49_KNOWN_LIMITATIONS.md` lists "Backup yok" (no backup) as CRITICAL — corroborated |
| R42 | Privacy/data control (delete conv/memory/project/etc.) (§50) | | | ✅ | | — | P1 | No delete-memory/delete-project endpoints found; `/api/chat/clear` only clears in-memory session |
| R43 | Caching (avoid reprocessing identical context) (§51) | ❓ | | | | — | UNKNOWN | Not searched yet |
| R44 | Conversation→project promotion preserving relationships (§52) | | | ✅ | | — | P2 | Depends on R6, which is missing |
| R45 | Undo/rollback for file/code changes, prefer Git (§53) | ❓ | | | | — | UNKNOWN | Not searched yet |
| R46 | Provenance/source trace (§54) | | | ✅ | | — | P2 | Not found in chat path specifically |
| R47 | Draft/autosave for long messages (§55) | | | ✅ | | — | P3 | No evidence in `panel.html`/API (unconfirmed — template unread) |
| R48 | Decision memory (§56) | | | ✅ | | — | P2 | No evidence found |
| R49 | Evaluation dataset / regression infra (§57) | ❓ | | | | `tests/` | UNKNOWN | 37 test files exist; whether any constitute an input/expected/actual eval harness is unconfirmed |
| R50 | Development logs (§62) & checkpoint file (§63) | ✅ | | | | `logs/DEVELOPMENT_LOG.md` (3000 lines!), this doc | — | Already extensive; this audit adds Chat-specific logs alongside it per spec's required filenames |

---

## Immediate read-outs

**P0 items confirmed broken/missing by direct inspection (not just inference):**
- R4 — chat history is in-memory only, lost on restart.
- R17 — no token/context budget tracking in the chat path.
- R41 — no backup system (corroborated by the project's own prior audit).
- R3, R15, R16 — solid persistence primitives exist (`task_state.py`,
  `approval_manager.py`) but are disconnected from the live chat endpoint.

**Notable existing strengths worth preserving/reusing, not replacing:**
- R32 — live activity SocketIO events are already a working partial
  implementation of spec §40.
- R7 — attachment size/type limits are already concretely defined.
- R28 — JSONL audit trail infrastructure (`logs/actions.jsonl`, `approvals.jsonl`,
  `tasks.jsonl`) already exists and matches the spirit of spec §36/§61.

**Rows marked UNKNOWN** should not be treated as "missing" — they require a further
targeted read (code_agent.py, vision_reader.py, document_reader.py, panel.html,
docker-compose.yml, rag/teach_umay.py) before being scored, per the spec's own rule
against inventing information.
