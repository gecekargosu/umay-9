# UMAY 9 — MIMARI ANALIZ RAPORU
**Tarih:** 2026-08-23 01:00
**Durum:** Analiz tamamlandi, kod degisikligi yapilmadi

---

## 1. MEVCUT MIMARI — GERCEK DURUM

### Execution Path (Telegram -> Cevap)

```
Telegram mesaji
  -> telegram_user_adapter.py (_handle_event)
  -> communication_manager.py (log_inbound + resolve_inbound_type)
  -> agent.py (run_agent)
  -> router.py (model_sec) — SADECE Telegram icin calisiyor
  -> CHAT_SYSTEM veya SYSTEM prompt secimi
  -> engine.py (chat) -> Ollama
  -> cevap -> Telegram
```

### Mevcut Dosya Yapisi

```
core/
  agent.py              — Ana agent loop (SYSTEM + CHAT_SYSTEM hardcoded)
  identity.py           — KAPSAMLI UMAY kimlik prompt'u (HIC KULLANILMIYOR!)
  router.py             — Basit keyword-based model router
  engine.py             — Ollama/multi-provider LLM engine
  conversation_store.py — SQLite conversation history
  agent_tools.py        — 55+ tool tanimi + DISPATCH
  planner.py            — TOOL_CATEGORIES tanimi (kullanilmiyor)
  communication_manager.py — Channel-agnostic mesaj yonlendirme
  telegram_user_adapter.py — Telethon user account adapter
  telegram_adapter.py   — Bot API adapter
  approval_manager.py   — Onay sistemi
  task_executor.py      — Background task execution
  task_state.py         — Task persistence (JSONL)
  token_budget.py       — Token estimation
  context_compression.py — Context compression
  failure_recovery.py   — Retry + recovery
```

---

## 2. KRITIK BULGULAR

### BULGU-1: identity.py HIC KULLANILMIYOR (KRITIK)

**Dosya:** `core/identity.py` (~100 satir)
**Icerik:** Tam UMAY kimlik sistemi:
- Kimlik tanimi
- Tool calling kurallari
- Risk/seviye sistemi
- Onay sistemi kurallari
- Gerceklik kurali
- Turkce iletisim kurallari
- Kendini tanimlama kurallari

**Ama agent.py'de:**
```python
SYSTEM = """Sen UMAY'in yerel yazilim muhendisi ajaniyin..."""
CHAT_SYSTEM = """Sen UMAY'sin, kisisel yapay zeka asistanisin..."""
```

**Sorun:** identity.py'deki ~100 satirlik kapsamli prompt hicbir yerde import edilmiyor veya kullanilmiyor. agent.py kendi hardcoded prompt'larini kullaniyor.

### BULGU-2: Intent Router YOK (KRITIK)

**Mevcut router.py:**
- Sadece model secimi yapiyor (hangi Ollama modeli kullanilsin)
- Chat vs Action ayrimi YAPMIYOR
- Tool kullanilip kullanilmayacagini belirlemiyor

**Ornek:**
```python
# router.py — sadece model secimi
("agent", ["dosya oku", "terminal", "komut", ...])
```

"Ara" kelimesi hem "web ara" hem "dosyalarda ara" icin eslesiyor ama hangi tool'un kullanilacagini belirtmiyor.

### BULGU-3: Chat vs Action Ayrimi Kontrolsuz

**Mevcut durum:**
```python
# agent.py
is_chat = context and context.get("channel") in ("telegram", "telegram_user")
use_tools = TOOLS if not is_chat or routed_task != "chat" else None
```

**Sorun:**
- Telegram'dan gelen TUM mesajlar "chat" olarak siniflandiriliyor
- "Bir klasoru listele" -> chat -> tool yok -> basarisiz
- Intent tespiti yok, sadece kanal bazli factorial

### BULGU-4: Conversation History Kismen Calisiyor

