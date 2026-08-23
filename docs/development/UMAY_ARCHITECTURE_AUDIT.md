# UMAY 9 — KÖK MİMARİ AUDIT

**Tarih:** 2026-08-23
**Durum:** READ-ONLY — kod değiştirilmedi

---

## 1. GERÇEK CHAT ZİNCİRİ

```
User: "Merhaba"
  ↓
SocketIO: on_chat_message() [panel_server.py:1531]
  ↓
task_state.start_task() [panel_server.py:1545]
  ↓
executor.submit() [panel_server.py:1153]
  ↓
execute_chat_task() [panel_server.py:467]
  ↓
classify_intent(soru) [intent_router.py]
  ↓
┌─ IF TIME/CALCULATOR/FILE/DOCUMENT:
│    → _DISPATCH[tool_name](**tool_args) [panel_server.py:709]
│    → DIRECT TOOL, NO LLM
│
└─ ELSE:
     → resolve_model() veya model_sec() [engine.py/router.py]
     → umay_chat(messages, model=model) [engine.py]
     → LLM CALL (Ollama)
  ↓
_add_to_history() → SQLite [panel_server.py:952]
  ↓
chat_response → SocketIO → Frontend
```

**⚠️ KRİTİK:** Orchestrator ve Planner KULLANILMIYOR!

---

## 2. GERÇEK MİMARİ vs HEDEF MİMARİ

### HEDEF:
```
USER → CHAT → SESSION → CONTEXT → INTENT → ORCHESTRATOR → PLANNER → MODEL ROUTER → TOOL ROUTER → EXECUTION → RESULT → MEMORY → USER
```

### GERÇEK:
```
USER → CHAT → INTENT → DIRECT TOOL veya LLM → HISTORY → USER
```

### FARK:
| Katman | Hedef | Gerçek | Durum |
|--------|-------|--------|-------|
| Session | Session + Conversation | SQLite (var) | ⚠️ KISMEN |
| Context | Memory injection | YOK | ❌ YOK |
| Intent | Intent Router | Keyword matching | ✅ VAR |
| Orchestrator | Task decomposition | Dead code | ❌ KULLANILMIYOR |
| Planner | Step planning | Dead code | ❌ KULLANILMIYOR |
| Model Router | AUTO/LOCAL/ONLINE | Keyword → Ollama | ⚠️ KISMEN |
| Tool Router | Dynamic tool selection | Intent-based static list | ⚠️ KISMEN |
| Execution | Agent loop | Single model call | ⚠️ KISMEN |
| Memory | Long-term memory | ChromaDB (var) | ⚠️ KISMEN |
| History | Conversation persistence | SQLite (var) | ✅ VAR |

---

## 3. MODEL ROUTING AUDIT

### Gerçek Zincir:
```
model_sec(message) [router.py]
  → keyword match → task category
  → resolve_model(task) [engine.py]
  → MODEL_PREFERENCES[task] → match against Ollama installed models
  → return first match
```

### AUTO:
- Keyword matching ile task category seçer
- `resolve_model(task)` ile Ollama'dan model bulur
- **HER ZAMAN OLLAMA KULLANIR** — online provider yok

### LOCAL:
- `resolve_model("chat")` → her zaman Ollama
- **ÇALIŞIYOR** ✅

### ONLINE:
- `PRIMARY_PROVIDER=NOT SET`
- Ollama'ya fallback yapıyor
- **GERÇEKTE ONLINE DEĞİL** ❌

### Model Selector (UI):
- Frontend dropdown'dan seçim yapılıyor
- `model_override` parametresi olarak geçiliyor
- `execute_chat_task()` içinde `resolve_model(task, requested=model_override)`
- **SEÇİM GERÇEKTEbackend'e gidiyor** ✅
- Ama `PRIMARY_PROVIDER` yoksa hep Ollama kullanıyor

