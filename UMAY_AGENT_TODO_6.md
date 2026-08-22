# UMAY Agent — Güncel Yapılacaklar Listesi 6

Tarih: 2026-08-14

## 🔴 P0 — GERÇEK WINDOWS + OLLAMA DOĞRULAMASI
- [ ] Windows makinede Ollama servisini çalıştır.
- [ ] `python scripts/verify_real_ollama.py` çalıştır.
- [ ] `/api/tags` erişimi PASS.
- [ ] Gerçek kurulu tool-capable model PASS.
- [ ] Gerçek native tool call PASS.
- [ ] `function.arguments` gerçek modelden string/object olarak alınması ve UMAY'da object'e normalize edilmesi PASS.
- [ ] `assistant(tool_calls) → role=tool → ikinci Ollama turu` PASS.
- [ ] Eski `Value looks like object, but can't find closing '}' symbol` hatası oluşmuyor.
- [ ] `C:\CREWINTEL` mevcutsa gerçek workspace round-trip PASS.
- [ ] 123+ kayıtlı gerçek workspace sonucu ikinci turda güvenli taşınıyor.
- [ ] P0 sonucu `logs/DEVELOPMENT_LOG.md` içine PASS/FAIL olarak işlendi.

### V6'da yapılan hazırlık
- [x] `scripts/verify_real_ollama.py` eklendi.
- [x] Script Ollama health/model keşfi yapıyor.
- [x] Script gerçek native/compatible tool-call normalization'ını doğruluyor.
- [x] Script ikinci Ollama turunu doğruluyor.
- [x] Script yalnızca `list_directory` kullanıyor; hedef projeyi değiştirmiyor.
- [x] Script sonucu otomatik `DEVELOPMENT_LOG.md`'ye yazıyor.
- [x] Verifier contract testi eklendi.
- [x] Test suite: **14/14 PASS**.

## 🟠 P1 — GERÇEK SOFTWARE ENGINEER AUDIT
- [ ] Gerçek `C:\CREWINTEL` auditini çalıştır.
- [ ] Python/Node/Docker/dependency/test/build/lint keşfini gerçek projede doğrula.
- [ ] Evidence tabanlı Finding schema'yı gerçek audit akışına bağla.
- [ ] Statik/kanıtsız audit iddialarını kaldır.
- [ ] P0/P1/P2/P3 bulgularını gerçek dosya + satır + test kanıtıyla üret.

## 🟠 P1 — AUTO-FIX / GÜVENLİ DEĞİŞİKLİK
- [ ] Approval CLI/UI uçtan uca test.
- [ ] Auto-fix → backup → modify → test → retry → rollback gerçek projede test.
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

## Test Durumu
- `python -m pytest -q` → **14/14 PASS**
- Python compileall → **PASS**
- Simulated Ollama round-trip → **PASS**
- Gerçek Windows Ollama → **Henüz bu ortamdan doğrulanamadı**
