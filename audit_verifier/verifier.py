"""Deterministic verifier: tries to disprove each finding against evidence.

No model, no judge, no scoring rubric. Every check is a recomputation or an
exact comparison against the cited evidence record. The verifier never reads
a finding's truth label (planted labels exist only for evaluation) -- a test
pins that removing / changing the label cannot change the verdict.
"""
from .data import parse_ts

# claim_type -> evidence kind that can support it
SUPPORTED = {
    "order_total_cents": "order",
    "billing_difference_cents": "billing",
    "defect_rate_pct": "quality",
}

REASON_FABRICATED = "FABRICATED_CITATION"
REASON_WRONG_QUOTE = "WRONG_QUOTE"
REASON_WRONG_CONCLUSION = "WRONG_CONCLUSION"
REASON_STALE = "STALE_EVIDENCE"


def compute_claim(record, claim_type):
    """Recompute the claimed number from the record, or None if unsupported."""
    f = record["fields"]
    if claim_type == "order_total_cents" and record["kind"] == "order":
        return f["quantity"] * f["unit_price_cents"]
    if claim_type == "billing_difference_cents" and record["kind"] == "billing":
        return f["billed_cents"] - f["expected_cents"]
    if claim_type == "defect_rate_pct" and record["kind"] == "quality":
        return round(f["defects"] * 100.0 / f["inspected"], 2)
    return None


def _values_match(claimed, actual):
    if isinstance(actual, float) or isinstance(claimed, float):
        try:
            return abs(float(claimed) - float(actual)) < 0.005
        except (TypeError, ValueError):
            return False
    return claimed == actual


def verify_finding(finding, index):
    """Return {finding_id, verdict, reasons} for one finding.

    index: dict record_id -> evidence record.
    verdict is SURVIVES only if every check passes.
    """
    reasons = []
    record = index.get(finding.get("cited_record_id"))
    if record is None:
        # Nothing else can be checked without the cited record.
        return {"finding_id": finding.get("id"), "verdict": "REJECTED",
                "reasons": [REASON_FABRICATED]}

    # 1. Quoted values must match the source record exactly.
    for key, quoted in (finding.get("quoted_values") or {}).items():
        if key not in record["fields"] or not _values_match(
                quoted, record["fields"][key]):
            reasons.append(REASON_WRONG_QUOTE)
            break

    # 2. Claim type must be supported by this evidence kind, and the
    #    claimed number must recompute from the cited record.
    claim_type = finding.get("claim_type")
    if SUPPORTED.get(claim_type) != record["kind"]:
        reasons.append(REASON_WRONG_CONCLUSION)
    else:
        computed = compute_claim(record, claim_type)
        claimed = finding.get("claimed_value")
        if claimed is None or not _values_match(claimed, computed):
            reasons.append(REASON_WRONG_CONCLUSION)

    # 3. Evidence timestamp must lie inside the claimed window.
    try:
        ts = parse_ts(record["timestamp"])
        start = parse_ts(finding["window_start"])
        end = parse_ts(finding["window_end"])
        if not (start <= ts <= end):
            reasons.append(REASON_STALE)
    except (KeyError, TypeError, ValueError):
        reasons.append(REASON_STALE)

    return {"finding_id": finding.get("id"),
            "verdict": "SURVIVES" if not reasons else "REJECTED",
            "reasons": reasons}


def verify_all(findings, index):
    return [verify_finding(f, index) for f in findings]
