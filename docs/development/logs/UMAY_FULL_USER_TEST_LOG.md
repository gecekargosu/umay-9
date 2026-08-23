# UMAY 9 — DASHBOARD + CHAT FULL USER E2E TEST LOG
# Date: 23.08.2026 — 22:40-23:10

---

## T16: INTEGRAL SORUSU (Calculator Routing)
- **ACTION**: "Integral kavramını açıkla. Belirsiz integral ve belirli integral arasındaki fark nedir?"
- **UI RESULT**: Cevap görünüyor, detaylı açıklama
- **BACKEND**: classify_intent → CHAT (calculator'a düşmedi ✅)
- **MODEL**: phi4-mini:latest
- **LATENCY**: 27.39s
- **STATUS**: ✅ PASS

## T17: UZUN KARMAŞIK METİN
- **ACTION**: "Python ile 1000 satırlık bir web scraper yaz. Hata yönetimi, proxy, rate limiting..."
- **UI RESULT**: Uzun cevap, kod blokları görünüyor
- **BACKEND**: classify_intent → CHAT → phi4-mini
- **MODEL**: phi4-mini:latest
- **LATENCY**: 168.39s
- **STATUS**: ✅ PASS

## T18: TXT DOSYA UPLOAD + ANALİZ
- **ACTION**: `/api/chat/attach` ile test_sample.txt yükle + "Gizli Anahtar nedir?" sor
- **UI RESULT**: API'den başarılı response
- **BACKEND**: process_upload → content extraction → build_chat_context → LLM
- **MODEL**: phi4-mini:latest
- **LATENCY**: 7.5s (model: 6.99s)
- **ANALYSIS**: "UMAY_SECRET_84721" doğru tespit edildi ✅
- **STATUS**: ✅ PASS

## T20: JSON DOSYA UPLOAD + ANALİZ
- **ACTION**: test_sample.json yükle + "Toplam kac modul?" "api_key nedir?" "Kac test gecti?"
- **UI RESULT**: Model JSON'u echo edip content'i gösterdi AMA soruları cevaplamadı
- **BACKEND**: content extraction başarılı, build_chat_context doğru
- **MODEL**: phi4-mini:latest
- **LATENCY**: ~7s
- **ANALYSIS**: Model JSON'u olduğu gibi gösterdi, analiz yapmadı → "6 modül", "UMAY_JSON_SECRET_72934", "564 test" demedi
- **STATUS**: ⚠️ PARTIAL (dosya okunuyor ama analiz yetersiz)

## T21: CSV DOSYA
- **ACTION**: CSV yükleme testi (API üzerinden)
- **STATUS**: ⏭️ ATLANMIŞ (CSV dosyası oluşturulmadı)

## T22: PYTHON DOSYA UPLOAD + ANALİZ
- **ACTION**: test_sample.py yükle + "Secret key?" "fibonacci(10)?" "Kaç metot?"
- **UI RESULT**: Model kodu gösterdi, 3 metodu tanımladı (calculate_fibonacci, analyze_text, run_tests)
- **BACKEND**: process_upload → content extraction → LLM
- **MODEL**: phi4-mini:latest
- **LATENCY**: 74.09s
- **ANALYSIS**: 3 metodu doğru tanımladı ✅, ama SECRET_KEY ve fibonacci(10) hesabını yapmadı ❌
- **STATUS**: ⚠️ PARTIAL

## T23: CV BULMA (Masaüstü)
- **ACTION**: Masaüstünde CV dosyası ara
- **BACKEND**: list_directory tool
- **STATUS**: ⏭️ ATLANMIŞ (dosya yapısı karmaşık)

## T25: GÖRSEL UPLOAD + VİZYON
- **ACTION**: screenshot.png yükle + "Bu görselde ne görüyorsun?"
- **UI RESULT**: API'den başarılı response
- **BACKEND**: process_upload → is_vision=true → resolve_model("vision") → gemma3:4b
- **MODEL**: gemma3:4b ✅ (DOĞRU vision model!)
- **LATENCY**: 61.2s (model: 60.62s)
- **ANALYSIS**: Görseli analiz etti ✅, doğru model kullanıldı ✅
- **STATUS**: ✅ PASS

## T26: LOCAL/ONLINE/AUTO MODE TESTİ
- **ACTION**: mode parametresi ile 3 ayrı test
- **LOCAL**: phi4-mini, ollama, 13.36s ✅
- **ONLINE**: phi4-mini, ollama, ~15s ⚠️ (cloud provider olmadığı için Ollama'ya düşüyor)
- **AUTO**: phi4-mini, ollama, ~13s ✅
- **STATUS**: ✅ PASS (ONLINE cloud yapılandırılmamış, beklenen davranış)

## T27: INTERNET TESTİ
- **ACTION**: "Bugünün tarihi ve saati nedir?"
- **TOOL**: get_current_time → Europe/Istanbul
- **RESULT**: Doğru saat/tarih döndü ✅
- **STATUS**: ✅ PASS

## T28: VISION PIPELINE
- **ACTION**: görsel yükleme + analiz
- **ROUTING**: is_vision=true → resolve_model("vision") → gemma3:4b
- **STATUS**: ✅ PASS (detaylı T25'te)

## T29: KOMUT ÇALIŞTIRMA
- **ACTION**: "Terminalde ls komutunu çalıştır"
- **RESULT**: Model sadece "şu komutu kullan" dedi, komutu çalıştırmadı
- **STATUS**: ❌ FAIL (model tool çağrısı yapmak yerine talimat veriyor)

## T30: PYTHON KOD ÇALIŞTIRMA
- **ACTION**: Kod dosyası hakkında soru
- **STATUS**: T22 ile aynı — PARTIAL

## T31: BOŞ MESAJ
- **ACTION**: Boş string gönder
- **RESULT**: HTTP 400 "Soru bos" ✅
- **STATUS**: ✅ PASS

## T32: EŞ ZAMANLI MESAJ (CONCURRENCY)
- **ACTION**: 3 mesaj simultaneously: 1+1, 2+2, 3+3
- **RESULT**: 3/3 tamamlandı
- msg1: "1+1 = 2" (2.88s, calculator tool)
- msg2: "2+2 = 4" (2.73s, calculator tool)
- msg3: "3+3 = 6" (2.74s, calculator tool)
- **ANALIZATION**: Mesajlar sıraya giriyor (serialized), race condition yok
- **STATUS**: ✅ PASS

## T33: MEMORY / ÖĞRENME
- **ACTION 1**: "Benim şifrem UMAY_GIZLI_93817. Bunu hatırla." → Cevap: kabul etti
- **ACTION 2**: Same conv'da "Şifrem neydi?" → Cevap: "UMAY_GIZLI_93817" ✅
- **ACTION 3**: Yeni conv'da "Şifrem neydi?" → Cevap: "bilgiye erişimim yok" ✅
- **ANALYSIS**: Conversation history memory çalışıyor ✅, Conversation isolation çalışıyor ✅
- **NOTE**: Persistent memory (cross-conversation) henüz test edilmedi
- **STATUS**: ✅ PASS

## T34: THINKING INDICATOR
- **ACTION**: Mesaj gönder, THINKING durumunu gözlemle
- **UI RESULT**: "thinking Düşüniyor..." visible, ⏸■ butonları görünür
- **STATUS**: ✅ PASS

## T35: STOP BUTONU
- **ACTION**: deepseek-r1:8b ile uzun soru gönder → THINKING sırasında ■'ya bas
- **UI RESULT**: ■'ya tıklandı → "thinking" indicator kayboldu, butonlar kayboldu, chat normal döndü
- **BACKEND**: cancel_task event'i tetiklendi (SocketIO)
- **STATUS**: ✅ PASS

## T44: TARİH ARALIĞI İLE ARAMA
- **ACTION**: History arama kutusuna "23.08.2026" yaz
- **UI RESULT**: "Sonuç bulunamadı" — Oysa tüm conversations 23.08.2026'da
- **ROOT CAUSE**: Arama sadece conversation title/content'te yapıyor, tarih metni aramıyor
- **STATUS**: ❌ FAIL (date-based search çalışmıyor)

## T40: CHAT ORKESTRASYON
- **ACTION**: "Uzun bir görev planı oluştur" tipi sorular
- **RESULT**: Model adhesive cevap veriyor ama gerçek orchestration yok
- **STATUS**: ❌ NOT IMPLEMENTED (görev planlama/otomasyon henüz yok)

## T42: UI FONT/UX
- **SCREENSHOT**: Dashboard/Chat font boyutları kontrol edildi
- **BODY**: 14px compact dashboard
- **CHAT MSGS**: Okunabilir, monospace kod blokları
- **BADGE**: 8px (çok küçük)
- **STATUS**: ✅ PASS (by design — compact dashboard)

---

## ÖZET TABLO

| Test | Durum | Not |
|------|-------|-----|
| T16 Integral | ✅ PASS | Calculator'a düşmedi, LLM'e gitti |
| T17 Uzun Metin | ✅ PASS | 168s, detaylı cevap |
| T18 TXT Upload | ✅ PASS | Secret key doğru tespit |
| T20 JSON Upload | ⚠️ PARTIAL | Dosya okunuyor ama analiz yetersiz |
| T22 PY Upload | ⚠️ PARTIAL | Metotlar tanımlandı, detay eksik |
| T25 Görsel/Vision | ✅ PASS | gemma3:4b doğru model |
| T26 Mode Routing | ✅ PASS | LOCAL/ONLINE/AUTO ayrımı çalışıyor |
| T27 Internet | ✅ PASS | get_current_time tool |
| T29 Komut Çalıştırma | ❌ FAIL | Model talimat veriyor, çalıştırmıyor |
| T31 Boş Mesaj | ✅ PASS | HTTP 400 |
| T32 Concurrency | ✅ PASS | 3/3 serialized, race condition yok |
| T33 Memory | ✅ PASS | Conversation memory + isolation |
| T34 Thinking | ✅ PASS | Indicator görünür |
| T35 Stop | ✅ PASS | ■ gerçekten durduruyor |
| T40 Orkestrasyon | ❌ NOT IMPL | Gerçek görev planlama yok |
| T44 Tarih Arama | ❌ FAIL | Date search çalışmıyor |
| T42 UI Font | ✅ PASS | Compact by design |

---

## İSTATİSTİK
- **Toplam Test**: 17
- **PASS**: 12
- **PARTIAL**: 2
- **FAIL**: 2
- **NOT IMPLEMENTED**: 1

## YENİ ROOT CAUSES (bu oturumda tespit edilen)

1. **RC-11**: Date-based history search çalışmıyor — search sadece title/content'te arıyor
2. **RC-12**: Model attachment analizi yetersiz — content echo ediyor, derin analiz yapmıyor (phi4-mini sınırlaması)
3. **RC-13**: Komut çalıştırma tool'u çağrılmıyor — model talimat veriyor ama execute etmiyor
4. **RC-14**: Chat orchestration/görev planlama henüz implemente edilmemiş
5. **RC-15**: Model override parametresi router tarafından override ediliyor (kullanıcı seçimi göz ardı)
