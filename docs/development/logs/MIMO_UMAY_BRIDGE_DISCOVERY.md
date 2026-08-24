# MIMO ↔ UMAY BAĞLANTI KEŞİF RAPORU
**Tarih:** 2026-08-24 03:20
**Durum:** KEŞİF TAMAMLANDI — IMPLEMENTASYON YAPILMADI

---

## A) MİMO'NUN GERÇEK ÇALIŞMA MİMARİSİ

Freebuff (Mimo) şu katmanlardan oluşur:

```
┌─────────────────────────────────────────┐
│  Electron Desktop App (Electron Main)   │
│  ┌───────────────────────────────────┐  │
│  │  Chromium Renderer (React UI)    │  │
│  │  - Chat input/output             │  │
│  │  - Preview/terminal/file tabs    │  │
│  │  - Build/Plan buttons            │  │
│  └───────────┬───────────────────────┘  │
│              │ IPC (electron IPC)        │
│  ┌───────────▼───────────────────────┐  │
│  │  Orchestrator (Express.js)       │  │
│  │  - /v1/messages endpoint         │  │
│  │  - Random port (127.0.0.1:0)    │  │
│  │  - JWT auth (runtime-generated)  │  │
│  │  - Bun.js runtime                │  │
│  └───────────┬───────────────────────┘  │
│              │ HTTP localhost             │
│  ┌───────────▼───────────────────────┐  │
│  │  Cloud/Model API                  │  │
│  │  (Anthropic, OpenAI, etc.)       │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Temel bulgular:**
- Orchestrator **127.0.0.1:0** (random port) dinliyor
- **IPC** üzerinden Electron ile haberleşiyor (HTTP değil)
- **JWT token** runtime'da üretiliyor (Local Storage'da saklanıyor)
- `/v1/messages` endpoint'i Anthropic API formatında
- Port ve token her başlatmada değişiyor
- **Dışarıdan erişilebilir bir API yok**

---

## B) MİMO'YA MESAJ GÖNDERİLEBİLEN GERÇEK KANAL

| Kanal | Durum | Açıklama |
|-------|-------|----------|
| **HTTP API** | ❌ ERİŞİLEMEZ | Random port + JWT — dışarıdan bağlantı kurulamıyor |
| **WebSocket** | ❌ YOK | Orchestrator'da WebSocket bulunamadı |
| **SSE/Event Stream** | ❌ YOK | Event stream mekanizması tespit edilmedi |
| **CLI/IPC** | ⚠️ SINIRLI | Electron IPC var ama Node.js process'inden erişilebilir değil |
| **File-based** | ⚠️ POTANSİYEL | worktree.md / CHANGELOG.md üzerinden dolaylı iletişim mümkün |
| **Browser Automation** | ✅ ÇALIŞIR | Playwright/Puppeteer ile Manipulate Chromium renderer |

**Sonuç:** Freebuff'un resmi, stabil, dışarıdan erişilebilir API'si **YOKTUR**.

---

## C) MİMO ÇIKTILARININ ALINABİLECEĞİ GERÇEK KANAL

| Çıktı Türü | Yakalanabilir mi? | Yöntem |
|------------|-------------------|--------|
| **Final response** | ⚠️ ZOR | Freebuff UI'da görünüyor ama API'den okunamıyor |
| **Thinking/progress** | ⚠️ ZOR | UI'da "Thinking..." olarak görünüyor |
| **Tool calls** | ⚠️ ZOR | "Run ..." formatında UI'da görünüyor |
| **Terminal output** | ⚠️ ZOR | Terminal sekmesinde görünüyor |
| **File changes** | ✅ KOLAY | worktree'de dosya değişiklikleri izlenebilir |
| **Git commits** | ✅ KOLAY | `git log` ile takip edilebilir |
| **Docker status** | ✅ KOLAY | `docker compose ps` ile kontrol edilebilir |

---

## D) YAKALANABİLEN EVENT TÜRLERİ

Freebuff'un doğrudan yakalanabilir eventleri:

1. **Dosya değişiklikleri** → `git status`, `git diff`
2. **Commit'ler** → `git log`
3. **Docker durumu** → `docker compose ps`
4. **worktree.md değişiklikleri** → Dosya okuma
5. **Log dosyaları** → `tail -f` benzeri okuma

Yakalanamayan eventler:
- Model cevabı (sadece UI'da)
- Thinking süreci (sadece UI'da)
- Tool çağrı detayları (sadece UI'da)

---

## E) SESSION/YÖNETİM

- Freebuff session'ları Electron Local Storage'da saklanıyor
- JWT token her başlatmada değişiyor
- UMAY'nin kendi session'ları: `telegram_user_sessions/`
- UMAY conversation'ları: `memory/conversations.jsonl`

---

## F) TELEGRAM → UMAY → MİMO MİMARİSİ ÖNERİSİ

### Mevcut Durum
UMAY zaten tam çalışan bir Telegram bağlantısına sahip:
- `telegram_user_adapter.py` (322 satır, Telethon MTProto)
- `telegram_adapter.py` (Bot API)
- `communication_manager.py` üzerinden mesaj yönlendirme
- `/approve`, `/reject`, `/cancel` komutları
- Dosya/medya desteği

### Gerçekçi Mimariler

#### SEÇENEK A: UMAY Bağımsız Çalışma (ÖNERİLEN — EN GÜVENİLİR)
```
📱 Telegram → UMAY → UMAY Agent (Ollama) → 📱 Telegram
                   → UMAY Panel
