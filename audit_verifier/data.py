"""Deterministic seeded generator for Helios Home evidence records.

Helios Home is a fictional smart-home retailer. All names, accounts and
amounts are synthetic. Stdlib only, no network, same seed -> same records.
"""
import random
from datetime import datetime, timedelta, timezone

SEED = 4207
BASE = datetime(2026, 1, 5, 9, 0, 0, tzinfo=timezone.utc)

_CUSTOMERS = ["Asha Patel", "Ben Ortiz", "Cara Nguyen", "Dev Shah",
              "Elena Rossi", "Farid Khan", "Grace Lee", "Hugo Meyer"]
_PRODUCTS = ["Helios Thermostat", "Helios Bulb 4-pack", "Helios Door Sensor",
             "Helios Hub Mini", "Helios Leak Sensor", "Helios Plug Duo"]
_BATCHES = ["HH-B100", "HH-B101", "HH-B102", "HH-B103", "HH-B104", "HH-B105"]


def _ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc)


def generate_evidence(seed=SEED, per_kind=20):
    """Return a deterministic list of evidence records.

    Record shape: {id, kind, fields, timestamp}
    kinds: order, billing, quality (per_kind of each, in that order).
    """
    rng = random.Random(seed)
    records = []
    n = 0
    for i in range(per_kind):
        for kind in ("order", "billing", "quality"):
            n += 1
            ts = _ts(BASE + timedelta(days=rng.randrange(0, 60),
                                       hours=rng.randrange(0, 9)))
            rid = "EV-%04d" % n
            if kind == "order":
                qty = rng.randrange(1, 6)
                unit = rng.choice([1999, 2499, 4999, 7999, 12999])
                fields = {
                    "customer": rng.choice(_CUSTOMERS),
                    "product": rng.choice(_PRODUCTS),
                    "quantity": qty,
                    "unit_price_cents": unit,
                    "total_cents": qty * unit,
                }
            elif kind == "billing":
                expected = rng.choice([4999, 7999, 9999, 14999, 19999])
                # About half the accounts are over-billed, half exact.
                over = rng.choice([0, 0, 250, 500, 1250])
                fields = {
                    "account": "HH-ACCT-%03d" % rng.randrange(100, 999),
                    "customer": rng.choice(_CUSTOMERS),
                    "expected_cents": expected,
                    "billed_cents": expected + over,
                    "difference_cents": over,
                }
            else:
                inspected = rng.choice([100, 200, 250, 400, 500])
                defects = rng.randrange(0, 21)
                fields = {
                    "batch": rng.choice(_BATCHES),
                    "inspected": inspected,
                    "defects": defects,
                    "defect_rate_pct": round(defects * 100.0 / inspected, 2),
                }
            records.append({"id": rid, "kind": kind,
                            "fields": fields, "timestamp": ts})
    return records


def evidence_index(records):
    return {r["id"]: r for r in records}
