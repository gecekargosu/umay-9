"""Regression tests for STEP-04.5: the mixed-attachment bug.

Root cause (confirmed in docs/development/CHAT_STEP04_AUDIT.md §4, and
re-verified directly before this fix): ui/panel_server.py's vision branch
built its Ollama request using raw `soru` instead of the already-computed
`att_context` (which is built from ALL attachments, not just the image).
Any PDF/code/text attachment sent alongside an image in the same turn was
silently dropped from what the vision model actually received.

These tests capture the exact JSON body chat_api() sends to the (fake)
Ollama vision endpoint and assert the non-image attachment's content is
present in it — the failure mode this bug produced would make every test
below fail before the fix (the assertions were verified failing against
the pre-fix code before this file was finalized).
"""
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _CapturingVisionHandler(BaseHTTPRequestHandler):
    """Fake Ollama server for vision requests. Records every POST body it
    receives so the test can inspect exactly what chat_api() sent."""

    received_bodies: list = []

    def _send(self, payload):
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/tags":
            self._send({"models": [{"name": "gemma3:4b"}, {"name": "llava:7b"}]})
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        _CapturingVisionHandler.received_bodies.append(body)
        self._send({"message": {"role": "assistant", "content": "gorsel analiz tamam"}})

    def log_message(self, *_args):
        pass


@pytest.fixture
def fake_vision_ollama(monkeypatch):
    _CapturingVisionHandler.received_bodies = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CapturingVisionHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    import core.engine as engine
    monkeypatch.setattr(engine, "OLLAMA_URL", f"http://127.0.0.1:{server.server_port}")
    yield _CapturingVisionHandler
    server.shutdown()
    server.server_close()


@pytest.fixture
def session_id():
    return f"vision-test-{uuid.uuid4().hex[:8]}"


def _register_fake_image():
    """Register a fake image in panel_server's in-memory image store and
    return an attachment dict referencing it, exactly like a real
    /api/chat/attach upload would produce."""
    from ui.panel_server import _image_store
    file_hash = f"hash-{uuid.uuid4().hex[:8]}"
    _image_store[file_hash] = "ZmFrZS1pbWFnZS1ieXRlcw=="  # base64 of "fake-image-bytes"
    return {"type": "image", "is_vision": True, "filename": "ekran.png", "hash": file_hash, "icon": "🖼️"}


class TestMixedAttachmentFix:
    def test_image_plus_pdf_keeps_pdf_content(self, fake_vision_ollama, session_id):
        from ui.panel_server import app

        image_att = _register_fake_image()
        pdf_att = {
            "type": "pdf",
            "filename": "rapor.pdf",
            "icon": "📄",
            "content": "YILLIK RAPOR OZETI: gelir 5 milyon TL, gider 2 milyon TL.",
        }

        with app.test_client() as client:
            r = client.post("/api/chat", json={
                "soru": "bu resmi ve pdf'i birlikte degerlendir",
                "session_id": session_id,
                "attachments": [image_att, pdf_att],
            })
        assert r.status_code == 200

        assert len(fake_vision_ollama.received_bodies) == 1
        sent = fake_vision_ollama.received_bodies[0]
        user_msg = next(m for m in sent["messages"] if m["role"] == "user")
        assert "images" in user_msg and user_msg["images"], "vision request should still include the image"
        assert "YILLIK RAPOR OZETI" in user_msg["content"], (
            "PDF content was dropped from the vision request — mixed-attachment bug regressed"
        )
        assert "gelir 5 milyon TL" in user_msg["content"]

    def test_image_plus_code_keeps_code_content(self, fake_vision_ollama, session_id):
        from ui.panel_server import app

        image_att = _register_fake_image()
        code_att = {
            "type": "code",
            "filename": "main.py",
            "icon": "💻",
            "content": "def hesapla_toplam(a, b):\n    return a + b  # UNIQUE_MARKER_CODE_1234",
        }

        with app.test_client() as client:
            r = client.post("/api/chat", json={
                "soru": "bu ekran goruntusundeki hatayi koddan bul",
                "session_id": session_id,
                "attachments": [image_att, code_att],
            })
        assert r.status_code == 200

        sent = fake_vision_ollama.received_bodies[0]
        user_msg = next(m for m in sent["messages"] if m["role"] == "user")
        assert "UNIQUE_MARKER_CODE_1234" in user_msg["content"]
        assert "hesapla_toplam" in user_msg["content"]

    def test_image_plus_text_file_keeps_text_content(self, fake_vision_ollama, session_id):
        from ui.panel_server import app

        image_att = _register_fake_image()
        txt_att = {
            "type": "text",
            "filename": "notlar.txt",
            "icon": "📝",
            "content": "TOPLANTI NOTU: UNIQUE_MARKER_TEXT_5678 karari alindi.",
        }

        with app.test_client() as client:
            r = client.post("/api/chat", json={
                "soru": "bu notu resimle karsilastir",
                "session_id": session_id,
                "attachments": [image_att, txt_att],
            })
        assert r.status_code == 200

        sent = fake_vision_ollama.received_bodies[0]
        user_msg = next(m for m in sent["messages"] if m["role"] == "user")
        assert "UNIQUE_MARKER_TEXT_5678" in user_msg["content"]

    def test_image_plus_multiple_attachments_keeps_all(self, fake_vision_ollama, session_id):
        from ui.panel_server import app

        image_att = _register_fake_image()
        pdf_att = {"type": "pdf", "filename": "a.pdf", "icon": "📄", "content": "MARKER_PDF_AAA"}
        code_att = {"type": "code", "filename": "b.py", "icon": "💻", "content": "MARKER_CODE_BBB"}
        txt_att = {"type": "text", "filename": "c.txt", "icon": "📝", "content": "MARKER_TEXT_CCC"}

        with app.test_client() as client:
            r = client.post("/api/chat", json={
                "soru": "hepsini birlikte incele",
                "session_id": session_id,
                "attachments": [image_att, pdf_att, code_att, txt_att],
            })
        assert r.status_code == 200

        sent = fake_vision_ollama.received_bodies[0]
        user_msg = next(m for m in sent["messages"] if m["role"] == "user")
        assert "MARKER_PDF_AAA" in user_msg["content"]
        assert "MARKER_CODE_BBB" in user_msg["content"]
        assert "MARKER_TEXT_CCC" in user_msg["content"]
        assert user_msg["images"], "image must still be present alongside the other attachments' text"

    def test_image_only_still_works_no_regression(self, fake_vision_ollama, session_id):
        """No other attachments — pure image turn must keep working exactly
        as before (image sent, question reaches the model)."""
        from ui.panel_server import app

        image_att = _register_fake_image()

        with app.test_client() as client:
            r = client.post("/api/chat", json={
                "soru": "bu resimde ne var UNIQUE_MARKER_QUESTION_9999",
                "session_id": session_id,
                "attachments": [image_att],
            })
        assert r.status_code == 200
        data = r.get_json()
        assert data["cevap"] == "gorsel analiz tamam"

        sent = fake_vision_ollama.received_bodies[0]
        user_msg = next(m for m in sent["messages"] if m["role"] == "user")
        assert user_msg["images"]
        assert "UNIQUE_MARKER_QUESTION_9999" in user_msg["content"]
