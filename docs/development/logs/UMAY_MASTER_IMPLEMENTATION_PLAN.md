# UMAY 9 — MASTER IMPLEMENTATION PLAN
# Tarih: 23.08.2026
# Sıralama: En kısa sürede bitebilenden en uzun süreye

---

## ✅ BAŞARI KRİTERİ (Kural)
> Bir problemi yalnızca UI'da düzeltilmiş göstermek YASAK.
> Her değişiklik gerçek execution pipeline'ında test edilmeli.
> Test sonucu kanıtlanmadan "tamamlandı" denmemeli.
> Uçtan uca gerçekten çalışıyor olmalı.

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FAZ 1 — HIZLI FIX'LER (1-2 saat)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### F1.1 — A3: Calculator Detection Daraltma
**Sorun:** "İnternette matematik ara" → CALCULATOR'a düşüyor
**Çözüm:** Keyword listesinden bağlam-sensitif kelimeleri kaldır
**Dosya:** `core/intent_router.py` → `classify_intent()`
**Nasıl:**
```python
# ÖNCE:
has_math_words = any(w in text_lower for w in [
    'hesapla', 'ortalama', 'matematik', 'işlem', ...
])

# SONRA: Sadece kesin matematik pattern'ları tut
# "matematik" tek başına CALCULATOR tetiklemesin
# "hesapla" bağlama göre: "125×48 hesapla" → CALC, "internette araştır ve hesapla" → WEB
# Yeni kural: Keyword + sayi birlikte olmalı, veya kesin pattern olmalı
```
**Test:** "İnternette matematik haberlerini ara" → Intent.WEB olmalı
**Test:** "125 × 48 kaç" → Intent.CALCULATOR olmalı

---

### F1.2 — C1: History Tarih Araması
**Sorun:** "23.08.2026" yazınca "Sonuç bulunamadı"
**Çözüm:** Search fonksiyonuna timestamp filtresi ekle
**Dosya:** `ui/panel_server.py` → `/api/conversations` endpoint + `ui/templates/panel.html` → `filterHistory()`
**Nasıl:**
```javascript
// Frontend: filterHistory fonksiyonuna tarih kontrolü ekle
function filterHistory(query) {
    const items = document.querySelectorAll('.conversation-item');
    items.forEach(item => {
        const text = item.textContent;
        const date = item.dataset.date || ''; // data-date attribute
        // Tarih formatı kontrolü: GG.AA.YYYY veya YYYY-MM-DD
        const datePattern = /(\d{2})\.(\d{2})\.(\d{4})/.exec(query);
        if (datePattern) {
            // Tarihe göre filtrele
            const match = date.includes(query) || date.includes(datePattern[0]);
            item.style.display = match ? '' : 'none';
        } else {
            // Normal metin araması (mevcut)
            item.style.display = text.toLowerCase().includes(query.toLowerCase()) ? '' : 'none';
        }
    });
}
```
**Backend:** `/api/conversations` response'una `created_at` timestamp ekle
**Test:** "23.08.2026" yaz → Tüm conversations görünmeli

---

### F1.3 — C3: Varsayılan Model Değişikliği
**Sorun:** deepseek-r1 çok yavaş
**Çözüm:** Varsayılan modeli phi4-mini veya qwen3:8b yap
**Dosya:** `core/router.py` → `model_sec()` + `core/engine.py` → `resolve_model()`
**Nasıl:**
```python
# ÖNCE (router.py):
DEFAULT_MODEL = "deepseek-r1:8b"

# SONRA:
DEFAULT_MODEL = "phi4-mini:latest"  # Hızlı, tool calling destekli
# Veya AUTO mode'da intent'e göre seçim:
# CHAT → phi4-mini
# REASONING → qwen3:8b
# CODING → qwen2.5-coder:7b
```
**Test:** Yeni conversation → varsayılan model phi4-mini olmalı

---

### F1.4 — B2: Model Override Düzeltmesi
**Sorun:** Kullanıcı deepseek seçiyor ama router override ediyor
**Çözüm:** `model_override != "auto"` ise router'ı bypass et
**Dosya:** `ui/panel_server.py` → `execute_chat_task()` satır ~504
**Nasıl:**
```python
# ÖNCE:
model = model_override if model_override and model_override != "auto" else None

# SONRA:
if model_override and model_override != "auto":
    model = model_override  # Kullanıcı seçimi kesin
    _user_picked_model = True  # Flag
else:
    model = None
    _user_picked_model = False

# Router kısmında:
if _user_picked_model:
    pass  # Router'ı atla, kullanıcının seçtiği modeli kullan
else:
    model, gorev = model_sec(soru)  # Normal routing
```
**Test:** deepseek-r1 seç → mesaj gönder → model: deepseek-r1 olmalı

