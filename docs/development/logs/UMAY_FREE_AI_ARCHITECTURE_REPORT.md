# UMAY ÜCRETSİZ AI / MİMO ENTEGRASYON ARAŞTIRMASI
**Tarih:** 2026-08-24
**Durum:** ARAŞTIRMA TAMAMLANDI — KOD YAZILMADI

---

## 1. MEVCUT UMAY DURUMU

### 1.1 Kurulu Local Modeller (10 adet)

| Model | Boyut | Görev | Durum |
|-------|-------|-------|-------|
| phi4-mini:latest | 2.3 GB | Chat (varsayılan) | ✅ Çalışıyor |
| qwen3:8b | 4.9 GB | Chat/Reasoning | ✅ Çalışıyor |
| qwen2.5-coder:7b | 4.4 GB | Coding | ✅ Çalışıyor |
| gemma2:9b | 5.1 GB | Genel | ✅ Çalışıyor |
| gemma3:4b | 3.1 GB | Vision | ✅ Çalışıyor |
| deepseek-r1:8b | 4.9 GB | Reasoning | ✅ Çalışıyor |
| granite3.3:8b | 4.6 GB | Analysis | ✅ Çalışıyor |
| llava:7b | 4.4 GB | Vision | ✅ Çalışıyor |
| bge-m3:latest | 1.1 GB | Embedding | ✅ Çalışıyor |
| nomic-embed-text | 0.3 GB | Embedding | ✅ Çalışıyor |

### 1.2 Cloud Model (1 adet — ÜCRETSİZ)

| Model | Sağlayıcı | Boyut | Görev | Durum |
|-------|-----------|-------|-------|-------|
| **gpt-oss:20b-cloud** | Ollama Cloud | Uzak sunucu | Coding/Agent | ✅ **ÇALIŞIYOR** |

**ÖNEMLİ:** `gpt-oss:20b-cloud` zaten kurulu ve çalışıyor! Bu model Ollama Cloud üzerinden sunuluyor ve ücretsiz tier'da erişilebilir.

### 1.3 Provider Altyapısı

```
core/engine.py → _get_provider_and_model()
    ├── mode == "local" → OllamaProvider (her zaman local)
    ├── mode == "online" → get_primary_provider()
    ├── mode == "auto" → PRIMARY_PROVIDER env var
    ├── PROVIDER_<TASK> → task-specific override
    └── fallback → Ollama

core/model_providers.py
    ├── OllamaProvider → localhost:11434 (local + cloud modeller)
    └── OpenAICompatibleProvider → herhangi bir OpenAI-compat API
```

---

## 2. MİMO'NUN MEVCUT KULLANIM ŞEKLİ

### 2.1 MiMo Kimdir?

Xiaomi tarafından geliştirilen açık kaynaklı dil modeli:
- **MiMo-V2-Flash:** 309B toplam, 15B aktif (MoE), MIT lisanslı
- **MiMo-V2-Pro:** Daha büyük,更强
- **MiMo-V2.5:** En yeni sürüm

### 2.2 MiMo Ücretsiz mi?

**HAYIR — Ücretsiz deneme süresi bitti.**

| Dönem | Durum |
|-------|-------|
| Aralık 2025 | Ücretsiz public beta başladı |
| Ocak 20, 2026 | Ücretsiz deneme süresi bitti |
| Ağustos 2026 | Ücretli API ($0.09-1/M input, $0.29-3/M output) |

### 2.3 MiMo Open Source mu?

**EVET — Ama local çalıştırma için çok büyük.**

- MiMo-V2-Flash: 309B parametre → 16GB RAM'de **çalışmaz**
- MiMo-V2.5-Pro: 1T+ parametre → kesinlikle **çalışmaz**
- GGUF versiyonları mevcut ama 16GB RAM için çok büyük

### 2.4 Freebuff MiMo'ya Nasıl Erişiyor?

Freebuff muhtemelen:
1. Xiaomi'nin API'sine doğrudan bağlanıyor
2. Veya OpenRouter/üçüncü parti üzerinden
3. Kullanıcının hesabına/kotasına bağlı

**Freebuff dışında aynı ücretsiz erişim kullanılabilir mi?**
**HAYIR** — Freebuff'a özel bir entegrasyon, UMAY'dan erişilemez.

---

## 3. FREEBUFF → MİMO BAĞLANTISI

### 3.1 Gerçek Durum

Freebuff:
- Electron uygulaması
- Orchestrator: random port + JWT
- IPC tabanlı iletişim
- Dışarıdan erişilebilir API: **YOK**

### 3.2 UMAY'dan Freebuff'a Bağlanma

