# UMAY 9 — MASTER BLUEPRINT

**Tarih:** 2026-08-21
**Sürüm:** UMAY 9.03
**Durum:** COMPLETED

---

## UMAY Nedir?

UMAY, Cengiz Kılıç tarafından geliştirilen kişisel yapay zeka işletim sistemi ve asistanıdır.

Amacı: Kullanıcının dijital hayatını yönetmek — e-posta, Telegram, web araştırma, dosya işleme, iş arama, kod yazma, belge analizi ve more.

---

## Çalışma Modeli

```
Kullanıcı
   ↓
[Panel / CLI / Telegram / Gmail]
   ↓
UMAY Router
   ↓
[Chat / Agent / Coding / Vision / Analysis]
   ↓
Model Provider (Ollama / MiMo / Gemini)
   ↓
Tool Calling (55 tool)
   ↓
[Browser / File / Memory / Web / Terminal / Gmail / Telegram]
   ↓
Result → Kullanıcı
```

---

## Ana Bileşenler

| Bileşen | Dosya | Durum |
|---|---|---|
| Engine | core/engine.py | ✅ VERIFIED |
| Router | core/router.py | ✅ VERIFIED |
| Agent | core/agent.py | ✅ VERIFIED |
| Tool Registry | core/agent_tools.py | ✅ VERIFIED |
| Planner | core/planner.py | 🔵 CODE ONLY |
| Model Providers | core/model_providers.py | ✅ VERIFIED |
| Memory | core/memory/ | ✅ VERIFIED |
| RAG | rag/ | ✅ VERIFIED |
| Browser | agents/browser_agent.py | ✅ VERIFIED |
| Gmail | core/gmail_agent.py | 🔐 CREDENTIAL |
| Telegram | core/telegram_adapter.py | 🔐 CREDENTIAL |
| Worker | core/worker.py | ✅ VERIFIED |
| Scheduler | core/scheduler.py | ✅ VERIFIED |
| Orchestrator | core/orchestrator.py | 🟡 PARTIAL |
| File Manager | core/file_manager.py | ✅ VERIFIED |
| Archive | core/archive.py | ✅ VERIFIED |
| Job Pipeline | core/job_pipeline.py | 🔵 CODE ONLY |
| Panel Server | ui/panel_server.py | ✅ VERIFIED |
| Panel HTML | ui/templates/panel.html | ✅ VERIFIED |
| Identity | core/identity.py | ✅ VERIFIED |
| Approval | core/approval_manager.py | 🔵 CODE ONLY |
| Communication | core/communication_manager.py | 🔵 CODE ONLY |
| Document Reader | core/document_reader.py | 🔵 CODE ONLY |
| Vision Reader | core/vision_reader.py | 🔵 CODE ONLY |
| Web Research | core/web_research.py | 🔵 CODE ONLY |
| Code Agent | core/code_agent.py | 🔵 CODE ONLY |
| Terminal Agent | core/terminal_agent.py | 🔵 CODE ONLY |

---

## Blueprint Dizin Yapısı