---

### F1.5 — A10: Tool Execution Logging
**Sorun:** "UMAY neden web aramadı?" sorusunun cevabı yok
**Çözüm:** Her tool çağrısını structured log'a yaz
**Dosya:** `ui/panel_server.py` → `execute_chat_task()`
**Nasıl:**
```python
import logging

def _log_tool_call(request_id, user_request, mode, intent, tool, tool_input, 
                   tool_result, tool_error, final_response, duration):
    log_entry = {
        "ts": datetime.now().isoformat(),
        "request_id": request_id,
        "intent": intent.value if intent else None,
        "mode": mode,
        "tool": tool,
        "input": str(tool_input)[:200],
        "result_status": "OK" if not tool_error else "ERROR",
        "error": str(tool_error)[:200] if tool_error else None,
        "duration_ms": round(duration * 1000),
        "response_preview": str(final_response)[:200],
    }
    log(f"[TOOL_TRACE] {json.dumps(log_entry, ensure_ascii=False)}")
```
**Test:** Her chat isteği sonrası logs/ klasöründe trace satırı olmalı

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FAZ 2 — CORE TOOL ROUTING (2-4 gün)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### F2.1 — A1: WEB Direct Execution ⭐ EN KRİTİK
**Sorun:** WEB intent tool çağrısı yapmıyor
**Çözüm:** Direct tool execution path'e Intent.WEB ekle
**Dosya:** `ui/panel_server.py` → satır ~574
**Nasıl:**
```python
# ÖNCE:
if _intent in (Intent.TIME, Intent.CALCULATOR, Intent.FILE, Intent.DOCUMENT) and _intent_tools_list and not has_image:

# SONRA:
if _intent in (Intent.TIME, Intent.CALCULATOR, Intent.FILE, Intent.DOCUMENT, 
               Intent.WEB, Intent.TERMINAL) and _intent_tools_list and not has_image:

# WEB intent için tool args extraction ekle:
elif _intent == Intent.WEB:
    if tool_name == "web_search":
        # Sorudan arama sorgusunu çıkar
        # "İnternette güncel haber ara" → "güncel haber"
        _query = _re.sub(r'(internette|webde|web\'de|google\'da|araştır|ara|bul)', '', soru, flags=_re.IGNORECASE).strip()
        if not _query:
            _query = soru  # Fallback: tüm soruyu arama olarak kullan
        tool_args = {"query": _query, "max_results": 5}
    elif tool_name == "browser_open":
        # URL çıkarma
        _url_match = _re.search(r'https?://[^\s]+', soru)
        if _url_match:
            tool_args = {"url": _url_match.group(0)}
        else:
            continue  # URL yoksa bu tool'u atla
```
**E2E Test:**
```
Input: "İnternette güncel haber ara"
→ Intent.WEB ✓
→ web_search("güncel haber") ✓
→ Sonuçlar döndü ✓
→ LLM sonucu analiz etti ✓
→ Cevap: "İşte güncel haberler: ..." ✓
```
**Kanıt:** Backend log'da `[TOOL_TRACE] tool=web_search` görülmeli

---

