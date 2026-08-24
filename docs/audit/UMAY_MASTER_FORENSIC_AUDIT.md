# UMAY MASTER FORENSIC AUDIT
## FINAL — FAZ 4

**Audit Date**: 2026-08-24
**Audit Phases**: Backend (FAZ 1) + Frontend (FAZ 2) + Human Use (FAZ 3) + Master Review (FAZ 4)
**Auditor**: Buffy (Freebuff)
**Method**: Code analysis + runtime testing + security probing + real human-use simulation
**Kural**: HİÇBİR KOD DEĞİŞTİRİLMEDİ. Sadece tespit ve raporlama.

---

# 1. EXECUTIVE SUMMARY

UMAY, 110 Python dosyası, 16K+ satır core, 1,297 satır frontend, 64 tool, 11 model ile çalışan bir AI asistanıdır. Teknik altyapısı çalışıyor — API endpoint'leri cevap veriyor, modeller bağlı, tool dispatch çalışıyor.

**AMA GERÇEK KULLANIM TESTLERİNDE %38 BAŞARI ORANI ALDI.**

Neden? Çünkü **intent router çok agresif** — dosya okuma, kod üretimi, hata analizi gibi görevler Calculator'a gidiyor ve başarısız oluyor. UMAY teknik olarak "çalışıyor" ama kullanıcının istediği işi yapamıyor.

| Metrik | Değer |
|--------|-------|
| Toplam incelenen dosya | 110+ Python, 1 HTML |
| Toplam test | 50+ |
| PASS | ~30 |
| FAIL | ~15 |
| PARTIAL | ~5 |
| NOT VERIFIED | 3 |
| P0 Critical | 0 |
| P1 High | 4 |
| P2 Medium | 12 |
| P3 Low | 11 |
| P4 Cleanup | 8 |
| **Toplam bulgu** | **35** |

---

# 2. MEVCUT SİSTEM MİMARİSİ

```
USER (Telegram/Panel)
    ↓
INTENT ROUTER (classify_intent) ← 🔴 KRİTİK SORUN BURADA
    ↓
ROUTER (model_sec) ← 🟡 Eksik kategoriler
    ↓
ENGINE (resolve_model) ← ✅ Çalışıyor
    ↓
PROVIDER (Ollama/Cloud) ← ✅ Çalışıyor
    ↓
AGENT LOOP (tool calling) ← ⚠️ Tool çağrılama sorunlu
    ↓
TOOLS (64 tanımlı, 62 dispatched) ← 🔴 2 tool eksik
    ↓
RESULT → USER
```

**Critical Path**: Intent Router → Tool Selection → Tool Execution
**Bu zincirdeki her kopukluk kullanıcı deneyimini bozuyor.**

---

# 3. BACKEND DURUMU

## Çalışan Sistemler ✅
| Sistem | Durum | Kanıt |
|--------|-------|-------|
| Flask+SocketIO server | ✅ | Port 5001 açık, health check 200 |
| Ollama connection | ✅ | 11 model kurulu, cloud model aktif |
| Intent classification (basit) | ✅ | "Merhaba" → CHAT, "resmi analiz" → VISION |
| Model routing (cloud) | ✅ | coding → gpt-oss:20b-cloud |
| Model routing (local) | ✅ | chat → phi4-mini |
| Tool dispatch (62/64) | ✅ | list_directory, read_file, run_command çalışıyor |
| Path traversal protection | ✅ | _safe_path engelliyor |
| Web search | ✅ | DuckDuckGo sonuçları geliyor |
| Document reading | ✅ | Multi-format okuma |
| File lifecycle | ✅ | Create→Read→Modify→Delete |
| Task state persistence | ✅ | JSONL okuma/yazma |
| Conversation store | ✅ | JSONL session management |
| Approval manager | ✅ | Singleton working |
| Rate limiter | ✅ | Basit rate limit |

## Bozuk Sistemler ❌
| Sistem | Sorun | Kök Neden |
|--------|-------|-----------|
| Intent Router (Calculator) | Çok agresif tetikleme | Tek karakter operatörler her yeri tetikliyor |
| FILE intent | Dosya istekleri algılanmıyor | Keywords çok dar |
| search_files | Glob pattern regex error | Manuel regex dönüşümü hatalı |
| get_system_info | CPU/RAM bilgisi yok | Docker container'da psutil kullanılmıyor |
| Vision analysis | Görsel analiz başarısız | Model multimodal yeteneği yetersiz |
| Tool dispatch (2) | aider_edit, multi_file_edit eksik | Fonksiyonlar tanımlı ama DISPATCH'e bağlanmamış |

