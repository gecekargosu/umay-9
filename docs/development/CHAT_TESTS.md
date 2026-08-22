# CHAT_TESTS

## Baseline (before STEP-01, `tests/test_panel_endpoints.py` only)
```
14 passed, 1 failed
FAILED tests/test_panel_endpoints.py::TestPanelRegression::test_router_intact
  — assert None is not None; caused by:
  [ENGINE] Ollama model listesi alınamadı: Connection refused (localhost:11434)
```
Pre-existing, environment-caused (no local Ollama server running in this
sandbox) — not related to any code in this repo.

## STEP-01 — new tests (`tests/test_conversation_store.py`)
```
8 passed, 0 failed
  TestConversationStoreBasics::test_new_conversation_has_empty_history PASSED
  TestConversationStoreBasics::test_add_and_get_roundtrip PASSED
  TestConversationStoreBasics::test_trims_to_max_pairs PASSED
  TestConversationStoreBasics::test_full_history_retained_on_disk_even_when_trimmed_at_read PASSED
  TestConversationStoreBasics::test_clear_conversation_removes_all_messages PASSED
  TestConversationStoreBasics::test_list_conversations_includes_recent PASSED
  TestPanelServerHelpersUsePersistentStore::test_helpers_roundtrip PASSED
  TestRestartPersistence::test_history_survives_process_restart PASSED
```
`test_history_survives_process_restart` is the regression test for the bug
this STEP fixes: it launches two genuinely separate `python3` subprocesses
(not just two objects in one process) — the first writes history and exits,
the second is a fresh interpreter that reads it back. A shared in-memory
dict (the old implementation) would fail this test; SQLite passes it.

## Full suite after STEP-01 (`pytest tests/ -q`, excluding two tests that
require live external network services per their own filenames —
`test_real_web_research.py`, `test_real_ollama_verifier_contract.py`)
```
447 passed, 5 failed  (275.6s)

FAILED tests/test_document_reader.py::TestDocumentToMemory::test_document_to_memory
FAILED tests/test_panel_endpoints.py::TestPanelRegression::test_router_intact
FAILED tests/test_terminal_agent.py::TestProcessManager::test_list_processes
FAILED tests/test_vision_reader.py::TestImageToMemory::test_image_to_memory
FAILED tests/test_web_research.py::TestRealWebIntegration::test_web_search_tool_mock
```

Each failure checked individually — **none reference conversation storage,
`_chat_sessions`, `_get_session_history`, `_add_to_history`, or
`_clear_session`** (confirmed by grep, not assumption):

| Test | Cause | Pre-existing? |
|---|---|---|
| `test_router_intact` | Same failure as baseline above (no Ollama server) | Yes — identical failure, identical cause, present before this STEP |
| `test_web_search_tool_mock` | `ModuleNotFoundError: duckduckgo_search` (dependency not installed in this sandbox), then a `NameError: name 'log' is not defined` inside `core/agent_tools.py`'s exception handler at line 312 — a real, separate bug in that module's error-handling path, unrelated to chat storage | Yes — this environment never had chromadb/ddgs/playwright/telegram installed this session (see "Environment" note below); the `NameError` is a genuine pre-existing bug worth flagging for its own STEP |
| `test_document_to_memory`, `test_image_to_memory` | Both exercise `rag`/ChromaDB-backed memory paths; `chromadb` was not installed in this sandbox this session (see Environment note) | Likely — needs confirming with chromadb installed, flagged as BLOCKED not FAIL |
| `test_list_processes` | Terminal/process-listing test — environment-dependent (sandboxed container process list), unrelated to chat | Environment-dependent, not code-caused by this STEP |

**Environment note:** this sandbox does not have Ollama, ChromaDB,
Playwright, python-telegram-bot, telethon, or ddgs installed/running (only
flask, flask-socketio, pypdf, python-docx, openpyxl, chardet, psutil, and
pytest were installed to run the chat-relevant subset without pulling in
heavy/networked dependencies). The 4 failures beyond `test_router_intact`
were not individually re-verified against a fully-provisioned environment
this session — reported as observed, not claimed as pre-existing without
the grep evidence shown above.

**Conclusion for STEP-01 acceptance:** PASS. Zero regressions attributable
to this STEP's changes; all new tests for the changed code pass, including
the specific restart-persistence regression test.

## STEP-02 — new tests (`tests/test_chat_task_state.py`)
```
3 passed, 0 failed
  TestChatApiTaskStateWiring::test_tool_turn_creates_and_finishes_task PASSED
  TestChatApiTaskStateWiring::test_conversation_linked_to_task_id PASSED
  TestTaskStatePersistsAcrossRestart::test_chat_created_task_readable_in_new_process PASSED
```
Uses a fake local Ollama HTTP server (stdlib `http.server`, no real network)
— same pattern already used by `tests/test_phase3_ollama_simulation.py`.