**Mevcut:**
- `conversation_store.py` — SQLite, calisiyor
- `agent.py` — history ekleniyor (son 10 mesaj)
- Session ID: `telegram_user:<USER_ID>`

**Sorun:**
- Her `run_agent` cagrisinda yeni `start_task()` olusturuluyor
- Task state ile conversation history baglantisi kopuk
- Tool kullaniminda mesaj history'sine tool call/result eklenmiyor (sadece basit cevaplar)

### BULGU-5: Ollama Timeout 180 Saniye

**Mevcut:**
```python
REQUEST_TIMEOUT = 180  # engine.py satir 32
```

**Sorun:**
- 180 saniye cok uzun — kullanici deneyimini olduruyor
- Baz model load'unun 30-60 suruyor (cold start)
- Hot start'ta 5-15 saniye normal
- 180 saniye gercekten gerekiyor mu? Model boyutuna gore degismeli

### BULGU-6: Tool Category Sistemi Kullanilmiyor

**Mevcut:**
- `planner.py` icinde `TOOL_CATEGORIES` tanimi var (40+ tool kategorisi)
- Keyword -> tool eslestirme yapiliyor

**Ama agent.py'de:**
- Bu TOOL_CATEGORIES hic import edilmiyor
- Tool secimi tamamen LLM'in kararina birakilmis
- LLM "list_directory" diye karar verirse cagiriyor

---

## 3. TESPIT EDILEN PROBLEMLER

### P1: UMAY Kimlik Tutarsizligi
- "Ben bir dil modeli degilim" vs "Ben UMAY'yim"
- identity.py'deki dogru prompt kullanilmiyor
- Farkli context'lerde farkli tanimlamalar

### P2: Intent Anlayisi Yok
- "Merhaba" ile "Klasoru listele" ayni pipeline'dan geciyor
- LLM'e tool verilince gereksiz tool cagiriyor
- Tool verilmeyince action isteklerini kaciriyor

### P3: Tool Routing Kontrolsuz
- Tum tool'lar her zaman LLM'e sunuluyor (veya hic sunulmuyor)
- Context-aware tool selection yok
- "Dosyayi oku" -> read_file olmali ama LLM hangi tool'u sececegini bilmiyor

### P4: Ollama Cold Start
- Container restart sonrasi ilk cagri 30-60 saniye suruyor
- Bu sırada kullanici bekliyor
- Warm-up stratejisi yok

---

## 4. ONERILEN MIMARI

### Hedef: Intent-Based Agent Router

```
                    TELEGRAM / WEB / VOICE
                              |
                    COMMUNICATION MANAGER
                              |
                    ┌─────────┴─────────┐
                    │   INTENT ROUTER   │
                    └─────────┬─────────┘
                              |
          ┌───────────────────┼───────────────────┐
          |                   |                   |
     CHAT MODE          ACTION MODE         COMPLEX TASK
          |                   |                   |
     LLM (tools=0)     TOOL ROUTER          AGENT LOOP
          |                   |                   |
     Natural Response    Tool -> LLM        Tool -> LLM -> Tool
          |                   |                   |
          └───────────────────┼───────────────────┘
                              |
                    RESPONSE LAYER
                              |
                         TELEGRAM
```

### Intent Kategorileri

| Intent | Ornek | Davranis |
|--------|-------|----------|
| CHAT | "Merhaba", "Nasilsin?" | LLM, tools=0 |
| IDENTITY | "Sen kimsin?" | LLM, tools=0, identity prompt |
| KNOWLEDGE | "Python'da decorator nedir?" | LLM, tools=0 |
| TIME | "Saat kac?" | time tool veya LLM |
| FILE_READ | "Dosyayi oku" | read_file tool |
| FILE_LIST | "Klasoru listele" | list_directory tool |
| FILE_WRITE | "Dosyayi olustur" | write_file tool + approval |
| TERMINAL | "Komut calistir" | run_command tool + approval |
| WEB | "Web'de ara" | web_search tool |
| MEMORY | "Hatirla" | memory tool |
| COMPLEX | "Proje incele" | Full agent loop + tools |