```
- UMAY kendi başına çalışır (zaten yapıyor)
- Freebuff'a bağımlılık yok
- Telegram'dan görev verilir, UMAY kendi agent'ıyla çözer
- Panel'de canlı durum gösterilir

**Avantaj:** Tamamen bağımsız, güvenilir, mevcut
**Dezavantaj:** Freebuff'un gelişmiş yeteneklerini (Claude, GPT vb.) kullanamaz

#### SEÇENEK B: Dosya Tabanlı Köprü (ORTA GÜVENİLİRLİK)
```
📱 Telegram → UMAY → worktree.md yazısı → Freebuff okur
📱 Telegram ← UMAY ← git log/diff ← Freebuff çalıştırır
```
- UMAY bir "görev dosyası" yazar
- Freebuff bu dosyayı worktree'de görür ve üzerinde çalışır
- UMAY sonuçları `git log/diff` ile takip eder

**Avantaj:** Freebuff'un gücünü kullanır
**Dezavantaj:** Güvenilir değil, dosya senkronizasyonu sorunlu

#### SEÇENEK C: Freebuff API Engelini Aşma (RİSKLİ)
```
📱 Telegram → UMAY → Freebuff Orchestrator (port+JWT) → Cloud API
📱 Telegram ← UMAY ← Freebuff UI ← response
```
- Freebuff'un random portunu bulup JWT ile bağlanma girişimi
- Port her başlatmada değişiyor, token runtime üretiliyor

**Avantaj:** Doğrudan bağlantı
**Dezavantaj:** Kırılgan, Freebuff güncellemeleriyle bozulabilir, etik olmayabilir

#### SEÇENEK D: Browser Automation (EN YAVAŞ)
```
📱 Telegram → UMAY → Playwright → Freebuff Chromium UI → Cloud API
📱 Telegram ← UMAY ← Playwright ← Freebuff UI ← response
```
- Playwright ile Freebuff Chromium'unu kontrol etme
- Input'a yaz, submit et, response'u DOM'dan oku

**Avantaj:** Her şeyi yapabilir
**Dezavantaj:** Çok yavaş, kırılgan, bakım maliyetli

---

## G) MİMO → UMAY → TELEGRAM + PANEL MİMARİSİ

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
│ Telegram │────▶│   UMAY  │────▶│ UMAY     │────▶│ UMAY     │
│ (Cengiz) │     │ Telegram│     │ Agent    │     │ Panel    │
│          │◀────│ Adapter │◀────│ (Ollama) │◀────│ (5001)   │
└─────────┘     └─────────┘     └──────────┘     └──────────┘
                                    │
                                    ▼
                              ┌──────────┐
                              │ Dashboard│
                              │ Chat     │
                              │ Tasks    │
                              │ Logs     │
                              └──────────┘
```

Bu mimari ZATEN ÇALIŞIYOR. UMAY'nin:
- Telegram User Account adapter'ı aktif
- UMAY Agent modülü çalışıyor
- Panel 5001 portunda çalışıyor
- Dashboard gerçek veri gösteriyor

---

## H) RECONNECT YÖNTEMİ

Telegram adapter'ı zaten reconnect mekanizmasına sahip:
- `telegram_user_adapter.py` → `run_until_disconnected()` + daemon thread
- `telegram_adapter.py` → polling loop + exponential backoff
- Connection lost → auto-reconnect

---

## I) GÜVENLİK MODELİ

