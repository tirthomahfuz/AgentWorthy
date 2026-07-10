#!/usr/bin/env python3
"""E2E fixture site with configurable verification token."""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN_FILE = os.environ.get("FIXTURE_TOKEN_FILE", "/tmp/agentworthy-fixture-token.txt")
PORT = int(os.environ.get("FIXTURE_PORT", "8765"))


def read_token() -> str:
    try:
        with open(TOKEN_FILE) as f:
            return f.read().strip() or "wrong-token"
    except FileNotFoundError:
        return "wrong-token"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        token = read_token()
        html = f"""<!DOCTYPE html>
<html><head>
<title>Fixture Test Site</title>
<meta name="agentworthy-verification" content="{token}" />
</head><body>
<h1>Fixture Site for E2E</h1>
<a href="/contact">Contact us</a>
<form><label for="email">Email</label><input id="email" name="email" type="email" /></form>
<p>Copyright 2026 Example Co</p>
</body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format: str, *args: object) -> None:
        pass


if __name__ == "__main__":
    print(json.dumps({"fixture_server": PORT, "token_file": TOKEN_FILE}))
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
