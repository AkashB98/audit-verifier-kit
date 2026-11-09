# audit-verifier-kit

**Agent findings should not reach a customer report unchecked.** An agent
doing operations-audit work produces findings — a billing anomaly here, a
data-quality claim there — each citing evidence. Some of those findings are
wrong: the cited record does not exist, the quote does not match the source,
the number does not recompute, the evidence is outside the claimed window.
This kit puts an independent, deterministic verifier between the findings
and the report: it tries to *disprove* each finding against its own cited
evidence before the finding is allowed through.

The verifier can fail two ways, and both matter. Let a false finding through
and the report misleads the customer. Reject a real finding and the report
goes silent on a real problem. So the score is a confusion matrix, not a
single pass rate: true findings survived, and false findings rejected —
broken down by *how* each false finding was falsified.

> The verifier checks claims against evidence; llm-judge-calibration
> (sibling repo) measures how often judges agree — different problem.
> There is no model and no judge anywhere in this kit.

Stdlib only. Zero network. Fully deterministic (seeded data, seeded corpus).

## Quickstart

```bash
python3 -m cli generate                 # 60 seeded evidence records (JSON)
python3 -m cli verify --split heldout   # per-finding SURVIVES / REJECTED + reason
python3 -m cli report                   # held-out confusion matrix + tuning, separately
python3 -m cli check                    # CI gate: exit 0 PASS / 1 WARN / 2 FAIL
python3 -m cli demo                     # end-to-end asserted demo (incl. serve)
python3 -m cli serve                    # JSON API on 127.0.0.1:8091
python3 tests/run_tests.py              # 41 hermetic tests, stdlib only
python3 evals/run_evals.py              # 11 golden evals -> evals/eval_report.json
```

## How it works

**Evidence** (`audit_verifier/data.py`) — a deterministic seeded generator
creates 60 records for the fictional Helios Home retailer: 20 `order`,
20 `billing`, and 20 `quality` records, each `{id, kind, fields, timestamp}`,
internally consistent (an order's `total_cents` really is
`quantity * unit_price_cents`, and so on). Records are interleaved by kind so
any slice of the dataset covers all three kinds.

**Findings** (`audit_verifier/findings.py`) — a planted corpus of agent
audit findings (data-quality, policy-breach, and billing-anomaly claims).
Each finding is `{id, claim_type, statement, cited_record_id, quoted_values,
claimed_value, window_start, window_end}` plus a planted `truth_label` used
only for scoring:

| truth label | what was planted |
|---|---|
| `TRUE` | everything checks out against the cited record |
| `FABRICATED_CITATION` | the cited record does not exist |
| `WRONG_QUOTE` | a quoted value does not match the source record |
| `WRONG_CONCLUSION` | evidence is real, but the claimed number does not recompute from it (or the claim type is not supported by that evidence kind) |
| `STALE_EVIDENCE` | the evidence timestamp falls outside the claimed window |

The corpus is split into a **tuning set** (18 findings) and a **held-out
scoring set** (18 findings), disjoint in both finding ids and cited records,
seeded deterministically. Each split plants 6 true findings and 3 of each
falsification type. The held-out set is never tuned on; it is reported
separately, always.

**Verifier** (`audit_verifier/verifier.py`) — five deterministic,
evidence-based checks, no model or judge scoring anywhere:

1. the cited record exists;
2. every quoted value matches the source record exactly;
3. the claim type is supported by that evidence kind
   (`order -> order_total_cents`, `billing -> billing_difference_cents`,
   `quality -> defect_rate_pct`);
4. the claimed number recomputes from the cited record;
5. the evidence timestamp lies inside the claimed window.

Output per finding: `SURVIVES`, or `REJECTED` with the specific falsification
reason(s). The verifier never reads the planted truth label — a test and an
eval pin that stripping or relabelling a finding cannot change its verdict.

**Report** (`audit_verifier/report.py`) — the full confusion matrix on the
held-out set, per falsification type, plus the tuning-set results reported
separately.

**API** (`audit_verifier/api.py`) — stdlib `http.server` on `127.0.0.1`:
`GET /health`, and `POST /verify` with `{"finding": {...}, "evidence": [...]}`
(evidence optional; the seeded dataset is used by default).

## Measured results (held-out set)

| outcome | score |
|---|---|
| TRUE findings survived | 6/6 |
| FABRICATED_CITATION rejected | 3/3 |
| WRONG_QUOTE rejected | 3/3 |
| WRONG_CONCLUSION rejected | 3/3 |
| STALE_EVIDENCE rejected | 3/3 |

The tuning set scores identically (6/6 survived, 3/3 per type rejected) and
is reported separately in `evals/eval_report.json`. A perfect score on a
planted corpus is the expected bar, not a boast: the planted falsifications
are exactly the failures the five checks are defined to catch. The value for
a real deployment is the *shape* — per-type rejection plus true survival —
because that is what tells you which way a verifier is failing when it does.

## Evals

`python3 evals/run_evals.py` — 11 golden evals pinning evidence determinism
and balance, tuning/held-out disjointness, per-type held-out rejection,
true-finding survival, the pinned held-out confusion matrix, separate tuning
results, and label-blindness of the verifier. `evals/eval_report.json` is
committed; md5 `d2f2b28cef397d6c4da30f37a70b5951`, byte-identical across runs.

## Validated design decisions

- **Interleaved evidence generation.** Records are generated round-robin by
  kind (order, billing, quality) rather than in kind blocks, so the first /
  second half split that defines tuning vs held-out leaves both sets
  covering all three claim types. A block layout would have silently made
  one set order-only at the top.
- **Fabricated citations short-circuit.** If the cited record does not
  exist, no other check can run, so the verdict carries exactly one reason:
  `FABRICATED_CITATION`. Other failures can stack (a finding can be both
  misquoted and stale), and the reasons list preserves all of them.
- **Recompute, don't compare to a stored answer.** For orders and billing
  the verifier recomputes from the raw inputs (`quantity * unit_price`,
  `billed - expected`) rather than trusting the record's stored total
  fields, so a corrupted stored total cannot launder a wrong claim.
- **Label-blindness is tested, not assumed.** The planted `truth_label`
  rides along on corpus findings for scoring; dedicated tests strip and
  relabel findings and assert identical verdicts.

## Honest scope limits

- This is not a security or vulnerability tool, and it does not judge
  whether a finding is *important* — only whether its cited evidence
  supports it as stated.
- The corpus is synthetic and planted: falsifications are clean,
  single-cause defects. Real agent findings fail messier ways (ambiguous
  quotes, partially supporting evidence, units mismatches) that these five
  checks do not cover.
- One cited record per finding. Claims that need to join several records
  would need a multi-citation extension of the finding schema.
- Claim support is a fixed table of three claim types. A new claim type is
  a code change (a recompute function plus a table entry), not a config
  change.

## Layout

```
audit_verifier/  data.py (evidence)  findings.py (planted corpus)
                 verifier.py (5 checks)  report.py (confusion matrix)
                 api.py (stdlib HTTP)
cli.py           generate / verify / report / check / demo / serve
demo.py          end-to-end asserted demo incl. serve round-trip
evals/           run_evals.py -> eval_report.json (11 evals)
tests/           41 hermetic unittest tests, no-network guard included
```

All data is fictional (Helios Home). No secrets, no personal data, no
network. MIT license, © 2026 Akash Bhargava.
