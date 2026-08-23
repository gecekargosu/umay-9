# UMAY 9 — FAZ 0: CURRENT STATE AUDIT
**Tarih:** 2026-08-23 02:00
**Durum:** Read-only audit tamamlandı, kod değişikliği yapılmadı

---

## A. MEVCUT MİMARİ

### Dosya Yapısı
```
core/ (35 Python dosyası)
  agent.py              — Ana agent loop (CHAT_IDENTITY + UMAY_SYSTEM)
  identity.py           — Merkezi UMAY kimlik sistemi
  engine.py             — Ollama/multi-provider LLM engine
  router.py             — Basit keyword-based model router
  agent_tools.py        — 55+ tool tanımı + DISPATCH
  planner.py            — TOOL_CATEGORIES (40+ tool)
  model_providers.py    — Ollama + OpenAI-compatible provider
  conversation_store.py — SQLite conversation history
  vision_reader.py      — Görsel okuma + Ollama vision
  document_reader.py    — PDF/Word/Excel/CSV okuma
  terminal_agent.py     — CMD/PowerShell + dosya açma
  web_research.py       — DuckDuckGo + Playwright research
  communication_manager.py — Channel-agnostic mesaj yonlendirme
  telegram_user_adapter.py — Telethon user account
  telegram_adapter.py   — Bot API adapter
  approval_manager.py   — Onay sistemi
  task_executor.py      — Background task execution
  task_state.py         — Task persistence (JSONL)
  token_budget.py       — Token estimation
  context_compression.py — Context compression
  failure_recovery.py   — Retry + recovery
  attachment_engine.py  — Dosya işleme
  code_agent.py         — Kod agentı
  gmail_agent.py        — Gmail agentı
  job_pipeline.py       — İş pipeline
  orchestrator.py       — Multi-agent orchestrator
  archive.py            — Arşiv sistemi
  file_manager.py       — Dosya yönetimi
  config_manager.py     — Yapılandırma
  audit.py              — Audit sistemi
  scheduler.py          — Zamanlayıcı
  worker.py             — Background worker

agents/ (4 dosya)
  browser_agent.py      — Playwright browser automation
  coding_agent.py       — Kod yazma agentı
  gemini_agent.py       — Gemini entegrasyonu

tests/ (30+ test dosyası, 565 test)
ui/ (panel_server.py + templates/panel.html)
scripts/ (5 dosya)
docs/ (AI_QUICK_START.md + development/ + blueprint/)
```

### Çalışan Servisler
| Servis | Durum | Port |
|---|---|---|
| Docker umay-agent | ✅ Healthy | 5001 |
| Ollama | ✅ Çalışıyor | 11434 |
| Telegram User Account | ✅ Bağlı | - |
| Telegram Bot | ❌ Token yok | - |

### Ollama Modelleri (11 adet)
| Model | Boyut | Kullanım |
|---|---|---|
| phi4-mini:latest | 2.5 GB | Chat (varsayılan) |
| qwen3:8b | 5.2 GB | Agent/coding |
| qwen2.5-coder:7b | 4.7 GB | Coding |
| gemma3:4b | 3.3 GB | Vision (tool desteklemiyor!) |
| gemma2:9b | 5.4 GB | Reasoning |
| deepseek-r1:8b | 5.2 GB | Reasoning |
| granite3.3:8b | 4.9 GB | Analysis |
| llava:7b | 4.7 GB | Vision |
| bge-m3:latest | 1.2 GB | Embedding |
| nomic-embed-text | 274 MB | Embedding |
| gpt-oss:20b-cloud | - | Cloud |

---

## B. ÇALIŞAN ÖZELLİKLER

