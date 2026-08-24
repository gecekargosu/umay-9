# UMAY 9 — TEST BASELINE

**Tarih:** 2026-08-24
**Commit:** dba0078
**Branch:** main

## ÖZET

| Metrik | Değer |
|--------|-------|
| **Toplam Test** | 565 |
| **PASS** | 564 |
| **SKIP** | 0 |
| **FAIL** | 0 |
| **ENV DEPENDENT** | 1 |

## TEST SINIFLANDIRMASI

### Unit Tests
- test_agent_tools.py (1)
- test_terminal_agent.py (12)
- test_task_state.py (12)
- test_token_budget.py (27)
- test_agent_path_parser.py (5)
- test_conversation_store.py (11)
- test_document_reader.py (13)
- test_code_agent.py (44)
- test_approval.py (17)
- test_planner.py (8)
- test_telegram_adapter.py (24)
- test_telegram_user_adapter.py (15)
- test_new_modules.py (48)

### Integration Tests
- test_step05_task_executor.py (24)
- test_panel_endpoints.py (12)
- test_safety_and_audit.py (3)
- test_context_compression.py (8)
- test_mixed_attachment_fix.py (5)

### Simulation Tests
- test_phase3_ollama_simulation.py (1)
- test_phase3_agent_loop_simulation.py (1)
- test_real_ollama_verifier_contract.py (1)

### Tool/Feature Tests
- test_gmail_agent.py (5)
- test_failure_recovery.py (10)
- test_browser_agent.py (8)
- test_tool_loop_serialization.py (10)
- test_vision_reader.py (33)
- test_web_research.py (59)
- test_worker_scheduler.py (13)
- test_token_budget_integration.py (7)

### Network/External (ENV DEPENDENT)
- test_real_web_research.py — timeout (DuckDuckGo network dependency)

## ENVIRONMENT DEPENDENCY

### test_real_web_research.py
- **Durum:** TIMEOUT
- **Neden:** Gerçek DuckDuckGo API çağrısı — network latency
- **Bug:** HAYIR — environment kaynaklı
- **Çözüm:** CI'da mock kullanılmalı veya network timeout artırılmalı

## KNOWN ISSUES

1. test_real_web_research.py — network timeout (environment)
2. Bazı testler 120s+ sürebilir (Ollama/LLM testleri)
3. Docker container testleri sadece Docker ortamında çalışır