## Güvenlik Sorunları 🔴
| Sorun | Ciddiyet | Kanıt |
|-------|---------|-------|
| run_command whitelist yok | P1 | Herhangi bir shell komutu çalıştırılabilir |
| /etc/passwd okunabilir | P1 | cat /etc/passwd returncode=0 |

---

# 4. FRONTEND DURUMU

## Çalışan Sistemler ✅
| Özellik | Durum |
|---------|-------|
| Dashboard (14 sayfa) | ✅ Tüm sayfalar açılıyor |
| API endpoint'leri (19) | ✅ Tümü 200 dönüyor |
| SocketIO (6 event) | ✅ Temel iletişim çalışıyor |
| Model selector (11 model) | ✅ Doğru listeleniyor |
| Mode selector (3 mod) | ✅ AUTO/LOCAL/ONLINE |
| Chat (SocketIO + HTTP fallback) | ✅ Mesaj gönderimi çalışıyor |
| Dosya ekleme (button+drag+clipboard) | ✅ Çalışıyor |
| Markdown rendering | ✅ Code blocks, bold, links |
| Conversation history | ✅ Session listesi + arama |
| Diagnostics | ✅ Çalışıyor |
| Benchmark | ✅ Çalışıyor |

## Bozuk/eksik Sistemler ❌
| Özellik | Sorun |
|---------|-------|
| local_fast/local_smart mapping | Backend'de karşılığı yok |
| api() error handling | Sessiz fail — hata mesajı yok |
| task_completed event | Backend emit ediyor, frontend dinlemiyor |
| telegram_status event | Backend emit ediyor, frontend dinlemiyor |
| Dosya silme | UI'da silme butonu yok |
| Model/Mode persistence | Sayfa yenilendiğinde kayboluyor |
| Dil tutarsızlığı | UI İngilizce, chat Türkçe |

---

# 5. HUMAN-USE DURUMU

## Test Sonuçları: %38 Başarı

| Test | Durum | Kök Neden |
|------|-------|-----------|
| Merhaba nasılsın | ✅ PASS | — |
| Hava durumu | ⚠️ PARTIAL | URL listesi, sentez yok |
| Kod üretimi (basit) | ✅ PASS | — |
| requirements.txt oku | ❌ FAIL | Intent FILE algılanmadı |
| engine.py ilk 10 satır | ❌ FAIL | Calculator'a gitti |
| core klasörünü listele | ❌ FAIL | Tool kullanılmadı |
| Dosya oluştur | ❌ FAIL | Calculator'a gitti |
| Fibonacci script yaz | ❌ FAIL | Calculator'a gitti |
| Kod hatası bul | ❌ FAIL | Calculator'a gitti |
| Python 3.13 araştır | ⚠️ PARTIAL | Eski bilgi |
| Hatalı dosya | ✅ PASS | — |
| Boş mesaj | ✅ PASS | — |

---

# 6. CRITICAL BUGS

## 🔴 BUG-01: Calculator Intent Over-Trigger (P1)
**Symptom**: Dosya okuma, kod üretimi, hata analizi Calculator'a gidiyor
**Immediate Cause**: `has_math_ops = any(op in text_lower for op in ['+', '-', '*', '/', '='])` tek karakter eşleşmesi
**Root Cause**: Intent router'da Calculator detection, diğer intent'lerden ÖNCE geliyor ve çok geniş
**Systemic Cause**: Intent priority sıralaması yanlış — Calculator en yüksek önceliğe sahip olmamalı
**Files**: `core/intent_router.py` satır 59-67, 195-280
**Impact**: Tüm dosya/kod/analiz görevleri başarısız

