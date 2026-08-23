# UMAY 9 — PANEL UI TREE

**Tarih:** 2026-08-23

---

## TAM EKRAN AĞACI

```
UMAY 9
│
├── SIDEBAR (sol panel, 230px)
│   ├── Logo: "UMAY 9 — AI Operating System"
│   │
│   ├── NAV GROUP: Control Center
│   │   ├── ◉ Dashboard ─── showPage('dashboard')
│   │   ├── 💬 Chat ──────── showPage('chat') [badge: AI]
│   │   ├── 🤖 Agents ─────── showPage('agents')
│   │   └── ⚡ Workflow ────── showPage('workflow')
│   │
│   ├── NAV GROUP: Workspace
│   │   ├── 📁 Files ─────── showPage('files')
│   │   ├── 🧠 Memory ─────── showPage('memory')
│   │   └── 📋 Projects ───── showPage('projects') [SOON]
│   │
│   ├── NAV GROUP: Communication
│   │   ├── 📱 Telegram ──── showPage('telegram')
│   │   └── 📡 Channels ──── showPage('comms')
│   │
│   ├── NAV GROUP: Career [SOON]
│   │   ├── 📄 CV Library ── showPage('cv') [SOON]
│   │   └── 🔍 Job Search ── showPage('jobsearch') [SOON]
│   │
│   ├── NAV GROUP: Knowledge [SOON]
│   │   ├── 📚 Education ── showPage('education') [SOON]
│   │   └── 💡 Patents ──── showPage('patents') [SOON]
│   │
│   ├── NAV GROUP: System
│   │   ├── 🌐 Browser ──── showPage('browser')
│   │   ├── 🔧 Tools ─────── showPage('tools')
│   │   ├── 📋 Tasks ─────── showPage('tasks')
│   │   ├── ⏰ Scheduler ──── showPage('scheduler')
│   │   ├── ✅ Approvals ─── showPage('approvals')
│   │   ├── 📜 Logs ──────── showPage('logs')
│   │   ├── 🖥️ System ─────── showPage('system')
│   │   ├── 🩺 Diagnostics ─ showPage('diagnostics')
│   │   └── ⚙️ Settings ──── showPage('settings')
│   │
│   └── STATUS BAR (alt)
│       ├── ● UMAY Online (s-umay)
│       ├── ● Ollama (s-ollama)
│       ├── ● Docker (s-docker)
│       └── ● Memory (s-memory)
│
├── TOPBAR (üst bar, 46px)
│   ├── Brand: "UMAY 9"
│   ├── Badge: "LOCAL"
│   ├── Status: "ONLINE" (tb-status)
│   ├── CPU: --% (tb-cpu)
│   ├── RAM: --% (tb-ram)
│   └── Clock: --:--:-- (tb-time)
│
└── CONTENT AREA
    │
    ├── PAGE: Dashboard (page-dashboard)
    │   ├── Title: "◉ Command Center"
    │   ├── Overview Cards (grid-4)
    │   │   ├── CPU card (stat-card)
    │   │   ├── RAM card (stat-card)
    │   │   ├── Docker card (stat-card)
    │   │   └── Ollama card (stat-card)
    │   ├── System Telemetry (CPU bar + RAM bar)
    │   ├── Active Agents (grid-2, max 6)
    │   ├── Processing Pipeline (USER→ROUTER→AGENT→TOOL→MEMORY→RESPONSE)
    │   ├── Installed Models (tag listesi)
    │   ├── Live Activity (son 12 log satırı)
    │   ├── Quick Actions
    │   │   ├── 💬 Chat ──── showPage('chat')
    │   │   ├── 🌐 Browser ─ browserNav()
    │   │   ├── 📁 Upload ── file-upload.click()
    │   │   ├── 🔧 Tools ── showPage('tools')
    │   │   ├── 🤖 Agents ─ showPage('agents')
    │   │   └── 📜 Logs ──── showPage('logs')
    │   └── Workspace Cards (grid-3)
    │       ├── 📁 Files
    │       ├── 🧠 Memory
    │       └── 📋 Projects
    │
    ├── PAGE: Chat (page-chat)
    │   ├── Title: "💬 UMAY Chat"
    │   ├── Button: "🔄 New Chat" → clearChat()
    │   ├── Task Status Bar (chat-status)
    │   │   ├── Phase label (chat-status-phase)
    │   │   └── Message (chat-status-msg)
    │   ├── Chat Messages (chat-messages)
    │   │   ├── User messages (bubble, right-aligned)
    │   │   └── Assistant messages (bubble, left-aligned)
    │   │       └── Meta: Model + Latency
    │   ├── Chat Attachments (chat-attachments)
    │   │   └── File chips with ✕ remove
    │   └── Chat Input
    │       ├── 📎 Attach → chat-file-input.click()
    │       │   └── Accept: .txt,.md,.py,.js,.ts,.json,.csv,.html,.css,.pdf,.docx,.xlsx,.png,.jpg,.jpeg,.webp
    │       ├── Text input (onkeydown Enter → sendChat())
    │       └── "Gönder" button → sendChat()
    │
    ├── PAGE: Agents (page-agents)
    │   ├── Title: "🤖 Agents"
    │   └── Agent Grid (grid-auto)
    │       └── Agent Card × N
    │           ├── Icon
    │           ├── Name + Role
    │           └── Status badge
    │
    ├── PAGE: Tasks (page-tasks)
    │   ├── Title: "📋 Tasks"
    │   └── Empty state: "No active tasks"
    │
    ├── PAGE: Browser (page-browser)
    │   ├── Title: "🌐 Browser"
    │   ├── URL Input + "Navigate" button → browserGo()
    │   ├── Screenshot Card (browser-screenshot)
    │   └── Page Analysis Card (browser-analysis)
    │
    ├── PAGE: Tools (page-tools)
    │   ├── Title: "🔧 Tools" + count badge
    │   └── Data Table
    │       └── Rows: Name + Description
    │
    ├── PAGE: Memory (page-memory)
    │   ├── Title: "🧠 Memory / RAG"
    │   ├── Stats (grid-3)
    │   │   ├── ChromaDB status
    │   │   ├── DB Size
    │   │   └── Memories count
    │   └── Recent Memories list
    │
    ├── PAGE: Files (page-files)
    │   ├── Title: "📁 Files"
    │   ├── Upload Zone → file-upload-2.click()
    │   │   └── "📤 Click to upload or drag & drop"
    │   └── Uploaded Files table (File + Size)
    │
    ├── PAGE: Approvals (page-approvals)
    │   ├── Title: "✅ Approvals"
    │   └── Empty state: "No pending approvals"
    │
    ├── PAGE: Scheduler (page-scheduler)
    │   ├── Title: "⏰ Scheduler"
    │   └── Task table (Name, Enabled, Next Run)
    │
    ├── PAGE: Communications (page-comms)
    │   ├── Title: "📡 Communication Channels"
    │   ├── Telegram Bot card (status + detail)
    │   └── Gmail card (status + detail)
    │
    ├── PAGE: Telegram (page-telegram)
    │   ├── Title: "📱 Telegram" + status badge
    │   ├── Bot Connection card
    │   └── User Account card
    │   └── Messages card (empty state)
    │
    ├── PAGE: Projects (page-projects)
    │   ├── Title: "📋 Projects"
    │   ├── UMAY AI Software (ACTIVE)
    │   ├── UMAY Patent (DRAFT)
    │   ├── CREWINTEL (PLANNING)
    │   └── New Project (dashed border, SOON)
    │
    ├── PAGE: CV Library (page-cv) [SOON]
    │   └── Empty state
    │
    ├── PAGE: Job Search (page-jobsearch) [SOON]
    │   └── Empty state
    │
    ├── PAGE: Education (page-education) [SOON]
    │   └── Empty state
    │
    ├── PAGE: Patents (page-patents) [SOON]
    │   └── Empty state
    │
    ├── PAGE: System (page-system)
    │   ├── Title: "🖥️ System"
    │   └── System Grid (grid-3)
    │       ├── CPU, RAM, Disk, Python
    │       ├── Ollama, Ollama Models
    │       └── Docker
    │
    ├── PAGE: Logs (page-logs)
    │   ├── Title: "📜 Logs"
    │   └── Log entries (monospace, color-coded)
    │
    ├── PAGE: Settings (page-settings)
    │   ├── Title: "⚙️ Settings"
    │   └── Config Table (read-only)
    │       ├── Ollama URL
    │       ├── Primary Provider
    │       ├── MiMo status
    │       ├── Telegram status
    │       ├── Gmail status
    │       └── Gemini status
    │
    ├── PAGE: Diagnostics (page-diagnostics)
    │   ├── Title: "🩺 UMAY Diagnostics"
    │   ├── "Run Diagnostics" button → runDiagnostics()
    │   ├── Diagnostics results (status + name + detail)
    │   └── Model Benchmark section
    │       ├── "Benchmark" button → runBenchmark()
    │       └── Results table (Model, Status, Latency, Response)
    │
    └── PAGE: Workflow (page-workflow)
        ├── Title: "⚡ Workflow / Agent Graph"
        ├── Processing Pipeline (interactive nodes)
        │   └── USER → ROUTER → PLANNER → AGENT → TOOL → MEMORY → RESPONSE
        │       └── onclick → alert() ile bilgi
        └── Recent Executions (boş)
```