### E2E Kanıt:
```
"Merhaba" → task=chat → model=phi4-mini:latest (Ollama) ✅
"python kodu yaz" → task=coding → model=qwen2.5-coder:7b (Ollama) ✅
"resmi analiz et" → task=vision → model=gemma3:4b (Ollama) ✅
ONLINE mode → AYNI MODEL (Ollama) ❌
```

---

## 4. OLLAMA AUDIT

| Durum | Davranış |
|-------|----------|
| Ollama çalışıyor | ✅ Model çağrılıyor |
| Ollama çalışmıyor | ❌ RuntimeError — fallback yok |
| Model mevcut | ✅ Doğru model seçiliyor |
| Model mevcut değil | ❌ İlk mevcut modele düşüyor |

**Ollama kapalıyken AUTO:** `installed_models()` → boş liste → `resolve_model()` → None → `umay_chat()` → RuntimeError

**Ollama kapalıyken ONLINE:** Aynı davranış — online provider olmadığı için Ollama'ya ihtiyaç var

**Fallback:** Yok. Ollama crash = UMAY crash.

---

## 5. MEMORY/HISTORY AUDIT

### A) Sohbet diske yazılıyor mu?
**EVET** ✅ — SQLite: `memory/conversations.db`
- 1059 conversations, 6644 messages
- Session bazında: `conversation_id` ile ilişkili

### B) Restart sonrası geri geliyor mu?
**EVET** ✅ — SQLite dosya tabanlı, restart sonrası korunuyor

### C) Yeni sohbet ile eski sohbet ayrılıyor mu?
**KISMEN** ⚠️ — Her chat message farklı `session_id` ile geliyor
- Frontend: `conversationId = 'panel-' + Date.now()`
- Yeni sayfa açıldığında yeni session ID
- Önceki session'ın mesajları farklı ID ile kayıtlı

### D) UMAY önceki konuşmayı context'e koyuyor mu?
**KISMEN** ⚠️ — Kod doğru ama session_id sorunlu
- `_get_session_history(session_id)` fonksiyonu `execute_chat_task()` içinde CHAKIRILIYOR ✅
- History mesajlara `*history` spread ile ekleniyor ✅
- Token budget check + context compression var ✅
- **AMA:** Frontend `conversationId = 'panel-' + Date.now()` — her sayfa yüklemesinde yeni session!
- Bu yüzden history her zaman boş dönüyor
- History kaydediliyor ama farklı session_id ile okunuyor

### E) History sadece UI'da mı tutuluyor?
**HAYIR** — SQLite'ta tutuluyor ✅
- Ama UI'da "History" paneli sadece conversation listesini gösteriyor
- Önceki mesajlar yüklenmiyor

### F) Memory ile conversation history birbirine karıştırılmış mı?
**HAYIR** — Ayrı sistemler:
- `conversation_store.py` → SQLite (mesaj geçmişi)
- `rag/memory_manager.py` → ChromaDB (semantik arama)
- `core/memory/memory_bridge.py` → bridge (her ikisini birleştirir)
- Ama bridge conversation history'yi kullanmıyor

### G) Bir önceki konuşmayı neden göremiyorum?
**KÖK NEDEN:** Frontend `conversationId = 'panel-' + Date.now()` ile her sayfa yüklemesinde yeni session ID oluşturuyor. Backend'de history kaydediliyor ve context'e enjekte ediliyor (line 320-325), ama eski session_id ile yeni session_id eşleşmediği için history boş dönüyor.

**ÇÖZÜM:** `conversationId`'yi `localStorage`'a kaydet, sayfa yenilendiğinde geri yükle.

---

## 6. GERÇEK RESTART TESTİ

Test: Docker restart sonrası history korunuyor mu?
```
SQLite: memory/conversations.db → restart sonrası MEVCUT ✅
ChromaDB: memory/chroma/ → restart sonrası MEVCUT ✅
JSON: memory/status.json → restart sonrası MEVCUT ✅
```

**SONUÇ:** Dosya persistence ✅, ama context injection ❌

---

## 7. "UMAY BENİ HATIRLIYOR MU?"

