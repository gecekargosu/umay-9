# UMAY 9 — PANEL PROBLEMS (FAZ 1 Audit)
**Date:** 2026-08-23 14:00

---

## PROBLEM LIST

### PROBLEM-001: Memory/RAG Empty
**Priority:** P0
**Status:** BROKEN
**Impact:** UMAY can't remember previous conversations or knowledge

**Expected:** Memory page shows stored memories, collections, search capability
**Actual:** Collections: 0, empty memory list
**Root Cause:** ChromaDB collections not being populated during chat
**Affected Files:** core/conversation_store.py, rag/chroma_manager.py
**Affected API:** /api/memory
**Risk:** HIGH — Core AI capability missing
**Suggested Fix:** Ensure conversation_store writes to ChromaDB during chat

---

### PROBLEM-002: Logs Empty
**Priority:** P0
**Status:** BROKEN
**Impact:** No visibility into system behavior

**Expected:** Logs page shows recent system events
**Actual:** Entries: 0
**Root Cause:** Logger not writing to panel-consumable format
**Affected Files:** core/utils/logger.py, ui/panel_server.py
**Affected API:** /api/logs
**Risk:** HIGH — No debugging capability
**Suggested Fix:** Route action_logger entries to /api/logs

---

### PROBLEM-003: Tasks Always Empty
**Priority:** P1
**Status:** PLACEHOLDER
**Impact:** Can't see/manage long-running tasks

**Expected:** Shows active, completed, failed tasks
**Actual:** Always "No active tasks"
**Root Cause:** /api/chat/tasks returns empty list
**Affected Files:** ui/panel_server.py, core/task_state.py
**Affected API:** /api/chat/tasks
**Risk:** MEDIUM — Task system invisible
**Suggested Fix:** Populate task list from task_state registry

---

### PROBLEM-004: Browser Screenshot Placeholder
**Priority:** P1
**Status:** PLACEHOLDER
**Impact:** Can't see what browser is doing

**Expected:** Shows real screenshot after browser navigation
**Actual:** "No screenshot" static text
**Root Cause:** No screenshot capture in browser agent
**Affected Files:** core/agent_tools.py (browser_open, ekran_al)
**Affected API:** None (前端only)
**Risk:** MEDIUM — Browser automation blind
**Suggested Fix:** Capture screenshot after browser_open, store in temp

---

### PROBLEM-005: Settings Read-Only
**Priority:** P2
**Status:** DEAD UI
**Impact:** Must edit config files manually

**Expected:** Edit Ollama URL, model preferences, channel config
**Actual:** Shows config flags only, no edit
**Root Cause:** /api/config is GET-only, no PUT/POST
**Affected Files:** ui/panel_server.py
**Affected API:** /api/config
**Risk:** LOW — Config editing possible via files
**Suggested Fix:** Add /api/config PUT endpoint

---

### PROBLEM-006: Pipeline Static
**Priority:** P2
**Status:** MOCK
**Impact:** Pipeline visualization doesn't reflect real processing

**Expected:** Shows current processing step in real-time
**Actual:** Static USER→INTENT→AGENT→TOOL→MEMORY→RESPONSE
**Root Cause:** No SocketIO integration for pipeline updates
**Affected Files:** ui/templates/panel.html
**Affected API:** None (frontend only)
**Risk:** LOW — Cosmetic
**Suggested Fix:** Add SocketIO events for pipeline steps

---

### PROBLEM-007: Approvals Always Empty
**Priority:** P2
**Status:** PLACEHOLDER
**Impact:** No approval workflow visible

**Expected:** Shows pending approvals with approve/deny buttons
**Actual:** "No pending approvals"
**Root Cause:** No approval system implemented
**Affected Files:** core/approval_manager.py (exists but unused)
**Affected API:** None
**Risk:** LOW — Not yet needed
**Suggested Fix:** Wire approval_manager to panel

---

### PROBLEM-008: Channels Empty
**Priority:** P3
**Status:** PLACEHOLDER
**Impact:** No communication channel management

**Expected:** Shows Telegram, Gmail, other channels with status
**Actual:** Empty grid
**Root Cause:** /api/config returns flags, not channel list
**Affected Files:** ui/panel_server.py
**Affected API:** /api/config
**Risk:** LOW — Channels work via other means
**Suggested Fix:** Build channel status from config + live checks

---

### PROBLEM-009: Tool Details Minimal
**Priority:** P3
**Status:** PARTIAL
**Impact:** Can't see tool parameters, test tools

**Expected:** Shows tool params, test button, last usage
**Actual:** Name + description only
**Root Cause:** /api/tools returns minimal data
**Affected Files:** ui/panel_server.py
**Affected API:** /api/tools
**Risk:** LOW — Tools work, just limited UI
**Suggested Fix:** Extend /api/tools with param schema + test endpoint

---

### PROBLEM-010: Scheduler Minimal
**Priority:** P3
**Status:** PARTIAL
**Impact:** Can't manage scheduled tasks

**Expected:** Add/edit/delete scheduled tasks
**Actual:** Shows 1 test task, no management
**Root Cause:** Scheduler API is minimal
**Affected Files:** core/scheduler.py, ui/panel_server.py
**Affected API:** /api/scheduler_status
**Risk:** LOW — Scheduler works, UI limited
**Suggested Fix:** Add CRUD endpoints for scheduler

---

## PROBLEM SUMMARY

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 2 | Memory empty, Logs empty |
| P1 | 2 | Tasks placeholder, Browser screenshot |
| P2 | 3 | Settings read-only, Pipeline static, Approvals empty |
| P3 | 3 | Channels empty, Tool details, Scheduler minimal |
| **Total** | **10** | |

---

## BACKLOG (Future Fazlar)

- PROBLEM-001 → FAZ 5 (Memory/ Knowledge)
- PROBLEM-002 → FAZ 2 (Logging hardening)
- PROBLEM-003 → FAZ 7 (Task system)
- PROBLEM-004 → FAZ 6 (Browser agent)
- PROBLEM-005 → FAZ 8 (Settings management)
- PROBLEM-006 → FAZ 7 (Pipeline visualization)
- PROBLEM-007 → FAZ 7 (Approval system)
- PROBLEM-008 → FAZ 6 (Channel management)
- PROBLEM-009 → FAZ 3 (Tool details)
- PROBLEM-010 → FAZ 7 (Scheduler management)
