# STEP-02 ONLINE MODE AUDIT

## Timestamp
2026-08-23

## Objective
Trace why ONLINE mode always uses Ollama, find root cause, create change plan.

## Baseline
- Git: c125633
- Tests: 564 passed, 1 skipped, 0 failed
- Docker: healthy
- PRIMARY_PROVIDER: NOT SET in .env or docker-compose.yml

---

## AŞAMA 1: CODE TRACE

### Complete Trace Chain

```
FRONTEND (panel.html L765):
  socket.emit('chat_message', {session_id, soru, model, mode, attachments})
  → mode = "online" | "local" | "auto"

BACKEND (panel_server.py L1533):
  on_chat_message(data):
    mode = data.get("mode", "auto")
    → execute_chat_task(..., mode=mode)

EXECUTE_CHAT_TASK (panel_server.py L500-554):
  IF mode == "local" AND intent == WEB:
    → intent = KNOWLEDGE (no web search)
  ELIF mode == "online" AND no internet:
    → mode = "local" (fallback)
  
  IF mode == "local":
    model = resolve_model("chat") → Ollama
  ELSE (AUTO/ONLINE):
    model, gorev = model_sec(soru) → Ollama keyword routing
    model = model or resolve_model("chat") → Ollama

  result = umay_chat(messages, model=model, tools=...)

ENGINE CHAT (core/engine.py L184-260):
  umay_chat = chat()
  provider, resolved_model = _get_provider_and_model(task, model)
  result = provider.chat(messages, model, tools)
  
  IF provider fails:
    → Ollama fallback (direct HTTP)

_GET_PROVIDER_AND_MODEL (core/engine.py L101-132):
  1. Check PROVIDER_<TASK> env → NOT SET
  2. Check PRIMARY_PROVIDER env → NOT SET → defaults to "OLLAMA"
  3. get_primary_provider() → OllamaProvider
  4. IF Ollama available → return OllamaProvider
  5. ELSE → return primary (OllamaProvider anyway)

PROVIDER RESOLUTION (core/model_providers.py):
  get_primary_provider():
    primary = os.getenv("PRIMARY_PROVIDER", "OLLAMA")
    IF primary == "OLLAMA":
      return OllamaProvider()
    ELSE:
      return OpenAICompatibleProvider(prefix=primary)
```

### KEY FINDING: The provider abstraction EXISTS and IS USED

`chat()` in `core/engine.py` DOES call `_get_provider_and_model()` which DOES check `PRIMARY_PROVIDER`. The problem is NOT that the code bypasses the abstraction — it's that **the abstraction always resolves to Ollama because PRIMARY_PROVIDER is not configured**.

### Mode Routing in execute_chat_task

```
mode="local":
  → resolve_model("chat") → Ollama (line 542)
  → umay_chat(messages, model="phi4-mini:latest")
  → _get_provider_and_model("chat", "phi4-mini:latest")
  → PRIMARY_PROVIDER="OLLAMA" → OllamaProvider
  → Ollama ✅ (correct behavior)

mode="online":
  → model_sec(soru) → resolve_model(task) → Ollama model name
  → umay_chat(messages, model="phi4-mini:latest")
  → _get_provider_and_model("chat", "phi4-mini:latest")
  → PRIMARY_PROVIDER="OLLAMA" → OllamaProvider
  → Ollama ❌ (should be cloud provider)

mode="auto":
  → model_sec(soru) → resolve_model(task) → Ollama model name
  → umay_chat(messages, model="phi4-mini:latest")
  → _get_provider_and_model("chat", "phi4-mini:latest")
  → PRIMARY_PROVIDER="OLLAMA" → OllamaProvider
  → Ollama ⚠️ (should try cloud first, fallback to Ollama)
```

### Provider Infrastructure Available

| Component | Status | Location |
|-----------|--------|----------|
| ModelProvider ABC | ✅ Implemented | model_providers.py L29 |
| OllamaProvider | ✅ Working | model_providers.py L66 |
| OpenAICompatibleProvider | ✅ Implemented | model_providers.py L162 |
| get_provider() | ✅ Works | model_providers.py L299 |
| get_primary_provider() | ✅ Works | model_providers.py L331 |
| resolve_provider_for_task() | ✅ Works | model_providers.py L340 |
| _get_provider_and_model() | ✅ Works | engine.py L101 |
| chat() provider integration | ✅ Works | engine.py L184 |

### Environment Configuration

| Var | .env | docker-compose | Default | Effect |
|-----|------|----------------|---------|--------|
| PRIMARY_PROVIDER | NOT SET | NOT SET | "OLLAMA" | Always Ollama |
| MIMO_API_KEY | NOT SET | NOT SET | "" | No cloud |
| MIMO_BASE_URL | NOT SET | NOT SET | "" | No cloud |
| MIMO_MODEL | NOT SET | NOT SET | "" | No cloud |
| EXTRA_PROVIDERS | NOT SET | NOT SET | "" | No extra |
| PROVIDER_REASONING | NOT SET | NOT SET | "" | No task override |