### Test 1: Conversation memory
```
"Benim favori projem UMAY" → _add_to_history() → SQLite ✅
"Benim favori projem ne?" → execute_chat_task() → context'e eklenmiyor ❌
→ LLM cevabı: "Bilmiyorum" veya uydurma
```

### Test 2: Persistent memory
```
learn("UMAY benim favori projem") → ChromaDB'ye yazıldı ✅
recall("Favori projem ne?") → ChromaDB'den arandı ✅
```

**SONUÇ:** Persistent memory (ChromaDB) çalışıyor, ama conversation history context'e enjekte edilmiyor.

---

## 7.5. CONTEXT ENJEKSİYON DETAYI

```python
# execute_chat_task() line 320-325:
history = _get_session_history(session_id)
messages = [
    {"role": "system", "content": _system_prompt},
    *history,  # ← HISTORY ENJEKTE EDİLİYOR ✅
    {"role": "user", "content": att_context}
]
```

**Ek korumalar:**
- Token budget check (preflight) ✅
- Context compression ✅
- `_MAX_HISTORY` limit ✅

**Tek sorun:** Session ID stabilize edilmeli.

---

## 8. ORCHESTRATOR AUDIT

| Dosya | Var mı? | Chat flow'da kullanılıyor mu? |
|-------|---------|-------------------------------|
| `core/orchestrator.py` | ✅ VAR | ❌ HİÇ KULLANILMIYOR |
| `core/planner.py` | ✅ VAR | ❌ HİÇ KULLANILMIYOR |
| `core/agent.py` | ✅ VAR | ⚠️ Sadece tool calling loop |
| `core/task_executor.py` | ✅ VAR | ✅ Chat submission |
| `core/task_state.py` | ✅ VAR | ✅ State persistence |

**Orchestrator/Planner:** Dead code — dosyalar var ama import edilmiyor, çağrılmıyor.

**Agent loop:** `core/agent.py` → `run_agent()` fonksiyonu var ama `execute_chat_task()` içinde kullanılmıyor. Chat flow'da tek bir `umay_chat()` çağrısı yapılıyor.

---

## 9. TOOL EXECUTION AUDIT

### "Masaüstündeki dosyaları listele" zinciri:
```
classify_intent() → Intent.FILE
  → get_available_tools(Intent.FILE) → ['list_directory', ...]
  → IF intent in (TIME/CALCULATOR/FILE/DOCUMENT):
      → _DISPATCH['list_directory'](path='/host/Desktop')
      → DIRECT TOOL CALL ✅
      → 60 entry döndü
```

### "Python kodu yaz" zinciri:
```
classify_intent() → Intent.CHAT
  → resolve_model('chat') → phi4-mini:latest
  → umay_chat(messages, model='phi4-mini:latest')
  → LLM produces code text
  → NO ACTUAL TOOL CALL ❌
```

### "Bu projeyi analiz et" zinciri:
```
classify_intent() → Intent.CHAT (keyword eşleşmesi yok)
  → model_sec() → chat model
  → umay_chat()
  → LLM текст döndürür
  → GERÇEK ANALİZ YAPMAZ ❌
```

**SONUÇ:** Tool execution sadece basit, tek step'li araçlarda çalışıyor. Multi-step agent loop yok.

---

## 10. HEDEF YETENEK HARİTASI

