#!/usr/bin/env python3
"""Golden evals: pin the held-out confusion matrix and tuning results.

Deterministic and byte-stable: no timestamps, sorted keys, fixed corpus.
The verifier is never tuned on the held-out set; these evals only measure it.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_verifier.data import generate_evidence
from audit_verifier.findings import build_corpus
from audit_verifier.report import full_report, is_perfect

RESULTS = []


def check(name, passed, **detail):
    entry = {"name": name, "passed": bool(passed)}
    if detail:
        entry["detail"] = detail
    RESULTS.append(entry)
    print(("PASS " if passed else "FAIL ") + name)
    return bool(passed)


def main():
    corpus = build_corpus()
    report = full_report(corpus)
    held, tuning = report["heldout"], report["tuning"]
    ok = True

    ok &= check("evidence_determinism",
                generate_evidence() == generate_evidence()
                and len(generate_evidence()) == 60,
                n=len(generate_evidence()))

    ok &= check("evidence_kinds_balanced",
                all(sum(1 for r in corpus["evidence"] if r["kind"] == k) == 20
                    for k in ("order", "billing", "quality")))

    tuning_ids = {f["id"] for f in corpus["tuning"]}
    heldout_ids = {f["id"] for f in corpus["heldout"]}
    tuning_cited = {f["cited_record_id"] for f in corpus["tuning"]
                    if f["truth_label"] != "FABRICATED_CITATION"}
    heldout_cited = {f["cited_record_id"] for f in corpus["heldout"]
                     if f["truth_label"] != "FABRICATED_CITATION"}
    ok &= check("tuning_heldout_disjoint",
                not (tuning_ids & heldout_ids)
                and not (tuning_cited & heldout_cited)
                and len(tuning_ids) == 18 and len(heldout_ids) == 18)

    ok &= check("heldout_true_survive_all",
                held["true"] == {"survived": 6, "total": 6},
                **held["true"])

    for eval_name, label in (
            ("heldout_fabricated_rejected", "FABRICATED_CITATION"),
            ("heldout_wrong_quote_rejected", "WRONG_QUOTE"),
            ("heldout_wrong_conclusion_rejected", "WRONG_CONCLUSION"),
            ("heldout_stale_rejected", "STALE_EVIDENCE")):
        v = held["per_type"][label]
        ok &= check(eval_name, v == {"rejected": 3, "total": 3}, **v)

    ok &= check("tuning_results_perfect_separate",
                is_perfect(tuning) and tuning["overall"]["total"] == 18,
                total=tuning["overall"]["total"])

    # The verifier must not cheat: stripping truth labels changes nothing.
    from audit_verifier.data import evidence_index
    from audit_verifier.verifier import verify_all
    stripped = [{k: v for k, v in f.items() if k != "truth_label"}
                for f in corpus["heldout"]]
    index = evidence_index(corpus["evidence"])
    ok &= check("verifier_ignores_truth_labels",
                verify_all(stripped, index)
                == verify_all(corpus["heldout"], index))

    ok &= check("heldout_confusion_matrix_pinned",
                held == {
                    "true": {"survived": 6, "total": 6},
                    "per_type": {
                        "FABRICATED_CITATION": {"rejected": 3, "total": 3},
                        "WRONG_QUOTE": {"rejected": 3, "total": 3},
                        "WRONG_CONCLUSION": {"rejected": 3, "total": 3},
                        "STALE_EVIDENCE": {"rejected": 3, "total": 3},
                    },
                    "overall": {"survived_true": 6, "rejected_false": 12,
                                "total": 18},
                })

    out = {
        "evals": RESULTS,
        "passed": sum(1 for r in RESULTS if r["passed"]),
        "total": len(RESULTS),
        "heldout": held,
        "tuning": tuning,
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "eval_report.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("evals: %d/%d passed" % (out["passed"], out["total"]))
    return 0 if ok and out["passed"] == out["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
