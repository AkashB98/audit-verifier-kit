import unittest

from audit_verifier.findings import TRUTH_LABELS, build_corpus


class TestFindings(unittest.TestCase):
    def setUp(self):
        self.corpus = build_corpus()

    def test_split_sizes(self):
        self.assertEqual(len(self.corpus["tuning"]), 18)
        self.assertEqual(len(self.corpus["heldout"]), 18)

    def test_label_counts_per_split(self):
        for split in ("tuning", "heldout"):
            counts = {}
            for f in self.corpus[split]:
                counts[f["truth_label"]] = counts.get(f["truth_label"], 0) + 1
            self.assertEqual(counts["TRUE"], 6)
            for label in TRUTH_LABELS:
                if label != "TRUE":
                    self.assertEqual(counts[label], 3, (split, label))

    def test_disjoint_finding_ids(self):
        tuning = {f["id"] for f in self.corpus["tuning"]}
        heldout = {f["id"] for f in self.corpus["heldout"]}
        self.assertFalse(tuning & heldout)

    def test_disjoint_cited_real_records(self):
        def real_cited(split):
            return {f["cited_record_id"] for f in self.corpus[split]
                    if f["truth_label"] != "FABRICATED_CITATION"}
        self.assertFalse(real_cited("tuning") & real_cited("heldout"))

    def test_determinism(self):
        self.assertEqual(build_corpus(), build_corpus())

    def test_fabricated_ids_do_not_exist(self):
        ids = {r["id"] for r in self.corpus["evidence"]}
        for split in ("tuning", "heldout"):
            for f in self.corpus[split]:
                if f["truth_label"] == "FABRICATED_CITATION":
                    self.assertNotIn(f["cited_record_id"], ids)

    def test_all_findings_have_required_fields(self):
        required = {"id", "claim_type", "statement", "cited_record_id",
                    "quoted_values", "claimed_value", "window_start",
                    "window_end", "truth_label"}
        for split in ("tuning", "heldout"):
            for f in self.corpus[split]:
                self.assertTrue(required <= set(f), f["id"])


if __name__ == "__main__":
    unittest.main()