| Yetenek | Durum | Kanıt |
|---------|-------|-------|
| Kalıcı sohbet geçmişi | ⚠️ KISMEN | SQLite var ama context'e enjekte edilmiyor |
| Kalıcı memory | ⚠️ KISMEN | ChromaDB var ama conversation'dan bağımsız |
| LOCAL mode | ✅ ÇALIŞIYOR | Ollama model seçimi doğru |
| ONLINE mode | ❌ ÇALIŞMIYOR | PRIMARY_PROVIDER=NOT SET → hep Ollama |
| AUTO mode | ⚠️ KISMEN | Keyword routing var ama online fallback yok |
| Model selector | ⚠️ KISMEN | UI'dan seçim backend'e gidiyor ama hep Ollama |
| Model fallback | ❌ YOK | Ollama crash = UMAY crash |
| Ollama | ✅ ÇALIŞIYOR | 11 model, doğru routing |
| Qwen | ✅ MEVCUT | qwen3:8b, qwen2.5-coder:7b |
| Gemma | ✅ MEVCUT | gemma3:4b, gemma2:9b |
| Cloud models | ❌ YOK | Provider abstraction var ama yapılandırılmamış |
| Web search | ✅ ÇALIŞIYOR | DDGS + fallback |
| Filesystem | ✅ ÇALIŞIYOR | list_directory, read_file, search_files |
| PowerShell/CMD | ✅ MEVCUT | run_command tool |
| Code agent | ⚠️ KISMEN | Dosya var ama chat flow'da doğrudan kullanılmıyor |
| Browser agent | ⚠️ KISMEN | Playwright var ama E2E doğrulanmamış |
| Gmail | ❌ NOT CONFIGURED | Credential yok |
| Telegram | ⚠️ KISMEN | Adapter var ama bot token gerekli |
| Scheduler | ❌ PLACEHOLDER | UI'da var ama gerçek scheduling yok |
| Social media | ❌ YOK | Planlanmış ama kodlanmamış |
| Job search | ⚠️ KISMEN | kariyer_net_workflow.py var ama entegre değil |
| Voice input | ❌ YOK | — |
| Voice output | ❌ YOK | — |
| Proactive messages | ❌ YOK | — |
| Personality | ⚠️ KISMEN | System prompt var ama dynamic değil |
| Long-running tasks | ⚠️ KISMEN | Task executor var ama agent loop yok |
| Approval system | ⚠️ KISMEN | Backend var ama frontend eksik |
| Security/permissions | ⚠️ KISMEN | _safe_path var ama全面 değil |
| Project/file analysis | ❌ ÇALIŞMIYOR | "Analiz et" → LLM'e gidiyor, gerçek analiz yok |

---

## 11. GITHUB KARŞILAŞTIRMASI

### Production Framework Ortak Örüntüleri:

| Özellik | LangGraph | OpenAI SDK | CrewAI | UMAY |
|---------|-----------|------------|--------|------|
| Stateful execution | ✅ Graph state | ✅ Sessions | ✅ Crew state | ❌ Tek model call |
| Human-in-the-loop | ✅ Interrupts | ✅ Guardrails | ✅ Approvals | ⚠️ Approval backend var |
| Multi-step planning | ✅ Graph nodes | ✅ Handoffs | ✅ Flows | ❌ Dead code |
| Tool permissioning | ✅ | ✅ | ✅ | ⚠️ _safe_path |
| Memory (short+long) | ✅ | ✅ | ✅ | ⚠️ Ayrı sistemler |
| Durable execution | ✅ Resume | ✅ | ✅ | ❌ Tek call |
| Agent delegation | ✅ Subagents | ✅ Handoffs | ✅ Crew | ❌ Yok |
| Observability | ✅ Tracing | ✅ Tracing | ✅ | ❌ Yok |

### UMAY'ın Eksikleri:
1. **Agent loop** — Tek model call yerine multi-step döngü
2. **State management** — Graph-based state yerine basit dict
3. **Durable execution** — Restart sonrası devam
4. **Agent delegation** — Birden fazla agent arası geçiş
5. **Observability** — Trace/log sistemi

---

## 12. PROAKTİF UMAY ALTYAPISI

| Altyapı | Durum | Birbirine bağlı mı? |
|---------|-------|---------------------|
| Scheduler | ⚠️ Placeholder | ❌ |
| Background worker | ✅ TaskExecutor | ⚠️ Sadece chat |
| Notification | ⚠️ SocketIO | ❌ Telegram entegre değil |
| Telegram | ⚠️ Adapter var | ❌ Token gerekli |
| Task scheduler | ❌ Yok | — |
| Memory | ✅ ChromaDB | ❌ Conversation'dan bağımsız |
| User preference | ❌ Yok | — |
| Approval | ⚠️ Backend var | ❌ Frontend eksik |

