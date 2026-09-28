import json
import os
from http.server import BaseHTTPRequestHandler

from api.kiwoom_api import KiwoomAPI


def _status_payload():
    """Build a read-only status response without making a broker request."""
    api = KiwoomAPI(
        app_key=os.environ.get("KIWOOM_APP_KEY"),
        app_secret=os.environ.get("KIWOOM_APP_SECRET"),
        paper=True,
    )
    if not api.is_paper:
        raise RuntimeError("Vercel entrypoint must remain in paper mode")
    return {"ok": True, "mode": "paper", "readonly": True}


class handler(BaseHTTPRequestHandler):
    """Vercel Python function entrypoint."""

    def do_GET(self):
        body = json.dumps(_status_payload()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
