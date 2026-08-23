# STEP-02.2 IMPLEMENTATION PLAN

## Timestamp
2026-08-23

## Baseline
- Tests: 564 PASS, 1 SKIP, 0 FAIL
- Docker: healthy
- Git: 639e0fc, clean

## Implementation Order
1. P0-4 (lowest risk, highest clarity)
2. P0-1 + P0-3 (medium risk, mode routing)
3. P0-2 + P1-1 (medium risk, security critical)
4. P1-2 (low risk, security hardening)

---

## FIX 1: P0-4 — Conversation History TypeError

### Problem
`agent.py` L268: `_conv.get_history(session_id, limit=10)`
`conversation_store.py` L105: `def get_history(conversation_id, max_pairs=DEFAULT_MAX_PAIRS)`

`limit=` keyword not accepted → TypeError → silently swallowed by `except Exception: pass`

### Exact Changes

**File: `core/agent.py`**

**Change 1a — L268:** Fix parameter name
```
BEFORE: raw_history = _conv.get_history(session_id, limit=10)
AFTER:  raw_history = _conv.get_history(session_id, max_pairs=10)
```

**Change 1b — L274-275:** Add logging instead of silent pass
```
BEFORE:
        except Exception:
            pass

AFTER:
        except Exception as exc:
            from core.utils.logger import log
            log(f"[AGENT] Conversation history okunamadı: {exc}")
```

### Risk: LOW
- Parameter name change only
- Backward compatible (panel_server.py already uses `max_pairs=`)
- No architectural change

### Tests
1. **Unit test:** `get_history(session_id, max_pairs=10)` returns correct format
2. **Regression:** 564 existing tests pass
3. **E2E:** Agent with conversation context remembers previous messages

### Regression Criteria
- 564 PASS maintained
- No TypeError in agent path
- History returns list of {role, content} dicts

### Rollback
- Revert L268 to `limit=10`
- Revert L274-275 to `except Exception: pass`

---

## FIX 2: P0-1 + P0-3 — ONLINE Provider/Model + Vision Routing

### Problem
1. `mode` parameter not passed to `umay_chat()` or `_get_provider_and_model()`
2. `PRIMARY_PROVIDER` defaults to "OLLAMA"
3. `resolve_model()` always returns Ollama model name
4. Vision routing uses `resolve_model("vision")` — always Ollama

### Exact Changes

**File: `core/engine.py`**

**Change 2a — L101:** Add `mode` parameter to `_get_provider_and_model()`
```
BEFORE:
def _get_provider_and_model(task: str, requested_model: str | None = None):

AFTER:
def _get_provider_and_model(task: str, requested_model: str | None = None, mode: str = "auto"):
```

**Change 2b — L122-125:** Add mode-aware provider selection
```
BEFORE:
    # Check primary provider
    primary = get_primary_provider()
    if primary.is_available():
        return primary, requested_model

AFTER:
    # MODE-AWARE provider selection
    if mode == "local":
        # LOCAL: always use Ollama regardless of PRIMARY_PROVIDER
        ollama = OllamaProvider()
        if ollama.is_available():
            return ollama, requested_model
    elif mode == "online":
        # ONLINE: prefer configured cloud provider
        primary = get_primary_provider()
        if primary.name != "ollama" and primary.is_available():
            return primary, requested_model
        # Cloud not available — fall through to Ollama
    
    # AUTO or fallback: use primary provider
    primary = get_primary_provider()
    if primary.is_available():
        return primary, requested_model
```

**Change 2c — L184-L191:** Add `mode` parameter to `chat()`
```
BEFORE:
def chat(
    messages: list[dict],
    model: str | None = None,
    ajan: str = "umay",
    task: str = "chat",
    tools: list[dict] | None = None,
    raw: bool = False,
) -> str | dict:

AFTER:
def chat(
    messages: list[dict],
    model: str | None = None,
    ajan: str = "umay",
    task: str = "chat",
    tools: list[dict] | None = None,
    raw: bool = False,
    mode: str = "auto",
) -> str | dict:
```

**Change 2d — L210:** Pass mode to provider resolution
```
BEFORE:
        provider, resolved_model = _get_provider_and_model(task, model)

AFTER:
        provider, resolved_model = _get_provider_and_model(task, model, mode=mode)
```

**File: `ui/panel_server.py`**

**Change 2e — L887:** Pass mode to umay_chat
```
BEFORE:
            result = umay_chat(messages, model=model, tools=active_tools if use_tools else None)

AFTER:
            result = umay_chat(messages, model=model, tools=active_tools if use_tools else None, mode=mode)
```

