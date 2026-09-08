"""TM-only loopback recovery server; no cloud writes or credential handling."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from dashboard.traffmonetizer import snapshot

ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/traffmonetizer":
                body = json.dumps(snapshot()).encode()
                content_type = "application/json; charset=utf-8"
            elif path in ("/", "/tm", "/traffmonetizer"):
                body = (ROOT / "dashboard/static/traffmonetizer.html").read_bytes()
                content_type = "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
        except (OSError, ValueError, KeyError) as error:
            self.send_error(503, "TM snapshot unavailable: " + type(error).__name__)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 8787), Handler) as server:
        print("TM recovery dashboard: http://127.0.0.1:8787/", flush=True)
        server.serve_forever()
