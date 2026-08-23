# FAZ 2 — CHECKPOINT: CORE / CHAT / ROUTING HARDENING
**Date:** 2026-08-23 14:45
**Status:** ✅ COMPLETE

---

## OBJECTIVE
UMAY'ın ana çalışma zincirini doğrula: Chat → Intent → Model → Tool → Response

## E2E TEST RESULTS (10/10 PASS)

| # | Test | Intent | Model | Latency | Result |
|---|------|--------|-------|---------|--------|
| 1 | Merhaba | chat | phi4-mini | 12.09s | ✅ Natural response |
| 2 | Sen kimsin? | chat | phi4-mini | 3.0s | ✅ "Ben UMAY'ım" |
| 3 | Saat kac? | time | direct | 0.36s | ✅ Real time |
| 4 | Bugun gunlerden ne? | time | direct | 0.45s | ✅ Real date |
| 5 | 9*8+7 kac? | calculator | direct | 0.41s | ✅ 79 |
| 6 | Masaustunu listele | file | direct | 0.59s | ✅ 69 real files |
| 7 | Belgeleri listele | file | direct | 0.5s | ✅ 6 items |
| 8 | BMW mi Mercedes mi? | chat | phi4-mini | 13.6s | ✅ Natural response |
| 9 | 3+5*2 kac? | calculator | direct | 0.45s | ✅ 13 |
| 10 | Indirilenler klasorunu listele | file | direct | 2.63s | ✅ 603 files |

## MODE ROUTING VERIFICATION (5/5 PASS)

| Mode | Test | Result |
|------|------|--------|
| LOCAL + Saat kac? | direct, time | ✅ |
| LOCAL + 9*8+7 | direct, calculator | ✅ |
| LOCAL + Masaustunu listele | direct, file | ✅ |
| ONLINE + Merhaba | phi4-mini, chat | ✅ |
| AUTO + Calculator | direct, calculator | ✅ |

## INTENT ROUTER REGRESSION (14/15 PASS)

| Message | Expected | Actual | Status |
|---------|----------|--------|--------|
| Merhaba | chat | chat | ✅ |
| Selam | chat | chat | ✅ |
| Sen kimsin? | chat | chat | ✅ |
| Saat kac? | time | time | ✅ |
| Bugun gunlerden ne? | time | time | ✅ |
| 9*8+7 kac? | calculator | calculator | ✅ |
| 3+5 | calculator | calculator | ✅ |
| Masaustunu listele | file | file | ✅ |
| Belgeleri listele | file | file | ✅ |
| Indirilenler klasorunu listele | file | file | ✅ |
| PDF oku | document | document | ✅ |
| Bu resimde ne var? | vision | vision | ✅ |
| Internette ara | web | web | ✅ |
| Kod yaz | code | code | ✅ |
| Komut calistir | terminal | code | ⚠️ |

**Note:** "Komut calistir" → CODE instead of TERMINAL (keyword overlap with "calistir")

## TOOL CALLING VERIFICATION (6/6 PASS)

| Tool | Args | Result |
|------|------|--------|
| get_current_time | timezone=Europe/Istanbul | ✅ Real time |
| get_current_date | {} | ✅ Real date |
| evaluate_expression | 9*8+7 | ✅ 79 |
| evaluate_expression | 3+5*2 | ✅ 13 |
| list_directory | path=. | ✅ 60 items |
| get_system_info | {} | ✅ OS info |

## CONVERSATION HISTORY

- History API returns messages correctly
- Session persistence works
- Context maintained across messages

## ERROR HANDLING

- Empty message → "Soru bos" error ✅
- Invalid path → Falls back to LLM gracefully ✅
- Tool failure → Per-tool try/except, other tools continue ✅

## REGRESSION TEST

```
564 passed, 1 skipped, 0 failed ✅
(Baseline maintained)
```

## DOCKER E2E

- Health: OK ✅
- Container intent tests: 5/5 PASS ✅

## FILES CHANGED

None (audit + verification only)

## KNOWN LIMITATIONS

1. "Komut calistir" intent classification: CODE vs TERMINAL overlap
2. History API returns `messages` not `history` (frontend uses correct key)
3. 14/15 intent classification (minor keyword overlap)

## BACKLOG

- PROBLEM-001 (Memory empty) → FAZ 5
- PROBLEM-002 (Logs empty) → FAZ 2 (logging hardening)
- PROBLEM-003 (Tasks placeholder) → FAZ 7

## NEXT STEP

**FAZ 3 — TOOL & EXECUTION HARDENING**
