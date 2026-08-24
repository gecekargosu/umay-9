# UMAY GERÇEK İNSAN KULLANIMI AUDIT — FINAL REPORT

**Audit Date**: 2026-08-24
**Method**: Gerçek kullanıcı gibi chat API üzerinden test
**Test ortamı**: Docker container, localhost:5001

---

## ÖZET

| Metrik | Değer |
|--------|-------|
| Toplam test | 13 |
| PASS | 5 |
| FAIL | 6 |
| PARTIAL | 2 |
| **Başarı oranı** | **38%** |

**KRİTİK SONUÇ**: UMAY teknik olarak çalışıyor ama **gerçek kullanıcı görevlerinin çoğunu yerine getiremiyor.**

---

## TEST SONUÇLARI

### GÖREV 1-2: CHAT / CONVERSATION

| Test | İstek | Beklenen | Gerçek | Durum |
|------|-------|----------|--------|-------|
| T1 | "Merhaba, nasılsın?" | Selamlama | ✅ Doğru cevap (phi4-mini, 134 chars) | PASS |
| T2 | "Peki ya hava durumu?" | Web araştırması | ⚠️ URL listesi döndü, gerçek hava durumu yok | PARTIAL |
| T3 | "Python ile hesap makinesi yap" | Kod üretimi | ✅ Python kodu üretildi (phi4-mini) | PASS |
| T4 | "requirements.txt dosyasında ne var?" | Dosya okuma | ❌ Dosyayı okumadı, "dosya ne işe yarar" dedi | FAIL |

### GÖREV 3: COMPUTER CONTROL

| Test | İstek | Beklenen | Gerçek | Durum |
|------|-------|----------|--------|-------|
| T5 | "core/engine.py dosyasının ilk 10 satırını göster" | Dosya okuma | ❌ Calculator'a gitti! "Hesaplama hatası" döndü | FAIL |
| T6 | "core klasöründe hangi dosyalar var?" | Klasör listeleme | ⚠️ Tool kullanmadı, "gezinme yeteneğim yok" dedi | FAIL |
| T7 | "core/.umay_test_audit.txt dosyasına Merhaba yaz" | Dosya yazma | ❌ Calculator'a gitti! Dosya oluşturulmadı | FAIL |
| T8 | "azorcar version bilgisi nedir?" | Komut çalıştırma | ❌ web_search() hatası döndü | FAIL |

### GÖREV 4: CODING AGENT

| Test | İstek | Beklenen | Gerçek | Durum |
|------|-------|----------|--------|-------|
| T9 | "Fibonacci serisinin ilk 10 terimini hesaplayan script yaz" | Kod üretimi | ❌ Calculator'a gitti! "10 = 10" döndü | FAIL |
| T10 | "Bu koddaki hatayı bul: def add(a,b): return a - b" | Hata analizi | ⚠️ Calculator'a gitti ama hata mesajı döndü | FAIL |

### GÖREV 5: WEB / RESEARCH

| Test | İstek | Beklenen | Gerçek | Durum |
|------|-------|----------|--------|-------|
| T11 | "Python 3.13 ile gelen yeni özellikler nelerdir?" | Güncel bilgi | ⚠️ Eski bilgi verdi, web search kullandı ama güncellemedi | PARTIAL |

### GÖREV 8: FAILURE TESTING

| Test | İstek | Beklenen | Gerçek | Durum |
|------|-------|----------|--------|-------|
| T12 | "olmayan_xyz_12345.txt dosyasını oku" | Hata mesajı | ✅ "dosyayı okumasanız için" dedi (tool kullanmadı ama hata verdi) | PASS |
| T13 | "" (boş mesaj) | Hata | ✅ 400 BAD REQUEST döndü | PASS |

---

## KRİTİK BULGULAR

### 🔴 HU-01: INTENT ROUTER CALCULATOR ÇOK AGRESİF (P1)