### F2.2 — A2: TERMINAL Direct Execution
**Sorun:** Terminal komutları çalışmıyor
**Çözüm:** Intent.TERMINAL'ı direct execution'a ekle + permission kontrolü
**Dosya:** `ui/panel_server.py` + `core/permission_manager.py`
**Nasıl:**
```python
elif _intent == Intent.TERMINAL:
    if tool_name == "run_command":
        # Komutu çıkar
        _cmd = _re.sub(r'(çalıştır|calistır|komutu|terminalde|cmd|powershell)', '', soru, flags=_re.IGNORECASE).strip()
        if not _cmd:
            continue
        # Permission kontrolü
        from core.permission_manager import check_permission
        if not check_permission("terminal", _cmd):
            cevap = f"⚠️ Bu komut için onay gerekiyor: {_cmd}"
            # Telegram'a onay isteği gönder (sonraki fazda)
            return
        tool_args = {"command": _cmd}
    elif tool_name == "run_powershell":
        _cmd = _re.sub(r'(powershell|ps)', '', soru, flags=_re.IGNORECASE).strip()
        tool_args = {"command": _cmd}
```
**Permission Manager:**
```python
# core/permission_manager.py
BLOCKED_COMMANDS = ['rm -rf', 'del /s', 'format', 'shutdown', 'reboot', 'taskkill']
REQUIRES_APPROVAL = ['pip install', 'npm install', 'docker', 'git push']

def check_permission(tool_type, command):
    cmd_lower = command.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return False  # Kesinlikle yasak
    for needs_approval in REQUIRES_APPROVAL:
        if needs_approval in cmd_lower:
            return "APPROVAL_NEEDED"  # Onay gerekiyor
    return True  # serbest
```
**E2E Test:**
```
Input: "cmd'de ipconfig çalıştır"
→ Intent.TERMINAL ✓
→ permission check ✓
→ run_command("ipconfig") ✓
→ Sonuç döndü ✓
```

---

### F2.3 — A4: Mode Policy (ONLINE/LOCAL/AUTO)
**Sorun:** ONLINE mod tool seçimini etkilemiyor
**Çözüm:** Mode'a göre orchestrator policy'si
**Dosya:** `ui/panel_server.py` → `execute_chat_task()` başı
**Nasıl:**
```python
# Mode policy dict
MODE_POLICY = {
    "local": {
        "web_allowed": False,      # İnternet kullanma
        "preferred_provider": "ollama",
        "fallback": None,
    },
    "online": {
        "web_allowed": True,       # İnternet kullan
        "preferred_provider": "ollama",  # veya cloud
        "web_mandatory": True,     # WEB intent geldiğinde web tool zorunlu
        "fallback": "ollama",
    },
    "auto": {
        "web_allowed": True,
        "preferred_provider": "ollama",
        "web_mandatory": False,    # Router karar verir
        "fallback": "ollama",
    },
}

# Intent routing'de mode'u değerlendir:
policy = MODE_POLICY.get(mode, MODE_POLICY["auto"])

if _intent == Intent.WEB and not policy["web_allowed"]:
    _intent = Intent.KNOWLEDGE  # LOCAL modda WEB → KNOWLEDGE'a çevir
    _intent_tools_list = None

if _intent == Intent.WEB and policy.get("web_mandatory"):
    # ONLINE modda WEB gelirse → tool zorunlu, LLM'e bırakma
    use_direct_tool = True
```
**E2E Test:**
```
Test 1: Mode=LOCAL → "İnternette haber ara" → "LOCAL modda web araması yapılamaz" mesajı
Test 2: Mode=ONLINE → "İnternette haber ara" → web_search çağrılır
Test 3: Mode=AUTO → "İnternette haber ara" → router karar verir (muhtemelen web_search)
```

---

### F2.4 — A5: CHAT_IDENTITY Tool Kullanım Prompt'u
**Sorun:** Model tool kullanması gerektiğini bilmiyor
**Çözüm:** System prompt'a toolusage instructions ekle
**Dosya:** `core/identity.py` → `CHAT_IDENTITY`
**Nasıl:**
```python
CHAT_IDENTITY = """...mevcut prompt..."""

# EKLE:
TOOL_INSTRUCTIONS = """

ARAÇ KULLANIMI:
- Güncel bilgi, haber, fiyat, hava durumu gerekiyorsa → web_search tool'unu kullan
- Dosya/klasör işlemleri → dosya tool'larını kullan  
- Terminal komutu → run_command tool'unu kullan
- Calculator → evaluate_expression tool'unu kullan

ÖNEMLİ KURALLAR:
- "İnternette", "güncel", "haber", "araştır" gibi kelimeler varsa → MUTLAKA web_search kullan
- Tool sonucunu görmezden gelme, sonuca göre cevap ver
- Tool başarısız olursa "arama başarısız oldu" de, uydurma cevap verme
- Asla "internete erişimim yok" deme — araçların var
"""
```
**Test:** "İnternette güncel döviz kurları" → model web_search çağırmalı

---

