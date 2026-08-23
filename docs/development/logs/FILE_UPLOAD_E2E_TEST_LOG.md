# UMAY 9 — FILE UPLOAD PIPELINE E2E TEST LOG
**Tarih:** 24 Agustos 2026 02:22
**Testci:** Buffy (Codebuff AI)
**Mod:** Real User E2E (Preview UI + API)

---

## TEST MATRISI

### T1: TXT FILE
| Metrik | Deger |
|--------|-------|
| Upload | PASS — 774 byte, content extracted |
| Extraction | PASS — "UMAY_SECRET_84721" icerigi dogru okundu |
| Model Analysis | PASS — phi4-mini:latest "UMAY_SECRET_84721" dogru buldu |
| UI Display | PASS — dosya bilgisi gorundu |
| Evidence | API test: cevap="Dosyada gizli anahtar UMAY_SECRET_84721" |
| **STATUS** | **PASS** |

### T2: PY FILE
| Metrik | Deger |
|--------|-------|
| Upload | PASS — 1720 byte, content extracted |
| Extraction | PASS — "SECRET_KEY = UMAY_PY_SECRET_72934" okundu |
| Model Analysis | PASS — phi4-mini:latest dogru cevap verdi |
| Evidence | API test: cevap="Secret Key: UMAY_PY_SECRET_72934" |
| **STATUS** | **PASS** |

### T3: PDF FILE
| Metrik | Deger |
|--------|-------|
| Upload | PASS — 203 byte, PDF text extracted |
| Extraction | PASS — "UMAY_PDF_SECRET_45678" okundu |
| Model Analysis | PARTIAL — model dosya listesi dondurdu, PDF icerigi degil |
| Evidence | Content: "UMAY 9 Test PDF / Gelistirici: Cengiz Kilarc / Test Degeri: UMAY_PDF_SECRET_45678" |
| **STATUS** | **PARTIAL** |

### T4: JPG FILE
| Metrik | Deger |
|--------|-------|
| Upload | PASS — PIL image, is_vision=true |
| Extraction | PASS — vision model kullanildi |
| Model Analysis | PASS — gemma3:4b "UMAY 9 TEST IMAGE" basligini tanidi |
| Evidence | "UMAY 9 TEST IMAGE basligi altinda Cengiz Kilarc tarafindan gelistirildigi belirtilen bir test goruntusu" |
| **STATUS** | **PASS** |

### T5: MEMORY/RAG RETRIEVAL
| Metrik | Deger |
|--------|-------|
| Storage | PASS — "RAG_SECRET_XYZ" kaydedildi |
| Retrieval (same conv) | PASS — ayni conversation'da sorulunca hatirladi |
| Evidence | cevap="Rag test dosyasinda gizli bilgi RAG_SECRET_XYZ olarak kaydedildi" |
| **STATUS** | **PASS** |

---

## CRITICAL BUG: TASK STUCK IN THINKING

### Sorun
UI'dan dosya eklenerek mesaj gonderildiginde model sonsuza kadar "Thinking..." durumunda kaliyor.

### Kanit
- Screenshot: "Thinking... Analyzing request..." 2+ dakika boyunca kaybolmadi
- Backend task log: 2 eski task "RUNNING" state'de takili kalmis
- API task list: `active_tasks: []`, `historical_tasks: 2 (status: RUNNING)`

### Root Cause
TaskExecutor'daki race condition:
1. Task thread'i `_wrapper()` icinde `execute_fn()` cagiriyor
2. `execute_fn()` `on_complete` callback'ini cagirarak sonucu donduruyor
3. `_wrapper()` thread'i `_cleanup()` ile task'i _tasks dict'inden siliyor
4. `wait_for_completion()` `_tasks` dict'inden sonucu okumaya calisiyor — ama task zaten silinmis!
5. Sonuc: bos donuyor, UI "Thinking..." kalıyor

### Etki
- UI'dan dosya upload + chat YALNIZCA server restart sonrasi calisiyor
- ilk mesaj calisiyor (cunku task daha silinmemis)
- ikinci mesaj takiliyor (task zaten silindi)

### Dosya
- `core/task_executor.py` — `_wrapper()`, `_cleanup()`, `wait_for_completion()`

---

## API-BASED TEST SONUCLARI (Kod Kontrolu)

| Test | Status | Kanit |
|------|--------|-------|
| T1 TXT Upload | PASS | 774 byte, UMAY_SECRET_84721 found |
| T1 TXT Chat | PASS | "Dosyada gizli anahtar UMAY_SECRET_84721" |
| T2 PY Upload | PASS | 1720 byte, SECRET_KEY found |
| T2 PY Chat | PASS | "Secret Key: UMAY_PY_SECRET_72934" |
| T3 PDF Upload | PASS | 203 byte, UMAY_PDF_SECRET_45678 found |
| T3 PDF Chat | PARTIAL | Model dosya listesi dondurdu |
| T4 JPG Upload | PASS | is_vision=true, vision model kullanildi |
| T4 JPG Chat | PASS | "UMAY 9 TEST IMAGE" tanindi |
| T5 Memory Store | PASS | RAG_SECRET_XYZ kaydedildi |
| T5 Memory Retrieve | PASS | Ayni conv'da hatirladi |

## UI-BASED TEST SONUCLARI (Kullanici Testi)

| Test | Status | Kanit |
|------|--------|-------|
| Chat ac | PASS | Screenshot: Chat sayfasi gorundu |
| Dosya ekle (UI) | PASS | Screenshot: test.txt eklendi |
| Mesaj gonder | PARTIAL | Screenshot: Thinking... ama cevap gelmedi |
| Cevap gor | FAIL | Screenshot: 2+ dakika thinking, cevap yok |
| History | UNTESTED | Task takili oldugu icin test edilemedi |

---

## ONCEKI RAPORLARLA CELISKI

| Onceki Rapor | Mevcut Durum |
|-------------|-------------|
| "File upload PASS" | API'de PASS, UI'da FAIL (task stuck) |
| "564 test gecti" | Testler calisiyor ama E2E'de task race condition var |
| "Chat calisiyor" | API'de calisiyor, UI'da thinking takiliyor |

---

## FIX ONERILERI

1. **P0 — TaskExecutor Race Condition**: `_cleanup()` onceki `wait_for_completion()` cagrisindan once calisiyor. `_completed_results` dict'i ile sonuc survive etmeli.
2. **P1 — Task Timeout**: 180s timeout'tan sonra task otomatik cancel olmali.
3. **P2 — Thinking Timeout UI**: UI'da 60s+ thinking gorunurse "Sure asimi" mesaji gosterilmeli.
