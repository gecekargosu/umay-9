# Run Doc — UMAY 9 Panel Preview

## Uncommitted Artifacts

No uncommitted artifacts needed. The panel server serves directly from committed source files:
- `ui/panel_server.py` (Flask + SocketIO server)
- `ui/templates/panel.html` (Dashboard HTML)
- `core/` (backend modules)

## Prerequisites

- Python 3.13+ with dependencies from `requirements.txt` installed
- Ollama running on `localhost:11434` (for full functionality; panel loads without it)
- Port 5001 must be free

## How to Run the Server

1. If Docker container `umay-agent` is running, stop it first:
   ```
   docker stop umay-agent
   ```

2. Start the native panel server from the project root:
   ```
   cd "C:\UMAY 9"
   python -m ui.panel_server
   ```

3. The server starts on `http://localhost:5001`

4. Health check:
   ```
   curl http://localhost:5001/api/health
   ```
   Expected: `{"service":"umay-panel","status":"ok"}`

## Notes

- Port 5001 is hardcoded in `ui/panel_server.py` line 1726
- SocketIO CORS origins are hardcoded to `localhost:5001` and `127.0.0.1:5001`
- Docker and native server cannot share port 5001 simultaneously
- The native server uses `UMAY_MODE=auto_fix` by default (no approval gates)
