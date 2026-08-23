# UMAY 9 — A GRUBU ÇALIŞMA SIRASI
# Tarih: 23.08.2026
# Bağımlılık zincirine göre sıralanmış

---

## SIRA 1 — A3: Calculator Detection Daraltma
**Neden önce bu?** Intent sınıflandırması her şeyin temeli. Yanlış intent → yanlış tool.
**Karmaşıklık:** Düşük (1-2 saat)
**Dosya:** `core/intent_router.py`

**Sorun:** "İnternette matematik ara" → CALCULATOR'a düşüyor
**Yapılacak:**
- "matematik", "ortalama", "işlem", "hesapla" tek başına CALCULATOR tetiklemesin
- Yeni kural: Keyword + sayi birlikte olmalı VEYA kesin math pattern olmalı
- "İnternette matematik haberlerini ara" → WEB olmalı
- "125 × 48 kaç" → CALCULATOR olmalı

**Test:**
```
"İnternette matematik haberlerini ara" → WEB ✓
"125 × 48 kaç eder" → CALCULATOR ✓
"Bugünkü hava durumunu hesapla" → WEB ✓ (hesapla tek başına trigger olmasın)
"2+2 kaç eder" → CALCULATOR ✓
"Ortalamayı bul" → CHAT veya WEB ✓ (calculator değil)
```

**Checkpoint:** Intent testleri geçmeden sonraki adıma geçilmez.

---

## SIRA 2 — A10: Tool Execution Logging
**Neden bu?** Sonraki fix'lerde ne olduğunu görebilmemiz için log altyapısı şart.
**Karmaşıklık:** Düşük (1-2 saat)
**Dosya:** `ui/panel_server.py`

**Yapılacak:**
Her tool çağrısında structured log yaz:
```
[TOL_TRACE] ts=2026-08-23T23:00:00 request_id=xxx intent=WEB mode=online 
tool=web_search input="güncel haber" status=OK duration=2340ms
```

**Checkpoint:** Her chat isteği sonrası logs/ klasöründe trace satırı olmalı.

---

## SIRA 3 — A5: CHAT_IDENTITY Tool Kullanım Prompt'u
**Neden bu?** Model'in tool kullanması gerektiğini bilmesi lazım. A1'den önce yapılmazsa A1 çalışsa bile model tool'u kullanmayı reddedebilir.
**Karmaşıklık:** Düşük (1 saat)
**Dosya:** `core/identity.py`

**Yapılacak:**
CHAT_IDENTITY'ye şunları ekle:
- "Güncel bilgi, haber, fiyat, hava durumu gerekiyorsa MUTLAKA web_search kullan"
- "Tool sonucunu görmezden gelme, sonuca göre cevap ver"
- "Asla 'internete erişimim yok' deme — araçların var"
- "Tool başarısız olursa 'arama başarısız oldu' de, uydurma cevap verme"

