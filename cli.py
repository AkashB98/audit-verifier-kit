#!/usr/bin/env python3
"""CLI: generate / verify / report / check / demo / serve."""
import argparse
import json
import sys

from audit_verifier.api import serve
from audit_verifier.data import evidence_index, generate_evidence
from audit_verifier.findings import build_corpus
from audit_verifier.report import format_report, full_report, is_perfect
from audit_verifier.verifier import verify_all


def _cmd_generate(args):
    records = generate_evidence()
    print(json.dumps(records, indent=2, sort_keys=True))
    return 0


def _cmd_verify(args):
    corpus = build_corpus()
    findings = corpus[args.split] if args.split != "all" else \
        corpus["tuning"] + corpus["heldout"]
    index = evidence_index(corpus["evidence"])
    for result in verify_all(findings, index):
        line = "%s %s" % (result["finding_id"], result["verdict"])
        if result["reasons"]:
            line += " " + ",".join(result["reasons"])
        print(line)
    return 0


def _cmd_report(args):
    print(format_report(full_report(build_corpus())))
    return 0


def _cmd_check(args):
    """CI gate: 0 = perfect held-out, 1 = WARN (>=80% both ways), 2 = FAIL."""
    report = full_report(build_corpus())
    held = report["heldout"]
    if is_perfect(held):
        print("PASS held-out verifier is perfect: %d/%d true survived, "
              "%d/%d false rejected"
              % (held["true"]["survived"], held["true"]["total"],
                 held["overall"]["rejected_false"],
                 held["overall"]["total"] - held["true"]["total"]))
        return 0
    true_rate = held["true"]["survived"] / max(1, held["true"]["total"])
    false_total = held["overall"]["total"] - held["true"]["total"]
    rej_rate = held["overall"]["rejected_false"] / max(1, false_total)
    if true_rate >= 0.8 and rej_rate >= 0.8:
        print("WARN held-out true survival %.2f, false rejection %.2f"
              % (true_rate, rej_rate))
        return 1
    print("FAIL held-out true survival %.2f, false rejection %.2f"
          % (true_rate, rej_rate))
    return 2


def _cmd_demo(args):
    import demo
    return demo.main()


def _cmd_serve(args):
    return serve(port=args.port)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="audit-verifier-kit")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate")
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--split", choices=("tuning", "heldout", "all"),
                          default="heldout")
    sub.add_parser("report")
    sub.add_parser("check")
    sub.add_parser("demo")
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--port", type=int, default=8091)
    args = parser.parse_args(argv)
    handlers = {"generate": _cmd_generate, "verify": _cmd_verify,
                "report": _cmd_report, "check": _cmd_check,
                "demo": _cmd_demo, "serve": _cmd_serve}
    try:
        return handlers[args.command](args)
    except Exception as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
