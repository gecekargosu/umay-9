# UMAY FRONTEND FORENSIC AUDIT — FINAL REPORT

**Audit Date**: 2026-08-24
**Scope**: ui/templates/panel.html (1,297 lines), ui/panel_server.py (2,094 lines)
**Method**: Code analysis + live preview testing + API endpoint verification

---

## ÖZET

| Metrik | Değer |
|--------|-------|
| Frontend dosyası | 1 (panel.html — monolith SPA) |
| Satır sayısı | 1,297 (CSS + HTML + JS) |
| Sayfa sayısı | 14 (dashboard, chat, agents, tasks, files, memory, browser, telegram, comms, tools, scheduler, approvals, logs, diagnostics, settings) |
| API endpoint | 14 GET + 5 POST |
| SocketIO event | 4 client→server, 8 server→client |
| Toplam bulgu | 17 |
| P0 | 0 |
| P1 | 2 |
| P2 | 5 |
| P3 | 6 |
| P4 | 4 |

---

## GÖREV 1-2: ÖNCEKİ EKSİK BACKEND İŞLERİ + ENVANTER

### Önceki Bulguların Re-Verify

| ID | Önceki Durum | Re-Verify Sonucu | Kanıt |
|----|-------------|-------------------|-------|
| F4-01 | search_files glob FAIL | ✅ CONFIRMED FAIL | `"*.py"` → `"nothing to repeat at position 0"` |
| F4-02 | get_system_info eksik | ✅ CONFIRMED FAIL | keys=['os','platform','python_version','cwd'] — cpu/ram yok |
| T6-01 | write_file overwrite PARTIAL | ✅ CONFIRMED | created=False, backup=".bak" oluşturuldu, içerik değişti |

---

## GÖREV 3: FRONTEND→BACKEND BAĞLANTILARI

### API Endpoint Mapping

| Frontend Çağrısı | Backend Route | HTTP | Durum | Not |
|------------------|---------------|------|-------|-----|
| `/api/system` | `system_status()` | GET | ✅ | CPU/RAM/docker/ollama dönüyor |
| `/api/agents` | `agents_status()` | GET | ✅ | 10 agent listeleniyor |
| `/api/tools` | `tools_list()` | GET | ✅ | 64 tool listeleniyor |
| `/api/models` | `models_api()` | GET | ✅ | 11 model + kategoriler |
| `/api/config` | `config_api()` | GET | ✅ | Config durumları |
| `/api/memory` | `memory_status()` | GET | ✅ | ChromaDB + memories |
| `/api/logs` | `logs_api()` | GET | ✅ | Log satırları |
| `/api/scheduler_status` | `scheduler_status_api()` | GET | ✅ | Scheduled tasks |
| `/api/telegram_status` | `telegram_status_api()` | GET | ✅ | Bot/user durumu |
| `/api/conversations` | `conversations_list_api()` | GET | ✅ | Session listesi |
| `/api/chat/history` | `chat_history_api()` | GET | ✅ | Mesaj geçmişi |
| `/api/diagnostics` | `diagnostics()` | GET | ✅ | Diagnostic checks |
| `/api/build` | `build_info()` | GET | ✅ | Build hash/version |
| `/api/uploads` | `list_uploads()` | GET | ✅ | Uploaded files |
| `/api/chat` | `chat_api()` | POST | ✅ | Chat message |
| `/api/chat/attach` | `chat_attach()` | POST | ✅ | File attachment |
| `/api/chat/clear` | `chat_clear()` | POST | ✅ | Clear conversation |
| `/api/upload` | `upload_file()` | POST | ✅ | File upload |
| `/api/git` | `siteye_git()` | POST | ⚠️ | Browser navigation (isim yanıltıcı) |

### SocketIO Eşleşme

| Event | Server→Client | Client Dinliyor | Durum |
|-------|--------------|-----------------|-------|
| `chat_response` | ✅ emit | ✅ on | ✅ |
| `task_status` | ✅ emit | ✅ on | ✅ |
| `screenshot` | ✅ emit | ✅ on | ✅ |
| `analiz` | ✅ emit | ✅ on | ✅ |
| `durum` | ✅ emit | ✅ on | ✅ |
| `log` | ✅ emit | ✅ on | ✅ |
| `task_completed` | ✅ emit | ❌ DİNLİNMİYOR | 🔴 |
| `telegram_status` | ✅ emit | ❌ DİNLİNMİYOR | 🔴 |