### F2.5 — A6: AUTO Mode Otomatik Web Search
**Sorun:** AUTO mode web araması yapmıyor
**Çözüm:** AUTO mode'da web-ihtiyaçlı soruları otomatik tespit et
**Dosya:** `core/intent_router.py` → `classify_intent()`
**Nasıl:**
```python
# WEB intent detection'ı genişlet:
WEB_CONTEXT_KEYWORDS = [
    'güncel', 'guncel', 'haber', 'news', 'fiyat', 'price',
    'hava', 'weather', 'bugün', 'bugun', 'şu an', 'su an',
    'şimdi', 'simdi', 'son durum', 'son haberler',
    'google', 'internette', 'webde',
]

# ALSO: Zaman-bağlı sorular WEB'e yönlendirilmeli
TIME_SENSITIVE_PATTERNS = [
    r'bugün.*ne\s+oldu',
    r'su\s+an.*durum',
    r'güncel.*bilgi',
    r'şu\s+anki.*fiyat',
]

# Intent.WEBKeyword listesini genişlet:
(Intent.WEB, [
    ...mevcut keyword'ler...
    'son durum', 'son haberler', 'güncel bilgi',
    'bugün ne oldu', 'şu anki',
])
```
**Test:** "Bugünkü döviz kurları ne?" → WEB intent → web_search

---

### F2.6 — A8: Tool-Result Guarantee
**Sorun:** Tool başarısız olursa model uydurma cevap verebilir
**Çözüm:** Tool sonucunu validate et
**Dosya:** `ui/panel_server.py` → tool result processing
**Nasıl:**
```python
# Tool sonucundan sonra:
if tool_results:
    last_result = tool_results[-1]["result"]
    if not last_result.get("results") and not last_result.get("text"):
        # Tool boş sonuç döndü
        cevap = f"⚠️ {tool_results[-1]['tool']} aracı boş sonuç döndü. Lütfen farklı bir sorgu deneyin."
    else:
        # Sonucu LLM'e gönder, analiz etsin
        cevap = _generate_response_from_tool_result(tool_results, messages)
```

---

### F2.7 — A9: Tool Failure/Fallback
**Sorun:** Tek tool başarısızsa görev bitiyor
**Çözüm:** Retry + fallback mekanizması
**Dosya:** `core/failure_recovery.py` → mevcut `with_recovery` fonksiyonunu genişlet
**Nasıl:**
```python
# WEB tool için fallback zinciri:
WEB_FALLBACK_CHAIN = [
    "web_search",           # 1. DuckDuckGo
    "browser_open",         # 2. Playwright ile直接 git
    "research_topic",       # 3. Kapsamlı araştırma
]

def execute_with_fallback(tool_chain, args):
    for tool_name in tool_chain:
        try:
            result = DISPATCH[tool_name](**args)
            if result.get("results") or result.get("text"):
                return result
        except Exception as e:
            log(f"[FALLBACK] {tool_name} başarısız: {e}, bir sonraki deneniyor")
            continue
    
    # Hepsi başarısız
    return {"error": "Tüm web araçları başarısız oldu", "fallback_chain": tool_chain}
```
**Test:** DuckDuckGo down → Playwright fallback → sonuç dönmeli

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FAZ 3 — DOSYA & UX (3-5 gün)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### F3.1 — B1: Attachment Analiz Prompt'u
**Sorun:** Model dosyayı echo ediyor, analiz yapmıyor
**Çözüm:** `build_chat_context()` fonksiyonunu iyileştir
**Dosya:** `core/attachment_engine.py`
**Nasıl:**
```python
# ÖNCE:
def build_chat_context(attachments, user_message):
    # Sadece dosya içeriğini ekliyor

# SONRA:
def build_chat_context(attachments, user_message):
    context_parts = []
    for att in attachments:
        content = att.get("content", "")
        filename = att.get("filename", "")
        file_type = att.get("type", "")
        
        if content:
            context_parts.append(
                f"📎 DOSYA: {filename} ({file_type})\n"
                f"İçerik:\n{content}\n"
                f"---\n"
                f"Bu dosya kullanıcı tarafından sağlandı. "
                f"Kullanıcının sorusunu dosya içeriğine göre cevapla. "
                f"Dosyayı olduğu gibi tekrar yazma, ANALİZ ET."
            )
    
    context_block = "\n\n".join(context_parts)
    return f"{context_block}\n\n---\n\nKullanıcı sorusu: {user_message}"
```
**Test:** JSON yükle + "Kaç modul var?" → "6 modul" demeli, JSON'u echo etmemeli

---

