import unittest

from audit_verifier.data import evidence_index, generate_evidence


class TestData(unittest.TestCase):
    def test_size_and_kinds(self):
        records = generate_evidence()
        self.assertEqual(len(records), 60)
        for kind in ("order", "billing", "quality"):
            self.assertEqual(sum(1 for r in records if r["kind"] == kind), 20)

    def test_determinism(self):
        self.assertEqual(generate_evidence(), generate_evidence())
        self.assertEqual(generate_evidence(seed=1), generate_evidence(seed=1))

    def test_different_seed_differs(self):
        self.assertNotEqual(generate_evidence(seed=1), generate_evidence(seed=2))

    def test_ids_unique(self):
        records = generate_evidence()
        self.assertEqual(len({r["id"] for r in records}), len(records))

    def test_order_totals_consistent(self):
        for r in generate_evidence():
            if r["kind"] == "order":
                f = r["fields"]
                self.assertEqual(f["total_cents"],
                                 f["quantity"] * f["unit_price_cents"])

    def test_billing_difference_consistent(self):
        for r in generate_evidence():
            if r["kind"] == "billing":
                f = r["fields"]
                self.assertEqual(f["difference_cents"],
                                 f["billed_cents"] - f["expected_cents"])

    def test_quality_rate_consistent(self):
        for r in generate_evidence():
            if r["kind"] == "quality":
                f = r["fields"]
                self.assertEqual(f["defect_rate_pct"],
                                 round(f["defects"] * 100.0 / f["inspected"], 2))

    def test_index(self):
        records = generate_evidence()
        index = evidence_index(records)
        self.assertEqual(len(index), 60)
        self.assertEqual(index[records[0]["id"]], records[0])


if __name__ == "__main__":
    unittest.main()
