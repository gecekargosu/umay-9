# UMAY Agent — Yeni Yapılacaklar Listesi

Tarih: 2026-08-13
Amaç: UMAY'ın gerçek bir yerel yazılım mühendisi ajanı gibi çalışması.

## P0 — Tool-calling sinir sistemini tamamla
- [x] Ollama tool tanımlarını modele gönder.
- [x] Modelin gerçek `tool_calls` cevabını yakala.
- [x] Tool'u gerçekten çalıştır.
- [x] Tool sonucunu `role=tool` mesajı olarak aynı konuşmaya geri besle.
- [x] Modelin ikinci/üçüncü/... turda yeni tool çağrıları yapmasına izin ver.
- [x] Tool-call JSON'u metin olarak gelirse güvenli biçimde parse edip çalıştır.
- [x] Agent görevi tool çağrısından sonra normal chat'e düşmesin.

## P0 — Gerçek hedef workspace desteği
- [x] `C:\CREWINTEL` gibi kullanıcı tarafından verilen proje yolunu algıla.
- [x] Agent'ın aktif workspace'ini UMAY klasöründen bağımsızlaştır.
- [x] Tool erişimini aktif workspace ile sınırla.
- [x] Workspace dışına path traversal engeli koy.
- [x] Audit sırasında hedef proje ile UMAY'ın kendi dosyalarını karıştırma.

## P1 — Dosya ve proje keşfi
- [x] Klasör ağacı çıkarma.
- [x] Dosya okuma.
- [x] Regex/metin arama.
- [x] Büyük dosyaları parça parça okuma.
- [x] Binary/generated klasörleri varsayılan olarak dışarıda tutma.

## P1 — Yazılım mühendisi doğrulama
- [x] Terminal komutu çalıştırma.
- [x] pytest/lint/build/git gibi komutları çalıştırabilme.
- [x] Komut timeout'u.
- [x] Temel yıkıcı komut engeli.
- [x] Tool hatasını modele geri gönderme.

## P1 — Audit workflow
- [x] Önce keşif.
- [x] Sonra ilgili dosyaları okuma.
- [x] Sonra test/lint/build çalıştırma.
- [x] P0/P1/P2/P3 bulguları üretme.
- [x] Audit raporu oluşturma.
- [x] Değişiklik öncesi ve sonrası loglama.

## P1 — Kalıcı log
- [x] `logs/DEVELOPMENT_LOG.md` append-only kayıt.
- [x] `logs/actions.jsonl` eylem kaydı.
- [x] `logs/umay.log` çalışma kaydı.
- [x] Tool çağrısı, sonucu ve hatasının kaydı.

## P2 — Sonraki geliştirme
- [ ] Git diff güvenlik özeti.
- [ ] Otomatik test sonucu özeti.
- [ ] Audit raporundan görev listesi üretme.
- [ ] Onaylı modda otomatik düzeltme + tekrar test döngüsü.
- [ ] Browser/MCP araçlarının ayrı güvenli tool katmanı olarak eklenmesi.
- [ ] Uzun görevler için checkpoint/resume mekanizması.