---

## GÖREV 4: UI FONKSİYONLARININ GERÇEK AMAÇ TESTİ

### Model Seçici
| Test | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| auto seçimi | Mode=auto → router karar verir | `selectedModel='auto'` → backend'e gidiyor | ✅ |
| model seçimi | Seçilen model gerçekten kullanılır | `selectedModel='gpt-oss:20b-cloud'` → backend'e gidiyor | ✅ |
| model listesi | Tüm kurulu modeller görünüyor | `/api/models` → 11 model dropdown'da | ✅ |
| local_fast/local_smart | fallback modeller seçilmeli | Backend'de bunun karşılığı YOK | ❌ |

### Mode Seçici
| Test | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| AUTO | Tüm modlar aktif | `selectedMode='auto'` → backend'e gidiyor | ✅ |
| LOCAL | Sadece local modeller | Backend mode policy var | ✅ |
| ONLINE | Web araştırması aktif | Backend mode policy var | ✅ |

### Chat
| Test | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| Mesaj gönderme | SocketIO ile non-blocking | `socket.emit('chat_message')` → backend | ✅ |
| Cevap gösterme | SocketIO response | `socket.on('chat_response')` | ✅ |
| Task controls | Pause/Resume/Cancel | 3 buton, SocketIO emit | ✅ |
| Intent indicator | Niyet gösterimi | `showIntent()` fonksiyonu | ✅ |
| Model bilgisi | Hangi model kullanıldı | Response'da `data.model` gösteriliyor | ✅ |
| Latency | Cevap süresi | Response'da `data.latency` gösteriliyor | ✅ |
| Tool kullanımı | Tool hangisiydi | Response'da `data.tool` gösteriliyor | ✅ |
| Dosya ekleme | Drag & drop + clipboard | `attachFile()`, drag/drop listener | ✅ |
| Markdown rendering | Kod blokları, bold, link | `renderMd()` fonksiyonu | ✅ |

### Dosya Upload
| Test | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| Upload | Dosya kaydedilir | `/api/upload` POST | ✅ |
| Listeleme | Yüklenen dosyalar görünür | `/api/uploads` GET | ✅ |
| Delete | Dosya silme | UI'da silme butonu YOK | ❌ |

### Browser
| Test | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| Navigate | URL'ye gidilir | `/api/git` POST (yanıltıcı isim) | ⚠️ |
| Screenshot | Ekran görüntüsü | SocketIO screenshot event | ✅ |
| Analysis | Sayfa analizi | SocketIO analiz event | ✅ |

---

## GÖREV 5: FRONTEND STATE / DATA FLOW

### Global State Variables
| Variable | Amaç | Durum |
|----------|------|-------|
| `currentPage` | Aktif sayfa | ✅ showPage() ile yönetiliyor |
| `chatHistory` | Mesaj geçmişi | ⚠️ TANIMLI AMA KULLANILMIYOR |
| `chatBusy` | Chat meşgul durumu | ✅ Send engeli için |
| `selectedModel` | Seçili model | ✅ |
| `selectedMode` | Seçili mode | ✅ |
| `conversationId` | Aktif conversation | ✅ localStorage'da persist |
| `availableModels` | Model listesi | ✅ |
| `currentTaskId` | Aktif task ID | ✅ |
| `currentTaskState` | Task durumu | ✅ RUNNING/PAUSED/COMPLETED |
| `pendingAttachments` | Bekleyen ekler | ✅ |
| `socket` | SocketIO connection | ✅ |

### Error Handling
| Durum | Frontend Davranışı | Durum |
|-------|-------------------|-------|
| Backend kapalı | `api()` → null, hiçbir gösterim yok | ❌ |
| Network hatası | `api()` → null, sessiz | ❌ |
| Chat hatası | `data.error` → "Hata: ..." gösteriliyor | ✅ |
| SocketIO disconnect | `s-umay` dot'u kırmızı oluyor | ✅ |
| Boş mesaj | `sendChat()` → return, hiçbir şey yapmıyor | ✅ |
| 400/500 | `api()` → null, sessiz | ❌ |

### Persistence
| Veri | Mekanizma | Durum |
|------|----------|-------|
| Conversation ID | localStorage | ✅ |
| Chat history | Backend JSONL | ✅ |
| Model/Mode seçimi | JavaScript global (kayıp) | ⚠️ Sayfa yenilendiğinde reset |