### F3.2 — C2: Gerçek Thinking Aşamaları
**Sorun:** "Düşünüyor..." çok genel
**Çözüm:** Backend'den gerçek status event'leri gönder
**Dosya:** `ui/panel_server.py` → `on_status` callback'leri
**Nasıl:**
```python
# Her aşama için on_status çağır:
if on_status:
    on_status(task_id, "analyzing", "İstek analiz ediliyor...")

if _intent == Intent.WEB:
    on_status(task_id, "web_searching", f"İnternette '{query}' aranıyor...")
    # tool çalıştıktan sonra:
    on_status(task_id, "web_results", f"{len(results)} sonuç bulundu, analiz ediliyor...")

if use_tools:
    on_status(task_id, "tool_running", f"🔧 {func_name} çalışıyor...")
```
**Frontend:** Status event'lerini göster:
```javascript
socket.on('task_status', (data) => {
    const statusEl = document.getElementById('thinking-status');
    if (statusEl) {
        statusEl.textContent = data.message;
        statusEl.className = 'thinking-stage-' + data.phase;
    }
});
```

---

### F3.3 — C4: UI'da Model/Mode/Tool Durumu
**Sorun:** Kullanıcı ne olduğunu göremiyor
**Çözüm:** Chat area'ya durum çubuğu ekle
**Dosya:** `ui/templates/panel.html`
**Nasıl:**
```html
<!-- Chat area üstüne status bar -->
<div id="chat-status-bar" style="display:none;">
    <span id="status-mode">Mode: AUTO</span>
    <span id="status-model">Model: phi4-mini</span>
    <span id="status-tool">Tool: -</span>
    <span id="status-action">Hazır</span>
</div>
```
**Backend:** Response'a tool bilgisi ekle (zaten var: `resp_data["tool"]`)

---

### F3.4 — B3: Multimodal Attachment Fix
**Sorun:** Image + text birlikte gönderildiğinde veri kaybı
**Çözüm:** Multimodal path'te tüm attachment'ları koru
**Dosya:** `ui/panel_server.py` → vision path
**Nasıl:**
```python
# ÖNCE: vision sadece image'ı alıyor

# SONRA: vision path'te diğer attachment'ları da context'e ekle
if has_image and vision_image:
    # Diğer attachment'ları (text, code) da ekle
    text_attachments = [a for a in attachments if a.get("type") != "image"]
    if text_attachments:
        extra_context = build_chat_context(text_attachments, "")
        # vision mesajına ekle
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FAZ 4 — ORKESTRASYON & OTONOMİ (1-2 hafta)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### F4.1 — D1: Görev Planlama Sistemi
**Amaç:** "Şu projeyi incele, hataları bul, düzelt" gibi multi-step görevler
**Yeni dosya:** `core/orchestrator.py` → genişletme
**Nasıl:**
```python
class TaskOrchestrator:
    def __init__(self, task_description, mode="auto"):
        self.description = task_description
        self.mode = mode
        self.steps = []
        self.results = []
    
    def plan(self):
        """Görevi adımlara böl"""
        # LLM'e "bu görevi adım adımlara böl" de
        plan_prompt = f"""
        Bu görevi adım adımlara böl: {self.description}
        Her adım için: tool, input, expected_output belirle.
        JSON formatında dön.
        """
        plan = umay_chat([{"role": "user", "content": plan_prompt}], model="qwen3:8b")
        self.steps = json.loads(plan)["steps"]
    
    def execute_step(self, step):
        """Tek bir adımı çalıştır"""
        tool = step["tool"]
        args = step["args"]
        result = DISPATCH[tool](**args)
        self.results.append({"step": step, "result": result})
        return result
    
    def run(self):
        """Tüm adımları sırayla çalıştır"""
        self.plan()
        for i, step in enumerate(self.steps):
            log(f"[ORCHESTRATOR] Step {i+1}/{len(self.steps)}: {step['description']}")
            self.execute_step(step)
        return self.generate_report()