## 🔴 BUG-02: FILE Intent Too Narrow (P1)
**Symptom**: "dosyasını oku", "ilk 10 satırını göster" algılanmıyor
**Immediate Cause**: FILE keywords sadece "dosyayı oku", "klasörü listele" gibi kesin kalıpları içeriyor
**Root Cause**: Doğal dildeki dosya istekleri yeterince kapsanmıyor
**Systemic Cause**: Intent设计'ı formal kalıplara dayanıyor, doğal dile değil
**Files**: `core/intent_router.py` satır 69-89
**Impact**: Dosya okuma/yazma/listeleme çalışmıyor

## 🔴 BUG-03: run_command No Whitelist (P1)
**Symptom**: Herhangi bir shell komutu çalıştırılabilir
**Immediate Cause**: `subprocess.run(command, shell=True)` filtre yok
**Root Cause**: Güvenlik katmanı hiç eklenmemiş
**Systemic Cause**: Tool security model'i eksik
**Files**: `core/agent_tools.py` → `run_command()`
**Impact**: Sistem güvenliği açıklığı

## 🔴 BUG-04: CHAT Intent Tool Bypass (P1)
**Symptom**: CHAT intent'inde tool kullanılmıyor
**Immediate Cause**: `use_tools = False` CHAT/KNOWLEDGE intent'lerinde
**Root Cause**: Basit sohbet ile dosya/komut istekleri ayrımı yapılamıyor
**Systemic Cause**: Intent → Tool mapping eksik
**Files**: `ui/panel_server.py` → `execute_chat_task()`
**Impact**: Dosya/klasör istekleri tool kullanılmadan reddediliyor

---

# 7. FALSE SUCCESS BUGS

## 🟡 FS-01: "Tool SUCCESSFUL" Ama Yanlış Tool
**Senaryo**: "requirements.txt dosyasında ne var?" → Intent.FILE → dosya okunmalı
**Gerçek**: Intent CHAT → tool kullanılmadı → "dosya ne işe yarar" cevabı
**False Success**: UMAY "başarılı" bir cevap döndü ama dosyayı okumadı

## 🟡 FS-02: Calculator "Hesaplama" Ama Görev Başarısız
**Senaryo**: "engine.py ilk 10 satırı göster" → Calculator tetiklendi
**Gerçek**: evaluate_expression("core/engine.py dosyasının ilk 10 satırını göster") → "invalid syntax"
**False Success**: Tool çağrıldı ama yanlış tool, yanlış argüman, başarız sonuç

## 🟡 FS-03: Web Search "Successful" Ama Sentez Yok
**Senaryo**: "hava durumu" → web_search → URL listesi
**Gerçek**: 3 URL döndü ama gerçek hava durumu bilgisi yok
**False Success**: Tool çalıştı ama kullanıcı isteği karşılanmadı

## 🟡 FS-04: "Model: gpt-oss:20b-cloud" Ama Aslında phi4-mini
**Senaryo**: Coding task'ı gpt-oss:20b-cloud seçmeli
**Gerçek**: Intent CHAT → phi4-mini kullanıldı (daha önce düzeltildi ama tekrar edebilir)
**False Success**: UI'da cloud model görünüyor ama local model kullandı

## 🟡 FS-05: API 200 Ama Yanlış Response
**Senaryo**: Boş mesaj gönderme
**Gerçek**: 400 BAD REQUEST — bu doğru Davranış
**False Success**: Yok — bu test PASS (olumlu istisna)

---

# 8. ROOT CAUSES

## Sistem Kök Nedenleri

### RC-01: Intent Priority Sistemi Yanlış
**Problem**: Calculator en yüksek önceliğe sahip ve tek karakter tetikleme yapıyor
**Çözüm**: Intent priority sıralamasını yeniden tasarla — dosya/kod/web intent'leri Calculator'dan önce gelmeli
**Bağımlılık**: Diğer tüm sorunların kök nedeni

### RC-02: Intent Keywords Formal Kalıplara Dayalı
**Problem**: "dosyayı oku" var ama "dosyasının", "ilk X satır", "göster" yok
**Çözüm**: Doğal dil kalıplarını ekle — regex pattern ile genişlet
**Bağımlılık**: RC-01'den sonra

### RC-03: Tool Security Model'i Eksik
**Problem**: run_command whitelist yok, her komut çalıştırılabilir
**Çözüm**: Command whitelist/blacklist + Docker sandbox kısıtlaması
**Bağımlılık**: Bağımsız