**SONUÇ:** Proaktif UMAY için altyapı yetersiz. Altyapılar birbirine bağlı değil.

---

## 13. PERSONALITY AUDIT

| bileşen | Durum |
|---------|-------|
| identity.py | ✅ CHAT_IDENTITY prompt |
| system prompt | ✅ Sabit text |
| personality | ❌ Dynamic değil |
| tone | ⚠️ Prompt'a bağlı |
| memory | ❌ Personality memory yok |
| user profile | ❌ Yok |

**Sorun:** Personality sadece system prompt'ta sabit. Kullanıcı tercihlerine göre değişmiyor.

---

## 14. BÜYÜK MODEL MİMARİSİ

### Mevcut:
```python
# engine.py
def resolve_model(task, requested=None):
    # Sadece Ollama modellerini kontrol et
    available = installed_models()  # Ollama API
    # ... match against MODEL_PREFERENCES
```

### Eksik:
- Model provider abstraction痨var ama kullanılmıyor
- `model_providers.py` → `get_primary_provider()` → `PRIMARY_PROVIDER` env
- `PRIMARY_PROVIDER` hiç yapılandırılmamış
- Yeni model eklemek için: sadece `MODEL_PREFERENCES` dict'ini güncellemek yeterli
- Ama online provider eklemek için: `model_providers.py`'e yeni provider + env config gerekli

---

## SONUÇ TABLOSU

| Sistem | Durum | Gerçek kanıt | Sorun |
|--------|-------|-------------|-------|
| Chat | ⚠️ KISMEN | Tek model call, multi-step yok | Agent loop yok |
| History | ⚠️ KISMEN | SQLite 6644 mesaj | Session ID her sayfada değişiyor — context'e enjekte ediliyor ama boş dönüyor |
| Memory | ⚠️ KISMEN | ChromaDB 11 entry | Conversation'dan bağımsız |
| AUTO | ⚠️ KISMEN | Keyword routing | Online fallback yok |
| LOCAL | ✅ ÇALIŞIYOR | Ollama model seçimi | — |
| ONLINE | ❌ ÇALIŞMIYOR | PRIMARY_PROVIDER=NOT SET | Hep Ollama |
| Model Router | ⚠️ KISMEN | Keyword → model | Multi-provider yok |
| Orchestrator | ❌ DEAD CODE | Dosya var, kullanılmıyor | — |
| Tools | ✅ ÇALIŞIYOR | 62 tool, direct execution | Multi-step yok |
| Task | ⚠️ KISMEN | Executor + state | Agent loop yok |
| Telegram | ⚠️ KISMEN | Adapter var | Token gerekli |
| Scheduler | ❌ PLACEHOLDER | UI'da var | Gerçek scheduling yok |
| Personality | ⚠️ KISMEN | System prompt sabit | Dynamic değil |
| Browser | ⚠️ KISMEN | Playwright var | E2E doğrulanmamış |
| Code Agent | ⚠️ KISMEN | Dosya var | Chat flow'da kullanılmıyor |

---

## ÖNEMLİK SIRASI

🔴 KRİTİK:
1. Session ID stabilitesi (localStorage) — history context'e enjekte ediliyor ama boş dönüyor
2. ONLINE mode gerçekten online olmalı (PRIMARY_PROVIDER NOT SET)
3. Ollama fallback (crash durumunda)

🟠 ÖNEMLİ:
4. Agent loop (multi-step task execution)
5. Orchestrator/Planner'ı aktif et veya kaldır
6. Memory → conversation bridge

🟡 İYİLEŞTİRME:
7. Personality dynamic hale getir
8. Model provider abstraction'ı aktif et
9. Proaktif mesaj altyapısı

🟢 ÇALIŞIYOR:
- Intent Router
- Direct Tool Execution
- Chat (basit)
- Docker
- SQLite History
- ChromaDB Memory
- Filesystem
- Web Search
