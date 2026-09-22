# Adversarial review of the analytics toolkit

Reviewer: native **gpt-6-astra**, **high** reasoning effort. Review date: 2026-09-22.
Scope: the corrected local analytics-only toolkit, its deterministic sources, invariants, metrics, lifecycle evidence, proposals, reports and artifact receipt. The archived application under `.workbench` is excluded. No business systems, contacts, dispatch, payments or external APIs were exercised.

## Final verdict

**PASS for the reviewed synthetic, local analytics scope. All nine confirmed findings are corrected and independently revalidated; no material known findings remain in that scope.** The final adversarial run executed **15 tests, zero failures and zero errors**. This is a bounded review conclusion, not a guarantee of defect absence or production certification.

Findings below were established from executable mutations of synthetic fixtures, not hypothetical operational risks. The review owns `tests/test_adversarial.py` and this report; production fixes were integrated by the parent agent.

Run the independent suite with:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p test_adversarial.py -v
```

## Confirmed findings — all resolved

| ID | Original priority | Original finding and reproduction | Correction verified in final rerun |
|---|---|---|---|
| ADV-01 | P1 | `sla_open_at_risk` included `on_track` in its numerator, making every eligible open order appear at risk. An additional received fleet order with a 200-hour SLA is on track yet originally counted at risk. | Count only at-risk/breached open orders over all eligible open orders. Parent correction already passes the independent regression. |
| ADV-02 | P1 | Changing CT-001 to `draft` or `cancelled` while retaining dates and approval reference passes source validation and labels WO-009 SLA `breached`. A nonoperative contract snapshot does not establish historical coverage. Cancelled work under an unknown contract also becomes an unnecessary unknown-SLA exception. | Preserve the source as analyzable but classify coverage `unknown` unless the contract state/evidence establishes applicability; exclude it from the measured SLA denominator. Evaluate work cancellation first so cancelled work remains `excluded` regardless of contract evidence. |
| ADV-03 | P1 | `analyze(fixture, '2026-09-01T00:00:00Z')` reports 185,000 cents of payments and September 18–21 service outcomes at an earlier cutoff. Validation used a fixed demo cutoff but projections accepted arbitrary cutoffs. | Reject unsupported snapshot cutoffs consistently; a future implementation may support genuine point-in-time reconstruction. Do not clamp future work durations to zero. |
| ADV-04 | P1 | Returning both consumed units at zero unit cost passes validation and leaves 3,600 cents of net consumption cost with zero net consumed units. Quantity and valuation reconciliation disagree. | Reconcile return quantity against consumed quantity at the same part/work/cost basis, or introduce explicit source movement linkage and a documented valuation policy. |
| ADV-05 | P2 | An `in_service` work order accepts `completed_at=opened_at`; projections then freeze its ongoing elapsed time at zero. | Reject completion timestamps incompatible with open states; ensure elapsed time for an open order runs to the cutoff. |
| ADV-06 | P2 | Shifting all WO-001 lifecycle events one day earlier preserves legal state order and grades history complete despite contradicting `opened_at` and `completed_at`. | Reconcile lifecycle start/terminal timestamps to corresponding snapshot business timestamps, in addition to state and sequence checks. |
| ADV-07 | P2 | Adding `unexpected/receipt.json` to an otherwise verified package is ignored because receipt verification excluded every matching basename. | Exempt only the root receipt and reject every additional unmanifested artifact. |
| ADV-08 | P2 | A measured duration of `0.0` renders as `Sin casos` through a truthiness fallback, falsely replacing an observed value with absence. | Test explicitly for `None` when rendering durations. |
| ADV-09 | P2 | Source proposal references can include a nonexistent field, invented value and version 999 while passing domain validation. Generated proposals are graded more strictly than imported proposal records, yet both persist in the source package. | Validate source proposal agent and reference structure; check supplied field/value/version against the source. Record-only references must remain clearly distinguished from fully validated field evidence. |

Malformed records in ADV-04/05/06/09 now fail validation. Insufficient contract evidence in ADV-02 remains visible as `unknown`, while cancelled work remains `excluded`. Source proposals now require the full entity/field/value/version evidence contract; record-only source references are rejected.

## Controls directly checked

- Capacity: duplicated active bay assignments reject. The analysis labels bay use as snapshot occupancy, not utilization over hours.
- Source joins: a mismatched invoice/customer join rejects. Existing domain checks reconcile vehicle ownership, quoted work, fleet contracts, maintenance and service invoices.
- Agent boundary: generated proposals require pending status, approval and disabled external execution; invented field evidence rejects. The agent module exposes no external action adapter.
- Financial concepts: quotes, issued invoices, payments, receivables and cash remain distinct; invoice amount and recorded payment bounds are checked. This is managerial demonstration data, not fiscal accounting or recognized revenue.
- SLA methodology: completed eligible services have their own denominator, missing coverage remains unknown, and open services are separated. ADV-01/02 must remain covered by regressions.
- Import/output boundary: snapshot inputs are deep-copied; builds stage locally and require a fresh destination. Invalid sources cannot publish a success receipt through the normal pipeline. CSV export neutralizes formula-like textual cells.
- Evidence claims: synthetic lifecycle paths declare fictional provenance; imported snapshots without events do not invent observed history. Lead/quote matches are explicitly candidates, not attributed conversions. Tow request-to-close time is not response or arrival time.

## Publication and remaining limits

The reviewed fixtures are generated locally and explicitly synthetic. Name-like values and company-like labels in them are fictional examples, not evidence about real people or businesses. `synthetic=true` is a source assertion, not an anonymization or secret-detection mechanism; authorized publication must use the generated fixtures and deliberately reviewed examples. No external source data was imported during this review.

Artifact hashes detect changes relative to the saved manifest; they are not a digital signature and cannot establish authenticity against an actor who rewrites the manifest too. No claim of production readiness, real SLA performance, real capacity, marketing impact or business adoption is supported by this review. Operator discovery and a governed real-data pilot remain separate work.

Publication itself and final Setup execution belong to the parent task. The reviewed CLI is batch-only (`demo`, `analyze`, `controlled-failure`, `verify`, `verify-receipt`, staging `import` and `export`); it exposes no HTTP server or live dispatch command. No remote push or deployed-state claim is made here.

## Revalidation record

Initial run: 11 independent test methods, 8 failing subtests across seven methods after ADV-01 was corrected concurrently. ADV-09 and the cancelled-work/unknown-contract case were subsequently added. A follow-up run passed 11 of 13 methods: only the cancelled-work/unknown-contract edge of ADV-02 and zero-duration rendering ADV-08 remained failing.

Inspection of the corrections confirmed matching cost-bucket returns, full source field evidence validation, business-history endpoint anchoring, fixed-cutoff rejection and root-only receipt exemption. Two additional control methods cover negative service durations and normal edited/deleted artifact detection, bringing the suite to 15 methods.

**Final independent rerun, 2026-09-22: 15/15 passed (0.186 seconds), exit code 0.** Cancellation precedence and zero-duration rendering now pass. Every regression corresponding to ADV-01 through ADV-09 passes, alongside the capacity, ownership, negative-time, agent-boundary and artifact-integrity controls. Production fixes were inspected; the tests were not weakened to obtain a pass.

## Bounded review of final integration

`milenio/sql.py` obtains identifiers from the code-owned field contract, opens query snapshots with SQLite `mode=ro`, enables `query_only`, and executes fixed local query files. Fleet and stock queries aggregate their one-to-many inputs before joining, avoiding multiplication of sums. The pipeline compares four financial fields from SQL and Python before writing the final receipt and publishing the staged directory.

A separate temporary-database check executed all four query sets (`finance`, `fleet_pipeline`, `stock`, `workshop`). The SQLite file SHA-256 was identical before and after the read-only queries. Independently queried and Python-calculated amounts matched exactly: invoiced 695,000; paid 185,000; receivable 510,000; net cash -18,000, all in MXN cents. Negative net cash is a signed cash-flow observation, not a negative receivable.

The bounded publication sentinel was independently rerun: **PASS, 71 files scanned, no findings**. Its code explicitly describes its heuristic scope and does not certify anonymization. The new verification harness discovers stdlib tests, records failures/errors, checks pinned installed dependencies, scans publication sources and emits receipts; the parent task owns the final complete-project run. These checks support the synthetic toolkit signoff above and do not establish real business safety, adoption or impact.