| Özellik | Durum | Detay |
|---|---|---|
| Web Panel | ✅ | Flask+SocketIO, port 5001 |
| Chat API | ✅ | STEP-05 background task |
| Ollama LLM | ✅ | Multi-provider fallback |
| Tool Calling | ✅ | 55+ tool, agent loop |
| Conversation History | ✅ | SQLite, session bazlı |
| Token Budget | ✅ | Estimation + context compression |
| Failure Recovery | ✅ | Retry + recovery |
| Attachment Engine | ✅ | PDF/DOCX/XLSX/image |
| Browser Agent | ✅ | Playwright/Chromium |
| Terminal Agent | ✅ | CMD/PowerShell + dosya açma |
| Web Research | ✅ | DuckDuckGo + Playwright |
| Document Reader | ✅ | PDF/Word/Excel/CSV |
| Vision Reader | ✅ | Pillow + Ollama vision |
| Approval Manager | ✅ | JSONL persisted |
| Communication Manager | ✅ | Channel-agnostic |
| Telegram User Account | ✅ | Telethon, E2E çalışıyor |
| Identity System | ✅ | UMAY_SYSTEM + CHAT_IDENTITY |
| Task Executor | ✅ | Background + pause/resume |
| Task State | ✅ | JSONL persistence |
| Scheduler | ✅ | Background scheduler |
| Worker | ✅ | Background worker |

---

## C. ÇALIŞMAYAN / SORUNLU ÖZELLİKLER

| Özellik | Durum | Kök Neden |
|---|---|---|
| Telegram Bot API | ❌ | Token yok (TELEGRAM_BOT_TOKEN) |
| MiMo Entegrasyonu | ❌ | API key yok, Ollama'da yok |
| Gemini Agent | ❌ | API key gerekli |
| Gmail Agent | ❌ | OAuth gerekli |
| Job Pipeline | ❌ | Credential gerekli |
| Multi-Agent Orchestrator | ❌ | Henüz test edilmemiş |

---

## D. KRİTİK PROBLEMLER (Önem Sırasına Göre)

### P1: Vision "sonucu boş" Sorunu
- **Durum:** photo gönderildiğinde "Vision sonucu boş" hatası
- **Kök Neden:** Vision model (gemma3:4b) tool desteklemiyor → tool call hatası → boş sonuç
- **Etki:** Tüm görsel analiz çalışmaları engelleniyor
- **Çözüm:** Vision'a tool gönderme, ayrı executor kullan

### P2: gemma3:4b Tool Desteklemiyor
- **Durum:** `gemma3:4b does not support tools` hatası
- **Kök Neden:** Ollama vision model'ine tools parametresi gönderiliyor
- **Etki:** Vision + tool kombinasyonu çalışmıyor
- **Çözüm:** Vision modellerine tools gönderme

### P3: Filesystem Tool Kullanılmıyor
- **Durum:** "Bir klasörü listele" dediğimizde tool çağrılmıyor
- **Kök Neden:** Chat mode'da `use_tools = None` — tüm Telegram mesajları chat sayılıyor
- **Etki:** Dosya sistemi erişimi chat üzerinden çalışmıyor
- **Çözüm:** Intent Router ile chat vs action ayrımı

### P4: Gerçek Saat/Kullanılmıyor
- **Durum:** "Şu an saat kaç?" → uydurma saat (13:45)
- **Kök Neden:** Time tool yok, LLM uyduruyor
- **Etki:** Güvenilirlik kaybı
- **Çözüm:** System clock tool ekle

### P5: Gerçek Tarih/Gün Kullanılmıyor
- **Durum:** "Bugün günlerden ne?" → yanlış gün (pazartesi, aslında cumartesi)
- **Kök Neden:** Time tool yok, LLM uyduruyor
- **Etki:** Güvenilirlik kaybı
- **Çözüm:** System clock tool ekle

### P6: Basit Sorulara Mantıksız Cevaplar
- **Durum:** "BMW mi Mercedes mi?" → "Ben UMAY'ım..." (alakasız)
- **Kök Neden:** CHAT_IDENTITY prompt'u her şeyde UMAY kimliğini vurguluyor
- **Etki:** Kullanıcı deneyimi kötü
- **Çözüm:** Prompt optimizasyonu