### Intent Router Tasarimi

```python
# intent_router.py (oneri)

INTENT_RULES = [
    # CHAT — tool gerektirmez
    ("CHAT", ["merhaba", "nasilsin", "selam", "n'aber", "gunaydin", "iyi geceler"]),
    
    # IDENTITY — tool gerektirmez
    ("IDENTITY", ["sen kimsin", "kendini tanit", "ne yapabilirsin", "umay nedir"]),
    
    # KNOWLEDGE — LLM cevaplayabilir
    ("KNOWLEDGE", ["nedir", "nasil calisir", "acikla", "soyle", "anlat"]),
    
    # TIME — time tool veya LLM
    ("TIME", ["saat kac", "bugun ne zaman", "tarih"]),
    
    # FILE READ
    ("FILE_READ", ["oku", "icerigi goster", "dosyayi oku"]),
    
    # FILE LIST
    ("FILE_LIST", ["listele", "klasoru goster", "dosyalari goster", "goz at"]),
    
    # FILE WRITE
    ("FILE_WRITE", ["yaz", "olustur", "kaydet", "guncelle"]),
    
    # TERMINAL
    ("TERMINAL", ["calistir", "komut", "terminal", "cmd", "powershell"]),
    
    # WEB SEARCH
    ("WEB", ["ara", "internette", "web'de", "google'da"]),
    
    # MEMORY
    ("MEMORY", ["hatirla", "bellekte tut", "kaydet"]),
]

def classify_intent(text: str) -> str:
    text_lower = text.lower().strip()
    for intent, keywords in INTENT_RULES:
        if any(kw in text_lower for kw in keywords):
            return intent
    return "CHAT"  # default
```

### System Prompt Secimi

```python
# identity.py'deki UMAY_SYSTEM'i kullan
from core.identity import UMAY_SYSTEM

def get_system_prompt(intent: str, context: dict) -> str:
    if intent in ("CHAT", "IDENTITY", "KNOWLEDGE"):
        return UMAY_SYSTEM  # identity.py'deki tam prompt
    elif intent in ("FILE_READ", "FILE_LIST", "FILE_WRITE", "TERMINAL"):
        return UMAY_SYSTEM + "\n\nAktif gorev: Tool kullanimi gerekli."
    else:
        return UMAY_SYSTEM
```

### Tool Selection Matrix

| Intent | Tools | Max Steps |
|--------|-------|-----------|
| CHAT | None | 1 |
| IDENTITY | None | 1 |
| KNOWLEDGE | None | 1 |
| TIME | time (if available) | 1-2 |
| FILE_READ | read_file | 2-3 |
| FILE_LIST | list_directory | 2-3 |
| FILE_WRITE | write_file + read_file | 3-5 |
| TERMINAL | run_command | 3-5 |
| WEB | web_search + browser_open | 3-5 |
| MEMORY | memory tools | 3-5 |
| COMPLEX | All tools | 10-40 |

---

## 5. OLLAMA TIMEOUT ANALIZI

### Mevcut Durum
```
REQUEST_TIMEOUT = 180 saniye
```

### Gercek Zaman Olcumleri (loglardan)
```
[21:47:36] ENGINE baslatildi
[21:47:43] UMAY_RESPONSE (7 saniye) — Normal

[21:48:39] ENGINE baslatildi
[21:48:42] UMAY_RESPONSE (3 saniye) — Hizli

[21:48:48] ENGINE baslatildi
[21:49:00] UMAY_RESPONSE (12 saniye) — biraz uzun
```

### Analiz
- **Normal calisma:** 3-15 saniye
- **Cold start:** 30-60 saniye (model yukleniyor)
- **180 saniye timeout:** Gercek timeout degil, uygulama timeout'u
- **Sorun:** Model yuklenirken kullanici hicbir feedback almıyor

