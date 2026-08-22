# 33 — AGENT CALISTIRMA

1. User msg -> /api/chat
2. router.model_sec() -> (model, gorev)
3. gorev agent/coding ise: engine.chat(tools=TOOLS)
4. Model tool_calls -> DISPATCH -> result -> model -> final
5. gorev chat ise: engine.chat(tools=None) -> direct response
6. Socket.IO task_status emit
7. JSON response