---

## GÖREV 6: I18N / TEXT / MODEL BİLGİLERİ

### Dil Karışıklığı
| Metin | Durum | Not |
|-------|-------|-----|
| "Merhaba! Ben UMAY..." | Türkçe | ✅ |
| "AI Operating System" | İngilizce | ⚠️ Karışık |
| "Command Center" | İngilizce | ⚠️ |
| "System Telemetry" | İngilizce | ⚠️ |
| "Active Agents" | İngilizce | ⚠️ |
| "Processing Pipeline" | İngilizce | ⚠️ |
| "Live Activity" | İngilizce | ⚠️ |
| "Quick Actions" | İngilizce | ⚠️ |
| "Sohbet ara..." | Türkçe | ✅ |
| "Mesajınızı yazın..." | Türkçe | ✅ |
| "Düşünüyor..." | Türkçe | ✅ |

**Sonuç**: UI ağırlıklı olarak İngilizce, chat kısmı Türkçe — tutarsız.

### Model İsimleri
- Frontend'de `gpt-oss:20b-cloud (coding, reasoning, analysis)` gösteriliyor
- Backend'de gerçek model adı `gpt-oss:20b-cloud` — doğru ✅
- `local_fast` ve `local_smart` seçeneği var ama backend'de karşılığı yok ❌

### Agent İsimleri
- "Browser Agent", "Coding Agent" vb. — doğru ✅
- Tüm agent'lar "idle" durumda — gerçek durum mu bilinmiyor ⚠️

---

## GÖREV 7: AUTH / PERMISSION / ERROR UX

### Hata Durumları

| Senaryo | Beklenen | Gerçek | Durum |
|---------|----------|--------|-------|
| Backend kapalı | Hata mesajı | Dashboard data null → boş gösterim | ❌ |
| Boş mesaj gönderme | Engelleme | `sendChat()` return — sessiz | ✅ |
| Geçersiz model | Hata mesajı | Backend kabul ediyor, hata yok | ⚠️ |
| SocketIO disconnect | Durum gösterimi | Yeşil dot → kırmızı | ✅ |
| Dosya bulunamadı | Hata mesajı | Read file hatası chat'te gösteriliyor | ✅ |
| Network timeout | Hata mesajı | `api()` → null, sessiz | ❌ |
| Yetkisiz işlem | Onay isteği | `UMAY_MODE=approval` var ama UI'dan yönetilmiyor | ⚠️ |

### Approval UX
- Backend'de `approval_manager` var
- Frontend'de Approvals sayfası var ama sadece "No pending approvals" gösteriyor
- Gerçek approval akışı test edilemedi (approval gerektiren işlem yapılmadı)

---

## GÖREV 8: GERÇEK SENARYO TESTLERİ

### Test 1: Dashboard Yükleme
- ✅ CPU/RAM stats doğru (3.9%, 24.5%)
- ✅ Ollama connected, 11 model
- ✅ Docker healthy, 1 container
- ✅ 10 agent listeleniyor
- ✅ Processing pipeline görünüyor
- ✅ Live activity log var

### Test 2: Sayfa Navigasyonu
- ✅ 14 sayfanın hepsine geçiş başarılı
- ✅ Aktif sayfa vurgulanıyor
- ✅ Veri yükleme tetikleniyor

### Test 3: Model Seçici
- ✅ Dropdown 11 model gösteriyor
- ✅ Kategoriler doğru (coding, reasoning, analysis)
- ⚠️ `local_fast`/`local_smart` seçimi var ama backend'de karşılığı yok

### Test 4: Chat Gönderme
- ✅ Mesaj SocketIO ile gönderiliyor
- ✅ Task status bar görünüyor
- ✅ Task controls (pause/resume/cancel) görünüyor
- ✅ Intent indicator çalışıyor
- ✅ Cevap geldiğinde correctly gösteriliyor

### Test 5: Dosya Ekleme
- ✅ 📎 butonu çalışıyor
- ✅ Drag & drop çalışıyor
- ✅ Clipboard paste çalışıyor
- ✅ Ekler chat mesajına ekleniyor

### Test 6: Hatalı İstek
- ✅ Boş mesaj → engellendi
- ✅ Boş chat body → 400 + error message
- ❌ Backend kapalı → sessiz fail

---