### P7: Intent Router Yetersiz
- **Durum:** Tüm Telegram mesajları "chat" sayılıyor
- **Kök Neden:** Intent classification yok, sadece kanal bazlı factorial
- **Etki:** Tool gerektiren mesajlar tool kullanamıyor
- **Çözüm:** FAZ 2 Intent Router

### P8: Offline/Online Ayrımı Yok
- **Durum:** İnternet durumu algılanmıyor
- **Kök Neden:** Network detection mekanizması yok
- **Etki:** Online-only özellikler offline'da başarısız oluyor
- **Çözüm:** Internet detection + fallback

### P9: Hybrid Execution Yok
- **Durum:** Local + online birlikte kullanılmıyor
- **Kök Neden:** Hybrid execution planner yok
- **Etki:** Karma görevlerde yetersiz kalıyor
- **Çözüm:** FAZ 9 Hybrid execution

### P10: Context/Memory Davranışı Güvensiz
- **Durum:** Ardışık mesajlarda context kaybolabiliyor
- **Kök Neden:** History eklendi ama test edilmedi
- **Etki:** Conversational AI deneyimi kötü
- **Çözüm:** Context testleri + optimizasyon

### P11: Tool Calling Mimarisi Yanlış Katmanlanmış
- **Durum:** Chat mode'da tool hiç kullanılmıyor, action mode'da her şey tool
- **Kök Neden:** Intent-based tool selection yok
- **Etki:** Ya çok tool ya hiç tool
- **Çözüm:** Intent Router + Tool Selection Matrix

### P12: Model/Provider Abstraction Eksik
- **Durum:** Sadece Ollama + OpenAI-compatible var
- **Kök Neden:** Online provider henüz eklenmemiş
- **Etki:** Online model kullanılamıyor
- **Çözüm:** Online provider abstraction

---

## E. RİSKLER

| Risk | Seviye | Detay |
|---|---|---|
| Uncommitted changes | YÜKSEK | 12 modified + 12 untracked dosya |
| Git history sadece 2 commit | ORTA | Geri dönüş zor |
| Docker image eski codebase'den | DÜŞÜK | Yeniden build edildi |
| Testler 565 ama bazıları environment-dependent | ORTA | Ollama/Vision testleri |
| Telegram session lock | DÜŞÜK | Adapter çalışırken unlock edilemiyor |

---

## F. EKSİK CAPABILITY'LER

| Capability | Durum | Gerekli |
|---|---|---|
| System Clock/Date | ❌ Yok | Tool ekle |
| Internet Detection | ❌ Yok | Implementasyon |
| Online Model Provider | ❌ Yok | API integration |
| Hybrid Execution | ❌ Yok | Planner |
| Intent Router | ❌ Yok | FAZ 2 |
| Proactive Notification | ❌ Yok | Telegram + Worker |
| Voice Input/Output | ❌ Yok | Gelecek |
| OAuth/Authentication | ❌ Yok | Credential gerekli |

---

## G. MODEL SORUNLARI

| Sorun | Detay |
|---|---|
| gemma3:4b tool desteklemiyor | Vision + tool kombinasyonu kırılıyor |
| phi4-mini yetersiz kalabiliyor | Karma görevlerde zayıf |
| Cold start 30-60sn | İlk model çağrısı çok uzun |
| 180s timeout | Kullanıcı deneyimini öldürüyor |
| Model selection rastgele | Intent-based selection yok |

---

## H. TOOL SORUNLARI

| Sorun | Detay |
|---|---|
| Chat mode'da tool hiç kullanılmıyor | "Klasörü listele" çalışmıyor |
| TOOL_CATEGORIES planner.py'de ama kullanılmıyor | Import edilmemiş |
| Tool permission sistemi var ama aktif değil | auto_fix mode |
| Open file/folder tool eklendi ama test edilmedi | Yeni tool'lar |

---

## I. VISION SORUNLARI

