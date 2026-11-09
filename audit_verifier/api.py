"""Stdlib HTTP API: POST /verify, GET /health. Binds 127.0.0.1 only."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from .data import evidence_index, generate_evidence
from .verifier import verify_finding


def make_server(port=8091, host="127.0.0.1"):
    default_index = evidence_index(generate_evidence())

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, payload):
            body = json.dumps(payload, sort_keys=True).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/verify":
                self._send(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                finding = payload["finding"]
                if "evidence" in payload:
                    index = evidence_index(payload["evidence"])
                else:
                    index = default_index
                self._send(200, verify_finding(finding, index))
            except Exception as exc:  # clean JSON error, never a traceback page
                self._send(400, {"error": str(exc)})

    return HTTPServer((host, port), Handler)


def serve(port=8091):
    server = make_server(port=port)
    print("listening on http://127.0.0.1:%d" % port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0
