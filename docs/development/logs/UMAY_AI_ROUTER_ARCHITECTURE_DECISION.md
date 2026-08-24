# UMAY AI ROUTER / FREEBUFF ARCHITECTURE DECISION
**Tarih:** 2026-08-24
**Durum:** MİMARİ KARAR — KOD YAZILMADI

---

## 1. MEVCUT UMAY MİMARİSİ

### 1.1 Bileşen Haritası

```
┌─────────────────────────────────────────────────────────────┐
│                    UMAY SYSTEM ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Telegram   │    │    Panel     │    │    API       │  │
│  │   Adapter    │    │  (Flask+     │    │  (REST)      │  │
│  │              │    │  SocketIO)   │    │              │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│         └───────────────────┼───────────────────┘           │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │  Communication  │                      │
│                    │    Manager      │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │    Agent        │                      │
│                    │  (run_agent)    │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│              ┌──────────────┼──────────────┐                │
│              │              │              │                │
│     ┌────────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐        │
│     │ Intent Router │ │  Router  │ │  Identity  │        │
│     │ (classify)    │ │ (model)  │ │ (prompt)   │        │
│     └────────┬──────┘ └────┬─────┘ └────────────┘        │
│              │              │                              │
│              └──────┬───────┘                              │
│                     │                                      │
│            ┌────────▼────────┐                             │
│            │   AI Engine     │                             │
│            │ (engine.py)     │                             │
│            └────────┬────────┘                             │
│                     │                                      │
│            ┌────────▼────────┐                             │
│            │ Model Provider  │                             │
│            │   Abstraction   │                             │
│            └────────┬────────┘                             │
│                     │                                      │
│    ┌────────────────┼────────────────┐                     │
│    │                │                │                     │
│    ▼                ▼                ▼                     │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│ │ Ollama   │  │ OpenAI   │  │ Cloud    │                 │
│ │ Provider │  │Compat.   │  │ Provider │                 │
│ │ (local)  │  │Provider  │  │ (API)    │                 │
│ └──────────┘  └──────────┘  └──────────┘                 │
│                     │                                      │
│            ┌────────▼────────┐                             │
│            │   Tool Layer    │                             │
│            │ (agent_tools)   │                             │
│            └────────┬────────┘                             │
│                     │                                      │
│    ┌────────────────┼────────────────┐                     │
│    │       │        │        │       │                     │
│    ▼       ▼        ▼        ▼       ▼                     │
│ Terminal  File    Web    Vision  Code                     │
│ Agent     Agent   Agent  Agent   Agent                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Her Bileşenin Durumu

| Bileşen | Dosya | Durum | Açıklama |
|---------|-------|-------|----------|
| **AI Engine** | `core/engine.py` | ✅ ÇALIŞIYOR | Multi-provider, Ollama fallback, tool calling |
| **Model Providers** | `core/model_providers.py` | ✅ ÇALIŞIYOR | Ollama + OpenAI-compatible (MiMo, DeepSeek, GPT, Claude) |
| **Intent Router** | `core/intent_router.py` | ✅ ÇALIŞIYOR | 12 intent kategorisi, keyword + pattern matching |
| **Task Router** | `core/router.py` | ✅ ÇALIŞIYOR | Model/task eşleştirme |
| **Agent Loop** | `core/agent.py` | ✅ ÇALIŞIYOR | Tool calling, approval, checkpoint, resume |
| **Tool Layer** | `core/agent_tools.py` | ✅ ÇALIŞIYOR | 40+ tool (terminal, file, web, vision, code, document) |
| **Terminal Agent** | `core/terminal_agent.py` | ✅ ÇALIŞIYOR | CMD/PowerShell, system info, process list |
| **Browser Agent** | `agents/browser_agent.py` | ✅ ÇALIŞIYOR | Playwright ile web tarama |
| **Web Research** | `core/web_research.py` | ✅ ÇALIŞIYOR | DuckDuckGo + Playwright fallback |
| **Vision Reader** | `core/vision_reader.py` | ✅ ÇALIŞIYOR | OCR + vision model |
| **Document Reader** | `core/document_reader.py` | ✅ ÇALIŞIYOR | PDF/Word/Excel/CSV |
| **Code Agent** | `core/code_agent.py` | ✅ ÇALIŞIYOR | Kod analizi, üretimi, test |
| **Conversation Store** | `core/conversation_store.py` | ✅ ÇALIŞIYOR | SQLite persist, session yönetimi |
| **Telegram Bot** | `core/telegram_adapter.py` | ✅ ÇALIŞIYOR | Bot API polling |
| **Telegram User** | `core/telegram_user_adapter.py` | ✅ ÇALIŞIYOR | Telethon MTProto |
| **Communication Mgr** | `core/communication_manager.py` | ✅ ÇALIŞIYOR | Multi-channel routing |
| **Approval Manager** | `core/approval_manager.py` | ✅ ÇALIŞIYOR | Tool onay sistemi |
| **Task State** | `core/task_state.py` | ✅ ÇALIŞIYOR | Checkpoint, resume |
| **Rate Limiter** | `core/rate_limiter.py` | ✅ ÇALIŞIYOR | API rate limiting |
| **Idempotency** | `core/idempotency.py` | ✅ ÇALIŞIYOR | Duplicate prevention |
| **Audit Timeline** | `core/audit_timeline.py` | ✅ ÇALIŞIYOR | Human-readable audit |
| **Token Budget** | `core/token_budget.py` | ✅ ÇALIŞIYOR | Token counting |
| **Panel** | `ui/panel_server.py` | ✅ ÇALIŞIYOR | Flask + SocketIO, dashboard, chat |
| **Config** | `.env` | ✅ MEVCUT | Provider, mode, Telegram yapılandırması |

---

## 2. FREEBUFF ENTEGRASYON GERÇEKLİĞİ

### 2.1 Freebuff Mimari Özeti

```
Freebuff (Electron App)
├── Electron Main Process
│   └── IPC Bridge
├── Orchestrator (Express.js)
│   ├── 127.0.0.1:0 (RANDOM PORT)
│   ├── /v1/messages (Anthropic API format)
│   ├── JWT token (runtime-generated)
│   └── Bun.js runtime
└── Chromium Renderer (React UI)
```

### 2.2 Entegrasyon Yöntemi Değerlendirmesi

| Yöntem | Durum | Neden |
|--------|-------|-------|
| **HTTP API** | ❌ MÜMKÜN DEĞİL | Random port + runtime JWT — stabil bağlantı kurulamaz |
| **WebSocket** | ❌ YOK | Orchestrator'da WebSocket bulunamadı |
| **SSE/Event Stream** | ❌ YOK | Event stream mekanizması tespit edilmedi |
| **CLI/Headless** | ❌ YOK | Freebuff'ta headless mod bulunamadı |
| **MCP Server** | ❌ DEĞİL | Freebuff MCP server değil |
| **IPC Bridge** | ❌ ERİŞİLEMEZ | Electron IPC Node.js process içinden erişilebilir, Python'dan değil |
| **File-based** | ⚠️ SINIRLI | worktree.md mümkün ama Freebuff bunu otomatik almıyor |
| **Browser Automation** | ✅ MÜMKÜN | Ama yavaş, kırılgan, bakım maliyetli |

### 2.3 Sonuç

**Freebuff ile stabil, güvenilir, resmi bir entegrasyon noktası BULUNMAMAKTADIR.**

Freebuff'un güçlü kıldığı şeyler:
1. Cloud API erişimi (Claude, GPT)
2. Tool use altyapısı
3. Planning/context management

Bu yeteneklerin **hiçbiri** Freebuff'a özgün değildir. UMAY'a doğrudan eklenebilir.

---

## 3. UMAY'IN MEVCUT YETENEKLERİ

### 3.1 Freebuff ile Karşılaştırma Tablosu

| Yetenek | Freebuff | UMAY | Durum |
|---------|----------|------|-------|
| **Local LLM (Ollama)** | ❌ Yok | ✅ Var | UMAY daha iyi |
| **Cloud API (Claude/GPT)** | ✅ Var | ⚠️ Altyapı var, API key gerekli | Eksik: sadece API key |
| **Tool Use** | ✅ Var | ✅ 40+ tool | UMAY daha geniş |
| **Terminal** | ✅ Var | ✅ CMD/PowerShell/Linux | Eşit |
| **File Operations** | ✅ Var | ✅ Read/Write/Search | Eşit |
| **Web Search** | ✅ Var | ✅ DuckDuckGo + Playwright | Eşit |
| **Browser** | ✅ Var | ✅ Playwright | Eşit |
| **Vision** | ✅ Var | ✅ OCR + Vision model | Eşit |
| **Document Processing** | ✅ Var | ✅ PDF/Word/Excel/CSV | Eşit |
| **Code Agent** | ✅ Var | ✅ Read/Generate/Explain/Bug/Test | Eşit |
| **Planning** | ✅ Var | ✅ Intent Router + Task State | Eşit |
| **Context Management** | ✅ Var | ✅ Conversation Store + Token Budget | Eşit |
| **Approval** | ✅ Var | ✅ Merkezi Approval Manager | Eşit |
| **Error Recovery** | ✅ Var | ✅ Failure Recovery + Checkpoint | Eşit |
| **Streaming** | ✅ Var | ⚠️ Yok | Eksik |
| **Multi-step Tasks** | ✅ Var | ✅ Agent Loop (40 step) | Eşit |
| **Telegram** | ❌ Yok | ✅ Bot + User Account | UMAY daha iyi |
| **Panel/Dashboard** | ✅ Var | ✅ Flask + SocketIO | Eşit |
| **Rate Limiting** | ⚠️ Belirsiz | ✅ Var | UMAY daha iyi |
| **Audit Trail** | ❌ Yok | ✅ Audit Timeline | UMAY daha iyi |

### 3.2 UMAY'ın Eksik Olduğu Tek Şey

**Cloud API anahtarı yapılandırması.**

UMAY'da `OpenAICompatibleProvider` zaten mevcut. Sadece `.env`'ye API key eklenmesi gerekiyor:

```
PRIMARY_PROVIDER=OPENAI    # veya ANTHROPIC, DEEPSEEK, vb.
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