### RC-04: Intent → Tool Mapping Eksik
**Problem**: CHAT intent'inde tool kullanılmıyor
**Çözüm**: CHAT intent'inde bile dosya/komut pattern'lerini kontrol et
**Bağımlılık**: RC-01 ve RC-02'den sonra

### RC-05: Model Routing gaps
**Problem**: WEB/FILE intent'leri model_sec'te karşılığı yok
**Çözüm**: model_sec() RULES listesini genişlet
**Bağımlılık**: Bağımsız

---

# 9. SECURITY ISSUES

| ID | Sorun | Ciddiyet | Dosya | Etki |
|----|-------|---------|-------|------|
| SEC-01 | run_command shell injection | 🔴 P1 | agent_tools.py | Herhangi bir komut çalıştırılabilir |
| SEC-02 | /etc/passwd okunabilir | 🔴 P1 | agent_tools.py | Sistem dosyaları okunabilir |
| SEC-03 | UMAY_MODE=approval bypass | 🟡 P2 | .env | UMAY_APPROVED=true ile her şey çalıştırılabilir |
| SEC-04 | .env container içinde okunabilir | 🟡 P2 | Docker | API key/secret'lar erişilebilir |

---

# 10. RELIABILITY SCORES

| Kategori | Puan | Kanıt |
|----------|------|-------|
| Chat | 3/5 | Basit selamlama çalışıyor, takip soruları kayıp |
| Memory | 2/5 | Conversation history var ama bağlam korunmuyor |
| File | 1/5 | Dosya işlemleri Calculator'a gidiyor |
| Computer Control | 1/5 | Komut çalıştırmada getRandom command succeeds |
| Coding | 2/5 | Basit kod üretiyor ama karmaşık istekler Calculator'a gidiyor |
| Agent | 1/5 | Tool calling Interrupted by wrong intent |
| Tool Calling | 2/5 | 62/64 tool dispatched ama intent routing başarısız |
| Web Research | 2/5 | Arama çalışıyor ama sentez yok |
| Deep Search | 1/5 | Test edilemedi |
| Model Routing | 3/5 | Cloud/local ayrımı çalışıyor ama gaps var |
| Error Recovery | 2/5 | Hata mesajları teknik, kullanıcı anlayamıyor |
| Telegram | 0/5 | Yapılandırılmamış — NOT VERIFIED |
| Proactive Behavior | 0/5 | Yok — NOT VERIFIED |
| Security | 1/5 | Whitelist yok, sistem dosyaları okunabilir |
| Frontend UX | 3/5 | Güzel görünüyor ama temel özellikler çalışmıyor |

**Ortalama: 1.5/5** — UMAY şu anda prototip seviyesinde.

---

# 11. DEPENDENCY GRAPH

```
RC-01 (Intent Priority)
├── RC-02 (Intent Keywords)
│   ├── HU-01 (Calculator Over-Trigger)
│   ├── HU-02 (File Operations)
│   └── HU-03 (Tool Bypass)
├── HU-04 (Web Synthesis)
└── HU-05 (Context Loss)

RC-03 (Tool Security) ← Bağımsız
├── SEC-01 (Shell Injection)
└── SEC-02 (System Files)

RC-05 (Model Routing) ← Bağımsız
├── RR-01 (FILE routing)
└── RR-02 (WEB routing)
```

**Kritik yol**: RC-01 → RC-02 → Tüm human-use sorunları

---

# 12. P0/P1/P2/P3/P4 LİSTESİ

## P0 Critical — Yok

## P1 High (4)
| ID | Sorun | Dosya | Etki |
|----|-------|-------|------|
| BUG-01 | Calculator over-trigger | intent_router.py | Tüm dosya/kod görevleri başarısız |
| BUG-02 | FILE intent too narrow | intent_router.py | Dosya okuma/yazma çalışmıyor |
| BUG-03 | run_command no whitelist | agent_tools.py | Güvenlik açığı |
| BUG-04 | CHAT tool bypass | panel_server.py | Tool kullanılmayan görevler |

