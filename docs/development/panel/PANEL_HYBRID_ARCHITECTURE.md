# UMAY 9 — PANEL HYBRID ARCHITECTURE

**Tarih:** 2026-08-23

---

## MEVCUT DURUM ANALİZİ

### LOCAL (Off-line) Çalışabilen

| Yetenek | Durum | Nasıl |
|---------|-------|-------|
| Sohbet | ✅ | Ollama → phi4-mini, qwen3, gemma2 |
| Dosya okuma | ✅ | local filesystem tools |
| Dosya yazma | ✅ | write_file tool (onaylı) |
| Kod yazma | ✅ | qwen2.5-coder |
| Matematik | ✅ | evaluate_expression (LLM yok) |
| Saat/Tarih | ✅ | get_current_time/date (LLM yok) |
| Sistem bilgisi | ✅ | psutil |
| PDF okuma | ✅ | pypdf |
| DOCX okuma | ✅ | python-docx |
| XLSX okuma | ✅ | openpyxl |
| Resim analizi | ✅ | gemma3:4b (vision) |
| Terminal | ✅ | subprocess |
| Process yönetimi | ✅ | psutil |
| Memory/ChromaDB | ✅ | local ChromaDB |

### ONLINE Gerektiren

| Yetenek | Durum | Nasıl |
|---------|-------|-------|
| Web araştırması | ✅ | DuckDuckGo + Playwright |
| Web sayfa okuma | ✅ | Playwright |
| Gmail | ⚠️ | Credential gerekli |
| Telegram Bot | ⚠️ | Token gerekli |
| Telegram User | ✅ | Telethon session |
| Cloud LLM | ❌ | Provider abstraction var ama aktif değil |
| Web scraping | ✅ | Playwright |

### HYBRID (Otomatik Seçim)

| Özellik | Durum | Nasıl |
|---------|-------|-------|
| Auto model selection | ✅ | engine.py → resolve_model() |
| Provider fallback | ✅ | primary → Ollama fallback |
| Online/offline detection | ⚠️ | intent_router.py → check_network() |
| Kullanıcı mod seçimi | ❌ | Yok — panel'de "LOCAL" badge sabit |

---

## PROVIDER MİMARİSİ

```
┌─────────────────────────────────────────────────────┐
│                    UMAY ENGINE                       │
│                                                     │
│  _get_provider_and_model(task, requested_model)     │
│                                                     │
│  1. PROVIDER_<TASK> env var                         │
│     ├── PROVIDER_VISION=gemma3                      │
│     ├── PROVIDER_CODING=qwen2.5-coder              │
│     └── ...                                         │
│                                                     │
│  2. PRIMARY_PROVIDER env var                        │
│     └── PRIMARY_PROVIDER=OLLAMA                     │
│                                                     │
│  3. OllamaProvider (fallback)                       │
│     └── http://host.docker.internal:11434           │
│                                                     │
└───────────────────┬─────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ↓           ↓           ↓
   OllamaProvider  MiMo       GPT/Claude
   (local)        (cloud)    (cloud)
```

### Mevcut Provider'lar

| Provider | Type | Durum | Nasıl |
|----------|------|-------|-------|
| OllamaProvider | Local | ✅ Aktif | Default, her zaman çalışıyor |
| Generic OpenAI | Cloud | ⚠️ Hazır | API key gerekli |
| MiMo | Cloud | ⚠️ Hazır | API key gerekli |
| DeepSeek | Cloud | ⚠️ Hazır | API key gerekli |

### ONLINE/OFFLINE TESPİT

```python
# intent_router.py
def check_network() -> str:
    # DNS test
    socket.create_connection(("8.8.8.8", 53), timeout=3)
    # HTTP test
    urllib.request.urlopen("http://www.google.com", timeout=3)
    return "online" | "offline"
```

**Mevcut kullanım:** Sadece `get_intent_info()` içinde,agent flow'da kullanılmıyor.

---

## MODELLERİN ONLINE/OFFLINE DURUMU