Bu kadar. UMAY zaten tüm altyapıya sahip.

---

## 4. FREEBUFF'UN GERÇEKTEN SAĞLADIĞI AVANTAJLAR

| Avantaj | Gerçek mi? | UMAY'da var mı? |
|---------|------------|-----------------|
| Cloud API erişimi | ✅ EVET | ⚠️ Altyapı var, key gerekli |
| Tool use | ✅ EVET | ✅ EVET (40+ tool) |
| Planning | ✅ EVET | ✅ EVET (Intent Router + Task State) |
| Context management | ✅ EVET | ✅ EVET (Conversation Store + Token Budget) |
| File editing | ✅ EVET | ✅ EVET (write_file + backup) |
| Terminal | ✅ EVET | ✅ EVET (CMD/PowerShell/Linux) |
| Multi-step tasks | ✅ EVET | ✅ EVET (Agent Loop 40 step) |
| Error recovery | ✅ EVET | ✅ EVET (Failure Recovery) |
| Streaming | ✅ EVET | ❌ YOK |
| Approval | ✅ EVET | ✅ EVET (merkezi) |

**Sonuç:** Freebuff'un UMAY'a sağlayabileceği **tek ek yetenek: Streaming.**

Ama bu da minor bir özellik — UMAY'ın mevcut senkron modeli zaten çalışıyor.