## P2 Medium (12)
| ID | Sorun | Dosya |
|----|-------|-------|
| F4-01 | search_files glob error | agent_tools.py |
| F4-02 | get_system_info CPU/RAM eksik | agent_tools.py |
| T6-03 | 2 tool dispatch eksik | agent_tools.py |
| T6-04 | Vision analysis başarısız | vision_reader.py |
| RR-02 | WEB intent cloud model seçmiyor | router.py |
| HU-04 | Web arama sentezlenmiyor | panel_server.py |
| HU-05 | Bağlam kaybı | panel_server.py |
| FE-02 | local_fast/local_smart mapping yok | panel.html |
| FE-07 | api() sessiz hata yutuyor | panel.html |
| FE-04 | task_completed event dinlenmiyor | panel.html |
| FE-05 | telegram_status event dinlenmiyor | panel.html |
| SEC-03 | UMAY_MODE bypass | .env |

## P3 Low (11)
| ID | Sorun | Dosya |
|----|-------|-------|
| F4-05 | CHAT intent routing bypass | panel_server.py |
| RR-01 | Intent.FILE model_sec("chat") | router.py |
| RR-04 | _cloud_model_available cache yok | engine.py |
| T6-01 | write_file overwrite created=false | agent_tools.py |
| FE-06 | Dosya silme yok | panel.html |
| FE-08 | Model/Mode persistence yok | panel.html |
| FE-09 | Settings read-only | panel.html |
| FE-10 | Approvals placeholder | panel.html |
| FE-11 | Scheduler read-only | panel.html |
| FE-12 | Workers sayfası eksik | panel.html |
| SEC-04 | .env okunabilir | Docker |

## P4 Cleanup (8)
| ID | Sorun |
|----|-------|
| F4-14-F4-19 | 6 dead code dosyası (1,936 satır) |
| FE-01 | chatHistory dead variable |
| FE-16 | Dil tutarsızlığı |
| FE-17 | Topbar LOCAL badge tutarsız |
| FE-18 | Agent durumları hardcoded |
| — | 140+ draft JSON email_cache |
| — | Eski rapor .md dosyaları |
| — | /api/git yanıltıcı isim |

---

# 13. DEVELOPMENT ROADMAP

## FAZ 0 — Kritik Güvenlik (1 gün)
- [ ] run_command whitelist/blacklist ekle
- [ ] /etc/passwd erişimini engelle

## FAZ 1 — Intent Router Yeniden Tasarımı (2-3 gün)
- [ ] Calculator detection'ı kısıtla (tek karakter operatörler yeterli değil)
- [ ] FILE intent'i genişlet (doğal dil kalıpları)
- [ ] Intent priority sıralamasını düzelt
- [ ] CHAT intent'inde tool kullanma kontrolü ekle

## FAZ 2 — Tool Sistemi (1-2 gün)
- [ ] search_files glob fix
- [ ] get_system_info CPU/RAM ekleme
- [ ] aider_edit/multi_file_edit dispatch ekle
- [ ] write_file overwrite response fix

## FAZ 3 — Model/Agent (1 gün)
- [ ] WEB/FILE intent için model_sec() genişletme
- [ ] _cloud_model_available() cache
- [ ] local_fast/local_smart mapping

## FAZ 4 — Frontend (2-3 gün)
- [ ] api() error handling
- [ ] task_completed/telegram_status event listener
- [ ] Dosya silme butonu
- [ ] Model/Mode persistence
- [ ] Dil tutarsızlığı fix

## FAZ 5 — Web/Research (1-2 gün)
- [ ] Web arama sonuçlarını sentezleme
- [ ] Güncellik kontrolü

## FAZ 6 — Memory/Context (1-2 gün)
- [ ] Bağlam yönetimi (conversation history)
- [ ] Takip sorusu desteği

## FAZ 7 — Telegram (1-2 gün)
- [ ] Telegram session oluşturma
- [ ] Proactive notification test

## FAZ 8 — Regression (1 gün)
- [ ] Tüm testleri çalıştır
- [ ] Human-use testlerini tekrar et
- [ ] %80+ başarı hedefle

---

# 14. DEVELOPER TASK LİSTESİ