| Sorun | Detay |
|---|---|
| "Vision sonucu boş" | Vision model hatası |
| gemma3:4b tool desteklemiyor | Tools gönderilmemeli |
| Photo handler çalışıyor ama sonuç boş | Adapter → vision → boş |
| Vision + tool ayrı pipeline olmalı | Tek pipeline'da birleşik |

---

## J. ONLINE/OFFLINE EKSİKLERİ

| Eksiklik | Durum |
|---|---|
| Internet detection | Yok |
| Offline fallback | Yok |
| Online model switching | Yok |
| Hybrid execution | Yok |
| Network status UI | Yok |

---

## K. TEST KAPSAMI

| Kategori | Test Sayısı | Durum |
|---|---|---|
| Agent/Tools | 10+ | ✅ Çoğu çalışıyor |
| Approval | 20+ | ✅ Çalışıyor |
| Browser | 5+ | ✅ Mock testler |
| Code Agent | 5+ | ✅ |
| Context Compression | 3+ | ✅ |
| Conversation Store | 5+ | ✅ |
| Document Reader | 5+ | ✅ |
| Failure Recovery | 5+ | ✅ |
| Gmail Agent | 10+ | ⚠️ Credential yok |
| Panel Endpoints | 10+ | ✅ |
| Safety/Audit | 5+ | ✅ |
| STEP-05 Task | 24 | ✅ |
| Telegram Adapter | 40+ | ✅ |
| Terminal Agent | 15+ | ✅ |
| Token Budget | 10+ | ✅ |
| Vision Reader | 5+ | ⚠️ Environment-dependent |
| Web Research | 10+ | ✅ Mock testler |
| Worker/Scheduler | 5+ | ✅ |
| **TOPLAM** | **565** | **564 PASS, 1 SKIP** |

---

## L. REGRESSION RİSKİ

| Değişiklik | Risk | Detay |
|---|---|---|
| identity.py değişikliği | DÜŞÜK | Sadece prompt |
| agent.py CHAT_IDENTITY | ORTA | Tool routing etkileniyor |
| telegram_user_adapter.py | ORTA | Self-message fix kritik |
| docker-compose.yml | DÜŞÜK | Session mount fix |
| task_executor.py | DÜŞÜK | Yeni dosya |

---

## M. ÖNERİLEN GELİŞTİRME SIRASI

| Faz | Amaç | Öncelik |
|---|---|---|
| FAZ 0 | Bu audit | ✅ TAMAM |
| FAZ 1 | Identity entegrasyonu | ✅ TAMAM |
| FAZ 2 | Intent Router | KRİTİK |
| FAZ 3 | Tool routing + filesystem | KRİTİK |
| FAZ 4 | System clock/date | YÜKSEK |
| FAZ 5 | Vision pipeline | YÜKSEK |
| FAZ 6 | PDF/document pipeline | ORTA |
| FAZ 7 | Offline/online detection | ORTA |
| FAZ 8 | Online provider abstraction | ORTA |
| FAZ 9 | Hybrid execution | DÜŞÜK |
| FAZ 10 | Context + memory | ORTA |
| FAZ 11 | Response quality | ORTA |
| FAZ 12 | Telegram E2E | YÜKSEK |
| FAZ 13 | Full regression | KRİTİK |
| FAZ 14 | Production hardening | DÜŞÜK |

---

## N. İLK CHECKPOINT

```
CHECKPOINT: UMAY-MELEZ-PHASE-00-001
Tarih: 2026-08-23 02:00
Faz: FAZ 0 (Audit)
Durum: Read-only audit tamamlandı
Test: 565 collected, 564 PASS, 1 SKIP
Docker: Healthy, port 5001
Telegram: User Account BAĞLI
Ollama: 11 model kurulu
Değişen dosya: Yok (read-only)
Sonraki: FAZ 2 Intent Router
```

---

**Sonraki AI:** Bu raporu oku. FAZ 2'ye geçmeden önce bu rapordaki P1-P12 problemlerini anlamış ol.
