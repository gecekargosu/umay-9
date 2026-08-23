# UMAY 9 — MASTER DEVELOPMENT LOG
**Proje:** UMAY 9 — Hybrid Offline/Online AI System
**Başlangıç:** 2026-08-22
**Son Güncelleme:** 2026-08-23 03:00

---

## PROJE AMACI

UMAY'ı gerçek anlamda kullanılabilir, mantıklı cevap verebilen, lokal/offline çalışabilen, internet mevcut olduğunda online kaynak/model kullanabilen, gerektiğinde iki tarafı birlikte kullanabilen MELEZ bir kişisel AI sistemi haline getirmek.

---

## GEÇMİŞ ÇALIŞMALAR

### 2026-08-22 — STEP-05 + Telegram
- STEP-05 background task execution tamamlandı
- Telegram User Account adapter bağlandı
- E2E Telegram mesaj akışı kanıtlandı
- 564 test PASS

### 2026-08-23 — FAZ 1 Identity
- identity.py → agent.py entegrasyonu
- CHAT_IDENTITY prompt'u yeniden yazıldı
- "AI değilim" sorunu çözüldü
- Saat uydurması önlendi
- Tool routing chat mode'da kapatıldı (geçici)
- 564 test PASS

### 2026-08-23 — FAZ 2 Intent Router
- intent_router.py → agent.py entegrasyonu
- Mesajlar CHAT/ACTION/TIME/FILE/DOCUMENT/VISION/WEB/CODE/TERMINAL/MEMORY/COMPLEX olarak sınıflandırılıyor
- CHAT/KNOWLEDGE intent → CHAT_IDENTITY prompt, 0 tool
- TIME intent → get_current_time/get_current_date tool'ları aktif
- FILE intent → filesystem tool'ları aktif
- VISION intent → vision tool'ları aktif
- Intent Router: 7/7 PASS (unit), 6/6 PASS (container)
- Time tools: gerçek sistem saati/tarihi dönüyor
- 564 test PASS, 0 regression

### 2026-08-23 — FAZ 2.5 Intent Router Fix + Calculator (KRİTİK)
- **KÖK NEDEN ÇÖZÜLDÜ:** panel_server.py execute_chat_task intent router'ı hiç kullanmıyordu!
- Intent Router panel_server.py'ye entegre edildi
- CALCULATOR intent + evaluate_expression tool eklendi
- TIME intent keywords genişletildi ("hangi tarihteyiz", "bugün ne")
- CHAT_IDENTITY prompt panel_server'da kullanılmaya başlandı
- "Bugün günlerden ne?" artık gerçek date tool'u çağırıyor
- "9/1*2-3+4" artık calculator ile çözülüyor (19.0)
- 8/8 intent classification PASS (container)
- 5/5 calculator PASS
- 564 test PASS, 0 regression

---

## FAZ PLANI

| Faz | Amaç | Durum |
|---|---|---|
| FAZ 0 | Current State Audit | ✅ TAMAM |
| FAZ 1 | Identity Entegrasyonu | ✅ TAMAM |
| FAZ 2 | Intent Router | ✅ TAMAM |
| FAZ 2.5 | Intent Router Fix + Calculator | ✅ TAMAM |
| FAZ 3 | Tool Routing + Filesystem | ⏳ BEKLİYOR |
| FAZ 4 | System Clock/Date | ✅ TAMAM (time tools + calculator eklendi) |
| FAZ 5 | Vision Pipeline | ⏳ BEKLİYOR |
| FAZ 6 | PDF/Document Pipeline | ⏳ BEKLİYOR |
| FAZ 7 | Offline/Online Detection | ⏳ BEKLİYOR |
| FAZ 8 | Online Provider Abstraction | ⏳ BEKLİYOR |
| FAZ 9 | Hybrid Execution | ⏳ BEKLİYOR |
| FAZ 10 | Context + Memory | ⏳ BEKLİYOR |
| FAZ 11 | Response Quality | ⏳ BEKLİYOR |
| FAZ 12 | Telegram E2E | ⏳ BEKLİYOR |
| FAZ 13 | Full Regression | ⏳ BEKLİYOR |
| FAZ 14 | Production Hardening | ⏳ BEKLİYOR |

---

## TEST MATRİSİ