## TASK-01: Calculator Intent Kısıtlama
**Amaç**: Calculator'ı sadece gerçek matematik işlemlerinde tetikle
**Dosyalar**: `core/intent_router.py`
**Yapılacak iş**:
- Tek karakter operatörleri (`-`, `+`, `*`, `/`, `=`) tek başına yeterli kabul etme
- Sayı + operatör kombinasyonunu daha spesifik yap
- Dosya yolu pattern'lerini kontrol et (`.py`, `.txt`, `/`)
- Kod kalıplarını kontrol et (`def `, `class `, `import `)
**Kabul kriteri**: "10 satır", "ilk 10", "def add(a,b)" Calculator'a gitmemeli
**Test kriteri**: 10 farklı doğal dil isteği test edilmeli
**Bağımlılık**: Yok
**Öncelik**: P1

## TASK-02: FILE Intent Genişletme
**Amaç**: Doğal dildeki dosya isteklerini algıla
**Dosyalar**: `core/intent_router.py`
**Yapılacak iş**:
- "dosyasının", "dosyasını", "ilk X satır", "göster", "oku" gibi kelimeleri ekle
- Dosya uzantısı pattern'lerini ekle (`.py`, `.txt`, `.json`)
- Regex pattern ile doğal dil kalıplarını yakala
**Kabul kriteri**: "engine.py dosyasının ilk 10 satırını göster" → FILE
**Test kriteri**: 5 farklı dosya isteği test edilmeli
**Bağımlılık**: TASK-01'den sonra
**Öncelik**: P1

## TASK-03: run_command Whitelist
**Amaç**: Tehlikeli komutları engelle
**Dosyalar**: `core/agent_tools.py`
**Yapılacak iş**:
- Tehlikeli komut blacklist'i ekle (`rm -rf`, `mkfs`, `dd`, vb.)
- Sistem dosyası erişimini engelle (`/etc/passwd`, `/etc/shadow`)
- Docker sandbox kısıtlaması ekle
**Kabul kriteri**: `rm -rf /` → reddedilmeli, `cat /etc/passwd` → reddedilmeli
**Test kriteri**: 5 tehlikeli komut test edilmeli
**Bağımlılık**: Yok
**Öncelik**: P1

## TASK-04: CHAT Intent Tool Check
**Amaç**: CHAT intent'inde bile dosya/komut pattern'lerini kontrol et
**Dosyalar**: `ui/panel_server.py`
**Yapılacak iş**:
- CHAT intent'inde `model_sec()` çağrısını koru (mevcut fix)
- Ama aynı zamanda dosya/komut pattern'lerini de kontrol et
- Eğer dosya/komut pattern'i varsa tool kullan
**Kabul kriteri**: "requirements.txt'de ne var?" → FILE intent → tool kullanmalı
**Test kriteri**: 3 farklı dosya isteği test edilmeli
**Bağımlılık**: TASK-01 ve TASK-02'den sonra
**Öncelik**: P1

## TASK-05: search_files Glob Fix
**Amaç**: `*.py` glob pattern'ini düzelt
**Dosyalar**: `core/agent_tools.py`
**Yapılacak iş**:
- `fnmatch` veya `pathlib.glob` kullan
- Manuel regex dönüşümünü kaldır
**Kabul kriteri**: `search_files(pattern="*.py")` → dosya listesi dönmeli
**Test kriteri**: 3 farklı glob pattern test edilmeli
**Bağımlılık**: Yok
**Öncelik**: P2

## TASK-06: get_system_info CPU/RAM
**Amaç**: CPU/RAM bilgisini ekle
**Dosyalar**: `core/agent_tools.py`
**Yapılacak iş**:
- Docker container'da `/proc/stat` ve `/proc/meminfo` oku
- Veya psutil'i container'a kur
**Kabul kriteri**: `get_system_info()` → cpu_percent, ram_percent içermeli
**Test kriteri**: CPU/RAM değerleri gerçek değerlerle eşleşmeli
**Bağımlılık**: Yok
**Öncelik**: P2

---

# 15. ACCEPTANCE CRITERIA

### Her Özellik İçin "Done" Tanımı

