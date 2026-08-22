# 03 — MODULLER

CORE: engine, router, agent, agent_tools, planner, task_state, identity
PROVIDERS: model_providers, engine (Ollama), gemini_agent
AGENTS: browser_agent, coding_agent, gmail_agent, terminal_agent, code_agent, vision_reader
COMMUNICATION: telegram_adapter, telegram_user_adapter, communication_manager, approval_manager
MEMORY: memory_bridge, memory_manager, chroma_manager, rag/memory_manager
TOOLS: agent_tools (55 tool + dispatch)
WORKER: worker, scheduler
FILE: file_manager, archive, document_reader, job_pipeline
RESEARCH: web_research, orchestrator
UI: panel_server, templates/panel.html
INFRA: docker-compose.yml, Dockerfile, requirements.txt, .env

Bagimliliklar:
engine <- agent <- agent_tools <- tool'lar
router <- engine, model_providers <- engine
memory_bridge <- memory_manager + rag/memory_manager
panel_server <- agent + engine + router + agent_tools + worker + scheduler
worker <- bagimsiz, scheduler <- bagimsiz
