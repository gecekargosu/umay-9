import http.server
import urllib.request
import socketserver

PORT = 5003
UPSTREAM = "http://localhost:5001"

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            resp = urllib.request.urlopen(f"{UPSTREAM}{self.path}", timeout=30)
            self.send_response(resp.status)
            for key, val in resp.headers.items():
                if key.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(resp.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(e).encode())
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            req = urllib.request.Request(
                f"{UPSTREAM}{self.path}",
                data=body,
                headers={k: v for k, v in self.headers.items() if k.lower() not in ("host", "transfer-encoding")},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=60)
            self.send_response(resp.status)
            for key, val in resp.headers.items():
                if key.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(resp.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(e).encode())
    def log_message(self, format, *args):
        pass

with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
    print(f"Proxy running on port {PORT} -> {UPSTREAM}", flush=True)
    httpd.serve_forever()
