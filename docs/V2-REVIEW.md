# V2 independent adversarial review

Reviewer: native **gpt-6-astra**, **high** effort. Date: 2026-09-22. Scope: normalized warehouse, synthetic longitudinal scenarios, process replay, analytical marts and the bounded native-agent runtime. Production code was inspected read-only; the reviewer owns this report and `tests/test_v2_adversarial.py`. No business operation, contact, dispatch, payment or external source import was performed.

## Current verdict

**PASS for the reviewed synthetic V2 analytics and agent-runtime scope. All nine identified findings are corrected; no material known findings remain within this bounded review.** The independent 15-method run established 11 passing controls and four remaining issues. After those four corrections, all four affected tests were independently rerun and passed (1.042 seconds, zero failures/errors). Existing checks for unchanged inputs were retained rather than unnecessarily repeated. The parent separately reports 23/23 passing across the full V2 adversarial, warehouse and replay suites.

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p test_v2_adversarial.py -v
```

| ID | Priority | Evidence and affected file | Status / correction |
|---|---|---|---|
| V2-01 | P1 | `process_replay.py` and `studio_analytics.py` sorted ISO strings. Representing one unchanged timestamp with a -12:00 offset changed states, transition validity and accumulated stage durations. | Corrected and revalidated: sort on parsed datetime values. Both independent equivalence tests pass. |
| V2-02 | P1 | `studio_analytics.build_marts` accepted a January cutoff for the September snapshot, counting later payments and services. | Corrected and revalidated: reject unsupported cutoffs before materializing marts. |
| V2-03 | P2 | A valid open fleet order aged 40 hours under a 48-hour SLA was `on_track` in existing projections but `at_risk` in `studio_analytics.py`: the latter introduced an undocumented 80% threshold instead of the existing four-hour warning window. | Corrected and independently revalidated: both paths use the four-hour warning window. |
| V2-04 | P2 | `agent_runtime.METRIC_SQL['active_contracts']` returned 1 for an active contract whose effective window begins in 2027. | Corrected and revalidated: enforce approval and the effective window at the synthetic cutoff. |
| V2-05 | P2 | The local native-result validator accepted seven alternatives although its own supplied JSON schema permits six. | Corrected and revalidated: local checks enforce declared array/string bounds rather than trusting provider schema enforcement. |
| V2-06 | P1 | The native command declared that no shell/browser tools existed but only selected a read-only sandbox. Read-only did not enforce the intended mediated three-tool scope. | Corrected in command configuration: explicit feature disables and disabled web search; runtime now also rejects prohibited provider tool events. Inspection and mocked guard tests pass. Live execution under this revised policy belongs to the parent's native-run evidence. |
| V2-07 | P1 | `warehouse.py` unconditionally compared a history endpoint with `completed_at`. A valid open WO-007 initial-to-received event raised `DomainError: Fecha inválida` because completion is correctly absent. | Corrected and independently revalidated: completion endpoints are checked only when completion exists; valid open history retains opening/cutoff/state checks and is accepted. |
| V2-08 | P2 | A delivered work history with its initial event missing reached `next(...)` in `warehouse.py` and raised uncaught `StopIteration`, rather than a bounded validation error. | Corrected and independently revalidated: every group requires an initial event upfront and uses a first-event map; malformed history raises `ValueError`. |
| V2-09 | P2 | `event_id=None` passed the `str(value).strip()` check in `warehouse.py` and was stored because the auxiliary event primary key was nullable in SQLite. | Corrected and independently revalidated: nonblank actual string validation plus NOT NULL primary keys and STRICT auxiliary tables. |

## Controls verified

The updated warehouse rejects an initial event jumping directly to delivery, disconnected individually legal state edges, shifted business endpoints, post-cutoff events and a journey using a different quote for the same customer/vehicle. STRICT source tables reject both text and fractional values in integer monetary columns. These regression controls pass; the final warehouse edge corrections also passed independent revalidation.

The existing agent-runtime suite was independently run after the policy changes: **12/12 passed**. It covers nine separate profiles, bounded planning, out-of-scope evidence rejection, source-hash changes, exact field/value/version validation, disabled external execution, read-only SQL and refusal to claim model invocation for injected test responses. Mocked execution is test evidence only, not proof of a native model run.

An independent source-to-mart reconciliation on the 90-day synthetic scenario matched **20,982,500 invoiced cents**, **17,081,250 paid cents**, and **3,901,250 receivable cents**. Delivered-service history coverage is **160/162**; observed rework is **16/160**. The two delivered cases without event histories remain outside the measured rework denominator. These are fixture results, not findings about the real workshop.

Native receipts and file hashes are local evidence, not signatures against a malicious local editor. The workbench prepares diagnoses, alternatives and drafts for human review; this review does not authorize business actions or certify real SLA terms, operational safety, causal impact or production adoption. The parent owns final studio/workbook integration, actual native execution, complete-suite validation and publication.
