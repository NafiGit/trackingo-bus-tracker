"""Vercel serverless proxy for the Trackingo live-tracking endpoints.

The browser never talks to Trackingo directly, so there is no CORS
problem. The tracking key is sent in a POST body, never in a URL, and
is never stored or logged: request logging is disabled in this handler.

Endpoints proxied (the tracker page's own internal endpoints, not a
published developer API):
  GET https://bus.trackingo.in/api/live/eta_map?current_status=true&key=<KEY>
  GET https://bus.trackingo.in/api/live/journey_details?key=<KEY>&zoom_position=12&platform=mobile

Usage:
  GET  /api/live?demo=1            -> bundled fictional example data
  POST /api/live {"key": "..."}     -> live eta_map for that key
  POST /api/live {"key": "...", "mode": "journey"} -> live journey details

Journey details can include booking and contact fields, so the proxy
strips anything that looks like a phone number, contact, email or
ticket field before returning it. No real key, ticket, vehicle number
or phone number is ever written into this repo.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

BASE = "https://bus.trackingo.in"
USER_AGENT = "trackingo-bus-tracker/0.1.0 (+https://github.com/NafiGit/trackingo-bus-tracker)"
SENSITIVE = ("phone", "mobile", "contact", "email", "whatsapp", "otp", "ticket")


def _scrub(value):
    """Drop anything that looks like a contact or booking field."""
    if isinstance(value, dict):
        return {
            key: _scrub(item)
            for key, item in value.items()
            if not any(word in key.lower() for word in SENSITIVE)
        }
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


def _fetch(url, timeout=15.0):
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _sample():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(
        os.path.join(here, "sample_eta_map.json"), encoding="utf-8"
    ) as handle:
        return json.load(handle)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if query.get("demo", [""])[0] == "1":
            self._send(200, {"demo": True, "eta_map": _sample()})
        else:
            self._send(400, {"error": "Use POST with a JSON body {\"key\": \"...\"}, or GET ?demo=1."})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except (ValueError, OSError):
            self._send(400, {"error": "Send a JSON body like {\"key\": \"...\"}."})
            return
        key = (body.get("key") or "").strip()
        mode = (body.get("mode") or "eta").strip().lower()
        if not key:
            self._send(400, {"error": "No key given. Paste your Trackingo key, or try the demo."})
            return
        try:
            if mode == "journey":
                url = (
                    f"{BASE}/api/live/journey_details"
                    f"?key={urllib.parse.quote(key)}&zoom_position=12&platform=mobile"
                )
                self._send(200, {"demo": False, "journey": _scrub(_fetch(url))})
            else:
                url = f"{BASE}/api/live/eta_map?current_status=true&key={urllib.parse.quote(key)}"
                self._send(200, {"demo": False, "eta_map": _fetch(url)})
        except urllib.error.HTTPError as exc:
            self._send(502, {"error": f"Trackingo returned HTTP {exc.code}. The key may be wrong or expired."})
        except Exception as exc:  # noqa: BLE001 - surface any fetch failure as JSON
            self._send(502, {"error": f"Could not reach Trackingo: {exc}"})

    def _send(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        # Never log requests: the key must not land in any log.
        pass