| Katman | Durum |
|--------|-------|
| Telegram yetkilendirme | ✅ `TELEGRAM_USER_ALLOWED_USER_ID` |
| UMAY agent onay sistemi | ✅ `approval_manager.py` |
| Tool execution | ✅ `EXECUTION_MODE=approval` |
| Rate limiting | ✅ `core/rate_limiter.py` |
| Idempotency | ✅ `core/idempotency.py` |
| Secret scanner | ✅ `scripts/secret_scanner.py` |

---

## J) WINDOWS/DOCKER AÇISINDAN ÖNERİLEN MİMARİ

```
Windows Host:
├── Docker Container (umay-agent)
│   ├── UMAY Panel (port 5001)
│   ├── UMAY Agent (Ollama)
│   ├── Telegram User Adapter
│   └── Telegram Bot Adapter
├── Ollama (localhost:11434)
├── Freebuff (Electron, ayrı process)
└── Telegram Desktop (ayrı process)
```

---

## K) EN GÜVENİLİR BAĞLANTI YÖNTEMİ

**SEÇENEK A: UMAY Bağımsız Çalışma**

Neden:
1. UMAY zaten Telegram entegrasyonuna sahip
2. UMAY zaten Ollama ile çalışıyor
3. UMAY zaten panel'e sahip
4. Freebuff'a bağımlılık = kırılganlık
5. UMAY tek başına zaten güçlü bir asistan

---

## L) UYGULAMA İÇİN GEREKEN UMAY DOSYALARI/MODÜLLER

Zaten mevcut:
- `core/telegram_user_adapter.py` ✅
- `core/telegram_adapter.py` ✅
- `core/communication_manager.py` ✅
- `core/approval_manager.py` ✅
- `core/rate_limiter.py` ✅
- `core/idempotency.py` ✅
- `core/audit_timeline.py` ✅
- `ui/panel_server.py` ✅
- `core/agent.py` ✅
- `core/engine.py` ✅

Geliştirme gerektirebilecekler:
- UMAY Agent'ın capability genişletme (daha güçlü tool'lar)
- Daha iyi intent routing
- Multi-step task planning
- Checkpoint/recovery

---

## M) TAHMİNİ IMPLEMENTASYON AŞAMALARI

Eğer SEÇENEK A (bağımsız çalışma) seçilirse:

1. Telegram adapter'ı test et ve aktif et (1-2 saat)
2. UMAY agent capability'lerini genişlet (2-4 saat)
3. Panel'de Telegram durumu göster (1 saat)
4. E2E test: Telegram → UMAY → Telegram döngüsü (2 saat)
5. Prova: Gerçek kullanıcı testi (1 saat)

Toplam: ~8-10 saat

---

## N) RİSKLER VE SINIRLAMALAR

### Freebuff Bağımlılığı Riskleri
1. Freebuff API'si stabil değil (random port, runtime JWT)
2. Freebuff güncellemeleri API'yı değiştirebilir
3. Electron IPC dışarıdan erişilemez
4. Browser automation çok yavaş ve kırılgan

### UMAY Bağımsız Çalışma Riskleri
1. Ollama model gücü sınırlı (lokal modeller)
2. İnternet erişimi için online mode gerekiyor
3. Büyük dosya işleme bellek sınırlı

### Ortak Riskler
1. Telegram rate limit (çok mesaj → engellenme)
2. Uzun görevlerde timeout
3. Docker restart sonrası session kaybı

---

## ÖZET

| Soru | Cevap |
|------|-------|
| Freebuff'ta dış API var mı? | ❌ HAYIR |
| Doğrudan bağlantı mümkün mü? | ❌ DEĞİL |
| UMAY zaten Telegram ile çalışıyor mu? | ✅ EVET |
| UMAY tek başına yeterli mi? | ⚠️ Ollama gücüne bağlı |
| En güvenilir mimari nedir? | UMAY bağımsız çalışma |
| Freebuff'u köprü olarak kullanabilir miyiz? | ⚠️ Dosya tabanlı possible ama güvenilir değil |

---

**SONUÇ:** UMAY zaten Telegram → Agent → Panel döngüsünü çalıştırıyor. Freebuff ile köprü kurmak yerine, UMAY'ın kendi yeteneklerini güçlendirmek daha güvenilir ve sürdürülebilir bir yaklaşımdır.

Eğer Freebuff'un model gücünü (Claude/GPT) kullanmak istiyorsan, **Seçenek B (dosya tabanlı)** veya **Seçenek D (browser automation)** denenmelidir — ama ikisi de güvenilir değildir.

**ÖNERİM:** UMAY'ı bağımsız güçlü bir asistan olarak geliştir. Telegram'dan UMAY'a görev ver, UMAY kendi başına çalışsın.