**Checkpoint:** "İnternette güncel döviz kurları" → model web_search çağırmalı (en azından tool calling path'te).

---

## SIRA 4 — A1: WEB Direct Execution ⭐ EN KRİTİK
**Neden önce bu?** UMAY'ın internete erişmesini sağlayan temel fix. Tüm online yeteneği buraya bağlı.
**Karmaşıklık:** Orta (3-4 saat)
**Dosya:** `ui/panel_server.py` → satır ~574

**Sorun:** Direct tool execution path sadece TIME/CALCULATOR/FILE/DOCUMENT'i handle ediyor. WEB yok.
**Yapılacak:**
1. `if _intent in (Intent.TIME, Intent.CALCULATOR, Intent.FILE, Intent.DOCUMENT)` satırına `Intent.WEB` ekle
2. WEB intent için tool args extraction yaz:
   - "İnternette güncel haber ara" → web_search(query="güncel haber")
   - Sorudan "internette", "webde", "ara" gibi kelimeleri temizle, geriye kalanı query yap
3. web_search tool'unu direkt çalıştır, LLM'e bırakma
4. Sonucu LLM'e gönder, analiz etsin ve cevap versin

**Test (E2E):**
```
Input: "İnternette güncel haber ara"
→ Intent.WEB ✓ (A3 sayesinde)
→ web_search("güncel haber") ✓ (direct execution)
→ DuckDuckGo'dan sonuçlar geldi ✓
→ LLM sonucu analiz etti ✓
→ Cevap: "İşte güncel haberler: ..." ✓
→ Log'da [TOOL_TRACE] tool=web_search görüldü ✓ (A10 sayesinde)
```

**Checkpoint:** Bu test geçmeden sonraki adıma geçilmez. Bu A grubunun %80'i.

---

## SIRA 5 — A2: TERMINAL Direct Execution
**Neden sonra bu?** WEB'den sonra ikinci en kritik. UMAY'ın cmd/powershell çalıştırmasını sağlar.
**Karmaşıklık:** Orta (3-4 saat)
**Dosya:** `ui/panel_server.py` + `core/permission_manager.py`

**Yapılacak:**
1. A1 ile aynı pathe `Intent.TERMINAL` ekle
2. Permission Manager oluştur:
   - BLOCKED: rm -rf, del /s, format, shutdown → kesinlikle yasak
   - APPROVAL: pip install, docker, git push → onay gerekiyor
   - FREE: ipconfig, dir, ls, cat, echo → serbest
3. Terminal komutunu çalıştır, sonucu döndür

**Test (E2E):**
```
Input: "cmd'de ipconfig çalıştır"
→ Intent.TERMINAL ✓
→ permission check: FREE ✓
→ run_command("ipconfig") ✓
→ Ağ bilgisi döndü ✓

Input: "rm -rf / calistir"
→ Intent.TERMINAL ✓
→ permission check: BLOCKED ✗
→ "⚠️ Bu komut yasak" mesajı ✓
```

**Checkpoint:** Hem çalışır hem de güveli olmalı.

---

## SIRA 6 — A11: Permission Manager Tüm Tool'ların Önünde
**Neden sonra bu?** A2 ile birlikte çalışır. A2 olmadan anlamsız, A2 olduktan sonra gerekli.
**Karmaşıklık:** Düşük-Orta (2-3 saat)
**Dosya:** `core/permission_manager.py`

**Yapılacak:**
```python
PERMISSION_RULES = {
    # Serbest (kontrol yok)
    "free": ["read_file", "list_directory", "web_search", "get_current_time",
             "evaluate_expression", "search_files"],
    
    # Onay gerekiyor
    "approval": ["write_file", "run_command", "run_powershell", 
                 "browser_open", "open_file"],
    
    # Yasak
    "blocked": ["delete_file", "format_disk", "shutdown_system"],
}
```

**Checkpoint:** Tehlikeli tool'lar onay olmadan çalışmamalı.

---

## SIRA 7 — A4: Mode Policy (ONLINE/LOCAL/AUTO)
**Neden sonra bu?** A1 ve A2 çalıştıktan sonra mode'un ne anlama geldiği anlamlı olur.
**Karmaşıklık:** Orta (3-4 saat)
**Dosya:** `ui/panel_server.py` → `execute_chat_task()` başı

**Yapılacak:**
```python
MODE_POLICY = {
    "local":  {"web_allowed": False, "web_mandatory": False},
    "online": {"web_allowed": True,  "web_mandatory": True},
    "auto":   {"web_allowed": True,  "web_mandatory": False},
}

# Intent routing'de:
policy = MODE_POLICY.get(mode, MODE_POLICY["auto"])

if _intent == Intent.WEB and not policy["web_allowed"]:
    # LOCAL modda web gelirse → bilgi olarak çevir
    _intent = Intent.KNOWLEDGE
    on_status(task_id, "info", "ℹ️ LOCAL modda web araması yapılamaz")

if _intent == Intent.WEB and policy.get("web_mandatory"):
    # ONLINE modda web zorunlu → LLM'e bırakma
    use_direct_tool = True
```

**Test:**
```
Mode=LOCAL + "İnternette haber ara" → "LOCAL modda web yapılamaz" ✓
Mode=ONLINE + "İnternette haber ara" → web_search çağrılır ✓
Mode=AUTO + "İnternette haber ara" → router karar verir ✓
```

---

## SIRA 8 — A6: AUTO Mode Otomatik Web Search
**Neden sonra bu?** A3 ve A1 çalıştıktan sonra_AUTO'nun da doğru çalışması sağlanır.
**Karmaşıklık:** Orta (2-3 saat)
**Dosya:** `core/intent_router.py` → `classify_intent()`

**Yapılacak:**
- WEB keyword listesini genişlet: "güncel", "haber", "fiyat", "hava", "bugün", "son durum"
- Zaman-bagli sorulari WEB'e yönlendir: "bugün ne oldu", "şu anki fiyat"
- AUTO mode'da web-ihtiyaçlı sorular otomatik tespit edilmeli

**Test:**
```
"Bugünkü döviz kurları ne?" → WEB intent → web_search ✓
"Şu anki hava durumu" → WEB intent → web_search ✓
"Python nedir?" → KNOWLEDGE intent (web gereksiz) ✓
```

---

## SIRA 9 — A8: Tool-Result Guarantee
**Neden sonra bu?** A1 ve A2 çalıştıktan sonra tool sonuçlarının doğru işlendiğinden emin olmalı.
**Karmaşıklık:** Düşük (1-2 saat)
**Dosya:** `ui/panel_server.py`

**Yapılacak:**
- Tool boş sonuç döndürdüğünde → kullanıcıya "sonuç bulunamadı" de
- Tool hata döndürdüğünde → "araç hatası: {detay}" de
- Model tool sonucunu görmezden gelip uydurma cevap veremesin

**Checkpoint:** Tool başarısızsa "arama başarısız oldu" demeli, uydurmamalı.

---

## SIRA 10 — A9: Tool Failure/Fallback
**Neden sonra bu?** A1/A2/A8 çalıştıktan sonra fallback mantıklı olur.
**Karmaşıklık:** Orta (2-3 saat)
**Dosya:** `core/failure_recovery.py` + `core/agent_tools.py`

**Yapılacak:**
```python
WEB_FALLBACK = ["web_search", "browser_open", "research_topic"]

def execute_with_fallback(tool_chain, args):
    for tool in tool_chain:
        try:
            result = DISPATCH[tool](**args)
            if result.get("results"):
                return result
        except:
            continue
    return {"error": "Tüm web araçları başarısız"}
```

**Test:** DuckDuckGo error → Playwright fallback → sonuç dönmeli

---

## SIRA 11 — A7: Tool Chain Uçtan Uca Doğrulama
**Neden sonra bu?** Tüm parçalar yerinde olduktan sonra zinciri test etmeli.
**Karmaşıklık:** Orta (2-3 saat — test yazımı)

**Test senaryosu:**
```
User → Intent → Router → Tool Registry → Permission → Executor → Tool → Result → LLM → Response

Her aşama tek tek test edilmeli:
1. Intent doğru mu? ✓
2. Tool seçimi doğru mu? ✓
3. Permission izin veriyor mu? ✓
4. Tool gerçekten çalıştı mı? ✓
5. Sonuç LLM'e gitti mi? ✓
6. LLM sonuca göre cevap verdi mi? ✓
```

---

## SIRA 12 — A12: Gerçek E2E Integration Test Suite
**Neden en son bu?** Tüm fix'ler yapıldıktan sonra kapsamlı test.
**Karmaşıklık:** Orta (3-4 saat — test yazımı)

**Testler:**
```python
# Her test real pipeline'ı çalıştırır
{"input": "25 × 17 hesapla", "expect_tool": "evaluate_expression"}
{"input": "İnternette güncel haber ara", "expect_tool": "web_search"}
{"input": "cmd'de ipconfig", "expect_tool": "run_command"}
{"input": "C:\\test listele", "expect_tool": "list_directory"}
{"input": "Bugünkü hava durumu", "expect_tool": "web_search"}
{"input": "Python nedir", "expect_tool": None}  # Sadece LLM
```

---

## ÖZET SIRA

```
SIRA 1  A3  Calculator detection     (1-2h)   ← Temel: intent doğru olmalı
SIRA 2  A10 Logging                  (1-2h)   ← Altyapı: ne olduğunu görelim
SIRA 3  A5  System prompt            (1h)     ← Hazırlık: model bilsin
SIRA 4  A1  WEB execution  ⭐        (3-4h)   ← KRİTİK: internet çalışsın
SIRA 5  A2  TERMINAL execution       (3-4h)   ← KRİTİK: cmd/powershell çalışsın
SIRA 6  A11 Permission Manager       (2-3h)   ← Güvenlik: tehlikeli komutlar durdurulsun
SIRA 7  A4  Mode policy              (3-4h)   ← ONLINE≠LOCAL olmalı
SIRA 8  A6  Auto web search          (2-3h)   ← Otomatik tespit
SIRA 9  A8  Tool-result guarantee    (1-2h)   ← Uydurma cevap engeli
SIRA 10 A9  Fallback                 (2-3h)   ← Dayanıklılık
SIRA 11 A7  Chain verification       (2-3h)   ← Doğrulama
SIRA 12 A12 E2E tests               (3-4h)   ← Final test

Toplam: ~25-35 saat
```

---

## 🔑 HER SIRA SONRASI CHECKPOINT

Her madde bitirildiğinde şunlar kontrol edilmeli:
1. Mevcut testler PASS mı? (regression yok)
2. Yeni test senaryosu çalışıyor mu?
3. Log'da doğru trace var mı?
4. UI'da doğru görünüyor mu? (AMA SADECE GÖRÜNMESİ YETMEZ — backend de çalışmalı)

**KURAL:** Bir sonraki sıraya geçmeden önce checkpoint geçilmeli.