---

## AŞAMA 2: E2E EVIDENCE

### TEST-01: ONLINE mode → what provider?
```
ONLINE mode selected in UI
→ mode="online" sent to backend
→ execute_chat_task(mode="online")
→ model_sec(soru) → resolve_model(task) → "phi4-mini:latest"
→ umay_chat(messages, model="phi4-mini:latest")
→ _get_provider_and_model("chat", "phi4-mini:latest")
→ PRIMARY_PROVIDER="OLLAMA" → OllamaProvider
→ provider.chat() → Ollama HTTP call
→ RESULT: Ollama (phi4-mini:latest) ❌ NOT ONLINE
```

### TEST-02: LOCAL mode → what provider?
```
LOCAL mode selected in UI
→ mode="local" sent to backend
→ execute_chat_task(mode="local")
→ resolve_model("chat") → "phi4-mini:latest"
→ umay_chat(messages, model="phi4-mini:latest")
→ _get_provider_and_model("chat", "phi4-mini:latest")
→ PRIMARY_PROVIDER="OLLAMA" → OllamaProvider
→ provider.chat() → Ollama HTTP call
→ RESULT: Ollama (phi4-mini:latest) ✅ CORRECT
```

### TEST-03: AUTO mode → what provider?
```
AUTO mode selected in UI
→ mode="auto" sent to backend
→ execute_chat_task(mode="auto")
→ model_sec(soru) → resolve_model(task) → "phi4-mini:latest"
→ umay_chat(messages, model="phi4-mini:latest")
→ _get_provider_and_model("chat", "phi4-mini:latest")
→ PRIMARY_PROVIDER="OLLAMA" → OllamaProvider
→ provider.chat() → Ollama HTTP call
→ RESULT: Ollama (phi4-mini:latest) ⚠️ Should try cloud first
```

### E2E VERDICT
ONLINE mode = Ollama (NOT online) ❌
LOCAL mode = Ollama ✅
AUTO mode = Ollama ⚠️ (should try cloud first)

---

## AŞAMA 3: EXACT CHANGE PLAN

### ROOT CAUSE:
`PRIMARY_PROVIDER` env var is not set. Defaults to `"OLLAMA"`. The provider abstraction layer exists and works, but always resolves to OllamaProvider because no cloud provider is configured.

### CURRENT BEHAVIOR:
```
ONLINE → Ollama (same as LOCAL)
AUTO → Ollama (no cloud fallback)
LOCAL → Ollama (correct)
```

### TARGET BEHAVIOR:
```
ONLINE → Cloud provider (if configured) → Ollama fallback
AUTO → Best available (cloud if configured, else Ollama)
LOCAL → Ollama (unchanged)
```

### FILES TO CHANGE (3 files, minimal):

**1. docker-compose.yml** — Add provider env vars
```yaml
environment:
  # ... existing ...
  - PRIMARY_PROVIDER=${PRIMARY_PROVIDER:-OLLAMA}
  - MIMO_API_KEY=${MIMO_API_KEY:-}
  - MIMO_BASE_URL=${MIMO_BASE_URL:-}
  - MIMO_MODEL=${MIMO_MODEL:-}
  - EXTRA_PROVIDERS=${EXTRA_PROVIDERS:-}
```

**2. core/engine.py** — Pass mode to provider resolution
```python
# In _get_provider_and_model(), add mode parameter:
def _get_provider_and_model(task, requested_model=None, mode="auto"):
    # If mode=="online" and PRIMARY_PROVIDER != "OLLAMA", prefer cloud
    # If mode=="local", force Ollama
    # If mode=="auto", try primary then fallback
```

**3. ui/panel_server.py** — Pass mode through to chat()
```python
# In execute_chat_task(), pass mode to umay_chat:
result = umay_chat(messages, model=model, tools=..., task=gorev, mode=mode)
```

### RISKS:
- LOW: docker-compose.yml change is additive (env vars with defaults)
- LOW: engine.py change is backward compatible (mode parameter optional)
- MEDIUM: If cloud provider is configured but API key is wrong, need graceful fallback
- MITIGATION: Ollama fallback already exists in chat() (line 248-260)

### TEST PLAN:
1. LOCAL mode → Ollama (unchanged) — regression test
2. ONLINE mode without provider → Ollama (fallback) — new test
3. ONLINE mode with provider → Cloud — new test (requires API key)
4. AUTO mode without provider → Ollama — regression test
5. AUTO mode with provider → Cloud first, Ollama fallback — new test
6. All 564 existing tests pass — regression
7. Docker rebuild + health check
8. E2E SocketIO test with mode parameter

### WHAT THIS PLAN DOES NOT DO:
- Does NOT add new provider implementations (OpenAICompatibleProvider already exists)
- Does NOT change LOCAL mode behavior
- Does NOT modify intent router
- Does NOT change tool execution
- Does NOT affect session persistence (STEP-01)
- Does NOT add Orchestrator/Planner (future STEP)
