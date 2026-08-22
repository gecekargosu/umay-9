"""Tests for STEP-04.3: Token budget integration into chat pipeline.

Verifies:
- Pre-flight budget estimation fires SocketIO event on large contexts
- Real token usage extracted from Ollama responses (prompt_eval_count/eval_count)
- Usage passthrough via engine.chat() → chat_api() → JSON response
- Vision branch also extracts usage from direct Ollama call
"""
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


# ---------------------------------------------------------------------------
# Fake Ollama server that returns real usage fields
# ---------------------------------------------------------------------------

class _UsageOllamaHandler(BaseHTTPRequestHandler):
    """Fake Ollama that returns prompt_eval_count / eval_count in response."""

    received_bodies: list = []
    _usage_input = 150
    _usage_output = 80

    def _send(self, payload):
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/tags":
            self._send({"models": [{"name": "phi4-mini:latest"}]})
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        _UsageOllamaHandler.received_bodies.append(body)
        self._send({
            "message": {"role": "assistant", "content": "test response"},
            "prompt_eval_count": self._usage_input,
            "eval_count": self._usage_output,
        })

    def log_message(self, *_args):
        pass


@pytest.fixture
def fake_ollama_with_usage(monkeypatch):
    """Start fake Ollama that returns real usage data."""
    _UsageOllamaHandler.received_bodies = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _UsageOllamaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    import core.engine as engine
    monkeypatch.setattr(engine, "OLLAMA_URL", f"http://127.0.0.1:{server.server_port}")
    yield _UsageOllamaHandler
    server.shutdown()
    server.server_close()


@pytest.fixture
def session_id():
    return f"budget-test-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Tests: OllamaProvider returns usage
# ---------------------------------------------------------------------------

class TestOllamaProviderUsage:
    def test_ollama_provider_returns_usage(self, fake_ollama_with_usage):
        """OllamaProvider.chat() should include usage in result dict."""
        from core.model_providers import OllamaProvider
        provider = OllamaProvider()
        result = provider.chat(
            messages=[{"role": "user", "content": "test"}],
            model="phi4-mini:latest",
        )
        assert "usage" in result, "OllamaProvider.chat() must return usage"
        usage = result["usage"]
        assert usage["input_tokens"] == 150
        assert usage["output_tokens"] == 80
        assert usage["total_tokens"] == 230
        assert usage["source"] == "ollama"
        assert usage["estimated"] is False


# ---------------------------------------------------------------------------
# Tests: engine.chat() passes usage through
# ---------------------------------------------------------------------------

class TestEngineUsagePassthrough:
    def test_engine_chat_returns_usage(self, fake_ollama_with_usage):
        """engine.chat() should pass usage from provider to caller."""
        from core.engine import chat
        result = chat(
            messages=[{"role": "user", "content": "test"}],
            model="phi4-mini:latest",
        )
        # engine.chat() returns dict when tools are None and raw=False,
        # but returns content string by default. Let's use raw=True.
        result_raw = chat(
            messages=[{"role": "user", "content": "test"}],
            model="phi4-mini:latest",
            raw=True,
        )
        assert isinstance(result_raw, dict)
        assert "usage" in result_raw, "engine.chat(raw=True) must include usage"
        usage = result_raw["usage"]
        assert usage["input_tokens"] == 150
        assert usage["output_tokens"] == 80

    def test_engine_chat_with_tools_returns_usage(self, fake_ollama_with_usage):
        """engine.chat() with tools should also include usage."""
        from core.engine import chat
        result = chat(
            messages=[{"role": "user", "content": "test"}],
            model="phi4-mini:latest",
            tools=[{"type": "function", "function": {"name": "test_tool"}}],
        )
        assert isinstance(result, dict)
        assert "usage" in result


# ---------------------------------------------------------------------------
# Tests: chat_api() includes usage in JSON response
# ---------------------------------------------------------------------------

class TestChatApiUsageInResponse:
    def test_plain_chat_includes_usage(self, fake_ollama_with_usage, session_id):
        """POST /api/chat should return usage field in response."""
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.post("/api/chat", json={
                "soru": "test message",
                "session_id": session_id,
            })
        assert r.status_code == 200
        data = r.get_json()
        assert "usage" in data, "chat API response must include usage"
        usage = data["usage"]
        assert usage["input_tokens"] == 150
        assert usage["output_tokens"] == 80
        assert usage["source"] == "ollama"
        assert usage["estimated"] is False

    def test_vision_chat_includes_usage(self, fake_ollama_with_usage, session_id):
        """Vision branch should also include usage in response."""
        from ui.panel_server import _image_store
        # Register a fake image
        file_hash = f"hash-{uuid.uuid4().hex[:8]}"
        _image_store[file_hash] = "ZmFrZS1pbWFnZS1ieXRlcw=="
        image_att = {
            "type": "image", "is_vision": True,
            "filename": "test.jpg", "hash": file_hash, "icon": "🖼️"
        }
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.post("/api/chat", json={
                "soru": "bu resimde ne var",
                "session_id": session_id,
                "attachments": [image_att],
            })
        assert r.status_code == 200
        data = r.get_json()
        assert "usage" in data, "vision chat response must include usage"


# ---------------------------------------------------------------------------
# Tests: Pre-flight budget check
# ---------------------------------------------------------------------------

class TestPreFlightBudgetCheck:
    def test_preflight_warning_emitted_for_large_context(self, fake_ollama_with_usage, session_id, monkeypatch):
        """When context is large enough to trigger WARNING, SocketIO should emit budget_warning."""
        from ui.panel_server import app, socketio
        emitted_events = []

        # Capture SocketIO emits
        original_emit = socketio.emit
        def capture_emit(event, data=None, **kwargs):
            if event == "task_status" and data and data.get("phase") == "budget_warning":
                emitted_events.append(data)
            return original_emit(event, data, **kwargs) if data else original_emit(event, **kwargs)

        monkeypatch.setattr(socketio, "emit", capture_emit)

        # Build a very large message to exceed 80% of 8192 tokens (~32768 chars)
        large_text = "x" * 40000  # ~10000 estimated tokens > 80% of 8192
        with app.test_client() as client:
            r = client.post("/api/chat", json={
                "soru": large_text,
                "session_id": session_id,
            })

        # Check that budget_warning was emitted
        warning_events = [e for e in emitted_events if e.get("phase") == "budget_warning"]
        assert len(warning_events) >= 1, (
            f"Expected budget_warning SocketIO event for large context, got: {emitted_events}"
        )
        assert "budget" in warning_events[0]

    def test_preflight_ok_for_small_context(self, fake_ollama_with_usage, session_id, monkeypatch):
        """Small context should NOT emit budget_warning."""
        from ui.panel_server import app, socketio
        emitted_events = []

        original_emit = socketio.emit
        def capture_emit(event, data=None, **kwargs):
            if event == "task_status" and data and data.get("phase") == "budget_warning":
                emitted_events.append(data)
            return original_emit(event, data, **kwargs) if data else original_emit(event, **kwargs)

        monkeypatch.setattr(socketio, "emit", capture_emit)

        with app.test_client() as client:
            r = client.post("/api/chat", json={
                "soru": "short message",
                "session_id": session_id,
            })

        warning_events = [e for e in emitted_events if e.get("phase") == "budget_warning"]
        assert len(warning_events) == 0, (
            f"Small context should NOT trigger budget warning, but got: {warning_events}"
        )