| Yöntem | Durum | Neden |
|--------|-------|-------|
| HTTP API | ❌ | Random port + JWT |
| WebSocket | ❌ | Yok |
| CLI | ❌ | Yok |
| IPC | ❌ | Electron içi |
| Browser automation | ⚠️ | Kırılgan, yavaş |

### 3.3 Sonuç

**Freebuff'u UMAY'ın "provider"ı olarak kullanmak MÜMKÜN DEĞİL.**

---

## 4. ÜCRETSİZ ALTERNATİFLER

### 4.1 Ollama Cloud (EN İYİ SEÇENEK)

**Zaten çalışıyor!** `gpt-oss:20b-cloud` kurulu ve aktif.

| Özellik | Değer |
|---------|-------|
| Ücretsiz mi? | ✅ EVET (free tier) |
| API key gerekli mi? | ✅ EVET (ollama.com hesabı) |
| Tool calling | ✅ EVET (`capabilities: ['completion', 'tools', 'thinking']`) |
| Coding gücü | 🟡 Orta (20B MoE) |
| İnternet gerekli mi? | ✅ EVET |
| Limit | Session limiti (5 saat), weekly limit (7 gün) |
| UMAY'a uyum | ✅ MÜKEMMEL — OllamaProvider ile doğrudan çalışır |

**Nasıl çalışır:**
```
UMAY → OllamaProvider → localhost:11434 → ollama.com (cloud) → gpt-oss:20b
```

**Hiçbir kod değişikliği gerekmez.** Sadece model adı olarak `gpt-oss:20b-cloud` seçilir.

### 4.2 Ollama Cloud Diğer Modeller

Ollama Cloud'da mevcut güçlü modeller:

| Model | Güç | Tool Calling | Coding | Durum |
|-------|-----|-------------|--------|-------|
| gpt-oss:20b-cloud | 🟡 Orta | ✅ | 🟡 | ✅ Kurulu |
| gpt-oss:120b-cloud | 🔴 Güçlü | ✅ | 🔴 | ⚠️ Free tier limiti |
| deepseek-v4-flash | 🔴 Güçlü | ✅ | 🔴 | ⚠️ Free tier limiti |
| qwen3.5:397b | 🔴 Çok güçlü | ✅ | 🔴 | ⚠️ Free tier limiti |

### 4.3 Local Modeller (İnternetsiz)

16GB RAM + Intel Iris Xe üzerinde çalışabilecekler:

| Model | Boyut | Coding | Tool Calling | Hız | Öneri |
|-------|-------|--------|-------------|-----|-------|
| qwen2.5-coder:7b | 4.4 GB | 🔴 İyi | ✅ | 🟡 | ✅ En iyi coding |
| qwen3:8b | 4.9 GB | 🟡 İyi | ✅ | 🟡 | ✅ İyi genel |
| phi4-mini:latest | 2.3 GB | 🟡 Orta | ✅ | 🔴 Hızlı | ✅ Hızlı chat |
| deepseek-r1:8b | 4.9 GB | 🟡 İyi | ✅ | 🟡 | ✅ Reasoning |
| gemma3:4b | 3.1 GB | 🟡 Orta | ✅ | 🔴 Hızlı | ✅ Vision |
| gemma2:9b | 5.1 GB | 🟡 Orta | ✅ | 🟡 | ✅ Genel |

### 4.4 Diğer Ücretsiz Seçenekler (Araştırma)

| Seçenek | Ücretsiz | UMAY'a Bağlanabilir | Durum |
|---------|----------|---------------------|-------|
| OpenRouter free tier | ✅ | ⚠️ API key gerekli | Araştırma gerekli |
| Google AI Studio | ✅ | ⚠️ API key gerekli | Araştırma gerekli |
| Groq free tier | ✅ | ⚠️ API key gerekli | Araştırma gerekli |

---

## 5. DONANIM DEĞERLENDİRMESİ

### Mevcut Sistem
- **CPU:** Intel i7-12700H (14 çekirdek)
- **RAM:** 16 GB
- **GPU:** Intel Iris Xe (paylaşımlı bellek)
- **NVIDIA:** YOK

### Model Seçenekleri

| Kaynak | Max Model | Coding | Tool Calling | Hız |
|--------|-----------|--------|-------------|-----|
| **Local (CPU)** | 8B (~5GB) | 🟡 | ✅ | 🟡 10-20 t/s |
| **Ollama Cloud** | 120B+ | 🔴 | ✅ | 🔴 30-50 t/s |
| **Hybrid** | Local + Cloud | 🔴 | ✅ | 🔴 En iyi |

---

## 6. MİMO + OLLAMA HİBRİTİ

