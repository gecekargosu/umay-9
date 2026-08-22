# UMAY Agent — Yapılacaklar Listesi 2

Tarih: 2026-08-14

## P0
- [ ] Gerçek Ollama round-trip testini Windows makinesinde doğrula.
- [ ] Tool result `role=tool` mesajının mevcut Ollama sürümüyle uyumunu doğrula.

## P1
- [ ] Komut sonuçlarını PASS/FAIL/TIMEOUT/ERROR şemasına standardize et.
- [ ] Audit workflow'u gerçek test/lint/build kanıtlarına bağla; statik iddiaları kaldır.
- [ ] Read-only / approval / auto-fix modlarını uygula.
- [ ] Değişiklik öncesi backup + diff + rollback ekle.
- [ ] Git diff güvenlik özeti ekle.

## P2
- [ ] Test sonucu özetleyici ekle.
- [ ] Audit bulgularından görev listesi üret.
- [ ] Checkpoint/resume ekle.
- [ ] Memory/Context/RAG katmanlarını ayır ve gerçek semantic retrieval kullan.
- [ ] Agent/Capability/Tool registry mimarisini tamamla.

## P3
- [ ] Browser/MCP gateway'i güvenli tool katmanına bağla.
- [ ] UI'da agent/task/tool/test/diff/approval durumlarını göster.
