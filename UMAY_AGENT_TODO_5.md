# UMAY Agent — Güncel Nihai Yapılacaklar Listesi 5

Tarih: 2026-08-14

## 🔴 P0 — TEK BLOKE KRİTİK İŞ
### Gerçek Windows + Ollama Round-Trip
- [ ] Windows makinede Ollama servisini çalıştır.
- [ ] `http://localhost:11434/api/tags` erişimini doğrula.
- [ ] Tool-capable kurulu modelin gerçek adını doğrula.
- [ ] Gerçek native `tool_calls` üretimini doğrula.
- [ ] `function.arguments` string/object normalization'ını gerçek modelle doğrula.
- [ ] `assistant(tool_calls) → role=tool → ikinci Ollama turu` zincirini gerçek Ollama'da doğrula.
- [ ] Önceki `Value looks like object, but can't find closing '}' symbol` hatasının artık oluşmadığını doğrula.
- [ ] Gerçek `C:\CREWINTEL` üzerinde `list_directory → read_file → search_files → run_command` zincirini doğrula.
- [ ] 123+ kayıtlı gerçek workspace sonucunun ikinci model turuna güvenli biçimde taşındığını doğrula.
- [ ] Gerçek sonuçları `logs/DEVELOPMENT_LOG.md` içine kaydet.

## 🟠 P1 — GERÇEK SOFTWARE ENGINEER AUDIT
- [ ] Gerçek `C:\CREWINTEL` auditini çalıştır.
- [ ] Python/Node/Docker/dependency/test/build/lint keşfini gerçek projede doğrula.
- [ ] Evidence tabanlı Finding schema'yı gerçek audit akışına bağla.
- [ ] Statik/kanıtsız audit iddialarını kaldır.
- [ ] P0/P1/P2/P3 bulgularını gerçek dosya + satır + test kanıtıyla üret.

## 🟠 P1 — AUTO-FIX / GÜVENLİ DEĞİŞİKLİK
- [ ] Approval CLI/UI akışını uçtan uca test et.
- [ ] Auto-fix → backup → modify → test → retry → rollback döngüsünü gerçek projede test et.
- [ ] Git diff'i otomatik kanıt olarak audit'e bağla.
- [ ] Command policy / timeout / output limitlerini gerçek Windows komutlarıyla doğrula.

## 🟡 P2 — TASK + MEMORY + CONTEXT
- [ ] Checkpoint/resume.
- [ ] Conversation / Project / Task / Audit memory ayrımı.
- [ ] Gerçek Chroma semantic retrieval.
- [ ] Context manager.
- [ ] Context compression.
- [ ] Audit bulgularından otomatik görev üretimi.

## 🟢 P3 — AGENT EKOSİSTEMİ
- [ ] Agent/Capability registry.
- [ ] Browser gateway.
- [ ] MCP gateway + permission layer.
- [ ] UI'da task/tool/test/diff/approval görünürlüğü.

## ✅ FAZ 3'TE DOĞRULANANLAR
- [x] Native tool-call string arguments → object normalization simülasyonu.
- [x] Assistant tool message serialization simülasyonu.
- [x] `role=tool` → ikinci model turu simülasyonu.
- [x] Gerçek `run_agent()` iki turlu tool-loop simülasyonu.
- [x] Büyük tool-result sınırı testi.
- [x] `python -m pytest -q` → 13/13 PASS.
- [x] Python compileall → PASS.
- [x] Static audit → syntax findings 0, test status PASS.
- [x] Audit test runner `pytest -q` → `python -m pytest -q` olarak düzeltildi.

## ⚠️ KESİN OLARAK TAMAMLANMAMIŞ
- Gerçek Windows Ollama round-trip henüz PASS değildir; mevcut çalışma ortamında Ollama `localhost:11434` bağlantısı reddedildi.
- Bu nedenle P0 kapatılmadı.
