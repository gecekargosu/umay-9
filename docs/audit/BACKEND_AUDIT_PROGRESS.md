# UMAY BACKEND AUDIT — PROGRESS TRACKER
## Audit Date: 2026-08-24

---

## TASK-01: PROJE ENVANTERİ
**Status: PASS**

### Proje Yapısı
- **Toplam Python dosyası**: 110
- **Test dosyası**: 35
- **Log dosyası (JSON)**: 140+ (email_cache draft'ları)
- **Config dosyası**: 4 (.env, .env.example, settings.json, ruff.toml)
- **Core satır sayısı**: 16,077 satır
- **UI satır sayısı**: 2,094 satır (panel_server.py — monolith)
- **Entrypoint**: `Dockerfile CMD ["python", "-m", "ui.panel_server"]`
- **Compose**: Docker + host Ollama + Telegram volumes
- **Runtime**: Python 3.13-slim + Playwright/Chromium

### Klasör Yapısı
```
C:\UMAY 9\
├── core/                    # Backend motor (42 dosya, 16K satır)
│   ├── engine.py            # LLM engine + provider
│   ├── agent.py             # Autonomous agent loop
│   ├── agent_tools.py       # Tool definitions + dispatch (1,446 satır)
│   ├── intent_router.py     # Intent classification
│   ├── router.py            # Task/model router
│   ├── model_providers.py   # Ollama + OpenAI-compat providers
│   ├── task_executor.py     # Background task execution
│   ├── task_state.py        # JSONL persistence
│   ├── approval_manager.py  # Approval workflow
│   ├── communication_manager.py  # Channel abstraction
│   ├── conversation_store.py     # Chat history
│   ├── context_compression.py    # Context management
│   ├── token_budget.py           # Token budgeting
│   ├── file_manager.py           # File upload
│   ├── document_reader.py        # Multi-format reader
│   ├── attachment_engine.py      # Attachment handling
│   ├── identity.py               # System prompts
│   ├── rate_limiter.py           # Rate limiting
│   ├── idempotency.py            # Duplicate prevention
│   ├── audit_timeline.py         # Event timeline
│   ├── failure_recovery.py       # Retry/degradation
│   ├── archive.py                # Memory archive [DEAD CODE]
│   ├── config_manager.py         # Config
│   ├── chat.py                   # Standalone chat [DEAD CODE]
│   ├── orchestrator.py           # Multi-agent [DEAD CODE]
│   ├── planner.py                # Planning engine [DEAD CODE]
│   ├── scheduler.py              # Task scheduler
│   ├── worker.py                 # Background worker
│   ├── job_pipeline.py           # Job search [DEAD CODE]
│   ├── code_agent.py             # Code analysis
│   ├── terminal_agent.py         # Terminal execution
│   ├── vision_reader.py          # Image analysis
│   ├── web_research.py           # Web research
│   ├── gmail_agent.py            # Gmail integration
│   ├── telegram_adapter.py       # Telegram Bot API
│   ├── telegram_user_adapter.py  # Telegram User Account
│   └── system/                   # System info
├── ui/
│   └── panel_server.py       # Flask+SocketIO (2,094 satır MONOLITH)
├── agents/                   # Sub-agents (674 satır)
│   ├── browser_agent.py      # Playwright browser
│   ├── coding_agent.py       # Code assistant
│   └── gemini_agent.py       # Gemini provider [25 satır]
├── rag/                      # RAG system
├── tests/                    # Test suite
├── scripts/                  # Utility scripts
├── config/                   # settings.json
├── memory/                   # ChromaDB + JSON
├── logs/                     # Audit + email cache
├── uploads/                  # Uploaded files
├── knowledge/                # Knowledge base
└── docker-compose.yml + Dockerfile
```

---

## TASK-02: BACKEND ENTRYPOINT VE MİMARİ
**Status: PASS**

### Gerçek Başlangıç Zinciri
```
Docker CMD: python -m ui.panel_server
    ↓
Flask + SocketIO server (port 5001)
    ↓
HTTP API endpoints (/api/chat, /api/system, etc.)
    ↓
SocketIO events (chat_message → execute_chat_task)
    ↓
execute_chat_task (background thread via task_executor)
    ↓
Intent Router (classify_intent → Intent enum)
    ↓
Router (model_sec → task category)
    ↓
Engine (resolve_model → installed model)
    ↓
Provider (OllamaProvider.chat or OpenAICompatible)
    ↓
Ollama API → Model response
    ↓
[If tool_call] Agent tools (DISPATCH → real function)
    ↓
[If tool result] Model processes tool result → final answer
    ↓
Response to UI/Telegram
```

### Dead Architecture
| Modül | Durum | Neden Dead |
|-------|-------|-----------|
| core/chat.py | ❌ DEAD | Hiçbir production dosyası import etmiyor |
| core/orchestrator.py | ❌ DEAD | Sadece test dosyaları import ediyor |
| core/planner.py | ❌ DEAD | Sadece test dosyaları import ediyor |
| core/job_pipeline.py | ❌ DEAD | Hiçbir dosya import etmiyor |
| core/archive.py | ❌ DEAD | Hiçbir dosya import etmiyor |
| agents/gemini_agent.py | ❌ DEAD | 25 satır, hiyerarşik import yok |

### Alive Architecture (production)
| Modül | Kullanım |
|-------|---------|
| panel_server.py | HTTP/SocketIO → task_executor |
| task_executor.py | Background thread management |
| intent_router.py | Intent classification |
| router.py | Task → model routing |
| engine.py | LLM provider + Ollama |
| agent.py | Autonomous agent loop |
| agent_tools.py | 64 tool definitions, 62 dispatched |

---

## TASK-03: TÜM BACKEND MODÜLLERİNİN AMAÇ ANALİZİ
**Status: PASS**

### Modül Haritası

| Modül | Amaç | Çağrılan | Çağrılan Yer |
|-------|------|---------|-------------|
| engine.py | LLM engine + model selection | panel_server, agent, run_umay | Everywhere |
| agent.py | Autonomous agent loop (tool calling) | panel_server, run_umay | Chat API |
| agent_tools.py | Tool definitions + execution | agent, panel_server, telegram | Agent loop |
| intent_router.py | User intent classification | panel_server, agent, router | Before model selection |
| router.py | Task category → model mapping | agent, panel_server, run_umay | Model selection |
| model_providers.py | Ollama + OpenAI-compatible providers | engine | LLM calls |
| task_executor.py | Background task thread management | panel_server | Chat API |
| task_state.py | JSONL task persistence | agent, task_executor | Task lifecycle |
| approval_manager.py | Task approval workflow | agent, panel_server | Risky operations |
| conversation_store.py | Chat history persistence | panel_server | Chat API |
| context_compression.py | Context window management | panel_server | Before LLM call |
| token_budget.py | Token budgeting | engine, panel_server | LLM calls |
| file_manager.py | File upload + storage | panel_server | File API |
| document_reader.py | Multi-format document reading | agent_tools | Tool dispatch |
| attachment_engine.py | Attachment handling | panel_server | Chat API |
| identity.py | System prompts | agent, panel_server | Prompt assembly |
| rate_limiter.py | API rate limiting | panel_server | API endpoints |
| idempotency.py | Duplicate operation prevention | panel_server | Task creation |
| audit_timeline.py | Event logging | agent, panel_server | Various |
| failure_recovery.py | Retry + degradation | agent | Tool failures |
| scheduler.py | Task scheduling | panel_server | Scheduler API |
| worker.py | Background worker | panel_server | Background tasks |
| terminal_agent.py | Terminal command execution | agent_tools | Tool dispatch |
| vision_reader.py | Image analysis | agent_tools | Tool dispatch |
| web_research.py | Web research | agent_tools | Tool dispatch |
| gmail_agent.py | Gmail operations | agent_tools | Tool dispatch |
| code_agent.py | Code analysis | agent_tools | Tool dispatch |
| communication_manager.py | Channel abstraction | telegram adapters | Telegram |

### Duplicate / Conflicting Systems
1. **CONVERSATION HISTORY**: `conversation_store.py` (JSONL) + `memory/history.json` — iki farklı hafıza sistemi
2. **MEMORY**: `core/memory/memory_manager.py` + `core/memory/memory_bridge.py` + `rag/memory_manager.py` + `rag/memory_bridge.py` — 4 dosya, aynı işi yapıyor olabilir
3. **UMAY_CHAT**: `core/system/umay_chat.py` + `core/system/umay_chat_backup.py` — yedek dosya runtime'da
4. **MODEL SELECTION**: `router.py model_sec()` + `engine.py resolve_model()` + `panel_server.py` routing — 3 katmanlı ama birbiriyle çelişebilir
5. **TOOLS DEF**: `agent_tools.py` TOOLS listesi (64) vs DISPATCH dict (62) — 2 tool eksik

---

## TASK-04: TÜM FONKSİYON VE METHOD DENETİMİ
**Status: PASS**

### Kritik Bulgular

| ID | Dosya | Fonksiyon | Sorun |
|----|-------|----------|-------|
| F4-01 | agent_tools.py | search_files() | Glob pattern `*.py` regex error — "nothing to repeat at position 0" |
| F4-02 | agent_tools.py | get_system_info() | CPU/RAM bilgisi yok — sadece OS/version döndürüyor, psutil kullanılmıyor |
| F4-03 | agent_tools.py | aider_edit() | Tool TOOLS listesinde tanımlı ama DISPATCH dict'te yok — çağırsanız bile çalışmaz |
| F4-04 | agent_tools.py | multi_file_edit() | Tool TOOLS listesinde tanımlı ama DISPATCH dict'te yok — çalışıyor gibi görünüyor ama çalışmaz |
| F4-05 | panel_server.py | execute_chat_task() | model_sec() çağrılıyor ama Intent.CHAT/KNOWLEDGE durumunda doğrudan resolve_model("chat") yapılıyor — model_sec bypass ediliyor |
| F4-06 | intent_router.py | classify_intent() | CODE intent'i "class", "python", "script" gibi temel kelimeleri içermiyor |
| F4-07 | conversation_store.py | list_conversations() | Class yok, modül-level fonksiyon — API endpoint'leri `ConversationStore()` import ediyor ama class değil |
| F4-08 | agent_tools.py | analyze_image() | Vision analizi başarısız — model hatası veya görsel format uyumsuzluğu |
| F4-09 | engine.py | resolve_model() | `cloud_tasks` set'i hardcoded — yeni task kategorileri eklenirse otomatik desteklenmez |
| F4-10 | panel_server.py | /api/chat endpoint | model_override parametresi ask() çağrısında kullanılmıyor olabilir |

### Exception Swallowing
| ID | Dosya | Satır | Sorun |
|----|-------|-------|-------|
| F4-11 | agent.py | _execute_tool() | try/except genel — tool hataları loglanıyor ama kullanıcıya hatanın türü bildirilmiyor |
| F4-12 | engine.py | chat() | Provider hatasında Ollama fallback — hata mesajı kayboluyor |
| F4-13 | panel_server.py | task executor | Task hataları on_error callback'ine gidiyor ama phone notification'a ulaşmıyor |

### Unreachable / Dead Code
| ID | Dosya | Kapsam |
|----|-------|-------|
| F4-14 | core/chat.py | 170+ satır — hiçbir yerde import edilmiyor |
| F4-15 | core/orchestrator.py | 268 satır — sadece test'lerde |
| F4-16 | core/planner.py | 988 satır — sadece test'lerde |
| F4-17 | core/job_pipeline.py | 218 satır — hiçbir yerde |
| F4-18 | core/archive.py | 267 satır — hiçbir yerde |
| F4-19 | agents/gemini_agent.py | 25 satır — minimal stub |

---

## TASK-05: AGENT/ENGINE/MODEL ROUTING
**Status: PASS**

### Routing Zinciri Test Sonuçları

| Input | Intent | Model | Kategori | Beklenen | Gerçek | Durum |
|-------|--------|-------|----------|----------|--------|-------|
| Merhaba nasılsın | CHAT | phi4-mini | chat | LOCAL | LOCAL | ✅ |
| Python class yaz | CODE | gpt-oss:20b-cloud | coding | CLOUD | CLOUD | ✅ |
| Dosyayı oku | FILE | phi4-mini | chat | LOCAL | LOCAL | ⚠️ |
| Hava durumu | WEB | phi4-mini | chat | CLOUD | LOCAL | ❌ |
| Kök neden analiz | COMPLEX | gpt-oss:20b-cloud | reasoning | CLOUD | CLOUD | ✅ |
| Powershell ile aç | TERMINAL | phi4-mini | chat | LOCAL | LOCAL | ✅ |
| Resmi analiz et | VISION | gemma3:4b | vision | LOCAL | LOCAL | ✅ |
| Komut çalıştır dir | TERMINAL | gpt-oss:20b-cloud | agent | CLOUD | CLOUD | ✅ |

### Kritik Routing Sorunları

**RR-01**: Intent.FILE → `model_sec()` "chat" döndürüyor. Dosya işlemleri kod gibi ağırlıklı olmasa da, `model_sec` RULES listesinde FILE kategorisi yok — sadece intent_router'da var ama model_sec onu kullanmıyor.

**RR-02**: Intent.WEB → `model_sec()` "chat" döndürüyor. Web araştırması için cloud model seçilmeli.

**RR-03**: `resolve_model()` 7 kategorili: chat, agent, vision, reasoning, coding, analysis, embedding, backup. Ama `model_sec()` RULES 5 kategorili: vision, reasoning, coding, analysis, agent. Eşleşmeyen: chat, embedding, backup.

**RR-04**: `_cloud_model_available()` her çağrıda Ollama API'ye istek atıyor — cache yok, her chat çağrısında 1 HTTP isteği.

---

## TASK-06: TOOL SİSTEMİ FORENSIC AUDIT
**Status: PASS**

### Tool Inventory
- **Tanımlı Tool (TOOLS)**: 64
- **Dispatch Edilen (DISPATCH)**: 62
- **Eksik Dispatch**: 2 (aider_edit, multi_file_edit)

### Tool Execution Test Sonuçları

| Tool | Durum | Kanıt |
|------|-------|-------|
| list_directory | ✅ PASS | Doğru dosya listesi döndürüyor |
| read_file | ✅ PASS | İçerik okunuyor, line number formatında |
| write_file | ⚠️ PARTIAL | Yeni dosya:create=True. Mevcut overwrite:created=False ama içerik değişiyor |
| run_command | Ⅰ PASS | Komut çalışıyor, stdout döndürüyor |
| get_current_time | ✅ PASS | Saat döndürüyor |
| get_current_date | ✅ PASS | Tarih döndürüyor |
| get_system_info | ❌ FAIL | CPU/RAM yok, sadece OS version |
| search_files | ❌ FAIL | Glob pattern regex error |
| web_search | ✅ PASS | DuckDuckGo sonuçları geliyor |
| document_reader | ✅ PASS | requirements.txt okundu |
| vision_reader | ❌ FAIL | Görsel analiz başarısız |

### Tool Tanımı vs Gerçek Davranış

**T6-01**: `write_file` overwrite durumunda `created: false` döndürüyor — API response'da success/failure ayrımı yapılamıyor.

**T6-02**: `search_files` glob pattern'i (`*.py`) regex'e çevirirken hata veriyor — `fnmatch` yerine manuel regex kullanıyor.

**T6-03**: `get_system_info` Docker container'da psutil kullanmıyor — bare minimum OS bilgisi döndürüyor.

**T6-04**: `analyze_image` vision model başarısız — gemma3:4b/llava vision capability'si yetersiz veya yanlış formatta.

**T6-05**: `run_command` herhangi bir komutu çalışıyor — whitelist/regex-based filtering yok.

---

## TASK-07: DOSYA/DATABASE/MEMORY
**Status: PASS**

### Dosya lifecycle (CREATE→READ→MODIFY→DELETE)
- ✅ CREATE: write_file ile dosya oluşturuldu
- ✅ READ: read_file ile okundu
- ✅ MODIFY: write_file ile overwrite edildi
- ⚠️ VERIFY: Değişiklik doğrulandı ama API'de created=false
- ✅ DELETE: run_command('rm') ile silindi
- ✅ VERIFY DELETE: Dosya doğrulandı

### Memory Systems
| Sistem | Dosya | Durum |
|--------|-------|-------|
| ChromaDB | memory/chroma, rag/chroma | Volume mount — persistence var |
| History JSON | memory/history.json | JSON dosyası — basit |
| Memory Bridge | core/memory/memory_bridge.py | Memory manager |

### Conversation Store
- JSONL tabanlı
- `list_conversations()` fonksiyon-level (class değil)
- API endpoint'leri doğru kullanıyor

---

## TASK-08: ERROR/RECOVERY/SECURITY
**Status: PASS**

### Güvenlik Bulguları

| ID | Ciddiyet | Bulgu | Detay |
|----|---------|-------|-------|
| S8-01 | 🔴 CRITICAL | run_command shell injection | Herhangi bir shell komutu çalıştırılabilir — whitelist yok. `rm -rf /` Linux tarafından engelleniyor ama `--no-preserve-root` ile geçilebilir |
| S8-02 | 🔴 CRITICAL | cat /etc/passwd çalışır | Sistem dosyaları okunabilir — Docker sandbox sınırlaması yok |
| S8-03 | 🟡 MEDIUM | UMAY_MODE=approval bypass | `UMAY_APPROVED=true` env var ile her şey çalıştırılabilir |
| S8-04 | 🟡 MEDIUM | .env içindeki secrets Docker volume'dan erişilebilir | Container içinden `.env` okunabilir |
| S8-05 | 🟢 LOW | Telegram session dosyası Docker volume'a mounted | Session dosyası host'tan erişilebilir |

### Path Traversal
- ✅ `_safe_path()` dosya işlemlerinde workspace dışına erişimi engelliyor
- ❌ `run_command()` path traversal engeli yok

### Error Handling
- ✅ `_safe_path()` PermissionError fırlatıyor
- ✅ `engine.py` provider fallback mekanizması var
- ❌ Agent tool hataları kullanıcıya detaylı bildirilmiyor
- ❌ Vision analiz hataları sessizce yutuluyor

---

## TASK-09: GERÇEK BACKEND SENARYO TESTLERİ
**Status: PASS**

### Senaryo Testleri

| Senaryo | Beklenen | Gerçek | Durum |
|---------|----------|--------|-------|
| "Merhaba" → CHAT → phi4-mini | Kısa sohbet | Cevap döndü (85 chars) | ✅ |
| "Python class yaz" → CODE → gpt-oss:20b-cloud | Kod üretimi | Kaliteli kod (1116 chars, type hints) | ✅ |
| "Kök neden analiz" → REASONING → gpt-oss:20b-cloud | Analiz | Analiz cevabı (506 chars) | ✅ |
| "Dosyayı oku" → FILE → tool call | Dosya okuma | Intent FILE algılandı, model_sec("chat") döndü | ⚠️ |
| "Web araştır" → WEB → web_search | Arama sonuçları | Web arama TOOLSUCCESSFUL | ✅ |
| Dosya lifecycle → write→read→modify→delete | Full cycle | Tüm adımlar çalıştı | ✅ |
| Tool dispatch → 62 tool | Working dispatch | 2 tool eksik (aider_edit, multi_file_edit) | ⚠️ |
| Security → path traversal | Blocked | Engellendi | ✅ |
| Security → shell injection | Blocked | Engellenmedi | ❌ |

---

## TASK-10: BULGU SINIFLANDIRMASI

### P0 — Sistemi Kullanılamaz Yapan
| ID | Bulgu |
|----|-------|
| — | Tespit edilmedi |

### P1 — Kritik Fonksiyon Bozuk
| ID | Bulgu |
|----|-------|
| S8-01 | `run_command` whitelist yok — herhangi bir shell komutu çalıştırılabilir |
| T6-05 | `run_command` shell injection koruması yok |

### P2 — Önemli Fonksiyon Eksik/Yanlış
| ID | Bulgu |
|----|-------|
| F4-01 | `search_files` glob pattern regex error |
| F4-02 | `get_system_info` CPU/RAM bilgisi yok |
| T6-04 | `analyze_image` vision analizi başarısız |
| T6-03 | 2 tool DISPATCH'te eksik (aider_edit, multi_file_edit) |
| RR-02 | WEB intent cloud model seçmiyor |
| S8-02 | /etc/passwd okunabilir |

### P3 — Orta Seviye Sorun
| ID | Bulgu |
|----|-------|
| F4-05 | panel_server.py CHAT intent routing bypass |
| RR-01 | Intent.FILE model_sec("chat") dönüyor |
| RR-04 | _cloud_model_available() cache yok |
| T6-01 | write_file overwrite created=false |
| S8-04 | .env container içinde okunabilir |

### P4 — Kalite/Temizlik
| ID | Bulgu |
|----|-------|
| F4-14-F4-19 | 6 dosya DEAD CODE (1,936 satır) |
| F4-09 | resolve_model cloud_tasks hardcoded |
| — | 140+ draft JSON dosyası logs/email_cache'de |
| — | Birçok eski rapor (.md) proje kökünde |

---

## RİSK DEĞERLENDİRMESİ

| Risk | Olasılık | Etki | Öncelik |
|------|----------|------|---------|
| Shell injection ile sistem komutu | Yüksek | Çok Yüksek | P1 |
| Sistem dosyası okunması | Yüksek | Yüksek | P2 |
| Tool dispatch hatası (2 tool eksik) | Orta | Orta | P2 |
| Vision analiz çalışmaması | Yüksek | Orta | P2 |
| Routing hataları (wrong model) | Orta | Orta | P3 |
| Dead code confusion | Düşük | Düşük | P4 |

---

## TAMAMLANAN GÖREVLER

- [x] TASK-01: Proje Envanteri — PASS
- [x] TASK-02: Backend Entrypoint ve Mimari — PASS
- [x] TASK-03: Tüm Backend Modüllerinin Amaç Analizi — PASS
- [x] TASK-04: Tüm Fonksiyon ve Method Denetimi — PASS
- [x] TASK-05: Agent/Engine/Model Routing — PASS
- [x] TASK-06: Tool Sistemi Forensic Audit — PASS
- [x] TASK-07: Dosya/Database/Memory — PASS
- [x] TASK-08: Error/Recovery/Security — PASS
- [x] TASK-09: Gerçek Backend Senaryo Testleri — PASS
- [x] TASK-10: Backend Hata Raporu — PASS