| ID | Test | Beklenen | Sonuç |
|----|------|----------|-------|
| T001 | Merhaba | doğal cevap | ✅ |
| T002 | Sen kimsin | "Ben UMAY'ım" | ✅ |
| T003 | Saat | gerçek saat | ✅ (time tool kullanıyor) |
| T004 | Gün | gerçek gün | ✅ (date tool kullanıyor) |
| T004b | Hesaplama | calculator tool | ✅ (evaluate_expression) |
| T005 | Klasör listele | filesystem tool | ❌ (chat mode'da tool yok) |
| T006 | Dosya ara | search_files | ❌ (chat mode'da tool yok) |
| T007 | PDF oku | document pipeline | ⚠️ (tool gerekli) |
| T008 | Resim analiz | vision | ❌ (sonucu boş) |
| T009 | Screenshot analiz | vision | ❌ (sonucu boş) |
| T010 | Web sorusu | online | ⚠️ (offline fallback yok) |
| T011 | Offline web sorusu | dürüst cevap | ❌ (henüz test edilmedi) |
| T012 | Hybrid görev | local+online | ❌ (henüz implemente edilmedi) |
| T013 | Context | geçmişi kullan | ⚠️ (history eklendi, test yok) |
| T014 | BMW/Mercedes | mantıklı cevap | ❌ (alakasız cevap) |
| T015 | MiMo nedir | bilgi/online | ❌ (henüz test edilmedi) |
| T016 | Tool gerektirmeyen soru | no tool | ✅ |
| T017 | Tool gerektiren soru | tool call | ✅ (intent-based tool selection) |
| T018 | Vision+tool | ayrı pipeline | ❌ (henüz implemente edilmedi) |
| T019 | Ardışık mesaj | context korunur | ⚠️ (test yok) |
| T020 | Telegram E2E | doğru cevap | ✅ (kimlik sorunu vardı, çözüldü) |

---

## CHECKPOINT'LER

### CP-001: FAZ 0 Audit
- Tarih: 2026-08-23 02:00
- Durum: Read-only audit tamamlandı
- Dosya: docs/development/phases/PHASE-00-AUDIT.md

### CP-002: FAZ 1 Identity
- Tarih: 2026-08-23 01:40
- Durum: Identity entegrasyonu tamamlandı
- Dosya: docs/development/FAZ1_IDENTITY_FIX_REPORT.md
- Değişen: core/identity.py, core/agent.py

### CP-003: FAZ 2.5 Intent Router Fix
- Tarih: 2026-08-23 03:00
- Durum: panel_server intent router entegrasyonu + calculator
- Dosya: docs/development/phases/PHASE-02.5-INTENT-ROUTER-FIX.md
- Değişen: core/intent_router.py, core/agent_tools.py, ui/panel_server.py
- Test: 564 PASS, 10/10 container PASS
- Checkpoint: UMAY-MELEZ-PHASE-02.5-001

---

## GELENEKSEL DOSYALAR

| Dosya | Amaç |
|---|---|
| docs/development/phases/PHASE-XX.md | Faz raporları |
| docs/development/checkpoints/CP-XXX.md | Checkpoint detayları |
| docs/development/tests/E2E/ | E2E test sonuçları |
| docs/development/tests/regression/ | Regression test sonuçları |
| docs/development/tests/vision/ | Vision test sonuçları |
| docs/development/tests/tools/ | Tool test sonuçları |
| docs/development/tests/routing/ | Routing test sonuçları |

---

### 2026-08-23 — FAZ 4 Hybrid Intelligence + Direct Tool Execution (KRİTİK)
- **KÖK NEDEN ÇÖZÜLDÜ:** TIME/CALCULATOR tool'ları LLM'e gitmek yerine direkt çalıştırılmıyordu
- Model/Mode forwarding: frontend → backend → execute_chat_task kwargs ile iletiliyor
- Calculator tool: AST tabanlı evaluate_expression() — 27s → 0.03s
- TIME tool: Europe/Istanbul timezone ile gerçek saat
- DATE tool: Gerçek tarih (Pazar, 23 Ağustos 2026)
- Per-tool error handling: bir tool'un hata vermesi diğerlerini engellemiyor
- Vision priority: image varken direct tool execution bypass ediliyor (mixed attachment bug fix)
- Panel readability: font 13px → 14px
- E2E: 4/4 test PASS (Merhaba, Saat, Calculator, Date)
- Regression: 564 PASS, 0 FAIL
- Checkpoint: UMAY-V2-PHASE-04-001

### 2026-08-23 — FAZ 4+ Ek Düzeltmeler (Web Research, Mode, File Intent)
- **Web Research:** fast_research() — DuckDuckGo-only, 4.5s (was 2+ min)
- **Mode Routing:** Internet check + LOCAL/ONLINE/AUTO behavior
- **FILE Intent:** Turkish natural language — Masaüstü, Belgeler, İndirilenler
- **Folder Resolution:** ~/Desktop, ~/Documents, ~/Downloads mapping
- E2E: 5/5 PASS (Merhaba, Saat, Calculator, Date, Masaustunu listele)
- Masaustunu listele: 2.12s (was 88s)
- Regression: 564 PASS, 0 FAIL
- Checkpoint: UMAY-V2-PHASE-04-PLUS-001

### 2026-08-23 — FAZ 4 FINAL (Mode Routing + Host Filesystem + Security)
- **AUTO/LOCAL/ONLINE real backend routing** — internet check, mode-based model/tool selection
- **Docker → Windows host filesystem** — volume mounts for Desktop/Documents/Downloads
- **Security:** sandbox + path traversal blocking + allowed roots
- **Host FS E2E:** 69 real files listed from Windows Desktop
- **Tool filtering:** listele→list_directory, oku→read_file, ara→search_files
- **scan_directory response:** improved with file type summary
- E2E: 4/4 PASS (LOCAL+Saat, LOCAL+Calc, AUTO+Desktop, ONLINE+Merhaba)
- Regression: 564 PASS, 0 FAIL
- Checkpoint: UMAY-V2-PHASE-04-FINAL-001
- **FAZ 4 NOW COMPLETE**

### 2026-08-23 — FAZ 1 PANEL FORENSIC AUDIT
- 46 UI component incelendi, %50 WORKING
- 10 problem tespit edildi (2 P0, 2 P1, 3 P2, 3 P3)
- En iyi: Files (100%), Chat (89%), Dashboard (75%)
- En kötü: Tasks (0%), Memory (0%), Logs (0%), Settings (0%)
- Backend sağlık: Ollama ✅, Telegram User ✅, Agents ✅, Tools ✅
- Kod değişikliği yok — sadece audit
- Checkpoint: PHASE-01-CHECKPOINT

### 2026-08-23 — FAZ 2 CORE/CHAT/ROUTING HARDENING
- E2E test: 10/10 PASS (Merhaba, Sen kimsin, Saat, Tarih, Calculator x2, File x3, Chat)
- Mode routing: 5/5 PASS (LOCAL, ONLINE, AUTO)
- Intent router: 14/15 PASS (1 minor: Komut calistir → CODE vs TERMINAL)
- Tool calling: 6/6 PASS (Time, Date, Calculator, Directory, System)
- Conversation history: Working (session persistence)
- Error handling: Empty message + Invalid path + Tool failure all handled
- Regression: 564 PASS, 0 FAIL (baseline maintained)
- Docker E2E: 5/5 PASS
- Checkpoint: PHASE-02-CHECKPOINT
- **FAZ 2 NOW COMPLETE**

### 2026-08-23 — FAZ 3 TOOL & EXECUTION HARDENING
- Filesystem: 3/3 PASS (list_directory, read_file, search_files)
- Terminal: 3/3 PASS (run_command, get_system_info, list_processes)
- Time/Calculator: 4/4 PASS (get_current_time, get_current_date, evaluate_expression x2)
- Web: 1/1 PASS (web_search)
- Tool isolation: PASS (division by zero → error dict, subsequent tools work)
- Tool classification: 11/11 WORKING (100%)
- Regression: 564 PASS, 0 FAIL (baseline maintained)
- Checkpoint: PHASE-03-CHECKPOINT
- **FAZ 3 NOW COMPLETE**

### 2026-08-23 — FAZ 5 FILE + KNOWLEDGE + MEMORY INTELLIGENCE
- File upload: Working (TXT upload + list)
- Document extraction: Working (6575 chars from identity.py)
- Attachment engine: Working (context built from attachments)
- Conversation history: Working (SQLite-backed, 4 messages)
- ChromaDB: Working (10 entries, 3/3 queries relevant)
- Memory add: Working (3 memories added)
- Memory query: Working (Cengiz kimdir? → correct answer)
- E2E file processing: Working (upload → attach → chat)
- Regression: 564 PASS, 0 FAIL (baseline maintained)
- Checkpoint: PHASE-05-CHECKPOINT
- **FAZ 5 NOW COMPLETE**

### 2026-08-23 — FAZ 6 REAL WORLD AGENT SYSTEM
- Terminal: 3/3 PASS (run_command, get_system_info, list_processes)
- Web Research: 2/2 PASS (web_search, fast_research 2.6s)
- Docker: 2/2 PASS (container management)
- Approval: 2/2 PASS (ApprovalManager, PermissionManager)
- Regression: 563 PASS, 1 flaky (network), 1 skipped
- Flaky tests: 2 network-dependent (pass individually)
- Checkpoint: PHASE-06-CHECKPOINT
- **FAZ 6 NOW COMPLETE**

### 2026-08-23 — CALCULATOR ROUTING FIX
- Problem: "127'nin karesini hesapla" calculator'a yönlendirilmiyordu
- Kök neden: Intent Router eksik keywords + panel_server Türkçe→Math dönüşümü yok
- Fix 1: Intent Router — calculator keywords genişletildi (karesi, küpü, topla, çıkar, çarp, böl)
- Fix 2: Intent Router — negation filter ("hesaplamanın değil" → chat)
- Fix 3: panel_server.py — Türkçe doğal dil → matematik expression dönüştürücü eklendi
- Intent classification: 14/14 PASS
- Turkish→Math conversion: 6/6 PASS
- E2E Chat API: 4/4 PASS
- Regression: 564 PASS, 0 FAIL
- Docker build + E2E: PASS
- Dosyalar: core/intent_router.py, ui/panel_server.py
- Checkpoint: UMAY-V2-CALCULATOR-FIX-001
- **CALCULATOR FIX COMPLETE**

---

## NOTLAR

- Bu log her faz sonunda güncellenecek
- Her checkpoint bu log'a referans verilecek
- Test matrisi sürekli güncellenecek
- Geri dönüş noktaları açıkça işaretlenecek
