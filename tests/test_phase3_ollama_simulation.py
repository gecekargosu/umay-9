import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import core.engine as engine


class FakeOllamaHandler(BaseHTTPRequestHandler):
    calls = []

    def _send(self, payload):
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == '/api/tags':
            self._send({'models': [{'name': 'qwen2.5-coder:7b'}]})
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = json.loads(self.rfile.read(length))
        FakeOllamaHandler.calls.append((self.path, body))
        if self.path != '/api/chat':
            self.send_error(404)
            return
        messages = body['messages']
        # First turn: request a native tool call with STRING arguments.
        if not any(m.get('role') == 'tool' for m in messages):
            self._send({'message': {'role': 'assistant', 'content': '', 'tool_calls': [
                {'id': 'call-1', 'type': 'function', 'function': {
                    'name': 'list_directory', 'arguments': '{"recursive": true}'
                }}
            ]}})
            return
        # Second turn: verify the assistant message is object arguments and a tool result exists.
        assistant = next(m for m in messages if m.get('role') == 'assistant' and m.get('tool_calls'))
        assert isinstance(assistant['tool_calls'][0]['function']['arguments'], dict)
        assert assistant['tool_calls'][0]['function']['arguments']['recursive'] is True
        assert any(m.get('role') == 'tool' for m in messages)
        self._send({'message': {'role': 'assistant', 'content': 'SIMULATED ROUND-TRIP PASS'}})

    def log_message(self, *_args):
        pass


def test_engine_ollama_payload_round_trip(monkeypatch):
    server = ThreadingHTTPServer(('127.0.0.1', 0), FakeOllamaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(engine, 'OLLAMA_URL', f'http://127.0.0.1:{server.server_port}')
        messages = [
            {'role': 'system', 'content': 'test'},
            {'role': 'user', 'content': 'tool test'},
        ]
        first = engine.chat(messages, model='qwen2.5-coder:7b', task='coding', tools=[{'type': 'function'}])
        assert first['message']['tool_calls']

        from core.agent import _parse_tool_calls, _assistant_tool_message, _tool_messages
        calls = _parse_tool_calls(first['message'])
        messages.append(_assistant_tool_message(calls))
        messages.extend(_tool_messages(calls))
        second = engine.chat(messages, model='qwen2.5-coder:7b', task='coding', tools=[{'type': 'function'}])
        assert second['message']['content'] == 'SIMULATED ROUND-TRIP PASS'
    finally:
        server.shutdown()
        server.server_close()
