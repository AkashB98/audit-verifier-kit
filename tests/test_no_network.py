"""No-network guard: generation, planting and verification work offline."""
import socket
import unittest

from audit_verifier.data import evidence_index, generate_evidence
from audit_verifier.findings import build_corpus
from audit_verifier.report import full_report, is_perfect
from audit_verifier.verifier import verify_all


class Offline:
    def __enter__(self):
        self._socket = socket.socket
        self._create = socket.create_connection

        def blocked(*a, **k):
            raise AssertionError("network access attempted during offline test")
        socket.socket = blocked
        socket.create_connection = blocked
        return self

    def __exit__(self, *exc):
        socket.socket = self._socket
        socket.create_connection = self._create
        return False


class TestNoNetwork(unittest.TestCase):
    def test_generate_offline(self):
        with Offline():
            self.assertEqual(len(generate_evidence()), 60)

    def test_corpus_and_verify_offline(self):
        with Offline():
            corpus = build_corpus()
            results = verify_all(corpus["heldout"],
                                 evidence_index(corpus["evidence"]))
        self.assertEqual(len(results), 18)

    def test_report_offline(self):
        with Offline():
            report = full_report(build_corpus())
        self.assertTrue(is_perfect(report["heldout"]))


if __name__ == "__main__":
    unittest.main()