```

---

### F4.2 — D2: Otonom Görev Yürütme
**Amaç:** Kullanıcı yokken UMAY çalışmaya devam etsin
**Mevcut altyapı:** `core/task_state.py` zaten var → genişlet
**Nasıl:**
```python
# Task state'e persistent execution ekle
class AutonomousTask:
    def __init__(self, task_id, orchestrator):
        self.task_id = task_id
        self.orchestrator = orchestrator
        self.state = "PLANNING"  # PLANNING → RUNNING → PAUSED → COMPLETED → FAILED
        self.checkpoint = None
    
    def save_checkpoint(self, step_index):
        """Her adım sonrası checkpoint kaydet"""
        self.checkpoint = {
            "step_index": step_index,
            "results": self.orchestrator.results,
            "timestamp": datetime.now().isoformat()
        }
        task_state.save_checkpoint(self.task_id, self.checkpoint)
    
    def resume(self):
        """Checkpoint'ten devam et"""
        if self.checkpoint:
            start_step = self.checkpoint["step_index"] + 1
            for i, step in enumerate(self.orchestrator.steps[start_step:], start_step):
                self.execute_step(step)
                self.save_checkpoint(i)
```

---

### F4.3 — D5: Checkpoint/Resume
**Amaç:** Crash sonrası devam edebilme
**Dosya:** `core/task_state.py` → checkpoint methods ekle
**Nasıl:**
```python
# task_state.py'ye ekle:
def save_checkpoint(task_id, checkpoint_data):
    db.execute(
        "INSERT INTO checkpoints (task_id, step_index, data, created_at) VALUES (?, ?, ?, ?)",
        (task_id, checkpoint_data["step_index"], json.dumps(checkpoint_data), datetime.now().isoformat())
    )

def get_last_checkpoint(task_id):
    row = db.execute(
        "SELECT data FROM checkpoints WHERE task_id = ? ORDER BY step_index DESC LIMIT 1",
        (task_id,)
    ).fetchone()
    return json.loads(row[0]) if row else None
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FAZ 5 — TELEGRAM & BİLDİRİM (1-2 hafta)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### F5.1 — F1: Telegram → UMAY Mesaj Akışı
**Amaç:** Telegram'dan mesaj gelince UMAY cevap versin
**Dosya:** `core/telegram_user_adapter.py` → mevcut, test et
**Test:**
```
1. Telegram'dan "Merhaba UMAY" gönder
2. UMAY "Merhaba!" diye cevap versin
3. Conversation history'ye kaydedilsin
4. Web UI'dan da görünsün
```

---

### F5.2 — F2: UMAY → Telegram Rapor
**Amaç:** Görev bitince Telegram'a rapor gönder
**Dosya:** `core/telegram_user_adapter.py` → `_send_text()` zaten var
**Nasıl:**
```python
# AutonomousTask.run() bittiğinde:
def send_task_report(self, telegram_client):
    report = self.generate_report()
    message = f"""
✅ GÖREV TAMAMLANDI
📅 {self.completed_at}
⏱️ Süre: {self.duration}
📊 Adımlar: {len(self.steps)}/{len(self.steps)} tamamlandı

{report}
"""
    telegram_client.send_message(TARGET_USER_ID, message)
```

---

### F5.3 — F3/D3: Telegram Onay Sistemi
**Amaç:** Riskli işlemler için Telegram'dan onay al
**Nasıl:**
```python
# Telegram'dan onay butonları:
# Inline keyboard: [ONAYLA] [REDDET]

async def request_approval(task_id, action, details):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ONAYLA", callback_data=f"approve_{task_id}"),
         InlineKeyboardButton("❌ REDDET", callback_data=f"reject_{task_id}")]
    ])
    await client.send_message(
        TARGET_USER_ID,
        f"⚠️ ONAY GEREKLİ\n\n{action}\n\nDetay: {details}",
        reply_markup=keyboard
    )

# Callback handler:
@client.on_callback_query()
async def handle_approval(callback):
    task_id = callback.data.split("_")[1]
    if callback.data.startswith("approve"):
        task_state.approve(task_id)
        await callback.message.edit_text("✅ Onaylandı — görev devam ediyor")
    else:
        task_state.reject(task_id)
        await callback.message.edit_text("❌ Reddedildi — görev iptal edildi")
```

---

