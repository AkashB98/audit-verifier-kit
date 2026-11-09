"""Planted findings corpus, split into tuning and held-out sets.

The two sets are disjoint: tuning findings cite the first half of the
evidence records, held-out findings cite the second half, and finding ids
never overlap. Truth labels describe how each finding was planted; the
verifier never reads them. Never tune verifier behaviour on the held-out
set -- it is the scoring set only.
"""
from datetime import timedelta

from .data import generate_evidence, parse_ts, _ts
from .verifier import SUPPORTED, compute_claim

TRUTH_LABELS = ("TRUE", "FABRICATED_CITATION", "WRONG_QUOTE",
                "WRONG_CONCLUSION", "STALE_EVIDENCE")

# Per split: 6 true + 3 of each falsification type = 18 findings.
TRUE_PER_SPLIT = 6
FALSE_PER_TYPE = 3


def _claim_type_for(record):
    for claim, kind in SUPPORTED.items():
        if kind == record["kind"]:
            return claim
    raise ValueError(record["kind"])


def _window(record, shift_days=0):
    ts = parse_ts(record["timestamp"])
    start = ts + timedelta(days=shift_days - 2)
    end = ts + timedelta(days=shift_days + 2)
    return _ts(start), _ts(end)


def _quoted(record):
    """Two relevant fields, quoted exactly from the record."""
    f = record["fields"]
    if record["kind"] == "order":
        return {"quantity": f["quantity"], "unit_price_cents": f["unit_price_cents"]}
    if record["kind"] == "billing":
        return {"billed_cents": f["billed_cents"],
                "expected_cents": f["expected_cents"]}
    return {"inspected": f["inspected"], "defects": f["defects"]}


def _statement(record, claim_type, claimed):
    return ("Helios Home audit: %s for record %s is %s."
            % (claim_type, record["id"], claimed))


def _base_finding(fid, record, truth):
    claim_type = _claim_type_for(record)
    claimed = compute_claim(record, claim_type)
    start, end = _window(record)
    return {
        "id": fid,
        "claim_type": claim_type,
        "statement": _statement(record, claim_type, claimed),
        "cited_record_id": record["id"],
        "quoted_values": _quoted(record),
        "claimed_value": claimed,
        "window_start": start,
        "window_end": end,
        "truth_label": truth,
    }


def _make_split(records, prefix):
    findings = []
    seq = [0]

    def nid():
        seq[0] += 1
        return "%s-%02d" % (prefix, seq[0])

    # Records cycle order/billing/quality in the generated list layout only
    # if we take them in order; here we simply take them as given.
    pool = list(records)

    for i in range(TRUE_PER_SPLIT):
        findings.append(_base_finding(nid(), pool[i], "TRUE"))

    # Fabricated citations: record ids that do not exist.
    for i in range(FALSE_PER_TYPE):
        rec = pool[i]
        f = _base_finding(nid(), rec, "FABRICATED_CITATION")
        f["cited_record_id"] = "EV-9%03d" % (900 + i)
        findings.append(f)

    # Wrong quotes: one quoted value altered, everything else correct.
    for i in range(FALSE_PER_TYPE):
        rec = pool[TRUE_PER_SPLIT + i]
        f = _base_finding(nid(), rec, "WRONG_QUOTE")
        key = sorted(f["quoted_values"])[0]
        val = f["quoted_values"][key]
        f["quoted_values"][key] = val + 7 if isinstance(val, int) else val
        if f["quoted_values"][key] == val:  # non-int fallback
            f["quoted_values"][key] = str(val) + "X"
        findings.append(f)

    # Wrong conclusions: quotes and window correct, claimed number does
    # not recompute from the evidence.
    for i in range(FALSE_PER_TYPE):
        rec = pool[TRUE_PER_SPLIT + FALSE_PER_TYPE + i]
        f = _base_finding(nid(), rec, "WRONG_CONCLUSION")
        delta = 250 if isinstance(f["claimed_value"], int) else 5.0
        f["claimed_value"] = round(f["claimed_value"] + delta, 2) \
            if isinstance(f["claimed_value"], float) else f["claimed_value"] + delta
        findings.append(f)

    # Stale evidence: everything correct except the claimed window, which
    # is shifted so the evidence timestamp falls outside it.
    for i in range(FALSE_PER_TYPE):
        rec = pool[TRUE_PER_SPLIT + 2 * FALSE_PER_TYPE + i]
        f = _base_finding(nid(), rec, "STALE_EVIDENCE")
        start, end = _window(rec, shift_days=30)
        f["window_start"], f["window_end"] = start, end
        findings.append(f)

    return findings


def build_corpus(seed=None):
    """Return {evidence, tuning, heldout}. Disjoint by construction."""
    records = generate_evidence() if seed is None else generate_evidence(seed)
    half = len(records) // 2
    tuning = _make_split(records[:half], "TUN")
    heldout = _make_split(records[half:], "HLD")
    return {"evidence": records, "tuning": tuning, "heldout": heldout}
