# 31 — VERI AKISI

Chat: User -> /api/chat -> router -> engine -> Ollama -> response
Tool: engine(tools) -> model tool_call -> DISPATCH -> result -> model
Memory: learn -> ChromaDB -> store; recall -> search -> context -> model
Upload: /api/upload -> validate -> storage
Archive: entry -> dual library
Browser: /api/git -> BrowserAgent -> screenshot -> analiz -> panel
