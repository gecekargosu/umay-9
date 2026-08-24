import os

content = """"""Tests for STEP-05: Background task execution, lifecycle, pause/resume/cancel."""
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _FakeOllamaHandler(BaseHTTPRequestHandler):
    received_bodies = []
    response_content = "test cevap"
    delay = 0

    def _send(self, payload):
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/tags":
            self._send({"models": [{"name": "qwen2.5:7b"}]})
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        _FakeOllamaHandler.received_bodies.append(body)
        if self.delay:
            time.sleep(self.delay)
        self._send({"message": {"role": "assistant", "content": self.response_content}})

    def log_message(self, *_args):
        pass
"""

with open(os.path.join("tests", "test_step05_task_executor.py"), "w", encoding="utf-8") as f:
    f.write(content)
print("Part 1 written")
