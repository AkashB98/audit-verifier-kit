"""Confusion-matrix reporting, held-out first, tuning reported separately."""
from .data import evidence_index
from .findings import TRUTH_LABELS
from .verifier import verify_all

FALSIFICATION_TYPES = ("FABRICATED_CITATION", "WRONG_QUOTE",
                       "WRONG_CONCLUSION", "STALE_EVIDENCE")


def confusion(findings, records):
    """Break verifier outcomes down by planted truth label.

    Returns a deterministic dict:
      true: {survived, total}
      per_type: {TYPE: {rejected, total}, ...}
      overall: {survived_true, rejected_false, total}
    """
    index = evidence_index(records)
    results = {r["finding_id"]: r for r in verify_all(findings, index)}
    true_survived = true_total = 0
    per_type = {t: {"rejected": 0, "total": 0} for t in FALSIFICATION_TYPES}
    for f in findings:
        label = f["truth_label"]
        verdict = results[f["id"]]["verdict"]
        if label == "TRUE":
            true_total += 1
            if verdict == "SURVIVES":
                true_survived += 1
        else:
            per_type[label]["total"] += 1
            if verdict == "REJECTED":
                per_type[label]["rejected"] += 1
    rejected_false = sum(v["rejected"] for v in per_type.values())
    total_false = sum(v["total"] for v in per_type.values())
    return {
        "true": {"survived": true_survived, "total": true_total},
        "per_type": per_type,
        "overall": {"survived_true": true_survived,
                    "rejected_false": rejected_false,
                    "total": true_total + total_false},
    }


def full_report(corpus):
    """Held-out is the score; tuning is reported separately, never merged."""
    return {
        "heldout": confusion(corpus["heldout"], corpus["evidence"]),
        "tuning": confusion(corpus["tuning"], corpus["evidence"]),
    }


def is_perfect(matrix):
    if matrix["true"]["survived"] != matrix["true"]["total"]:
        return False
    return all(v["rejected"] == v["total"] for v in matrix["per_type"].values())


def format_report(report):
    lines = []
    for name in ("heldout", "tuning"):
        m = report[name]
        lines.append("== %s ==" % name)
        lines.append("TRUE findings survived: %d/%d"
                     % (m["true"]["survived"], m["true"]["total"]))
        for t in FALSIFICATION_TYPES:
            v = m["per_type"][t]
            lines.append("%s rejected: %d/%d" % (t, v["rejected"], v["total"]))
    return "\n".join(lines)
