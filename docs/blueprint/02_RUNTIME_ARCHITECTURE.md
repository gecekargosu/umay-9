# 02 — RUNTIME

Host -> Docker -> umay-agent (umay9-umay:latest)
  Flask+SocketIO (0.0.0.0:5001)
  Worker (daemon), Scheduler (daemon)
  Screenshot sender, Log sender, Telegram status
  Playwright/Chromium

Port: 5001, 11434 (Ollama)
Health: curl http://localhost:5001/api/health
Startup: load_dotenv -> Flask -> SocketIO -> threads -> worker -> scheduler -> serve