| Model | Local | Online | Hybrid Kullanım |
|-------|-------|--------|-----------------|
| phi4-mini | ✅ | ❌ | Sadece local |
| qwen3:8b | ✅ | ❌ | Sadece local |
| qwen2.5-coder | ✅ | ❌ | Sadece local |
| gemma3:4b | ✅ | ❌ | Sadece local |
| deepseek-r1 | ✅ | ⚠️ | Local + cloud versiyonu var |
| granite3.3 | ✅ | ❌ | Sadece local |
| llava:7b | ✅ | ❌ | Sadece local |
| gpt-4o | ❌ | ✅ | Sadece online |
| claude-3.5 | ❌ | ✅ | Sadece online |

---

## EKSİK OLAN HYBRID ÖZELLİKLER

### 1. Online/Offline Mode Seçimi
- **Mevcut:** "LOCAL" badge sabit,değiştirilemez
- **Gerekli:** Auto/Offline/Online dropdown
- **Nerede:** Topbar veya Settings

### 2. Provider Fallback Chain
- **Mevcut:** Primary → Ollama (basit)
- **Gerekli:** Online model → Local model → Error
- **Nerede:** engine.py

### 3. Internet Durumu Gösterimi
- **Mevcut:** Topbar'da "LOCAL" yazıyor
- **Gerekli:** Gerçek online/offline durumu
- **Nerede:** check_network() → sidebar/topbar

### 4. Model Provider Seçimi
- **Mevcut:** Env vars ile
- **Gerekli:** Panel'den değiştirilebilir
- **Nerede:** Settings

### 5. Hybrid Task Routing
- **Mevcut:** Tüm görevler local
- **Gerekli:** Görev online gerektiriyorsa online model kullan
- **Nerede:** intent_router.py + engine.py

---

## V2 İÇİN HYBRID MİMARİ ÖNERİSİ

```
┌─────────────────────────────────────────────────────┐
│                  UMAY 9 V2                           │
│                                                     │
│  USER REQUEST                                       │
│      ↓                                              │
│  INTENT ROUTER                                      │
│      ↓                                              │
│  NETWORK CHECK                                      │
│      ├── ONLINE                                     │
│      │   ├── Görev online gerektiriyor mu?          │
│      │   │   ├── EVET → Online Provider             │
│      │   │   └── HAYIR → Local Provider             │
│      │   └── Fallback: Online → Local               │
│      │                                              │
│      └── OFFLINE                                    │
│          └── Local Provider (her zaman)             │
│                                                     │
│  MODEL SELECTION                                    │
│      ↓                                              │
│  EXECUTION                                          │
│      ↓                                              │
│  RESPONSE                                           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Panel'de Gösterim

```
┌─────────────────────────────────────────┐
│  MODE: [AUTO ▼]                         │
│  🟢 ONLINE | Model: phi4-mini           │
│  Provider: Ollama (local)               │
│  Intent: CHAT                           │
│  Tools: None                            │
└─────────────────────────────────────────┘
```

### Settings'de Ayar

```
┌─────────────────────────────────────────┐
│  Online Mode: [AUTO ▼]                  │
│  ├── AUTO: Göreve göre seç              │
│  ├── OFFLINE: Sadece local              │
│  └── ONLINE: Öncelikle online           │
│                                         │
│  Primary Provider: [OLLAMA ▼]           │
│  Fallback Provider: [NONE ▼]            │
│                                         │
│  Online API Key: [***]                  │
└─────────────────────────────────────────┘
```

---

## ONLINE ÖZELLİKLER İÇİN GEREKENLER

### Gmail
- [ ] Gmail credentials (.env)
- [ ] OAuth2 flow
- [ ] Panel'de Gmail ayarları
- [ ] Send/Read/Search

### Cloud LLM
- [ ] API key (OpenAI, Anthropic, vb.)
- [ ] Provider configuration
- [ ] Model listesi
- [ ] Cost tracking

### Web Research
- [ ] Playwright kurulu (✅)
- [ ] DuckDuckGo erişimi (✅)
- [ ] Web scraping (✅)
- [ ] Content extraction (✅)

### Telegram
- [ ] Bot token (⚠️ ayarlı değil)
- [ ] User session (✅ Telethon)
- [ ] Send/Receive (✅)
- [ ] File send (❌)