### 6.1 Mimari

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
                   │ Router  │
                   └────┬────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  Ollama  │  │ Ollama   │  │  UMAY    │
    │  Local   │  │ Cloud    │  │  Tools   │
    │          │  │          │  │ Terminal │
    │ qwen3:8b │  │ gpt-oss  │  │ Dosya    │
    │ coder:7b │  │ :20b     │  │ Web      │
    │ phi4-mini│  │ cloud    │  │ Browser  │
    └──────────┘  └──────────┘  └──────────┘
```

### 6.2 Router Mantığı

```python
# Basit sohbet → Local (hızlı, ücretsiz, offline)
if intent == "CHAT" and not requires_coding:
    return "phi4-mini:latest"  # veya qwen3:8b

# Kodlama/geliştirme → Cloud (güçlü, tool calling)
if intent in ["CODE", "COMPLEX"] and online_available:
    return "gpt-oss:20b-cloud"

# Offline durumda → Local coding
if not online_available:
    return "qwen2.5-coder:7b"

# Vision → Local
if intent == "VISION":
    return "gemma3:4b"  # veya llava:7b

# Reasoning → Local veya Cloud
if intent == "REASONING":
    if online_available:
        return "gpt-oss:20b-cloud"
    return "deepseek-r1:8b"
```

### 6.3 Bu Gerçekçi mi?

**EVET — VE ZATEN ÇALIŞIYOR.**

`gpt-oss:20b-cloud` zaten kurulu. UMAY'ın mevcut `OllamaProvider`'ı bu modelle doğrudan çalışabilir. Tek gereken:

1. `engine.py`'de `resolve_model("coding")` çağrıldığında `gpt-oss:20b-cloud`'u seçmesi
2. Veya `mode == "online"` olduğunda cloud modeli tercih etmesi

**Bu zaten mevcut kodla mümkün:**
```python
# engine.py → _get_provider_and_model()
# mode == "online" olduğunda cloud modeli kullanır
# mode == "auto" olduğunda PRIMARY_PROVIDER'a bakar
```

---

## 7. MİMO ÖZEL DEĞERLENDİRMESİ

### 7.1 UMAY'da MiMo Desteği

| Soru | Cevap |
|------|-------|
| MiMo UMAY'da destekleniyor mu? | ⚠️ Kodda var ama API key yok |
| Hangi endpoint? | OpenAI-compatible API |
| Hangi format? | `/chat/completions` (OpenAI formatı) |
| Tool calling? | ✅ OpenAI-compatible provider ile mümkün |
| Uyumlu mu? | ✅ EVET — `OpenAICompatibleProvider` ile |

### 7.2 MiMo'yu UMAY'a Bağlama Seçenekleri

| Seçenek | Ücretsiz | Mümkün | Risk |
|---------|----------|--------|------|
| MiMo API (Xiaomi) | ❌ Ücretli | ✅ | Düşük |
| Ollama Cloud (gpt-oss) | ✅ Ücretsiz | ✅ Zaten kurulu | Düşük |
| OpenRouter free | ✅ Ücretsiz | ⚠️ | Orta |
| Local MiMo | ✅ Ücretsiz | ❌ RAM yetersiz | Yok |

### 7.3 Sonuç

**MiMo'yu ücretsiz kullanmak İSTEMİYORSANIZ:**
→ Ollama Cloud (`gpt-oss:20b-cloud`) en iyi seçenek. Zaten kurulu.

**MiMo'yu özel olarak kullanmak İSTİYORSANIZ:**
→ Xiaomi API'sine kayıt + API key gerekli ($0.09-1/M token).

---

## 8. EN KRİTİK TABLO

| Seçenek | Ücretsiz | Resmi/izinli | Stabil | UMAY'a bağlanabilir | Tool Calling | Coding | İnternet |
|---------|----------|-------------|--------|---------------------|-------------|--------|----------|
| **Ollama Local** | ✅ | ✅ | ✅ | ✅ Zaten bağlı | ✅ | 🟡 Orta | ❌ Gerekmez |
| **Ollama Cloud** | ✅ (free tier) | ✅ | ✅ | ✅ **Zaten kurulu** | ✅ | 🟡 İyi | ✅ Gerekli |
| **MiMo API** | ❌ Ücretli | ✅ | ✅ | ✅ Possible | ✅ | 🔴 Güçlü | ✅ Gerekli |
| **OpenRouter Free** | ✅ | ✅ | ⚠️ | ⚠️ API key gerekli | ⚠️ | 🟡 | ✅ Gerekli |
| **qwen2.5-coder:7b** | ✅ | ✅ | ✅ | ✅ Kurulu | ✅ | 🔴 İyi | ❌ Gerekmez |
| **qwen3:8b** | ✅ | ✅ | ✅ | ✅ Kurulu | ✅ | 🟡 İyi | ❌ Gerekmez |
| **phi4-mini** | ✅ | ✅ | ✅ | ✅ Kurulu | ✅ | 🟡 Orta | ❌ Gerekmez |
| **deepseek-r1:8b** | ✅ | ✅ | ✅ | ✅ Kurulu | ✅ | 🟡 İyi | ❌ Gerekmez |

---

## 9. RİSKLER

| Risk | Olasılık | Etki | Azaltma |
|------|----------|------|---------|
| Ollama Cloud free tier limiti | Orta | Orta | Local fallback |
| gpt-oss modeli emekli olabilir | Düşük | Orta | Alternatif cloud model |
| İnternet kesintisi | Düşük | Düşük | Local modeller |
| Model kalitesi yetersiz | Orta | Orta | Hybrid approach |

---

## 10. ÖNERİLEN MİMARİ

### En Güçlü ÜCRETSİZ Mimari

```
UMAY AI Router:
├── LOCAL (offline, hızlı, ücretsiz)
│   ├── Chat → phi4-mini / qwen3:8b
│   ├── Coding → qwen2.5-coder:7b
│   ├── Vision → gemma3:4b / llava:7b
│   ├── Reasoning → deepseek-r1:8b
│   └── Analysis → granite3.3:8b
│
├── CLOUD (online, güçlü, ücretsiz-tier)
│   ├── Coding → gpt-oss:20b-cloud ✅ ZATEN KURULU
│   ├── Complex → gpt-oss:20b-cloud
│   └── Fallback → deepseek-v4-flash (eğer free tier müsaitse)
│
└── TOOLS (her zaman yerel)
    ├── Terminal → run_command
    ├── File → read/write/search
    ├── Web → web_search (DuckDuckGo)
    ├── Browser → Playwright
    └── Document → PDF/Word/Excel