**Change 2f — L524:** Mode-aware vision routing
```
BEFORE:
            vision_model = resolve_model("vision")

AFTER:
            vision_model = resolve_model("vision")
            # If ONLINE mode and cloud provider available, use cloud vision
            if mode == "online":
                from core.model_providers import get_primary_provider
                primary = get_primary_provider()
                if primary.name != "ollama" and primary.is_available():
                    vision_model = None  # Let provider handle vision
```

### Risk: MEDIUM
- Provider routing changes affect all modes
- LOCAL mode must NOT be affected (forced Ollama)
- Fallback to Ollama when cloud unavailable

### Tests
1. **LOCAL + text:** Ollama provider selected
2. **ONLINE + text:** Cloud provider selected (if configured)
3. **ONLINE + no provider:** Falls back to Ollama
4. **AUTO + text:** Primary provider selected
5. **Vision LOCAL:** Ollama vision model
6. **Vision ONLINE:** Cloud vision (if available)
7. **Regression:** 564 tests pass

### Regression Criteria
- LOCAL mode behavior unchanged
- AUTO mode behavior unchanged (when PRIMARY_PROVIDER=OLLAMA)
- Fallback works when cloud unavailable

### Rollback
- Revert all changes to `engine.py` and `panel_server.py`

---

## FIX 3: P0-2 + P1-1 — Approval Gate

### Problem
`_execute_tool()` in `core/agent.py` calls `DISPATCH[name](**args)` directly without approval.
`_DISPATCH[tool_name](**tool_args)` in `panel_server.py` also bypasses approval.
`ApprovalManager` exists with `needs_approval()`, `request_approval()`, `approve()`, `reject()` but is only wired to Telegram.

### Exact Changes

**File: `core/agent.py`**

**Change 3a — L124-L136:** Add approval check in `_execute_tool()`
```
BEFORE:
def _execute_tool(call: dict) -> tuple[dict, dict]:
    call=_normalize_tool_call(call)
    fn=call.get("function") or {}; name=fn.get("name"); args=fn.get("arguments") or {}
    if name not in DISPATCH: return call,{"error":f"Bilinmeyen tool: {name}"}
    try:
        print(f"[UMAY AI][EL] {name}({json.dumps(args, ensure_ascii=False)})")
        result=DISPATCH[name](**args)
        ...

AFTER:
def _execute_tool(call: dict, task_id: str | None = None) -> tuple[dict, dict]:
    call=_normalize_tool_call(call)
    fn=call.get("function") or {}; name=fn.get("name"); args=fn.get("arguments") or {}
    if name not in DISPATCH: return call,{"error":f"Bilinmeyen tool: {name}"}
    
    # APPROVAL GATE: Check if tool needs approval
    try:
        from core.approval_manager import needs_approval, get_tool_risk, request_approval
        if needs_approval(name):
            risk = get_tool_risk(name)
            if risk in ("high", "medium"):
                # Create approval request — tool execution pauses until approved
                if task_id:
                    req = request_approval(
                        task_id=task_id,
                        tool_name=name,
                        action=f"{name}({json.dumps(args, ensure_ascii=False)[:200]})",
                        risk=risk,
                    )
                    return call, {"error": f"Onay bekleniyor: {name}", "approval_id": req.approval_id, "status": "WAITING_FOR_APPROVAL"}
                else:
                    return call, {"error": f"Onay gerektiriyor ama task_id yok: {name}"}
    except ImportError:
        pass  # Approval manager not available — allow execution
    
    try:
        print(f"[UMAY AI][EL] {name}({json.dumps(args, ensure_ascii=False)})")
        result=DISPATCH[name](**args)
        ...
```

**Change 3b — L156-L163:** Pass task_id to `_execute_tool()`
```
BEFORE:
def _tool_messages(tool_calls: list[dict]) -> list[dict]:
    messages=[]
    for call in tool_calls:
        call,result=_execute_tool(call)
        ...

AFTER:
def _tool_messages(tool_calls: list[dict], task_id: str | None = None) -> list[dict]:
    messages=[]
    for call in tool_calls:
        call,result=_execute_tool(call, task_id=task_id)
        ...
```

**File: `ui/panel_server.py`**

**Change 3c — L709:** Add approval check in direct dispatch
```
BEFORE:
                        tool_result = _DISPATCH[tool_name](**tool_args)

AFTER:
                        # APPROVAL GATE: Check if tool needs approval
                        try:
                            from core.approval_manager import needs_approval
                            if needs_approval(tool_name):
                                risk = __import__('core.approval_manager', fromlist=['get_tool_risk']).get_tool_risk(tool_name)
                                if risk in ("high", "medium"):
                                    from core.approval_manager import request_approval
                                    req = request_approval(
                                        task_id=task_id,
                                        tool_name=tool_name,
                                        action=f"{tool_name}({str(tool_args)[:200]})",
                                        risk=risk,
                                    )
                                    tool_results.append({"tool": tool_name, "result": {"error": f"Onay bekleniyor", "approval_id": req.approval_id}, "duration": 0, "status": "WAITING"})
                                    continue
                        except ImportError:
                            pass
                        tool_result = _DISPATCH[tool_name](**tool_args)
```

