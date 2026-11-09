import unittest

from audit_verifier.findings import build_corpus
from audit_verifier.report import confusion, format_report, full_report, is_perfect


class TestReport(unittest.TestCase):
    def setUp(self):
        self.corpus = build_corpus()
        self.report = full_report(self.corpus)

    def test_heldout_perfect(self):
        self.assertTrue(is_perfect(self.report["heldout"]))

    def test_tuning_perfect(self):
        self.assertTrue(is_perfect(self.report["tuning"]))

    def test_heldout_numbers(self):
        held = self.report["heldout"]
        self.assertEqual(held["true"], {"survived": 6, "total": 6})
        for t, v in held["per_type"].items():
            self.assertEqual(v, {"rejected": 3, "total": 3}, t)

    def test_tuning_and_heldout_reported_separately(self):
        self.assertEqual(set(self.report), {"heldout", "tuning"})
        self.assertEqual(self.report["tuning"]["overall"]["total"], 18)
        self.assertEqual(self.report["heldout"]["overall"]["total"], 18)

    def test_confusion_totals(self):
        m = confusion(self.corpus["heldout"], self.corpus["evidence"])
        self.assertEqual(m["overall"]["total"], 18)
        self.assertEqual(m["overall"]["rejected_false"], 12)

    def test_format_report_mentions_both_sets(self):
        text = format_report(self.report)
        self.assertIn("heldout", text)
        self.assertIn("tuning", text)
        self.assertIn("TRUE findings survived: 6/6", text)


if __name__ == "__main__":
    unittest.main()