### Oneri
```python
# Zaman asimini kademeli yap
STEP_TIMEOUT = 60   # Tek model cagrisi icin
TOTAL_TIMEOUT = 300 # Tum agent loop icin
WARM_UP_INTERVAL = 300  # Model warm-up periyodu
```

---

## 6. TEST PLANI

### Chat Intent Testleri (0 tool beklenen)
```python
["Merhaba", "Nasilsin?", "Sen kimsin?", "Ne yapabilirsin?", "UMAY nedir?"]
# Beklenen: 0 tool call, dogal cevap, UMAY kimligi tutarli
```

### Action Intent Testleri (tool beklenen)
```python
["Klasoru listele", "Dosyayi oku", "Komut calistir"]
# Beklenen: ilgili tool cagirisi, dogru parametreler
```

### Identity Testleri
```python
["Sen kimsin?", "Kendini tanit", "UMAY ne demek?"]
# Beklenen: "Ben UMAY'yim. Kisisel yapay zeka isletim sistemi..."
```

### Context Testleri
```python
# 3 mesajlik konusma
["Merhaba", "Nasılsın?", "Bugun hava nasıl?"]
# Beklenen: history korunur, tutarli cevaplar
```

### Timeout Testleri
```python
# Uzun mesaj
["1000 kelimelik bir makale yaz..."]
# Beklenen: timeout olmaz, feedback verilir
```

---

## 7. DEGISIKLIK LISTESI

### Yapilacaklar (sira ile)

1. **identity.py'yi agent.py'ye entegre et**
   - `from core.identity import UMAY_SYSTEM`
   - CHAT_SYSTEM ve SYSTEM'i kaldir
   - Tum context'lerde UMAY_SYSTEM kullan

2. **Intent Router olustur**
   - `core/intent_router.py` yeni dosya
   - Intent classification fonksiyonu
   - Tool selection matrix

3. **agent.py'de intent-based routing ekle**
   - Intent'e gore system prompt sec
   - Intent'e gore tool sec
   - Intent'e gore max_steps belirle

4. **Tool routing'i iyilestir**
   - planner.py'deki TOOL_CATEGORIES'i kullan
   - Intent -> tool eslestirme
   - LLM'e sadece gerekli tool'lari sun

5. **Ollama timeout'i optimize et**
   - Kademeli timeout
   - Cold start feedback
   - Warm-up stratejisi

6. **Test yaz**
   - Chat intent testleri
   - Action intent testleri
   - Identity testleri
   - Context testleri

---

## 8. DOSYA DEGISIKLIKLERI

### Degisecek dosyalar
- `core/agent.py` — identity import, intent routing, tool selection
- `core/router.py` — Intent classification ekle

### Yeni dosyalar
- `core/intent_router.py` — Intent classification + tool routing

### Kullanilacak dosyalar
- `core/identity.py` — Zaten mevcut, sadece import edilecek
- `core/planner.py` — TOOL_CATEGORIES mevcut, kullanilacak

---

## 9. SONU

### Mevcut Durum
- Telegram transport: CALISIYOR
- Dogal sohbet: KISMEN CALISIYOR (CHAT_SYSTEM ile)
- Tool routing: CALISMIYOR (intent yok)
- Identity: TUTARSIZ (identity.py kullanilmiyor)
- Ollama: CALISIYOR (timeout sorunlari var)

### Hedef Durum
- Telegram transport: CALISIYOR
- Dogal sohbet: TAMAMEN CALISIYOR (UMAY_SYSTEM ile)
- Tool routing: CALISIYOR (intent router ile)
- Identity: TUTARLI (identity.py ile)
- Ollama: OPTIMIZE (kademeli timeout ile)

---

**Sonraki AI:** Bu raporu oku. Onerilen mimariyi uygula. identity.py'yi agent.py'ye entegre et, intent router olustur, test yaz.