```

### Neden Bu Mimari?

1. **Sıfır maliyet** — Tüm modeller ücretsiz
2. **Zaten çalışıyor** — gpt-oss:20b-cloud kurulu
3. **Offline destek** — İnternet yoksa local modeller
4. **Tool calling** — Tüm modeller destekliyor
5. **UMAY altyapısına uygun** — Mevcut kodda değişiklik gerekmez

---

## 11. UYGULAMA YOL HARİTASI

### FAZ 1: Cloud Model Aktifleştirme (1 saat)
**Değişen dosyalar:** `.env`
- `gpt-oss:20b-cloud` zaten kurulu — sadece `mode=online` test et
- UMAY chat'ten "kod yaz" deyince cloud modeli kullanıp kullanmadığını doğrula

### FAZ 2: AI Router İyileştirmesi (2-3 gün)
**Değişen dosyalar:** `core/engine.py`, `core/router.py`
- Intent'e göre otomatik local/cloud seçimi
- Online durumda cloud, offline'da local
- Coding görevlerinde cloud önceliği

### FAZ 3: Model Selection UI (1 gün)
**Değişen dosyalar:** `ui/panel.html`, `ui/panel_server.py`
- Panel'de model dropdown
- Local/Cloud ayrımı görünür
- Seçilen model bilgisi

### FAZ 4: Telegram Entegrasyonu (1-2 gün)
**Değişen dosyalar:** `core/telegram_user_adapter.py`
- Telegram'dan "online mod" komutu
- Görev bazlı otomatik mod seçimi

---

## SONUÇ

**"Ben olsam UMAY için şu ücretsiz mimariyi seçerdim: OLLAMA LOCAL + OLLAMA CLOUD HİBRİTİ"**

**Neden:**

1. **`gpt-oss:20b-cloud` zaten kurulu ve çalışıyor.** Hiçbir ek kurulum gerekmez. UMAY'ın mevcut `OllamaProvider`'ı bu modelle doğrudan çalışır.

2. **Sıfır maliyet.** Ollama Cloud free tier + local modeller = tamamen ücretsiz. MiMo API ücretli ($0.09-1/M token), gerek yok.

3. **Offline destek.** İnternet yoksa bile `qwen2.5-coder:7b` ve `qwen3:8b` ile güçlü coding/agent çalışır.

4. **Tool calling desteği.** `gpt-oss:20b-cloud`'un `capabilities: ['completion', 'tools', 'thinking']` — UMAY'ın 40+ tool'uyla uyumlu.

5. **Mevcut altyapıya uygun.** `engine.py`'deki `_get_provider_and_model()` zaten `mode="online"` olduğunda cloud modeli seçiyor. Tek gereken model adını bilmek.