---

## MODAL/POPUP YAPISI

Panelde gerçek modal/popup yok.
Tek "popup" davranışı:
- **Workflow node tıklama** → `alert()` ile bilgi gösteriyor
- **Drag & Drop** → Chat area'ya dosya bırakma
- **Clipboard paste** → Resim yapıştırma

---

## BUTON ENVANTERİ

| Buton | Sayfa | Fonksiyon | API | Durum |
|-------|-------|-----------|-----|-------|
| 🔄 New Chat | Chat | clearChat() | POST /api/chat/clear | ✅ |
| 📎 Attach | Chat | file-upload.click() | POST /api/chat/attach | ✅ |
| Gönder | Chat | sendChat() | POST /api/chat | ✅ |
| Navigate | Browser | browserGo() | POST /api/git | ⚠️ |
| Upload | Dashboard | file-upload.click() | POST /api/upload | ✅ |
| Upload Zone | Files | file-upload-2.click() | POST /api/upload | ✅ |
| Run Diagnostics | Diagnostics | runDiagnostics() | GET /api/diagnostics | ✅ |
| Benchmark | Diagnostics | runBenchmark() | GET /api/model_benchmark | ✅ |
| Approvals approve | Approvals | — | — | ❌ Yok |
| Approvals reject | Approvals | — | — | ❌ Yok |
| Settings save | Settings | — | — | ❌ Yok |
| Tool test | Tools | — | — | ❌ Yok |
| Memory search | Memory | — | — | ❌ Yok |
| Telegram send | Telegram | — | — | ❌ Yok |
| Chat stop | Chat | — | — | ❌ Yok |
| Chat retry | Chat | — | — | ❌ Yok |
| Chat copy | Chat | — | — | ❌ Yok |

---

## DRAG & DROP + CLIPBOARD

- Chat area'ya dosya bırakma → `attachFileObj()` ile `/api/chat/attach`
- Clipboard'dan resim yapıştırma → otomatik attach
- Desteklenen formatlar: .txt,.md,.py,.js,.ts,.json,.csv,.html,.css,.pdf,.docx,.xlsx,.png,.jpg,.jpeg,.webp

---

## SOCKETIO EVENTS

| Event | Yön | Kullanım |
|-------|-----|----------|
| `connect` | Client→Server | Bağlantı kuruldu |
| `task_status` | Server→Client | Task durumu (phase, message) |
| `screenshot` | Server→Client | Browser screenshot (base64) |
| `analiz` | Server→Client | Browser page analysis |
| `durum` | Server→Client | System durum değişikliği |
| `log` | Server→Client | Live log satırı |

---

## REFRESH DAVRANIŞI

- Dashboard: her 15 saniyede `loadDashboard()` → `/api/system`, `/api/agents`, `/api/logs`
- Clock: her 1 saniye
- Diğer sayfalar: sadece sayfaya geçişte (`showPage()`)
- SocketIO: sürekli bağlı, event geldiğinde güncelleme