| Özellik | IMPLEMENTED | UNIT TEST | INTEGRATION | REAL BEHAVIOR | FAILURE TEST | USER SCENARIO |
|---------|-------------|-----------|-------------|---------------|--------------|---------------|
| Intent Router | Calculator kısıtlama + FILE genişletme | 10 intent test | Tüm mesaj türleri | "engine.py ilk 10 satır" → FILE | Boş mesaj, hatalı input | 5 doğal dil senaryosu |
| Tool Security | Whitelist/blacklist | 5 tehlikeli komut | Container runtime | `cat /etc/passwd` → engellenmeli | Bypass denemeleri | Güvenli kullanım |
| Dosya İşlemleri | read/write/list | 3 dosya lifecycle | Agent loop | "dosyayı oku" → dosya gerçekten okunmalı | Hatalı dosya, perm error | Kullanıcı senaryosu |
| Web Research | Sentez + kaynak gösterimi | 3 arama testi | Chat API | "hava durumu" → gerçek bilgi | Network yok | Kullanıcı senaryosu |
| Model Routing | WEB/FILE intent mapping | 7 model test | Engine + Provider | Coding → cloud, chat → local | Cloud unavailable | Kullanıcı senaryosu |

---

# 16. NOT VERIFIED LİSTESİ

| Öğe | Neden |
|-----|-------|
| Telegram bildirimleri | Telegram yapılandırılmamış — session dosyası yok |
| Proactive behavior | Sistemde mekanizma var ama test edilemedi |
| Otonom uzun görev | Intent routing sorunları nedeniyle başlatılamadı |
| Deep search | Web research test edildi ama deep search test edilmedi |
- Computer use (Windows mouse/keyboard) | Playwright sandbox içinde, gerçek Windows kontrolü test edilmedi
- Gmail integration | Credentials yok, test edilemedi
- Telegram user account | Session yok, test edilemedi

---

# 17. KNOWN LIMITATIONS

1. **Model gücü**: gpt-oss:20b-cloud iyi ama Claude/GPT kadar güçlü değil
2. **Context window**: Uzun sohbetlerde bağlam kaybı olabilir
3. **Tool calling**: Model her zaman doğru tool'u çağırmayabilir
4. **Docker sandbox**: Container sınırlamaları bazı özellikleri kısıtlıyor
5. **Offline mod**: Sadece local modeller çalışıyor — capability sınırlı
6. **Multi-language**: İngilizce/Türkçe karışık — tutarsız UX

---

# 18. FINAL RECOMMENDATION

## UMAY Şu Anda Ne Kadar Hazır?

**Prototip seviyesinde — %38 insan kullanma başarısı.**

### Gerçekçi Değerlendirme

| Kullanım Senaryosu | Durum |
|-------------------|-------|
| Basit sohbet | ✅ Çalışıyor |
| Kod üretimi (basit) | ✅ Çalışıyor |
| Dosya okuma/yazma | ❌ Çalışmıyor (Calculator hatası) |
| Klasör listeleme | ❌ Çalışmıyor |
| Hata analizi | ❌ Çalışmıyor |
| Web araştırması | ⚠️ Kısmen çalışıyor |
| Kod hata bulma | ❌ Çalışmıyor |
| Otonom görev | ❌ Çalışmıyor |
| Telegram | ❌ Çalışmıyor |

### Önerilen Sıralama

1. **Hemen**: Intent router fix (Calculator kısıtlama + FILE genişletme)
2. **Hafta 1**: Tool security + dosya işlemleri
3. **Hafta 2**: Model routing + web sentezi
4. **Hafta 3**: Frontend fixes + memory
5. **Hafta 4**: Telegram + regression test

### Nihai Hedef

**%38 → %80+ insan kullanma başarısı.**

Bu sadece intent router fix ile mümkün olabilir. Calculator over-trigger sorunu çözüldüğünde, dosya okuma/kod üretimi/hata analizi gibi temel özellikler otomatik olarak çalışmaya başlayacak.

---

**Audit Status**: ✅ COMPLETE
**Total Findings**: 35
**P0**: 0 | **P1**: 4 | **P2**: 12 | **P3**: 11 | **P4**: 8
**NOT VERIFIED**: 7
**Human-Use Success Rate**: 38%
**Reliability Score**: 1.5/5

**Raporlar**:
- `docs/audit/BACKEND_AUDIT_REPORT.md`
- `docs/audit/FRONTEND_AUDIT_REPORT.md`
- `docs/audit/HUMAN_USE_AUDIT_REPORT.md`
- `docs/audit/UMAY_MASTER_FORENSIC_AUDIT.md` (bu dosya)
