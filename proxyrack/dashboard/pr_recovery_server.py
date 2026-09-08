#!/usr/bin/env python3
"""PR-only recovery page; reads local files and never calls account APIs."""
import argparse
import json
from pathlib import Path
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from proxyrack import DATA, public_snapshot

PAGE = Path(__file__).parent / "static/proxyrack.html"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urlsplit(self.path).path
        try:
            if route in ("/", "/proxyrack", "/proxyrack.html"):
                body, media, status = PAGE.read_bytes(), "text/html; charset=utf-8", 200
            elif route == "/ps1.js":
                body, media, status = (PAGE.parent / "ps1.js").read_bytes(), "application/javascript; charset=utf-8", 200
            elif route == "/api/proxyrack":
                result = public_snapshot(DATA)
                body, media, status = json.dumps(result).encode(), "application/json", 200
            else:
                body, media, status = b"Not found", "text/plain", 404
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
            body, media, status = b'{"error":"PR recorder data is not available yet"}', "application/json", 503
        self.send_response(status)
        self.send_header("Content-Type", media)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
