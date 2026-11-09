import copy
import unittest

from audit_verifier.data import evidence_index
from audit_verifier.findings import build_corpus
from audit_verifier.verifier import verify_all, verify_finding


class TestVerifier(unittest.TestCase):
    def setUp(self):
        self.corpus = build_corpus()
        self.index = evidence_index(self.corpus["evidence"])

    def _by_label(self, split, label):
        return [f for f in self.corpus[split] if f["truth_label"] == label]

    def test_true_findings_survive_both_splits(self):
        for split in ("tuning", "heldout"):
            for f in self._by_label(split, "TRUE"):
                r = verify_finding(f, self.index)
                self.assertEqual(r["verdict"], "SURVIVES", f)
                self.assertEqual(r["reasons"], [])

    def test_each_falsification_type_rejected_with_its_reason(self):
        for label in ("FABRICATED_CITATION", "WRONG_QUOTE",
                      "WRONG_CONCLUSION", "STALE_EVIDENCE"):
            for split in ("tuning", "heldout"):
                for f in self._by_label(split, label):
                    r = verify_finding(f, self.index)
                    self.assertEqual(r["verdict"], "REJECTED", f)
                    self.assertIn(label, r["reasons"], (f, r))

    def test_fabricated_has_only_fabricated_reason(self):
        for f in self._by_label("heldout", "FABRICATED_CITATION"):
            r = verify_finding(f, self.index)
            self.assertEqual(r["reasons"], ["FABRICATED_CITATION"])

    def test_verifier_ignores_truth_label(self):
        for f in self.corpus["heldout"]:
            baseline = verify_finding(f, self.index)
            stripped = {k: v for k, v in f.items() if k != "truth_label"}
            self.assertEqual(verify_finding(stripped, self.index), baseline)
            relabelled = copy.deepcopy(f)
            relabelled["truth_label"] = "TRUE"
            self.assertEqual(verify_finding(relabelled, self.index), baseline)

    def test_unsupported_claim_type_is_wrong_conclusion(self):
        f = copy.deepcopy(self._by_label("heldout", "TRUE")[0])
        f["claim_type"] = "defect_rate_pct" \
            if f["claim_type"] != "defect_rate_pct" else "order_total_cents"
        r = verify_finding(f, self.index)
        self.assertEqual(r["verdict"], "REJECTED")
        self.assertIn("WRONG_CONCLUSION", r["reasons"])

    def test_tampered_quote_rejected(self):
        f = copy.deepcopy(self._by_label("heldout", "TRUE")[0])
        key = sorted(f["quoted_values"])[0]
        f["quoted_values"][key] = "tampered"
        r = verify_finding(f, self.index)
        self.assertIn("WRONG_QUOTE", r["reasons"])

    def test_tampered_claimed_value_rejected(self):
        f = copy.deepcopy(self._by_label("heldout", "TRUE")[0])
        f["claimed_value"] = f["claimed_value"] + 999 \
            if isinstance(f["claimed_value"], int) else f["claimed_value"] + 9.5
        r = verify_finding(f, self.index)
        self.assertIn("WRONG_CONCLUSION", r["reasons"])

    def test_missing_window_is_stale(self):
        f = copy.deepcopy(self._by_label("heldout", "TRUE")[0])
        del f["window_start"]
        r = verify_finding(f, self.index)
        self.assertIn("STALE_EVIDENCE", r["reasons"])

    def test_verify_all_length(self):
        results = verify_all(self.corpus["heldout"], self.index)
        self.assertEqual(len(results), 18)


if __name__ == "__main__":
    unittest.main()