## GÖREV 9: FRONTEND DEAD / BROKEN FEATURES

### Çalışmayan Özellikler

| ID | Özellik | Durum | Detay |
|----|---------|-------|-------|
| FE-01 | `chatHistory` global değişkeni | DEAD | Tanimli ama hiç kullanılmıyor |
| FE-02 | `local_fast`/`local_smart` model seçimi | BROKEN | Backend'de karşılığı yok — hangi modele bağlanacağı belli değil |
| FE-03 | `/api/git` ismi | CONFUSING | Browser navigasyonu `/api/git` üzerinden — yanıltıcı |
| FE-04 | `task_completed` event | UNLISTENED | Backend emit ediyor ama frontend dinlemiyor |
| FE-05 | `telegram_status` event | UNLISTENED | Backend emit ediyor ama frontend dinlemiyor |
| FE-06 | Dosya silme | MISSING | Files sayfasında silme butonu yok |
| FE-07 | `api()` error handling | BROKEN | Tüm hataları yutuyor, kullanıcıya hiçbir şey göstermiyor |
| FE-08 | Model/Mode persistence | PARTIAL | Conversation ID localStorage'da, ama model/mode kayboluyor |
| FE-09 | Settings sayfası | MINIMAL | Sadece config gösteriyor, düzenleme yok |
| FE-10 | Approvals sayfası | PLACEHOLDER | "No pending approvals" — gerçek approval akışı yok |
| FE-11 | Scheduler sayfası | READ-ONLY | Görevleri göstertiyor ama ekleme/düzenleme yok |
| FE-12 | Workers sayfası | MISSING | Backend'de `/api/workers` var ama frontend'de sayfası yok |
| FE-13 | Browser sayfası | PARTIAL | Navigate çalışyor ama screenshot polling yok |
| FE-14 | Memory sayfası | READ-ONLY | Bellek gösteriyor ama silme/arama yok |
| FE-15 | Diagnostics | WORKS | Gerçek çalışıyor ✅ |
| FE-16 | Benchmark | WORKS | Gerçek çalışıyor ✅ |

---

## BULGU DETAYLARI

### P1 — Kritik

#### FE-02: local_fast/local_smart Mapping Yok
- **Dosya**: `ui/templates/panel.html` → `onModelChange()`
- **Sorun**: `local_fast` ve `local_smart` seçildiğinde backend'e `"local_fast"` gönderiliyor. Backend'de `resolve_model()` bu değeri model adı olarak arıyor — bulamıyor
- **Kanıt**: `resolve_model("local_fast")` → fallback olarak ilk modeli dönüyor
- **Kök neden**: Frontend'de preset model seçimi var ama backend'de preset mapping yok
- **Etki**: Kullanıcı "Local Fast" seçtiğinde aslında hangi modeli kullandığını bilmiyor

#### FE-07: api() Sessiz Hata Yutma
- **Dosya**: `ui/templates/panel.html` → `api()` function
- **Sorun**: `catch(e) { return null; }` — tüm API hatalarını sessizce yutuyor
- **Kanıt**: Backend kapalıyken dashboard boş görünüyor, hata mesajı yok
- **Kök neden**: Centralized error handling yok
- **Etki**: Kullanıcı backend'in neden çalışmadığını anlayamıyor

### P2 — Orta

#### FE-04: task_completed Event Dinlenmiyor
- **Dosya**: `ui/templates/panel.html`
- **Sorun**: Backend `task_completed` emit ediyor ama frontend'de handler yok
- **Etki**: Task tamamlandığında UI'da özel bir gösterim yapılmıyor (task_status kullanılıyor ama task_completed farklı bilgi taşıyor)

#### FE-05: telegram_status Event Dinlenmiyor
- **Dosya**: `ui/templates/panel.html`
- **Sorun**: Backend `telegram_status` emit ediyor ama frontend'de handler yok
- **Etki**: Telegram durum değişiklikleri anlık olarak gösterilmiyor

#### FE-03: /api/git Yanıltıcı İsim
- **Dosya**: `ui/panel_server.py` → `@app.route("/api/git")`
- **Sorun**: Browser navigasyonu `/api/git` üzerinden — isim yanıltıcı
- **Etki**: Bakım/developers için kafa karışıklığı

