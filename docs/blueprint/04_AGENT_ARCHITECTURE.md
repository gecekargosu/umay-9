# 04 — AGENT

Zincir:
User -> /api/chat -> router model_sec() -> engine chat(tools) -> model -> tool_calls? -> DISPATCH -> result -> model -> response

Router: vision/reasoning/coding/analysis/agent (5 kategori)
Agent dosyalari: agent.py, agent_tools.py, engine.py, router.py, identity.py, planner.py
Tool calling: 55 tool, OpenAI function schema, dispatch map
