# UMAY Agent — Yapılacaklar Listesi 4

Tarih: 2026-08-14

## P0 — GERÇEK WINDOWS / OLLAMA DOĞRULAMASI — BLOKE
- [ ] Windows makinede Ollama servisini çalıştır.
- [ ] `http://localhost:11434/api/tags` erişimini doğrula.
- [ ] Tool-capable kurulu modelin gerçek adını doğrula.
- [ ] Gerçek native tool-call round-trip çalıştır.
- [ ] `assistant(tool_calls) -> tool -> ikinci Ollama turu` zincirini doğrula.
- [ ] Gerçek `C:\CREWINTEL` üzerinde `list_directory -> read_file -> search_files -> run_command` zincirini doğrula.
- [ ] Gerçek 123+ kayıtlı workspace sonucunun ikinci model turuna güvenli biçimde taşındığını doğrula.
- [ ] Gerçek sonuçları `logs/DEVELOPMENT_LOG.md` içine ekle.

## P1 — FAZ 4/5
- [ ] Gerçek CREWINTEL auditini çalıştır.
- [ ] Proje keşfi, dependency, test, build ve lint tespitini gerçek projede doğrula.
- [ ] Evidence tabanlı Finding schema'yı audit akışına bağla.
- [ ] Statik/kanıtsız audit iddialarını kaldır.

## P1 — FAZ 6/7
- [ ] Approval CLI/UI akışını uçtan uca test et.
- [ ] Auto-fix -> backup -> modify -> test -> retry -> rollback döngüsünü gerçek proje üzerinde test et.
- [ ] Command policy / timeout / output limitlerini gerçek komutlarla doğrula.

## P2
- [ ] Checkpoint/resume.
- [ ] Memory katmanlarını Conversation / Project / Task / Audit olarak ayır.
- [ ] Gerçek Chroma semantic retrieval.
- [ ] Context manager / compression.

## P3
- [ ] Agent/Capability registry.
- [ ] Browser gateway.
- [ ] MCP gateway + permission layer.
- [ ] UI görev/tool/test/diff/approval görünürlüğü.