#### FE-06: Dosya Silme Yok
- **Dosya**: `ui/templates/panel.html` → `loadFiles()`
- **Sorun**: Dosya listesi var ama silme butonu yok
- **Etki**: Kullanıcı yüklediği dosyaları silemez

#### FE-08: Model/Mode Kaybı
- **Dosya**: `ui/templates/panel.html`
- **Sorun**: `selectedModel` ve `selectedMode` JavaScript global değişkenler — sayfa yenilendiğinde reset
- **Etki**: Kullanıcı her seferinde model/mode seçmek zorunda

### P3 — Düşük

#### FE-01: chatHistory Dead Code
- **Dosya**: `ui/templates/panel.html`
- **Sorun**: `let chatHistory = []` tanimli ama hiç kullanılmıyor

#### FE-09: Settings Read-Only
- **Dosya**: `ui/templates/panel.html` → `loadSettings()`
- **Sorun**: Sadece config gösteriyor, düzenleme formu yok

#### FE-10: Approvals Placeholder
- **Dosya**: `ui/templates/panel.html` → `loadApprovals()`
- **Sorun**: Hardcoded "No pending approvals" — gerçek approval akışı bağlanmamış

#### FE-11: Scheduler Read-Only
- **Dosya**: `ui/templates/panel.html` → `loadScheduler()`
- **Sorun**: Sadece listeleme, CRUD yok

#### FE-12: Workers Sayfası Eksik
- **Dosya**: `ui/templates/panel.html`
- **Sorun**: Backend'de `/api/workers` endpoint'i var ama frontend'de sayfa yok

#### FE-13: Browser Polling Yok
- **Dosya**: `ui/templates/panel.html` → `browserGo()`
- **Sorun**: Navigate çalışıyor ama screenshot otomatik güncellenmiyor

### P4 — Kalite

#### FE-16: Dil Tutarlılığı
- UI büyük ölçüde İngilizce, chat Türkçe — tutarsız

#### FE-17: Model/Mode Tutarlılığı
- Topbar'da "LOCAL" badge var ama gerçek durum未必 LOCAL

#### FE-18: Agent Durumları
- Tüm agent'lar "idle" — gerçek durum mu bilinmiyor

#### FE-19: XSS Riski
- `renderMd()` URL re-injection sonrası `escHtml` kullanılmıyor — düşük risk ama mevcut

---

## ÇALIŞAN SAĞLAM ÖZELLİKLER

| Özellik | Durum | Kanıt |
|---------|-------|-------|
| Dashboard telemetry | ✅ | CPU/RAM/docker/ollama doğru |
| 14 sayfa navigasyonu | ✅ | Tüm sayfalar açılıyor |
| Model selector (11 model) | ✅ | Doğru listeleniyor, kategoriler doğru |
| Mode selector (3 mod) | ✅ | AUTO/LOCAL/ONLINE |
| Chat (SocketIO) | ✅ | Non-blocking, task controls |
| Chat (HTTP fallback) | ✅ | SocketIO yoksa HTTP kullanıyor |
| Dosya ekleme | ✅ | Button + drag/drop + clipboard |
| Markdown rendering | ✅ | Code blocks, bold, links |
| Intent indicator | ✅ | Niyet + tool + source gösteriyor |
| Task controls | ✅ | Pause/Resume/Cancel |
| Conversation history | ✅ | Session listesi + arama |
| Live activity log | ✅ | Dashboard'da gerçek zamanlı |
| Diagnostics | ✅ | Çalışıyor |
| Model benchmark | ✅ | Çalışıyor |
| SocketIO connection | ✅ | Connect/disconnect durumu |
| Conversation persistence | ✅ | localStorage + backend |

---

## SONUÇ

Frontend **temel olarak çalışıyor**. Dashboard, chat, model/mode seçimi, dosya ekleme, task controls — hepsi fonksiyonel.

**Ana sorunlar**:
1. **`local_fast`/`local_smart` mapping yok** — backend'de karşılığı belirsiz (P1)
2. **`api()` sessiz hata yutuyor** — network hatası görünmüyor (P1)
3. **2 SocketIO event dinlenmiyor** — task_completed, telegram_status (P2)
4. **Dosya silme yok** (P2)
5. **Model/mode persistence yok** (P2)
6. **Dil tutarsızlığı** — İngilizce/Türkçe karışık (P4)

---

**Audit Status**: ✅ COMPLETE
**Report**: docs/audit/FRONTEND_AUDIT_REPORT.md
