# STEP-02.1 CRITICAL FIXES AUDIT

## Timestamp
2026-08-23

## Baseline
- Git: 639e0fc, branch main
- Tests: 564 passed, 1 skipped, 0 failed
- Docker: healthy, port 5001
- LOCAL == GITHUB ✅

---

## P0-1: ONLINE PROVIDER/MODEL ROUTING

### Status: CONFIRMED ROOT CAUSE ✅

### Trace Chain
```
Frontend (panel.html L770):
  socket.emit('chat_message', {mode: selectedMode})

Backend (panel_server.py L1536):
  mode = data.get("mode", "auto")

execute_chat_task (panel_server.py L500-L554):
  IF mode == "local":
    model = resolve_model("chat")  → Ollama ✅
  ELIF mode == "online" AND no internet:
    mode = "local"  → fallback ✅
  ELSE (AUTO/ONLINE):
    model, gorev = model_sec(soru)  → Ollama keyword routing
    model = model or resolve_model("chat")  → Ollama

  result = umay_chat(messages, model=model, tools=...)

engine.py chat() (L184-L260):
  provider, resolved_model = _get_provider_and_model(task, model)
  result = provider.chat(messages, model, tools)

_get_provider_and_model (L101-L132):
  1. PROVIDER_<TASK> env → NOT SET
  2. PRIMARY_PROVIDER env → NOT SET → default "OLLAMA"
  3. get_primary_provider() → OllamaProvider
  4. return OllamaProvider
```

### Root Cause
1. `mode` parameter is NOT passed to `umay_chat()` or `_get_provider_and_model()`
2. `PRIMARY_PROVIDER` defaults to "OLLAMA" (not configured in .env or docker-compose)
3. `resolve_model()` always returns Ollama model name regardless of mode
4. ONLINE mode only affects: internet check + web intent override — NOT provider selection

### Impact
- ONLINE mode = Ollama (same as LOCAL) — misleading to user
- Cloud provider abstraction exists but is never used by chat flow
- If user configures `PRIMARY_PROVIDER=MIMO`, it would work for ALL modes (not just ONLINE)

### Fix Required
1. Pass `mode` through to `_get_provider_and_model()`
2. When `mode=="online"` and `PRIMARY_PROVIDER != "OLLAMA"`, prefer cloud provider
3. When `mode=="local"`, force Ollama regardless of `PRIMARY_PROVIDER`
4. Add env vars to docker-compose.yml for provider configuration

### Files to Change
- `core/engine.py` — `_get_provider_and_model()` add mode param
- `ui/panel_server.py` — pass mode to `umay_chat()`
- `docker-compose.yml` — add provider env vars

---

## P0-2: PRODUCTION CHAT APPROVAL BYPASS

### Status: CONFIRMED ROOT CAUSE ✅

### Trace Chain
```
Panel Server (L579-L709):
  from core.agent_tools import DISPATCH as _DISPATCH
  tool_result = _DISPATCH[tool_name](**tool_args)
  → DIRECT EXECUTION, NO APPROVAL CHECK

Agent (core/agent.py L124-L136):
  def _execute_tool(call):
    name = fn.get("name")
    result = DISPATCH[name](**args)
    → DIRECT EXECUTION, NO APPROVAL CHECK

Approval Manager Usage:
  - ONLY used for Telegram (panel_server.py L1678-1697)
  - NOT used in chat tool execution path
```

### Root Cause
- `_execute_tool()` in `core/agent.py` calls `DISPATCH[name](**args)` directly
- No approval gate exists in the tool execution path
- `_DISPATCH[tool_name](**tool_args)` in `panel_server.py` also bypasses approval
- `ApprovalManager` is only wired to Telegram adapter, not chat

### Impact
- ANY tool (write_file, run_command, browser_click, etc.) can be executed without approval
- In production chat, LLM tool calls execute immediately
- Security risk: malicious or incorrect tool calls have no human-in-the-loop

### Fix Required
- Add approval check in `_execute_tool()` for medium/high risk tools
- Add approval check in `panel_server.py` direct dispatch path
- Use existing `ApprovalManager` — do not create new approval system

### Files to Change
- `core/agent.py` — add approval check in `_execute_tool()`
- `ui/panel_server.py` — add approval check in direct dispatch path
- `core/approval_manager.py` — ensure chat integration exists

---

## P0-3: ONLINE VISION ROUTING

### Status: CONFIRMED ROOT CAUSE ✅

### Trace Chain
```
execute_chat_task (panel_server.py L521-L532):
  has_image = any(a.get("is_vision") or a.get("type") == "image" for a in attachments)
  IF has_image:
    vision_model = resolve_model("vision")  → ALWAYS OLLAMA
    model = vision_model
    gorev = "vision"
```