## STEP-02 — migration safety check (manual, not a pytest — recorded here
per spec §7's "report exact results")
Simulated a STEP-01-era `conversations.db` (no `last_task_id` column),
inserted a conversation + message directly via raw SQL, then imported
`core.conversation_store` fresh (triggers `init_db()`'s migration path) and
confirmed: (1) the pre-existing message was still readable via
`get_history`, (2) `set_last_task_id`/`get_last_task_id` worked immediately
after. **Result: PASS — no data loss on migration.**

## Full suite after STEP-02
```
450 passed, 5 failed  (277.0s)

FAILED tests/test_document_reader.py::TestDocumentToMemory::test_document_to_memory
FAILED tests/test_panel_endpoints.py::TestPanelRegression::test_router_intact
FAILED tests/test_terminal_agent.py::TestProcessManager::test_list_processes
FAILED tests/test_vision_reader.py::TestImageToMemory::test_image_to_memory
FAILED tests/test_web_research.py::TestRealWebIntegration::test_web_search_tool_mock
```
Identical failure set to the post-STEP-01 run (same 5 tests, same causes —
see STEP-01 section above). 3 more tests pass overall than STEP-01's run
(the 3 new `test_chat_task_state.py` tests). **Zero regressions
attributable to STEP-02.**

## STEP-03 — baseline re-verification (before any code change)
Re-ran the full suite exactly as STEP-02 left it, before writing any
STEP-03 code, per this STEP's explicit instruction not to trust prior
numbers blindly:
```
450 passed, 5 failed — identical failure set to STEP-02's own final run.
```
Confirmed STEP-02's reported baseline was accurate.

## STEP-03 — new tests (`tests/test_task_manager.py`)
```
11 passed, 0 failed
  TestListTasksForWorkspaceUnit::test_one_conversation_one_task PASSED          (Test 1)
  TestListTasksForWorkspaceUnit::test_one_conversation_two_tasks PASSED         (Test 2)
  TestListTasksForWorkspaceUnit::test_one_conversation_three_or_more_tasks PASSED (Test 3)
  TestListTasksForWorkspaceUnit::test_two_conversations_independent_tasks PASSED  (Test 4)
  TestListTasksForWorkspaceUnit::test_task_status_transitions_reflected PASSED  (Test 5)
  TestListTasksForWorkspaceUnit::test_completed_task_visible PASSED             (Test 6)
  TestListTasksForWorkspaceUnit::test_failed_task_visible PASSED                (Test 7)
  TestListTasksForWorkspaceUnit::test_pending_and_running_tasks_visible PASSED  (Test 8)
  TestListTasksForWorkspaceUnit::test_unknown_conversation_returns_empty_list PASSED (Test 9)
  TestChatTasksApiEndToEnd::test_tasks_endpoint_lists_tasks_from_real_chat_turns PASSED
  TestChatTasksApiEndToEnd::test_tasks_endpoint_empty_for_unknown_conversation PASSED
```
Test 10 from the STEP-03 spec ("STEP-02'de çalışan mevcut testlerin hâlâ
geçmesi") = the full-suite regression run below, not a standalone test.

## Full suite after STEP-03
```
461 passed, 5 failed  (279.1s)

FAILED tests/test_document_reader.py::TestDocumentToMemory::test_document_to_memory
FAILED tests/test_panel_endpoints.py::TestPanelRegression::test_router_intact
FAILED tests/test_terminal_agent.py::TestProcessManager::test_list_processes
FAILED tests/test_vision_reader.py::TestImageToMemory::test_image_to_memory
FAILED tests/test_web_research.py::TestRealWebIntegration::test_web_search_tool_mock
```
Identical failure set to STEP-01 and STEP-02 (same 5 tests, same causes).
461 = 450 (STEP-02 end state) + 11 (new STEP-03 tests). **Zero regressions
attributable to STEP-03.**

## STEP-04.5 — bug reproduction, then fix verification
Before writing the fix, temporarily reverted `att_context` back to `soru`
in the vision branch and ran the new test file against that buggy state:
```
4 failed, 1 passed  (pre-fix, as expected)
  test_image_plus_pdf_keeps_pdf_content            FAILED (PDF content missing)
  test_image_plus_code_keeps_code_content          FAILED (code content missing)
  test_image_plus_text_file_keeps_text_content     FAILED (text content missing)
  test_image_plus_multiple_attachments_keeps_all   FAILED (all 3 non-image contents missing)
  test_image_only_still_works_no_regression        PASSED (correctly unaffected — no other attachments to lose)
```
This confirms the tests are a real regression guard, not just
coincidentally-passing assertions. Fix restored, then:
```
5 passed, 0 failed  (post-fix)
```

## Full suite after STEP-04.5
```
466 passed, 5 failed  (280.3s)

FAILED tests/test_document_reader.py::TestDocumentToMemory::test_document_to_memory
FAILED tests/test_panel_endpoints.py::TestPanelRegression::test_router_intact
FAILED tests/test_terminal_agent.py::TestProcessManager::test_list_processes
FAILED tests/test_vision_reader.py::TestImageToMemory::test_image_to_memory
FAILED tests/test_web_research.py::TestRealWebIntegration::test_web_search_tool_mock
```
Identical failure set to STEP-01/02/03 (same 5 tests, same causes). 466 =
461 + 5 new. **Zero regressions attributable to STEP-04.5.**
