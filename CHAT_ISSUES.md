# CHAT_ISSUES

Open items discovered during Chat subsystem work. Not all are this STEP's
responsibility to fix — logged here so they aren't lost.

## Found during STEP-01 (persistent conversation storage)

1. **Not yet fixed — carried over from Phase 0 audit:** the vision branch of
   `chat_api()` (`ui/panel_server.py`) sends only the image + raw `soru` to
   the model, silently dropping any other attachment's extracted text
   context (`att_context`) built earlier in the same request. Mixed
   image+PDF (or image+code) turns lose the non-image content. See
   CHAT_CURRENT_STATE.md §5. Targeted for a dedicated STEP (Phase 3 in the
   roadmap), not folded into STEP-01 to keep this STEP's diff small and
   reviewable.

2. **New, found this STEP:** `core/agent_tools.py` line ~312, inside
   `web_search()`'s exception handler, calls `log(...)` but `log` is not
   imported in that module — a `NameError` masks whatever the original
   `duckduckgo-search`/`ddgs` import error was. This is a real bug
   independent of chat storage; surfaced by `tests/test_web_research.py`.
   Not fixed here (out of scope for a chat-persistence STEP; flagging per
   spec §67 "Failure Handling" rather than silently ignoring it).

3. **Environment gap, not a code bug:** this sandbox does not have
   `chromadb`, `playwright`, `python-telegram-bot`, `telethon`, or `ddgs`
   installed, so `test_document_to_memory`, `test_image_to_memory`, and
   `test_web_search_tool_mock` could not be independently re-verified
   against a fully-provisioned environment this session. Recorded as
   BLOCKED-BY-ENVIRONMENT in CHAT_TESTS.md rather than claimed fixed or
   ignored.

## Still open from Phase 0 (unchanged by STEP-01)

- No token/context budget tracking in the chat path (R17, P0).
- No backup system for the project (R41, P0).
- `task_state.py`, `approval_manager.py`, `orchestrator.py`, `planner.py`,
  `memory_bridge.py`, `terminal_agent.py` still not called from
  `chat_api()` — STEP-01 only fixed storage, not orchestration wiring.