**Dosya**: `core/intent_router.py` → `classify_intent()`
**Sorun**: Mesajda `-`, `/`, `+`, `*`, `=` karakterlerinden herhangi biri VE sayı varsa Calculator tetikleniyor.
**Kanıt**:
- "core/engine.py dosyasının ilk 10 satırını göster" → CALCULATOR (path'teki `/` ve `10` tetikledi)
- "Fibonacci serisinin ilk 10 terimini hesaplayan script yaz" → CALCULATOR (`10` tetikledi)
- "Bu koddaki hatayı bul: def add(a,b): return a - b" → CALCULATOR (`-` tetikledi)
**Kök neden**: `has_math_ops = any(op in text_lower for op in ['+', '-', '*', '/', '=', '^', '**', '×', '÷'])` — tek karakter eşleşmesi her yeri tetikliyor
**Etki**: Dosya okuma, kod üretimi, hata analizi gibi birçok görev Calculator'a gidiyor ve başarısız oluyor

### 🔴 HU-02: DOSYA İŞLEMLERİ ÇALIŞMIYOR (P1)

**Dosya**: `core/intent_router.py` → FILE intent
**Sorun**: "dosyasını oku", "ilk 10 satırını göster" gibi yaygın dosya istekleri FILE olarak algılanmıyor
**Kanıt**: T4, T5, T6, T7 testlerinin hepsi başarısız
**Kök neden**: FILE intent keywords çok dar — "dosyayı oku" var ama "dosyasının", "göster", "ilk X satır" yok
**Etki**: Kullanıcı dosya okuyamıyor, klasör listelemiyor, dosya oluşturamıyor

### 🟡 HU-03: TOOL ÇAĞRILMAMA SORUNU (P2)

**Dosya**: `ui/panel_server.py` → `execute_chat_task()`
**Sorun**: Intent.CHAT/KNOWLEDGE durumunda tool kullanılmıyor — sadece LLM cevabı dönüyor
**Kanıt**: T6'da "core klasöründe hangi dosyalar var?" → CHAT intent → tool kullanılmadı → "gezinme yeteneğim yok"
**Kök neden**: panel_server.py'de CHAT intent'inde `use_tools = False` ayarlı
**Etki**: Basit dosya/klasör istekleri bile tool kullanılmadan LLM'in genel bilgisine dayanıyor

### 🟡 HU-04: WEB ARAMA SONUÇLARI SENTEZLENMİYOR (P2)

**Dosya**: `core/agent_tools.py` → `web_search()`
**Sorun**: Web araması sonuçları döndürülüyor ama LLM tarafından sentezlenmiyor
**Kanıt**: T2'de "hava durumu" → URL listesi döndü, gerçek hava durumu bilgisi yok
**Kök neden**: Web search tool sonucu modele gidiyor ama model sonucu yorumlamak yerine raw listeyi gösteriyor
**Etki**: Kullanıcı arama sonuçlarını kendisi incelemek zorunda kalıyor

### 🟡 HU-05: BAĞLAM KAYBI (P2)

**Dosya**: `ui/panel_server.py`
**Sorun**: Her chat isteği bağımsız — önceki mesaj hatırlanmıyor
**Kanıt**: T2'de "Peki ya hava durumu?" → önceki selamlama bağlamı kayıp
**Kök neden**: Conversation history API'den yükleniyor ama LLM'e gönderilen context'te kullanılmıyor
**Etki**: Takip soruları anlaşılmıyor

### 🟢 HU-06: LOCAL_FAST/LOCAL_SMART MAPPING YOK (P3)

**Dosya**: `ui/templates/panel.html`
**Sorun**: Frontend'de "Local Fast" ve "Local Smart" seçeneği var ama backend'de karşılığı yok
**Etki**: Kullanıcı bu seçeneği yaptığında hangi modeli kullandığını bilmiyor

---

## ÇALIŞAN SAĞLAM ÖZELLİKLER

| Özellik | Durum | Kanıt |
|---------|-------|-------|
| Basit selamlama | ✅ | T1: Doğru Türkçe cevap |
| Kod üretimi (basit) | ✅ | T3: Python kodu üretildi |
| Boş mesaj engelleme | ✅ | T13: 400 BAD REQUEST |
| Hatalı dosya mesajı | ✅ | T12: Hata mesajı verdi |
| Intent classification (basit) | ✅ | Basit istekler doğru |

---

## NEDEN BAŞARISIZ?

### Kök Neden Zinciri

```
Kullanıcı: "core/engine.py dosyasının ilk 10 satırını göster"
    ↓
Intent Router: "/" karakteri + "10" → CALCULATOR ❌
    ↓
Router: CALCULATOR → evaluate_expression tool
    ↓
Tool: "core/engine.py dosyasının ilk 10 satırını göster" → matematik ifadesi değil
    ↓
Sonuç: "Hesaplama hatası: invalid syntax" ❌
    ↓
Kullanıcı: Dosyayı okuyamadı, hata aldı ❌
```

### Temel Sorunlar

1. **Intent Router**: Calculator algılaması çok geniş — tek karakter operatörler her yerde
2. **FILE intent**: Dosya istekleri yeterince algılanmıyor
3. **Tool calling**: CHAT intent'inde tool kullanılmıyor
4. **Web sentezi**: Arama sonuçları işlenmiyor
5. **Bağlam**: Önceki mesajlar hatırlanmıyor

---

## GÖREV 9: OTONOM UZUN GÖREV TESTİ

**Test edilemedi** — Mevcut intent routing sorunları nedeniyle uzun görevler başlatılamıyor. Calculator'a giden istekler başarısız oluyor.

**NOT VERIFIED**: Otonom görev yürütme test edilemedi.

---

## GÖREV 10: İNSAN KULLANIMI DEĞERLENDİRMESİ

### UMAY Güvenilir mi?
**HAYIR** — %38 başarı oranı ile güvenilir değil. Temel dosya okuma/yazma işlemleri çalışmıyor.

### Yaptığı İşleri Doğruluyor mu?
**HAYIR** — Calculator hatası döndüğünde "başarılı" gibi görünmüyor ama kullanıcıya anlamlı bir hata mesajı da vermiyor.

### Başarısızlığı Dürüstçe Söylüyor mu?
**KISMEN** — Boş mesaj ve hatalı dosya testlerinde hata verdi. Ama Calculator hatalarında teknik hata mesajı dönüyor ("invalid syntax"), kullanıcı anlayamıyor.

### Bağlamı Koruyor mu?
**HAYIR** — Her mesaj bağımsız işleniyor.

### Bilgisayarı Kontrol Edebiliyor mu?
**HAYIR** — Dosya okuma/yazma/klasör listeleme çalışmıyor (Calculator'a gidiyor).

### Kod Yazıp Doğrulayabiliyor mu?
**KISMEN** — Basit kod üretimi çalışıyor (T3). Ama karmaşık istekler Calculator'a gidiyor.

### Web Araştırması Yapılabiliyor mu?
**KISMEN** — Arama çalışıyor ama sonuçlar sentezlenmiyor (T2, T11).

### Kullanıcı Yokken Görevini Sürdürebiliyor mu?
**NOT VERIFIED** — Test edilemedi.

### Yaptığı ve Yapmadığı İşleri Ayırabiliyor mu?
**HAYIR** — Calculator hatası döndüğünde ne yaptığını ne yapamadığını açıklamıyor.

---

## ÖNERİLEN ÇÖZÜM SIRASI

| Sıra | Öncelik | Çözüm | Etki |
|------|---------|-------|------|
| 1 | 🔴 P1 | Calculator algılamasını kısıtla — tek karakter operatörler yeterli değil | Tüm testleri iyileştirir |
| 2 | 🔴 P1 | FILE intent'i genişlet — "dosya", "göster", "satır" kelimelerini ekle | Dosya işlemleri çalışır |
| 3 | 🟡 P2 | CHAT intent'inde tool kullanma zorunluluğu ekle | Dosya/klasör istekleri çalışır |
| 4 | 🟡 P2 | Web arama sonuçlarını sentezleme | Araştırma kalitesi artar |
| 5 | 🟡 P2 | Bağlam yönetimi (conversation history) | Takip soruları çalışır |

---

**Audit Status**: ✅ COMPLETE
**Report**: docs/audit/HUMAN_USE_AUDIT_REPORT.md
**Başarı Oranı**: %38 (13 testten 5 PASS)
