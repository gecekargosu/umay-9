# UMAY 9 — PANEL BACKEND MAP

**Tarih:** 2026-08-23

---

## UI → JAVASCRIPT → API → BACKEND → SERVICE → SONUÇ

### 1. DASHBOARD

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Overview cards | `loadDashboard()` | `GET /api/system` | `system_status()` | psutil, Ollama API | ✅ Gerçek CPU/RAM/Disk |
| Ollama status | `loadDashboard()` | `GET /api/system` → `sys.ollama` | `system_status()` | Ollama `/api/tags` | ✅ Gerçek |
| Docker status | `loadDashboard()` | `GET /api/system` → `sys.docker` | `system_status()` | `docker ps` | ✅ Gerçek (fallback: self) |
| Active agents | `loadDashboard()` | `GET /api/agents` | `agents_status()` | Hardcoded list | ⚠️ Statik liste,real-time değil |
| Live activity | `loadDashboard()` | `GET /api/logs` | `logs_api()` | `logs/DEVELOPMENT_LOG.md` | ✅ Gerçek log |
| Models list | `loadDashboard()` | `GET /api/system` → `sys.ollama.models` | `system_status()` | Ollama `/api/tags` | ✅ Gerçek |
| Sidebar status dots | `loadDashboard()` | — | — | — | ✅ JS ile güncelleniyor |

### 2. CHAT

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Mesaj gönderme | `sendChat()` | `POST /api/chat` | `chat_api()` → `execute_chat_task()` | `core/engine.py` → Ollama | ✅ Gerçek LLM çağrısı |
| Dosya ekleme | `attachFile()` | `POST /api/chat/attach` | `chat_attach()` | `core/attachment_engine.py` | ✅ Gerçek processing |
| Conversation temizleme | `clearChat()` | `POST /api/chat/clear` | `chat_clear()` | `conversation_store.py` | ✅ SQLite temizleme |
| Task status bar | SocketIO `task_status` | — | `emit_task_status()` | TaskExecutor | ✅ Gerçek status |
| Markdown render | `renderMd()` | — | — | JS (regex) | ✅ Temel markdown |
| Drag & drop | Event listener | `POST /api/chat/attach` | `chat_attach()` | `attachment_engine.py` | ✅ |
| Clipboard paste | Event listener | `POST /api/chat/attach` | `chat_attach()` | `attachment_engine.py` | ✅ |

### 3. AGENTS

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Agent listesi | `loadAgents()` | `GET /api/agents` | `agents_status()` | Hardcoded | ⚠️ Statik liste |
| Agent durumu | `loadAgents()` | — | — | — | ⚠️ Hep "idle" |
| Agent başlatma | — | — | — | — | ❌ Yok |
| Agent detayı | — | — | — | — | ❌ Yok |

### 4. TOOLS

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Tool listesi | `loadTools()` | `GET /api/tools` | `tools_list()` | `agent_tools.TOOLS` | ✅ 62 tool |
| Tool detayı | — | — | — | — | ❌ Yok |
| Tool çalıştırma | — | — | — | — | ❌ Yok |

### 5. FILES

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Dosya yükleme | `uploadFile()` | `POST /api/upload` | `upload_file()` | `file_manager.py` | ✅ |
| Yüklenen dosyalar | `loadFiles()` | `GET /api/uploads` | `list_uploads()` | `file_manager.py` | ✅ |
| Dosya okuma | — | — | — | — | ❌ Yok |
| Dosya silme | — | — | — | — | ❌ Yok |

### 6. MEMORY

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Memory istatistikleri | `loadMemory()` | `GET /api/memory` | `memory_status()` | ChromaDB | ✅ |
| Memory listesi | `loadMemory()` | `GET /api/memory` → `memories` | `memory_status()` | `memory_bridge.recall()` | ⚠️ Boş (0 recall) |
| Memory arama | — | — | — | — | ❌ Yok |
| Memory ekleme | — | — | — | — | ❌ Yok |

### 7. TELEGRAM

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Bot connection | `loadTelegram()` | `GET /api/telegram_status` | `telegram_status_api()` | `telegram_user_adapter` | ✅ Gerçek durum |
| User account | `loadTelegram()` | `GET /api/telegram_status` | `telegram_status_api()` | `telegram_user_adapter` | ✅ Gerçek durum |
| Messages | — | — | — | — | ❌ Yok |
| Send message | — | — | — | — | ❌ Yok |

### 8. BROWSER

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Navigate | `browserGo()` | `POST /api/git` | `git_api()` | `browser_agent.py` | ⚠️ Kısmen |
| Screenshot | SocketIO `screenshot` | — | — | `browser_agent.py` | ✅ |
| Analysis | SocketIO `analiz` | — | — | `browser_agent.py` | ⚠️ Sınırlı |