```
docs/blueprint/
├── 00_MASTER_BLUEPRINT.md        ← Bu dosya
├── 01_PROJECT_TREE.md             ← Klasör/dosya ağacı
├── 02_RUNTIME_ARCHITECTURE.md     ← Docker runtime
├── 03_MODULE_ARCHITECTURE.md      ← Modül haritası
├── 04_AGENT_ARCHITECTURE.md       ← Agent zinciri
├── 05_MODEL_PROVIDER.md           ← Model/provider sistemi
├── 06_TOOL_CALLING.md             ← Tool calling akışı
├── 07_PLANNER.md                  ← Planner mimarisi
├── 08_MULTI_AGENT.md              ← Multi-agent
├── 09_MEMORY.md                   ← Memory sistemi
├── 10_RAG.md                      ← RAG sistemi
├── 11_FILE_SYSTEM.md              ← Dosya sistemi
├── 12_FILE_UPLOAD.md              ← Dosya yükleme
├── 13_ARCHIVE.md                  ← Arşiv sistemi
├── 14_BROWSER.md                  ← Browser
├── 15_GMAIL.md                    ← Gmail
├── 16_TELEGRAM.md                 ← Telegram
├── 17_WORKER.md                   ← Worker
├── 18_SCHEDULER.md                ← Scheduler
├── 19_EVENT.md                    ← Event sistemi
├── 20_STREAMING.md                ← Streaming
├── 21_APPROVAL_SECURITY.md        ← Approval/güvenlik
├── 22_ERROR_RECOVERY.md           ← Hata kurtarma
├── 23_RETRY.md                    ← Retry mekanizması
├── 24_DATABASE.md                 ← Database
├── 25_API.md                      ← API endpointleri
├── 26_FRONTEND.md                 ← Frontend/panel
├── 27_DOCKER.md                   ← Docker mimarisi
├── 28_CONFIGURATION.md            ← Konfigürasyon
├── 29_TEST.md                     ← Test mimarisi
├── 30_E2E_TEST.md                 ← E2E testler
├── 31_DATA_FLOW.md                ← Veri akışı
├── 32_EVENT_FLOW.md               ← Event akışı
├── 33_AGENT_EXECUTION_FLOW.md     ← Agent çalıştırma
├── 34_TOOL_EXECUTION_FLOW.md      ← Tool çalıştırma
├── 35_APPROVAL_FLOW.md            ← Approval akışı
├── 36_ERROR_FLOW.md               ← Hata akışı
├── 37_BACKGROUND_TASK_FLOW.md     ← Background görev
├── 38_SECURITY_MODEL.md           ← Güvenlik modeli
├── 39_DEPENDENCY_MAP.md           ← Bağımlılık haritası
├── 40_FILE_RESPONSIBILITY.md      ← Dosya sorumluluk
├── 41_FEATURE_STATUS.md           ← Özellik durumu
├── 42_API_ENDPOINT_MAP.md         ← API haritası
├── 43_ENVIRONMENT_MAP.md          ← Env değişkenleri
├── 44_TEST_MAP.md                 ← Test haritası
├── 45_TROUBLESHOOTING.md          ← Hata ayıklama
├── 46_CHANGE_IMPACT.md            ← Değişiklik etkisi
├── 47_BLUEPRINT_UPDATE.md         ← Blueprint güncelleme
├── 48_ARCHITECTURE_DECISIONS.md   ← Mimari kararlar
├── 49_KNOWN_LIMITATIONS.md        ← Bilinen eksikler
└── 50_FUTURE_ARCHITECTURE.md      ← Gelecek mimari
```

---

## Dış Servisler

| Servis | Durum | Erişim |
|---|---|---|
| Ollama | ✅ CONNECTED | localhost:11434 |
| MiMo | 🔐 CREDENTIAL REQUIRED | API key gerekli |
| Gmail | 🔐 CREDENTIAL REQUIRED | IMAP/SMTP |
| Telegram Bot | 🔐 CREDENTIAL REQUIRED | Bot token |
| Telegram User | 🔐 CREDENTIAL REQUIRED | Telethon API |
| Gemini | 🔵 CODE ONLY | API key gerekli |
| Playwright/Chromium | ✅ VERIFIED | Docker içinde |

---

## İstatistikler

| Metrik | Değer |
|---|---|
| Python dosyası | 80 |
| Toplam satır | 20,119 |
| Class | 190 |
| Fonksiyon | 334 |
| Tool sayısı | 55 |
| Agent rolü | 7 |
| Test | 457 PASSED |
| Docker image | umay9-umay:latest |
| Container | umay-agent (healthy) |
| Port | 5001 |

---

## İlgili Blueprint Dosyaları

Her bileşen için detaylı mimari: ilgili 01-50 numaralı dosyalarda.

Sorun giderme: `45_TROUBLESHOOTING.md`
Değişiklik etkisi: `46_CHANGE_IMPACT.md`
Özellik durumu: `41_FEATURE_STATUS.md`
