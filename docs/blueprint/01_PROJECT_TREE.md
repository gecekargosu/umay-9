# 01 — PROJE AGACI

Kok: C:\UMAY 9

```
run_umay.py              (CLI giris)
ui/panel_server.py       (Flask+SocketIO, 290+ satir)
ui/templates/panel.html  (Frontend)
core/engine.py           (LLM engine)
core/router.py           (Gorev siniflandirma)
core/agent.py            (Agent loop + tool calling)
core/agent_tools.py      (55 tool, 1105 satir)
core/planner.py          (989 satir, 5 engine)
core/task_state.py       (Task lifecycle)
core/approval_manager.py (565 satir)
core/communication_manager.py (367 satir)
core/telegram_adapter.py (934 satir)
core/telegram_user_adapter.py (323 satir)
core/gmail_agent.py      (1144 satir)
core/identity.py         (84 satir)
core/model_providers.py  (250+ satir)
core/worker.py           (150+ satir)
core/scheduler.py        (250+ satir)
core/orchestrator.py     (250+ satir)
core/file_manager.py     (150+ satir)
core/archive.py          (270+ satir)
core/job_pipeline.py     (200+ satir)
core/chat.py, code_agent.py, terminal_agent.py
core/document_reader.py, vision_reader.py, web_research.py
core/audit.py, config_manager.py
core/memory/ (bridge + manager)
core/models/, system/, utils/
agents/ (browser_agent, coding_agent, gemini_agent)
rag/ (chroma_manager, memory_manager, teach_umay)
tests/ (24 dosya, 457 test)
knowledge/ (5 dosya), memory/, uploads/, profiles/
UMAY_MEMORY/, UMAY_ARCHIVE/, logs/, backup/
docs/blueprint/
docker-compose.yml, Dockerfile, requirements.txt, .env, .env.example
```
