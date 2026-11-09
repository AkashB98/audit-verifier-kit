import contextlib
import io
import json
import threading
import unittest
import urllib.request

import cli
from audit_verifier.api import make_server
from audit_verifier.findings import build_corpus


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path):
        with urllib.request.urlopen(
                "http://127.0.0.1:%d%s" % (self.port, path), timeout=5) as r:
            return r.status, json.loads(r.read())

    def _post_verify(self, payload):
        req = urllib.request.Request(
            "http://127.0.0.1:%d/verify" % self.port,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())

    def test_health(self):
        status, body = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_verify_true_finding_survives(self):
        corpus = build_corpus()
        finding = [f for f in corpus["heldout"]
                   if f["truth_label"] == "TRUE"][0]
        status, body = self._post_verify(
            {"finding": finding, "evidence": corpus["evidence"]})
        self.assertEqual(status, 200)
        self.assertEqual(body["verdict"], "SURVIVES")

    def test_verify_fabricated_rejected(self):
        corpus = build_corpus()
        finding = [f for f in corpus["heldout"]
                   if f["truth_label"] == "FABRICATED_CITATION"][0]
        status, body = self._post_verify(
            {"finding": finding, "evidence": corpus["evidence"]})
        self.assertEqual(body["verdict"], "REJECTED")
        self.assertIn("FABRICATED_CITATION", body["reasons"])

    def test_verify_uses_default_evidence(self):
        corpus = build_corpus()
        finding = corpus["heldout"][0]
        status, body = self._post_verify({"finding": finding})
        self.assertEqual(status, 200)
        self.assertIn(body["verdict"], ("SURVIVES", "REJECTED"))


class TestCli(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(argv)
        return rc, buf.getvalue()

    def test_check_passes(self):
        rc, out = self._run(["check"])
        self.assertEqual(rc, 0)
        self.assertIn("PASS", out)

    def test_report(self):
        rc, out = self._run(["report"])
        self.assertEqual(rc, 0)
        self.assertIn("heldout", out)

    def test_verify_heldout(self):
        rc, out = self._run(["verify", "--split", "heldout"])
        self.assertEqual(rc, 0)
        self.assertIn("SURVIVES", out)
        self.assertIn("REJECTED", out)

    def test_generate(self):
        rc, out = self._run(["generate"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(json.loads(out)), 60)


if __name__ == "__main__":
    unittest.main()
