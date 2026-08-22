# 20 — STREAMING

Durum: PARTIAL
Olan: task_status Socket.IO events (thinking, calling_model, tool_running, completed)
Olmayan: Token-by-token streaming (SSE/WebSocket)
Neden: engine.chat() stream=False, SSE endpoint yok