### F5.4 — D4: Hata Yönetimi + Bildirim
**Amaç:** Görev başarısız olursa Telegram'a bildir
**Nasıl:**
```python
def notify_error(telegram_client, task_id, error):
    error_type = classify_error(error)
    message = f"""
❌ GÖREV BAŞARISIZ
📋 Görev: {task_id}
🔴 Hata: {error_type}
💬 Detay: {str(error)[:500]}

{get_recovery_suggestion(error_type)}
"""
    telegram_client.send_message(TARGET_USER_ID, message)

def classify_error(error):
    error_str = str(error).lower()
    if "timeout" in error_str: return "TIMEOUT"
    if "connection" in error_str: return "NETWORK_ERROR"
    if "permission" in error_str: return "PERMISSION_DENIED"
    if "not found" in error_str: return "RESOURCE_NOT_FOUND"
    return "UNKNOWN_ERROR"

def get_recovery_suggestion(error_type):
    suggestions = {
        "TIMEOUT": "💡 Öneri: Daha kısa bir görev veya farklı model deneyin",
        "NETWORK_ERROR": "💡 Öneri: İnternet bağlantınızı kontrol edin",
        "PERMISSION_DENIED": "💡 Öneri: Terminal izinlerini kontrol edin",
    }
    return suggestions.get(error_type, "💡 Manuel müdahale gerekebilir")
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FAZ 6 — STOP/CANCEL & HATA YÖNETİMİ (3-5 gün)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### F6.1 — E1: Stop/Cancel Gerçek Test
**Amaç:** Tool gerçekten durmalı, sadece UI'da yazmamalı
**Test senaryosu:**
```
1. Uzun web search başlat
2. THINKING sırasında STOP'a bas
3. Kontrol:
   - Backend'de tool execution durdu mu?
   - Process memory serbest kaldı mı?
   - Yeni mesaj gönderilebiliyor mu?
```

---

### F6.2 — E2: Hata Türleri Ayrıştırma
**Dosya:** `core/failure_recovery.py`
**Nasıl:**
```python
class UmayError(Exception):
    def __init__(self, error_type, message, details=None):
        self.error_type = error_type
        self.message = message
        self.details = details

ERROR_TYPES = {
    "MODEL_NOT_FOUND": "Model bulunamadı — model adını kontrol edin",
    "TOOL_NOT_FOUND": "Araç bulunamadı — UMAY henüz bu aracı desteklemiyor",
    "TOOL_FAILED": "Araç çalıştırılamadı — detay için logları kontrol edin",
    "PERMISSION_DENIED": "İzin reddedildi — bu işlem için onay gerekiyor",
    "TIMEOUT": "Zaman aşımı — işlem çok uzun sürdü",
    "NETWORK_ERROR": "Ağ hatası — internet bağlantınızı kontrol edin",
    "INVALID_INPUT": "Geçersiz giriş — lütfen mesajınızı kontrol edin",
}
```

---

### F6.3 — E3: Timeout Yönetimi
**Dosya:** `ui/panel_server.py` → `executor.wait_for_completion(timeout=300)`
**Nasıl:**
```python
# Timeout sonrası:
result = executor.wait_for_completion(task_id, timeout=300)
if result is None:
    # Timeout gerçekleşti
    _emit_task_status(task_id, "timeout", 
        "⏰ İşlem zaman aşımına uğradı (300s). Görev arka planda devam ediyor.")
    # Görev devam ediyor mu kontrol et
    if executor.is_running(task_id):
        _emit_task_status(task_id, "warning", 
            "⚠️ Görev arka planda hâlâ çalışıyor. Sonuçlar hazır olduğunda bildirilecek.")
    else:
        _emit_task_status(task_id, "error",
            "❌ Görev zaman aşımı ve durduruldu.")
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FAZ 7 — WEB INTELLIGENCE (1-2 hafta)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### F7.1 — G1: Search Result Quality
**Amaç:** Ham arama sonuçlarını filtrele ve sırala
**Dosya:** `core/agent_tools.py` → `web_search()`
**Nasıl:**
```python
def web_search(query, max_results=8):
    raw_results = DDGS().text(query, max_results=max_results * 2)  # 2x al
    
    # Dedup
    seen = set()
    unique = []
    for r in raw_results:
        if r["href"] not in seen:
            seen.add(r["href"])
            unique.append(r)
    
    # Relevance scoring (title-based)
    scored = []
    query_words = set(query.lower().split())
    for r in unique[:max_results]:
        title_words = set(r["title"].lower().split())
        relevance = len(query_words & title_words) / max(len(query_words), 1)
        scored.append({**r, "relevance": relevance})
    
    scored.sort(key=lambda x: x["relevance"], reverse=True)
    return scored[:max_results]
```

---