### Root Cause
- `resolve_model("vision")` always returns Ollama vision model (gemma3:4b, llava:7b, etc.)
- No mode-aware routing for vision
- ONLINE + image → still Ollama vision model
- Provider abstraction bypassed for vision path

### Impact
- ONLINE mode with images still uses local Ollama vision
- User expects cloud vision model in ONLINE mode
- Image + other attachments: image branch may override other content routing

### Fix Required
- Route vision through provider abstraction when mode is ONLINE
- Ensure image + attachment combination works correctly

### Files to Change
- `ui/panel_server.py` — mode-aware vision routing

---

## P0-4: CONVERSATION HISTORY BUG

### Status: CONFIRMED ROOT CAUSE ✅

### Trace Chain
```
agent.py L268:
  raw_history = _conv.get_history(session_id, limit=10)

conversation_store.py L105:
  def get_history(conversation_id: str, max_pairs: int = DEFAULT_MAX_PAIRS)

panel_server.py L110:
  return _conv_store.get_history(session_id, max_pairs=_MAX_HISTORY)
```

### Root Cause
1. **Parameter mismatch:** `agent.py` passes `limit=10` but function expects `max_pairs=`
2. **Silent exception:** `except Exception: pass` (L274-275) swallows the TypeError
3. **Result:** `run_agent()` NEVER gets conversation history — always empty

### Impact
- Agent loop (run_agent) has no conversation context
- Each message is treated as isolated — UMAY "forgets" previous messages in agent path
- panel_server.py direct path works correctly (uses `max_pairs=`)

### Fix Required
1. Change `limit=10` to `max_pairs=10` in agent.py L268
2. Replace `except Exception: pass` with proper logging
3. Verify history is injected into agent context

### Files to Change
- `core/agent.py` — fix parameter name + add logging

---

## P1-1: DIRECT TOOL EXECUTION BYPASS

### Status: CONFIRMED (same root cause as P0-2) ✅

### Trace
```
panel_server.py L709:
  tool_result = _DISPATCH[tool_name](**tool_args)
  → No approval check

core/agent.py L130:
  result = DISPATCH[name](**args)
  → No approval check
```

### Root Cause
Same as P0-2. Two entry points for tool execution, neither checks approval.

### Fix Required
Centralize approval check in DISPATCH or _execute_tool().

---

## P1-2: PANEL API SECURITY

### Status: CONFIRMED ✅

### Endpoints (35 total)
| Endpoint | Method | State-Changing? | Auth? |
|----------|--------|----------------|-------|
| `/` | GET | No | No |
| `/api/health` | GET | No | No |
| `/api/git` | POST | YES (git ops) | No |
| `/api/durdur` | POST | YES (stop) | No |
| `/api/devam` | POST | YES (resume) | No |
| `/api/kapat` | POST | YES (shutdown) | No |
| `/api/chat` | POST | YES (chat) | No |
| `/api/upload` | POST | YES (file write) | No |
| `/api/chat/attach` | POST | YES (file upload) | No |
| `/api/chat/clear` | POST | YES (delete history) | No |
| `/api/chat/tasks/<id>/pause` | POST | YES (task control) | No |
| `/api/chat/tasks/<id>/resume` | POST | YES (task control) | No |
| `/api/chat/tasks/<id>/cancel` | POST | YES (task control) | No |
| SocketIO `chat_message` | event | YES (chat) | No |
| SocketIO `pause_task` | event | YES (task) | No |
| SocketIO `resume_task` | event | YES (task) | No |
| SocketIO `cancel_task` | event | YES (task) | No |

### Root Cause
- No authentication/authorization on any endpoint
- Port 5001 published to 0.0.0.0 (all interfaces)
- Docker: `ports: "5001:5001"` — network accessible

### Risk Assessment
- **LOCALHOST ONLY:** If Docker Desktop restricts to localhost, risk is LOW
- **NETWORK EXPOSED:** If port 5001 is accessible from network, risk is HIGH
- State-changing endpoints (git, kapat, durdur) are most dangerous

### Fix Required (Minimal)
- Add `UMAY_SECRET_KEY` check on state-changing endpoints
- Or restrict Docker to localhost: `ports: "127.0.0.1:5001:5001"`

---

## P1-3: DOUBLE PROVIDER ARCHITECTURE

### Status: CONFIRMED ✅

### Two Paths
```
Path A (Provider Abstraction):
  chat() → _get_provider_and_model() → provider.chat()
  → OpenAICompatibleProvider or OllamaProvider

Path B (Direct Ollama):
  chat() exception handler → resolve_model() → _post_json("/api/chat")
  → Direct HTTP to Ollama
```

