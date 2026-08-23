# FAZ 4 — CHECKPOINT
**Date:** 2026-08-23
**Checkpoint:** UMAY-V2-PHASE-04-001
**Status:** ✅ COMPLETE

---

## What Changed

### 1. Model/Mode Forwarding (`ui/panel_server.py` + `core/task_executor.py`)
- Frontend now sends `model` and `mode` to `/api/chat`
- Backend forwards to `execute_chat_task` via `**kwargs`
- Response includes `mode` field

### 2. Direct Tool Execution Fix (`ui/panel_server.py`)
- **TIME**: `get_current_time(timezone="Europe/Istanbul")` — proper timezone
- **CALCULATOR**: Math expression extraction from Turkish messages + `evaluate_expression()`
- **FILE/DOCUMENT**: Per-tool error handling — one tool failing doesn't kill the whole block
- **Vision path priority**: `has_image` check now skips direct tool execution

### 3. Panel Readability (`ui/templates/panel.html`)
- Font: 13px → 14px
- Line height: 1.5 → 1.6

### 4. Calculator Tool (`core/agent_tools.py`)
- `evaluate_expression(expression)` — AST-based calculator
- Registered in TOOLS list and DISPATCH dict

### 5. Intent Router Enhancement (`core/intent_router.py`)
- CALCULATOR intent with math regex
- TIME intent with expanded keywords

---

## E2E Test Results (Docker Container)

| Test | Intent | Model | Latency | Result |
|------|--------|-------|---------|--------|
| Merhaba | chat | phi4-mini | 14.48s | ✅ Natural response |
| Saat kac? | time | direct | 0.21s | ✅ Real time (09:45:35) |
| 9*8+7 kac? | calculator | direct | 0.03s | ✅ 9*8+7 = 79 |
| Bugun gunlerden ne? | time | direct | 0.02s | ✅ Real date (Pazar, 23 Ağustos 2026) |

### Before vs After

| Test | Before (FAZ3) | After (FAZ4) |
|------|---------------|--------------|
| Saat kac? | LLM + get_system_info() ❌ | direct get_current_time() ✅ |
| 9*8 kac? | LLM 27s ⚠️ | direct evaluate_expression() 0.03s ✅ |
| Bugun gunlerden ne? | LLM + get_system_info() ❌ | direct get_current_date() ✅ |
| Mixed image+PDF | Vision bug (test fail) ❌ | Fixed (test pass) ✅ |

---

## Test Suite
```
564 passed, 1 skipped, 0 failed ✅
```

---

## Files Changed

| File | Lines Changed |
|------|---------------|
| `ui/panel_server.py` | +35 (mode forwarding, TIME/CALCULATOR args, per-tool error handling, vision priority) |
| `core/task_executor.py` | +2 (kwargs forwarding) |
| `core/agent_tools.py` | +30 (calculator tool, TIME_TOOLS) |
| `core/intent_router.py` | +15 (CALCULATOR intent, expanded TIME) |
| `ui/templates/panel.html` | +5 (font size) |

---

## Known Limitations

1. **Web research timeout**: Full research pipeline is slow (>2min) for complex topics
2. **Mode switching**: AUTO/LOCAL/ONLINE modes are UI-only — backend always uses same logic
3. **File listing**: "Masaustundeki dosyalari listele" routes to LLM (no Windows path regex match)

---

## Next Phase

FAZ 5: Task/Autonomy System — long-running tasks with progress tracking
