# UMAY 9 — PANEL TREE (FAZ 1 Audit)
**Date:** 2026-08-23 14:00
**Source:** ui/templates/panel.html + ui/panel_server.py

---

## SIDEBAR NAVIGATION

```
UMAY 9 PANEL
│
├── HOME
│   ├── ◉ Dashboard (page-dashboard) [DEFAULT]
│   ├── 💬 Chat (page-chat) [badge: AI]
│   ├── 🤖 Agents (page-agents)
│   └── 📋 Tasks (page-tasks)
│
├── WORKSPACE
│   ├── 📁 Files (page-files)
│   └── 🧠 Memory (page-memory)
│
├── ONLINE
│   ├── 🌐 Browser (page-browser)
│   ├── 📱 Telegram (page-telegram)
│   └── 📡 Channels (page-comms)
│
└── SYSTEM
    ├── 🔧 Tools (page-tools)
    ├── ⏰ Scheduler (page-scheduler)
    ├── ✅ Approvals (page-approvals)
    ├── 📜 Logs (page-logs)
    ├── 🩺 Diagnostics (page-diagnostics)
    └── ⚙️ Settings (page-settings)
```

**Total:** 4 groups, 15 pages

---

## PAGE DETAILS

### 1. Dashboard (page-dashboard)
**Title:** ◉ Command Center
**Layout:** Grid-based dashboard

**Components:**
- Overview Cards (dynamic, loaded from /api/system)
- System Telemetry (CPU, RAM, Docker, Ollama)
- Active Agents (loaded from /api/agents)
- Processing Pipeline (static: USER→INTENT→AGENT→TOOL→MEMORY→RESPONSE)
- Installed Models (loaded from /api/models)
- Live Activity (log stream)
- Quick Actions (Chat, Browser, Upload, Tools)
- Workspace (Files, Memory links)

**Backend:** /api/system, /api/agents, /api/models

### 2. Chat (page-chat)
**Title:** Chat (no visible title)
**Layout:** Split view — sidebar + main

**Components:**
- New Chat button
- Conversation History sidebar
- Chat Controls (Model selector, Mode selector: AUTO/LOCAL/ONLINE)
- Intent Badge (shows current intent)
- Task Status Bar
- Chat Messages
- Attachments area
- Input bar (file attach, text input, send button)

**Backend:** /api/chat, /api/chat/history, /api/chat/clear, /api/chat/attach

### 3. Agents (page-agents)
**Title:** 🤖 Agents
**Layout:** Grid

**Components:**
- Agent cards (loaded from /api/agents)
- Shows: name, role, status, model

**Backend:** /api/agents

### 4. Tasks (page-tasks)
**Title:** 📋 Tasks
**Layout:** Single card

**Components:**
- Empty state: "No active tasks"

**Backend:** /api/chat/tasks

### 5. Files (page-files)
**Title:** 📁 Files
**Layout:** Upload zone + file list

**Components:**
- Upload zone (click/drag)
- File list (loaded from /api/uploads)

**Backend:** /api/upload, /api/uploads

### 6. Memory (page-memory)
**Title:** 🧠 Memory / RAG
**Layout:** Stats + list

**Components:**
- Memory stats (3 cards)
- Recent Memories list

**Backend:** /api/memory

### 7. Browser (page-browser)
**Title:** 🌐 Browser
**Layout:** URL bar + screenshot + analysis

**Components:**
- URL input + Navigate button
- Screenshot display
- Page Analysis

**Backend:** /api/chat (browser commands)

### 8. Telegram (page-telegram)
**Title:** 📱 Telegram
**Layout:** 2-column cards

**Components:**
- Bot Connection status
- User Account status

**Backend:** /api/telegram_status

### 9. Channels (page-comms)
**Title:** 📡 Communication Channels
**Layout:** Grid

**Components:**
- Channel cards (dynamically loaded)

**Backend:** /api/config

### 10. Tools (page-tools)
**Title:** 🔧 Tools
**Layout:** Table

**Components:**
- Tool count badge
- Tool table (Name, Description)

**Backend:** /api/tools

### 11. Scheduler (page-scheduler)
**Title:** ⏰ Scheduler
**Layout:** Single card

**Components:**
- Scheduler content (dynamically loaded)

**Backend:** /api/scheduler_status

### 12. Approvals (page-approvals)
**Title:** ✅ Approvals
**Layout:** Single card

**Components:**
- Empty state: "No pending approvals"

**Backend:** None (placeholder)

### 13. Logs (page-logs)
**Title:** 📜 Logs
**Layout:** Single card (monospace)

**Components:**
- Log entries (scrollable)

**Backend:** /api/logs

### 14. Diagnostics (page-diagnostics)
**Title:** 🩺 Diagnostics
**Layout:** Run button + results

**Components:**
- Run button
- Diagnostic results
- Model Benchmark section

**Backend:** /api/diagnostics, /api/model_benchmark

### 15. Settings (page-settings)
**Title:** ⚙️ Settings
**Layout:** Single card

**Components:**
- Settings content (dynamically loaded)

**Backend:** /api/config