### 9. SYSTEM

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| System info | `loadSystem()` | `GET /api/system` | `system_status()` | psutil, Ollama | ✅ |

### 10. LOGS

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Log listesi | `loadLogs()` | `GET /api/logs` | `logs_api()` | `DEVELOPMENT_LOG.md` | ✅ |
| Log arama | — | — | — | — | ❌ Yok |
| Log filtreleme | — | — | — | — | ❌ Yok |

### 11. DIAGNOSTICS

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Run Diagnostics | `runDiagnostics()` | `GET /api/diagnostics` | `diagnostics()` | 10+ check | ✅ Gerçek |
| Benchmark | `runBenchmark()` | `GET /api/model_benchmark` | `model_benchmark()` | Ollama `/api/chat` | ✅ Gerçek |

### 12. SETTINGS

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Config gösterimi | `loadSettings()` | `GET /api/config` | `config_api()` | os.getenv | ✅ Salt okunur |
| Config düzenleme | — | — | — | — | ❌ Yok |

### 13. APPROVALS

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Onay listesi | — | — | — | — | ❌ Yok |
| Onay verme | — | — | — | — | ❌ Yok |

### 14. SCHEDULER

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Task listesi | `loadScheduler()` | `GET /api/scheduler_status` | `scheduler_status_api()` | `scheduler.py` | ⚠️ 1 test task |
| Task ekleme | — | — | — | — | ❌ Yok |

### 15. TASKS

| UI Element | JS Fonksiyonu | API | Backend Fonksiyonu | Servis | Sonuç |
|-----------|---------------|-----|-------------------|--------|-------|
| Task listesi | — | — | `GET /api/chat/tasks` | `task_state.py` | ✅ API var |
| Task detayı | — | — | `GET /api/chat/tasks/<id>` | `task_state.py` | ✅ API var |
| Pause/Resume/Cancel | — | — | `POST /api/chat/tasks/<id>/pause|resume|cancel` | `task_executor.py` | ✅ API var |

---

## API ENDPOINTS TAM LİSTE

| # | Endpoint | Method | Çalışıyor | Not |
|---|----------|--------|-----------|-----|
| 1 | `/` | GET | ✅ | Ana sayfa |
| 2 | `/api/health` | GET | ✅ | Health check |
| 3 | `/api/system` | GET | ✅ | CPU/RAM/Disk/Ollama/Docker |
| 4 | `/api/agents` | GET | ✅ | Agent listesi (statik) |
| 5 | `/api/tools` | GET | ✅ | 62 tool listesi |
| 6 | `/api/memory` | GET | ✅ | ChromaDB + memories |
| 7 | `/api/chat` | POST | ✅ | Chat mesaj gönderme |
| 8 | `/api/chat/attach` | POST | ✅ | Dosya ekleme |
| 9 | `/api/chat/clear` | POST | ✅ | Conversation temizleme |
| 10 | `/api/chat/tasks` | GET | ✅ | Task listesi |
| 11 | `/api/chat/tasks/<id>` | GET | ✅ | Task detayı |
| 12 | `/api/chat/tasks/<id>/pause` | POST | ✅ | Task duraklat |
| 13 | `/api/chat/tasks/<id>/resume` | POST | ✅ | Task devam |
| 14 | `/api/chat/tasks/<id>/cancel` | POST | ✅ | Task iptal |
| 15 | `/api/telegram_status` | GET | ✅ | Telegram durumu |
| 16 | `/api/config` | GET | ✅ | Konfigürasyon |
| 17 | `/api/logs` | GET | ✅ | Log satırları |
| 18 | `/api/diagnostics` | GET | ✅ | Sistem tanı |
| 19 | `/api/model_benchmark` | GET | ✅ | Model benchmark |
| 20 | `/api/upload` | POST | ✅ | Dosya yükleme |
| 21 | `/api/uploads` | GET | ✅ | Yüklenen dosyalar |
| 22 | `/api/git` | POST | ✅ | Browser git |
| 23 | `/api/scheduler_status` | GET | ⚠️ | Kısmen |
| 24 | `/api/durdur` | POST | ✅ | Task durdur |
| 25 | `/api/devam` | POST | ✅ | Task devam |
| 26 | `/api/kapat` | POST | ✅ | Task kapat |
| 27 | `/api/workers` | GET | ✅ | Worker listesi |

### Eksik API'ler (V2 için)
- `POST /api/config` — Settings düzenleme
- `GET /api/approvals` — Approval listesi
- `POST /api/approvals/<id>/approve` — Onay verme
- `POST /api/approvals/<id>/reject` — Reddetme
- `POST /api/chat/<id>/retry` — Mesaj tekrar
- `GET /api/conversations` — Conversation listesi
- `DELETE /api/conversations/<id>` — Conversation silme
- `POST /api/models/pull` — Model çekme
- `DELETE /api/models/<name>` — Model silme
