# 39 — BAGIMLILIK

engine.py: requests, logger -> agent, panel_server, run_umay
agent.py: engine, agent_tools -> panel_server, telegram
agent_tools.py: ~20 modul -> agent.py
router.py: engine.resolve_model -> agent, panel_server
worker.py: bagimsiz -> panel_server
scheduler.py: bagimsiz -> panel_server
memory_bridge.py: memory_manager, rag/memory_manager -> agent_tools
panel_server.py: tum moduller -> Docker