### Root Cause
- `chat()` in engine.py has primary path (provider abstraction) + fallback path (direct Ollama HTTP)
- `_post_json()` at L135 bypasses provider abstraction
- Fallback is used when primary provider fails

### Impact
- Dual architecture means two code paths to maintain
- Provider abstraction may not be exercised if fallback always triggers
- But this is BY DESIGN — fallback is intentional safety net

### Fix Required
- Minimal: Ensure primary path works correctly when provider is configured
- Do NOT remove fallback — it's a safety mechanism
- Future: Consider unified path

---

## P1-4: TASK EXECUTOR LIFECYCLE

### Status: NO CRITICAL BUG FOUND ✅

### Functions Verified
- `pause(task_id)` — sets pause_event ✅
- `resume(task_id)` — sets resume_event ✅
- `cancel(task_id)` — sets cancel_flag ✅
- `_cleanup(task_id)` — removes from registry ✅
- `wait_for_completion(task_id, timeout)` — blocks with timeout ✅
- `check_cancel(task_id)` — checks cancel_flag ✅
- `check_pause(task_id)` — checks pause_event ✅

### Potential Race Condition
- completion_event.set() + _cleanup() — if wait_for_completion returns before cleanup
- But cleanup is called AFTER wait returns, so this is safe

### No Fix Required
- Existing implementation is sound
- Pause/resume/cancel mechanism works correctly

---

## CONFIRMED ROOT CAUSES SUMMARY

| ID | Issue | Severity | Root Cause | Fix Complexity |
|----|-------|----------|-----------|----------------|
| P0-1 | ONLINE mode always Ollama | P0 | mode not passed to provider resolution | Medium |
| P0-2 | No approval in chat tool execution | P0 | No approval gate in _execute_tool() | Medium |
| P0-3 | Vision always Ollama | P0 | resolve_model() is Ollama-only | Medium |
| P0-4 | Agent history always empty | P0 | Parameter mismatch + silent exception | Low |
| P1-1 | Direct tool bypass (same as P0-2) | P1 | Same as P0-2 | Medium |
| P1-2 | No auth on API endpoints | P1 | No auth layer | Low |
| P1-3 | Dual provider architecture | P1 | By design (fallback) | Info only |
| P1-4 | Task executor lifecycle | P1 | No bug found | None |

---

## CHANGE PLAN

### Phase A: P0-4 (Low risk, high impact)
1. `core/agent.py` L268: `limit=10` → `max_pairs=10`
2. `core/agent.py` L274: `except Exception: pass` → log error
3. Test: agent history injection

### Phase B: P0-1 + P0-3 (Medium risk, high impact)
1. `core/engine.py`: Add `mode` param to `_get_provider_and_model()`
2. `ui/panel_server.py`: Pass `mode` to `umay_chat()`
3. `engine.py chat()`: Thread `mode` through
4. `docker-compose.yml`: Add provider env vars
5. Test: LOCAL/ONLINE/AUTO routing

### Phase C: P0-2 + P1-1 (Medium risk, critical security)
1. `core/agent.py`: Add approval check in `_execute_tool()` for medium/high risk tools
2. `ui/panel_server.py`: Add approval check in direct dispatch
3. Test: approval flow for write_file, run_command

### Phase D: P1-2 (Low risk, security hardening)
1. `docker-compose.yml`: Change `ports: "5001:5001"` → `"127.0.0.1:5001:5001"`
2. Test: endpoint accessibility

### NOT CHANGING
- P1-3: Dual provider architecture (by design, fallback is safety net)
- P1-4: Task executor lifecycle (no bug found)

---

## TESTS TO ADD

1. P0-1: ONLINE mode uses correct provider (mock test)
2. P0-2: Approval check blocks unauthorized tool execution
3. P0-3: ONLINE + image uses provider abstraction
4. P0-4: Agent history is loaded correctly
5. P1-2: State-changing endpoints require auth

## RISKS

1. P0-1 fix: If PRIMARY_PROVIDER not configured, ONLINE falls back to Ollama (expected)
2. P0-2 fix: Approval check may block legitimate tool calls (need risk levels)
3. P0-3 fix: Vision provider selection depends on P0-1 fix
4. P0-4 fix: Low risk — parameter name change only

## REGRESSION PLAN

- All 564 existing tests must pass
- New tests added for each fix
- E2E test with real chat endpoint
- Docker rebuild + health check

## LOG FILE
docs/development/logs/STEP-02.1_CRITICAL_FIXES_AUDIT.md

## STATUS
**READY FOR IMPLEMENTATION**
