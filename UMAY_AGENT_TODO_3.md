# UMAY Agent — Yapılacaklar Listesi 3

Tarih: 2026-08-14

## P0 — Kullanıcı Windows makinesinde doğrulanacak
- [ ] Ollama servisinin gerçekten çalıştığını doğrula.
- [ ] Kurulu tool-capable model ile gerçek native tool-call round-trip testi yap.
- [ ] `role=assistant -> role=tool -> ikinci Ollama turu` zincirini gerçek Ollama'da doğrula.
- [ ] Gerçek `C:\CREWINTEL` audit'i çalıştır ve kanıtlı bulguları kaydet.

## P1 — Gerçek düzeltme döngüsü
- [ ] Approval moduna kullanıcı onayı sağlayan CLI/UI akışı ekle.
- [ ] Auto-fix modunda değişiklik → test → başarısızsa düzelt → tekrar test döngüsünü agent loop'a bağla.
- [ ] Git diff'i değişiklik sonrası otomatik audit kanıtına ekle.
- [ ] Backup/rollback'i gerçek auto-fix akışında uçtan uca test et.
- [ ] Audit raporundaki statik iddiaları tamamen kaldırıp yalnızca test/evidence kaynaklı sonuçları raporla.

## P2 — Hafıza ve görev sürekliliği
- [ ] Checkpoint/resume.
- [ ] Conversation / Project / Task / Audit memory ayrımı.
- [ ] Gerçek Chroma semantic retrieval.
- [ ] Context manager ve context compression.
- [ ] Audit bulgularından otomatik görev üretimi.

## P3 — Ekosistem
- [ ] Agent/Capability registry.
- [ ] Browser tool gateway.
- [ ] MCP gateway ve güvenli izin katmanı.
- [ ] UI'da görev, tool, test, diff ve approval durumları.