### Risk: MEDIUM
- Approval check may block legitimate tool calls
- Need to ensure read-only tools (LOW risk) are NOT blocked
- Telegram approval flow must not be affected
- `UMAY_MODE=auto_fix` should bypass approval for development

### Tests
1. **HIGH risk tool without approval:** Returns WAITING_FOR_APPROVAL
2. **LOW risk tool:** Executes without approval
3. **Approval granted:** Tool executes after approval
4. **Telegram approval:** Still works (no change)
5. **Regression:** 564 tests pass

### Regression Criteria
- Read-only tools (list_directory, read_file, etc.) work without approval
- Write tools (write_file, run_command) require approval
- Telegram approval flow unchanged
- `UMAY_MODE=auto_fix` bypasses approval (check existing behavior)

### Rollback
- Remove approval check from `_execute_tool()` and direct dispatch

---

## FIX 4: P1-2 — API Security

### Problem
Port 5001 published to `0.0.0.0` (all interfaces). 35 endpoints with no auth.

### Exact Changes

**File: `docker-compose.yml`**

**Change 4a — ports:** Restrict to localhost
```
BEFORE:
    ports:
      - "5001:5001"

AFTER:
    ports:
      - "127.0.0.1:5001:5001"
```

### Risk: LOW
- Localhost only — Docker Desktop standard behavior
- External access blocked at Docker level
- No code changes
- Backward compatible for local development

### Tests
1. **Localhost access:** http://localhost:5001 works
2. **External access:** Blocked (if testing from another machine)
3. **Docker health:** Still healthy
4. **Regression:** 564 tests pass

### Regression Criteria
- Local development workflow unchanged
- Docker health check passes
- Panel accessible at localhost:5001

### Rollback
- Revert ports to `"5001:5001"`

---

## TEST PLAN SUMMARY

### P0-4 Tests
| Test | Input | Expected | Path |
|------|-------|----------|------|
| History loads | session with messages | list of {role, content} | agent.py |
| No TypeError | any session | no exception | agent.py |
| Empty history | new session | empty list | agent.py |

### P0-1 Tests
| Test | Mode | Provider | Expected |
|------|------|----------|----------|
| LOCAL text | local | Ollama | OllamaProvider |
| ONLINE text | online | Cloud | OpenAICompatibleProvider |
| ONLINE no cloud | online | None | OllamaProvider (fallback) |
| AUTO text | auto | Primary |取决于 PRIMARY_PROVIDER |

### P0-3 Tests
| Test | Mode | Image | Expected |
|------|------|-------|----------|
| LOCAL vision | local | Yes | Ollama vision |
| ONLINE vision | online | Yes | Cloud vision (if available) |

### P0-2 Tests
| Test | Tool | Risk | Approval | Expected |
|------|------|------|----------|----------|
| write_file | write_file | medium | No | WAITING |
| list_directory | list_directory | low | No | Executes |
| run_command | run_command | high | No | WAITING |

### P1-2 Tests
| Test | URL | Expected |
|------|-----|----------|
| localhost | http://localhost:5001 | 200 OK |
| health | http://localhost:5001/api/health | ok |

---

## IMPLEMENTATION SEQUENCE

```
FIX 1 (P0-4)
  ↓
  Unit test → Regression → Docker → E2E → Git checkpoint
  ↓
FIX 2 (P0-1 + P0-3)
  ↓
  Unit test → Integration test → Regression → Docker → E2E → Git checkpoint
  ↓
FIX 3 (P0-2 + P1-1)
  ↓
  Unit test → Integration test → Regression → Docker → E2E → Git checkpoint
  ↓
FIX 4 (P1-2)
  ↓
  Docker test → Regression → Git checkpoint
  ↓
FINAL REGRESSION → 564 PASS → COMMIT → PUSH
```

## STATUS
**READY FOR IMPLEMENTATION**

## RISKS
1. FIX 2: If PRIMARY_PROVIDER not configured, ONLINE falls back to Ollama (expected)
2. FIX 3: Approval check may block legitimate tool calls in auto_fix mode
3. FIX 4: Localhost restriction may affect Docker Desktop networking

## REGRESSION PLAN
- After each fix: `python -m pytest -q`
- After all fixes: full suite + Docker E2E
- Final baseline must be ≥ 564 PASS
