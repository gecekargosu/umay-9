# 06 — TOOL CALLING

55 tool (agent_tools.py, 1105 satir)
Kategoriler: Dosya(~10), Web(~5), Kod(~5), Terminal(~3), Memory(~3), Gmail(~5), Browser(~5), Belge(~3), Gorsel(~2), Sistem(~3)

Zincir: engine.chat(tools) -> model tool_call -> DISPATCH[func](**args) -> result -> model -> final
Permission: chat_api'de YOK, orchestrator'da var