### F7.2 — G2: Kaynak Bilgisi Korunma
**Nasıl:**
```python
# web_search result'una kaynak bilgisi ekle:
result = {
    "query": query,
    "results": links,
    "sources": [{"title": r["title"], "url": r["href"]} for r in links],
    "timestamp": datetime.now().isoformat(),
}

# LLM cevabında kaynak göster:
if result.get("sources"):
    sources_text = "\n".join([f"  - {s['title']}: {s['url']}" for s in result["sources"][:3]])
    prompt_with_sources = f"Arama sonuçları:\n{raw_results}\n\nKaynaklar:\n{sources_text}\n\nBu kaynaklara göre cevap ver."
```

---

### F7.3 — G3: Context/Token Kontrolü
**Dosya:** `core/token_budget.py` → mevcut, genişlet
**Nasıl:**
```python
# Arama sonuçlarını token bütçesine sığdır:
def compress_search_results(results, max_tokens=2000):
    compressed = []
    current_tokens = 0
    for r in results:
        # Her sonuç ~100 token
        estimated = len(r.get("text", "").split()) * 1.3
        if current_tokens + estimated > max_tokens:
            break
        compressed.append(r)
        current_tokens += estimated
    return compressed
```

---

### F7.4 — G4: Güncellik Kontrolü
**Nasıl:**
```python
# Cache kullanma — her web_search taze sonuç getirsin
def web_search(query, max_results=8, no_cache=True):
    # no_cache=True → her zaman taze arama
    # Kullanıcı "bugün" dediğinde cache kullanılmamalı
    ...
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## E2E TEST SUITE (Her faz sonunda)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```python
# tests/test_e2e_pipeline.py

TEST_CASES = [
    # FAZ 1 testleri
    {"input": "25 × 17 hesapla", "expected_intent": "CALCULATOR", "expected_tool": "evaluate_expression"},
    {"input": "İnternette matematik haberlerini ara", "expected_intent": "WEB", "expected_tool": "web_search"},
    {"input": "23.08.2026 tarihinde ne konuşulmuş?", "test_type": "history_date_search"},
    
    # FAZ 2 testleri
    {"input": "İnternette güncel döviz kurları", "expected_intent": "WEB", "expected_tool": "web_search", "expected_mode": "online"},
    {"input": "cmd'de ipconfig çalıştır", "expected_intent": "TERMINAL", "expected_tool": "run_command"},
    {"input": "C:\\test klasörünü listele", "expected_intent": "FILE", "expected_tool": "list_directory"},
    
    # FAZ 3 testleri
    {"input": "Bu PDF'i özetle", "attachment": "test.pdf", "expected": "content_analysis"},
    {"input": "Bu görselde ne var?", "attachment": "test.png", "expected_tool": "analyze_image"},
    
    # FAZ 5 testleri
    {"input": "Merhaba UMAY", "channel": "telegram", "expected": "greeting_response"},
]
```

---

## 📊 ZAMAN ÇİZELGESİ

```
HAFTA 1:  FAZ 1 (Hızlı Fix'ler) — 1-2 gün
HAFTA 1-2: FAZ 2 (Core Tool Routing) — 3-4 gün
HAFTA 2-3: FAZ 3 (Dosya & UX) — 3-5 gün
HAFTA 3-4: FAZ 4 (Orkestrasyon) — 5-7 gün
HAFTA 4-5: FAZ 5 (Telegram) — 5-7 gün
HAFTA 5-6: FAZ 6 (Stop/Cancel) — 3-5 gün
HAFTA 6-7: FAZ 7 (Web Intelligence) — 5-7 gün

Toplam tahmini: 4-7 hafta
```

---

## 🔑 KRİTİK MİMARİ PRENSİPLER

1. **UI ≠ Functional**: Ekranda doğru görünmesi = çalışmıyor olması
2. **Tool garanti**: WEB/TERMINAL intent geldiğinde tool çağrısı garanti edilmeli
3. **Permission before execution**: Tehlikeli tool'lar önünde onay mekanizması
4. **Structured logging**: Her tool çağrısı loglanmalı
5. **Checkpoint**: Uzun görevlerde her adım kaydedilmeli
6. **Fallback chain**: Tek tool başarısızsa alternatif denenmeli
7. **No hallucination**: Tool sonucu yoksa uydurma cevap verilmemeli
8. **Mode = Policy**: ONLINE/LOCAL/AUTO sadece etiket değil, gerçek davranış politikası