---

## 5. AI ROUTER GEREKSİNİMLERİ

### 5.1 Mevcut Durum

UMAY'da zaten bir "AI Router" var:

```python
# core/engine.py
def _get_provider_and_model(task, requested_model, mode):
    # 1. LOCAL mode → Ollama
    # 2. ONLINE mode → Cloud provider
    # 3. AUTO mode → Primary provider
    # 4. Task-specific override → PROVIDER_<TASK>
    # 5. Fallback → Ollama
```

```python
# core/model_providers.py
class OpenAICompatibleProvider:
    # Any OpenAI-compatible API works
    # MIMO_API_KEY, MIMO_BASE_URL, MIMO_MODEL
    # DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
    # OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
    # ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
```

### 5.2 Eksik Olan

| Eksik | Önem | Çözüm |
|-------|------|-------|
| Streaming support | Düşük | `stream=True` ile SSE chunk parsing |
| Anthropic native provider | Orta | `AnthropicProvider` class (Claude API formatı farklı) |
| Token counting (cloud) | Orta | Cloud API response'dan usage okuma |
| Model selection UI | Düşük | Panel'de model seçici |

### 5.3 Gereksiz Olan

| Gereksiz | Neden |
|----------|-------|
| Freebuff entegrasyonu | UMAY zaten bağımsız çalışabilir |
| Yeni provider abstraction | `OpenAICompatibleProvider` zaten yeterli |
| Yeni intent router | `intent_router.py` zaten çalışıyor |
| Yeni tool layer | 40+ tool zaten mevcut |
| Yeni approval sistemi | Merkezi approval zaten var |

