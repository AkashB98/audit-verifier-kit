#!/usr/bin/env python3
"""End-to-end demo: generate -> plant -> verify -> report -> serve round-trip.

Every step is asserted; exits 0 only if the held-out set is perfect and the
HTTP round-trip agrees with the in-process verifier.
"""
import json
import threading
import urllib.request

from audit_verifier.api import make_server
from audit_verifier.data import evidence_index
from audit_verifier.findings import build_corpus
from audit_verifier.report import format_report, full_report, is_perfect
from audit_verifier.verifier import verify_finding


def main():
    corpus = build_corpus()
    print("evidence records: %d" % len(corpus["evidence"]))
    print("tuning findings: %d, held-out findings: %d"
          % (len(corpus["tuning"]), len(corpus["heldout"])))

    report = full_report(corpus)
    print(format_report(report))
    assert is_perfect(report["heldout"]), "held-out set must be perfect"
    assert is_perfect(report["tuning"]), "tuning set must be perfect"
    print("confusion matrix: perfect on both sets")

    # Serve round-trip on an ephemeral localhost port.
    server = make_server(port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/health" % port, timeout=5) as resp:
            health = json.loads(resp.read())
        assert health == {"status": "ok"}, health

        finding = corpus["heldout"][0]
        body = json.dumps({"finding": finding,
                           "evidence": corpus["evidence"]}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:%d/verify" % port, data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            via_http = json.loads(resp.read())
        direct = verify_finding(finding, evidence_index(corpus["evidence"]))
        assert via_http == direct, (via_http, direct)
        print("serve round-trip: /health ok, /verify agrees (%s -> %s)"
              % (finding["id"], via_http["verdict"]))
    finally:
        server.shutdown()
        server.server_close()

    print("DEMO PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
