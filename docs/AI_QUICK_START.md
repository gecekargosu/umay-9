# UMAY 9 — AI QUICK START

> Bu dosya gelecek AI oturumlarının ilk okuması gereken merkezi belgedir.
> Tüm codebase'i baştan okumaya gerek yok — bu dosya + ilgili dosyalar yeterli.

---

## UMAY 9 Nedir?
Kişisel yapay zeka işletim sistemi. Ollama tabanlı local LLM, Docker container, web panel, Telegram entegrasyonu.

## Çalışan Sistemler (Doğrulanmış)
- ✅ Web panel (Flask + SocketIO, port 5001)
- ✅ Ollama LLM engine (multi-provider fallback)
- ✅ Tool calling (55 tool, agent loop)
- ✅ Conversation persistence (SQLite)
- ✅ Task state persistence (JSONL)
- ✅ Token budget estimation + context compression + failure recovery
- ✅ Approval manager (JSONL persisted, channel-agnostic)
- ✅ Communication manager (channel-agnostic messaging hub)
- ✅ Telegram Bot API adapter (polling, approval, commands, media)
- ✅ Telegram User Account adapter (Telethon MTProto)
- ✅ Background worker + scheduler
- ✅ Browser agent (Playwright/Chromium)
- ✅ Attachment engine (PDF/DOCX/XLSX/image)

## Durum: STEP-05 COMPLETE + TELEGRAM AKTİF + TOOLS EKLENDİ
- **564 tests passing, 0 failures**
- Docker container healthy on port 5001
- **Telegram User Account: BAĞLI** (User Account connected)
- **Dosya/Klasör Açma Tool'ları: EKLENDİ** (open_file, open_folder, open_url, open_with_app)

## Uncommitted Changes (all tested, ready to commit)
```
M  ui/panel_server.py              ← STEP-05 sync chat fix (wait_for_completion)
M  core/task_executor.py           ← wait_for_completion + completion_event
M  core/agent_tools.py             ← open_file/folder/url tool definitions
M  core/terminal_agent.py          ← open_file/folder/url implementations
M  docker-compose.yml              ← telegram session bind mount fix
M  tests/test_step05_task_executor.py
M  tests/test_mixed_attachment_fix.py
M  tests/test_token_budget_integration.py
M  docs/development/CHAT_CHECKPOINT.md
M  docs/development/CHAT_PROGRESS.md
?? core/task_executor.py
?? docs/AI_QUICK_START.md
?? docs/development/UMAY9_FULL_AUDIT_2026-08-22.md
?? docs/development/STEP05_TELEGRAM_MIMO_BROWSER_2026-08-22.md
?? scripts/kariyer_net_workflow.py
?? tests/test_step05_task_executor.py
```

## Dosya Haritası (En Sık Kullanılacaklar)
```
ui/panel_server.py         → Web UI + API (1070 lines)
core/engine.py             → LLM engine
core/agent.py              → Autonomous agent with tool loop
core/task_state.py         → Task persistence (JSONL)
core/task_executor.py      → Background executor (UNCOMMITTED)
core/conversation_store.py → Chat history (SQLite)
core/token_budget.py       → Token estimation
core/context_compression.py → Context compression
core/failure_recovery.py   → Retry + recovery
core/approval_manager.py   → Approval state machine
core/communication_manager.py → Channel-agnostic messaging
core/telegram_adapter.py   → Telegram Bot adapter
core/telegram_user_adapter.py → Telegram User adapter
core/attachment_engine.py  → File processing
```

## Git Durumu
- Branch: `main`
- 2 commits total
- Last: `5ec4fdd` (2026-08-22 15:08)
- Uncommitted: STEP-05 + Telegram fix + Tools + Browser workflow

## Test Durumu
- **Current:** 564 passed, 0 failed, 1 skipped
- **Docker container:** Healthy on port 5001
- **STEP-04 features preserved:** token budget, compression, recovery, attachments, vision, tools

## Telegram Durumu
- ✅ **User Account: BAĞLI** (User Account connected)
- ❌ Bot API: Token yok (opsiyonel)
- Session: `telegram_user_sessions/umay_user.session`
- API: Set in `.env` (see `.env.example` for required variables)
- Container'da bind mount: `./telegram_user_sessions:/run/umay/telegram`

## Dosya/Klasör Açma Tool'ları (YENİ)
- `open_file(path)` — varsayılan uygulama ile dosya aç
- `open_folder(path)` — dosya yöneticisinde klasör aç
- `open_url(url)` — tarayıcıda URL aç
- `open_with_app(app, path)` — belirli uygulama ile aç

## Browser Durumu
- ✅ Playwright/Chromium çalışıyor
- ✅ LinkedIn erişilebilir (login sayfası)
- ⚠️ Kariyer.net CAPTCHA engeli var
- Workflow scripti: `scripts/kariyer_net_workflow.py`

## MiMo Durumu
- Ollama library'de henüz yok
- `OpenAICompatibleProvider` hazır — `MIMO_API_KEY` + `MIMO_BASE_URL` ile bağlanabilir
- Şu an: 11 Ollama modeli kurulu (phi4-mini, qwen3:8b, gemma3:4b, vb.)

## Sıradaki Doğru İş
1. Git commit (STEP-05 + Telegram + Tools)
2. Kariyer.net CAPTCHA çözümü (stealth plugin / non-headless)
3. LinkedIn credential tasarımı
4. STEP-06/07 (checkpoint/recovery)

## Detaylı Audit
→ `docs/development/UMAY9_FULL_AUDIT_2026-08-22.md`
→ `docs/development/STEP05_TELEGRAM_MIMO_BROWSER_2026-08-22.md`

## Development Progress
→ `docs/development/CHAT_PROGRESS.md`

## Roadmap
→ `docs/development/CHAT_ROADMAP.md`

---
*Last updated: 2026-08-22 by Buffy (AI audit)*