---

## 6. A/B/C MİMARİ KARŞILAŞTIRMASI

### SEÇENEK A: Freebuff'a Bağlan

**Avantaj:**
- Freebuff'un cloud API erişimi kullanılabilir

**Dezavantaj:**
- Stabil değil (random port, JWT)
- Güncellemelerle bozulabilir
- Tek nokta hata
- Ek karmaşıklık
- Hız kaybı (ek katman)

**Geliştirme Maliyeti:** Yüksek (2-3 hafta, sürekli bakım)
**Güvenilirlik:** Düşük
**Performans:** Yavaş
**Bakım:** Yüksek
**Güvenlik:** Riskli

### SEÇENEK B: UMAY'a AI Router Kur

**Avantaj:**
- UMAY zaten altyapıya sahip
- Sadece API key eklenmesi yeterli
- Stabil, dokümante API'ler
- Bağımsız, modüler
- Düşük bakım

**Dezavantaj:**
- Streaming eksik (minor)
- Anthropic native format farklı (ama OpenAI-compatible endpoint'i var)

**Geliştirme Maliyeti:** Düşük (1-2 gün)
**Güvenilirlik:** Yüksek
**Performans:** Hızlı
**Bakım:** Düşük
**Güvenlik:** İyi

### SEÇENEK C: Hibrit Mimari

**Avantaj:**
- UMAY bağımsız çalışırken, Freebuff opsiyonel olarak kullanılabilir

**Dezavantaj:**
- İki sistem arasındaki senkronizasyon zor
- Bakım maliyeti yüksek
- Gereksiz karmaşıklık

**Geliştirme Maliyeti:** Çok yüksek (4+ hafta)
**Güvenilirlik:** Orta
**Performans:** Orta
**Bakım:** Çok yüksek
**Güvenlik:** Orta

---

## 7. ÖNERİLEN NİHAI MİMARİ

```
                    📱 Telegram
                        │
                        ▼
                   ┌─────────┐
                   │  UMAY   │
                   │  Core   │
                   └────┬────┘
                        │
                        ▼
                   ┌─────────┐
                   │   AI    │
                   │ Router  │  ← engine.py + model_providers.py
                   └────┬────┘     (ZATEN MEVCUT)
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  Ollama  │  │  Cloud   │  │  UMAY    │
    │  (Local) │  │  API     │  │  Tools   │
    │          │  │ Claude   │  │ Terminal │
    │ Basit    │  │ GPT      │  │ Dosya    │
    │ sohbet   │  │ Gemini   │  │ Web      │
    │ Hızlı    │  │ DeepSeek │  │ Browser  │
    │ Ücretsiz │  │ Güçlü    │  │ Gmail    │
    └──────────┘  └──────────┘  └──────────┘
```

### Neden Bu Mimari?

1. **UMAY zaten bu mimariye sahip** — `engine.py` + `model_providers.py` + `intent_router.py`
2. **Sadece API key eklenmesi gerekiyor** — `.env`'ye 3-4 satır
3. **Freebuff'a bağımlılık yok** — UMAY bağımsız çalışır
4. **Modüler** — Yeni provider eklemek kolay
5. **Güvenilir** — Stabil API'ler, bağımsız çalışma

---

## 8. EKSİK BİLEŞENLER

| Bileşen | Durum | Öncelik | Çözüm |
|---------|-------|---------|-------|
| Cloud API key | ❌ Eksik | 🔴 Yüksek | `.env`'ye ekle |
| Streaming | ❌ Eksik | 🟡 Orta | `stream=True` + SSE parsing |
| Anthropic native | ⚠️ OpenAI-compat. ile çalışır | 🟡 Orta | Gerekirse `AnthropicProvider` ekle |
| Model selection UI | ❌ Eksik | 🟢 Düşük | Panel'e model dropdown |
| Progress streaming | ❌ Eksik | 🟡 Orta | SocketIO ile real-time update |

---

## 9. UYGULAMA SIRASI

### FAZ 1: Cloud API Bağlantısı (1-2 gün)
1. `.env`'ye API key ekle (OpenAI, Anthropic, veya DeepSeek)
2. `model_providers.py`'de provider'ı test et
3. `engine.py`'de online mode'u test et
4. Telegram'dan test mesajı gönder

### FAZ 2: Streaming Desteği (2-3 gün)
1. `engine.py`'ye `stream=True` desteği ekle
2. `panel_server.py`'de SocketIO ile streaming emit et
3. Panel'de real-time cevap gösterimi

### FAZ 3: Model Selection UI (1 gün)
1. Panel'e model dropdown ekle
2. Mode seçiciyi (LOCAL/ONLINE/AUTO) çalıştır
3. Seçilen modeli engine'e aktar

### FAZ 4: Telegram + Cloud Entegrasyonu (1-2 gün)
1. Telegram'dan "online mod" komutu
2. Görev bazlı otomatik mod seçimi
3. Progress bildirimleri

---

## 10. RİSKLER

| Risk | Olasılık | Etki | Azaltma |
|------|----------|------|---------|
| API key sızıntısı | Düşük | Yüksek | `.env` gitignore'da, scanner aktif |
| Cloud API maliyeti | Orta | Orta | Rate limiting, token budget |
| API rate limit | Orta | Düşük | Retry + backoff |
| Internet kesintisi | Düşük | Orta | Ollama fallback |
| Provider güncellemesi | Düşük | Düşük | OpenAI-compatible standard |

---

## 11. TEST STRATEJİSİ

1. **Unit test:** Provider availability check
2. **Integration test:** Cloud API → response → tool calling
3. **E2E test:** Telegram → UMAY → Cloud → Telegram
4. **Fallback test:** Cloud unavailable → Ollama fallback
5. **Rate limit test:** Burst traffic → rate limiter
6. **Security test:** API key exposure check

---

## 12. SON KARAR

### "Ben olsam şu mimariyi seçerdim: SEÇENEK B — UMAY'a AI Router Kur"

**NEDEN:**

1. **UMAY zaten bu altyapıya sahip.** `engine.py` + `model_providers.py` + `intent_router.py` + `agent_tools.py` — hepsi çalışıyor. Tek eksik API key.

2. **Freebuff entegrasyonu gereksiz risk.** Random port + JWT + Electron IPC = kırılgan. Her güncelleme entegrasyonu bozabilir.

3. **Freebuff'un güçlü kıldığı şey → Cloud API erişimi.** Bunu UMAY'a doğrudan verebilirsin. `OpenAICompatibleProvider` zaten Claude, GPT, DeepSeek, Gemini ve MiMo'yu destekliyor.

4. **UMAY zaten Freebuff'tan daha geniş tool set'ine sahip.** 40+ tool, terminal, browser, vision, document, code agent — hepsi mevcut.

5. **Maliyet ve bakım.** Freebuff entegrasyonu = haftalarca geliştirme + sürekli bakım. API key ekleme = 1-2 gün + sıfır bakım.

---

**ÖZET:**

UMAY zaten bir AI Router'a sahip. Sadece cloud API anahtarı eklenmesi gerekiyor. Freebuff'u araya koymak, elindeki güçü gereksiz yere zayıflatır. En doğru yol: **UMAY'ı kendi başına güçlendir.**
