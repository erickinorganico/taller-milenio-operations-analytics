# V6 cross-phase integration review — 2026-09-22

Scope: independent read-only trace of the current checkout against `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, and Phase 5–8 plans. Phase 5–7 summaries now exist; the Phase 8 summary was still pending at this inspection. The provides/consumes map was checked against the implementation. Local fixtures and package acceptance are separate gates.

## Integration Check Complete

### Wiring Summary

**Connected:** six principal interfaces: V5 models → analytics materializer; analytics models → snapshot dashboard; snapshot references → protected source explorer; audit events/intervals → worker job; worker → snapshot and agents; launcher → worker lifecycle. **Orphaned key exports:** none found. **Missing cross-phase connections:** none in the tested local candidate. Its release/publication state remains separate.

### API Coverage

There are no new V6 JSON API routes. The six V6 HTML/POST endpoints (`/`, `/analytics/`, `/analytics/data/<key>/`, `/automations/`, `/automations/configure/`, `/automations/enqueue/`) have navigation, link, or form callers. Dashboard JSON and mart CSV exports have guarded handlers and UI links. Call paths were traced and Django client tested. Browser observations below come from the parent reviewer; I did not repeat them.

### Auth Protection

Dashboard and worker history require `intelligence_read`; mart browse/CSV and dashboard JSON require `data_read`; configuration requires `manage`; enqueue requires `review`. Source links use `/data/<key>/?id=<pk>`, also guarded by `data_read`. The landing page routes only intelligence readers to the dashboard. No unprotected V6 data endpoint was found by static trace. An authorized `advisor` can now see delivery/wait coverage counts without `data_read`.

### E2E Flows

| Flow | Full connection traced | Status/evidence |
|---|---|---|
| Operations to display | V5 order/quote/movement/invoice/payment/audit → atomic `refresh_analytics` → `AnalyticsSnapshot`/`AnalyticsRow` → date/segment builder → guarded dashboard/mart/export | WIRED; semantic fixtures and Django client tests pass |
| Business change to human follow-up | V5 `AuditEvent`/periodic due → deduplicated job → snapshot → three live agent runs → evidence proposal → review → task/owner → observed outcome | WIRED in code and fixtures; parent reports browser interval job produced a snapshot and three runs |
| Worker control/lifecycle | `run_web` migrate → child `run_automations --watch-parent` → pause/resume → lease heartbeat/recovery → server stop closes child stdin | WIRED in code; pause/recovery/heartbeat tests pass; parent reports pause held a queued job; process restart untested here |
| V5 to distributable V6 | V5 fixture → V6 migrations → analytics/queue → backup/restore → ZIP → extracted server/dashboard/worker | WIRED for candidate2 SHA `a0845d2f…` and its matching receipt |

I independently ran `manage.py test workshop.tests.test_analytics workshop.tests.test_automation workshop.tests.test_analytics_web --noinput` using `MILENIO_MODE=test` and disposable temp data: **38 tests, 0 failures** after the analytics, worker and UI fixes. After the native-output and demo-seed changes, I separately ran `test_intelligence` and `test_analytics_demo`: **24 tests, 0 failures**. At this independent review, the full `artifacts/v6-verification.json` reported **115 tests, 0 failures, 0 errors, 2 skipped** because the legacy fixed demo/live ports were already occupied; the extracted candidate uses an ephemeral port and its own HTTP smoke. `artifacts/v6-delivery-verification.json` reports preserved V5 fixture data, restored V6 counts/fingerprint, fresh-demo 36 V6 orders and disabled temporary actor, authenticated extracted `/analytics/` and `/automations/` HTTP 200, worker heartbeat/completed job, and stdin shutdown for ZIP SHA-256 `a0845d2f2a418f863e86d06a0da2a42999849018146c0b92081a4cf916e8fa1f`. I independently matched the ZIP SHA and verified its native code, seed command, and focused tests match current source bytes.

### Detailed Findings

#### No open cross-phase blocker in the tested local candidate

Candidate2 (`dist/Milenio-V6-review-candidate2.zip`) has 158 ZIP members; the receipt verifies 157 payload hashes and the actual extracted server, dashboard, worker and shutdown. The tested candidate includes the native-output and demo-seed fixes. This establishes local technical integration for DEL-05. A later documentation-only release ZIP needs its own exact-SHA receipt before that new artifact inherits this conclusion; no real customer data, live deployment, client acceptance or native Codex inference was tested by the package smoke.

#### Planning traceability after reconciliation

The Phase 6/7 plans now name the implemented `workshop/analytics_views.py` and `workshop/tests/test_analytics_web.py`; Phase 5–7 summaries exist. A Phase 8 summary was not present at this inspection, so GSD phase closure remains a planning/evidence step. It is not an application connection break.

### Resolved during review

- **AUT-02 queue and mode:** the initial pause logic still claimed pending jobs, and automatic jobs ignored `policy.native_enabled`. The worker now leaves queued work pending during pause, uses configured automatic mode, and sleeps on paused ticks. Updated tests pass; the parent reports a browser pause check.
- **ANA-01/05 coverage:** `dashboard.html:11` shows observed delivery/wait counts and missing-promise/audit counts outside the `data_read` block; the advisor path is tested.
- **AGT-04/05 cut disclosure:** the snapshot is still recorded before live agent review. `automation.py:215-227` stores snapshot/post-agent audit cursors and an advancement flag; `automations.html` displays the warning and cursor pair. The marker detects audited activity only. The UI says agents use current records, and proposal acceptance revalidates evidence. It does not claim that both reads share one immutable cut.
- **AUT-03/04 lease:** `automation.py:233-296` renews the lease on a separate connection and fences final job/state writes by lease owner. Tests cover renewal and stale-owner finalization; interrupted native work remains single-attempt.
- **Native output safety (AGT-04/05):** `intelligence.py:655-679,734-757` requires a nonempty cited `entity_type`/`entity_id`; `run_native_agent` retains a completed CLI receipt and `model_invoked=True` when output fails validation, marks that run failed and creates no proposals. Focused tests pass; no actual model call was independently made in this review.
- **Fresh demo path (ANA-01, DEL-05):** `seed_workshop.py:130-143` invokes the V6 synthetic seed before disabling its temporary demo actor; tests and the extracted candidate receipt confirm 36 dated orders, a first cut and an inactive temporary actor, while live-mode guards remain.

### Requirements Integration Map

| Requirement | Integration path | Status | Issue or limit |
|---|---|---|---|
| ANA-01 | snapshot rows → period/segment builder → protected landing dashboard | WIRED | Client tests; parent reports browser filter check |
| ANA-02 | signed movements → `part_usage` → units/orders ranking and mart | WIRED | Fixtures exclude purchases/reservations and count returns |
| ANA-03 | approved quote lines + invoice association → `service_lines` → ranking | WIRED | Quote version and billed-association fixtures pass |
| ANA-04 | invoice/payment dates → `receivables`/trend → dashboard | WIRED | Separate dates, voids and balance tested |
| ANA-05 | audited delivery/wait intervals → medians and visible coverage | WIRED | Observed counts now reach advisor dashboard |
| ANA-06 | V5 tables → atomic refresh → immutable snapshot/rows/fingerprint | WIRED | Old cut unchanged after source mutation |
| ANA-07 | snapshot → guarded mart/CSV/JSON → source ID lookup | WIRED | Permission and CSV neutralization tests pass |
| AUT-01 | audit cursor/interval → job → worker refresh and agents | WIRED | Fixtures and parent-reported browser interval run |
| AUT-02 | manager form → policy → pause/frequency/native mode → worker | WIRED | Tests; parent reports pending job held during pause |
| AUT-03 | durable job → attempts/renewed lease/recovery → history | WIRED | Retry, renewal, stale owner and native ambiguity tests pass |
| AUT-04 | launcher child → heartbeat/state UI → stop/restart lease path | WIRED | Extracted launch/shutdown passed; lease recovery tested with simulated expiry |
| AGT-04 | worker → current live findings → evidence proposals | WIRED | Cut sequence and audit advancement disclosed; acceptance rechecks |
| AGT-05 | job → run → proposal → decision → task owner/outcome | WIRED | Django client and intelligence paths traced |
| DEL-05 | migration/backup/docs/package → extracted startup | WIRED | Candidate2 exact-SHA smoke passed; later release ZIP requires its own receipt |

**Requirements with no cross-phase wiring:** none. All 14 requirements have a producer/consumer path in the tested local candidate. Client acceptance and release publication are separate from this technical result.

### Subsequent integration correction (primary agent)

CI exposed a stale expectation of two demo orders in a previously skipped legacy launch test. The primary agent updated it to 38 orders, selected temporary ports and used supervised shutdown. All 11 affected delivery tests passed locally. Final suite/CI and release receipts supersede the earlier fixed-port skips; this note does not claim an additional independent review. Runtime analytics and native code are unchanged.
