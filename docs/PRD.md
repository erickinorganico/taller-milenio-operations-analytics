# PRD — Taller Milenio Operations & Growth Analytics

## 1. Product statement

Build an offline, reproducible Analytics and consulting toolkit that models synthetic private-customer, workshop/parts, fleet, towing, and administrative journeys; measures defined snapshot signals; exposes data-quality and operational exceptions; and produces evidence-bearing recommendations for human review.

The product is a batch information package, not a navigable application or live operating system. It does not contact people, dispatch towing units, diagnose vehicles, set prices, issue fiscal documents, accept payments, or move money.

## 2. Evidence status

The implemented release is synthetic-only. No owner/operator interviews, direct observation, real-system connection, real-data import, or operational pilot has occurred. The process blueprint, metric definitions, thresholds, capacity, SLA terms, and playbooks are working hypotheses for a portfolio demonstration. They must not be presented as Taller Milenio performance or adopted process.

## 3. Users and jobs

| User role | Job supported by the toolkit | Excluded action |
|---|---|---|
| Owner/manager | review a reconciled snapshot, exceptions, evidence, and prioritized questions | treat synthetic values as current business truth |
| Analyst/consultant | validate an input, reproduce metrics, compare report lenses, prepare discovery | silently repair or discard bad records |
| Intake/workshop/parts stakeholder | review hypothesized funnel, WIP, block, capacity, and inventory definitions | operate work orders or promise completion dates |
| Fleet stakeholder | distinguish commercial pipeline, active contract, maintenance, SLA, and receivable states | send outreach or commit contract/SLA terms |
| Tow stakeholder | review milestone completeness and missing human gates | decide safety, assign a unit, promise ETA, or dispatch |
| Finance/admin stakeholder | reconcile quote, invoice, payment, receivable, expense, and cash concepts | use the output as fiscal accounting or execute money movement |

## 4. Functional requirements and acceptance evidence

| ID | Requirement | Acceptance evidence |
|---|---|---|
| PRD-01 | Generate a complete deterministic synthetic dataset across every contracted entity. | `dataset.json`, per-entity CSV, SQLite snapshot; fixture determinism and reference tests |
| PRD-02 | Validate field types, IDs, references, state consistency, time, money, stock, capacity, fleet, tow, invoice/payment, and source-proposal evidence. | domain and adversarial tests; invalid input fails before publishing a successful receipt |
| PRD-03 | Preserve customer, vehicle, lead, quote, appointment, work-order, QC/delivery, and rework as distinct analytical facts. | particulares/taller analysis and reports; candidate lead/quote matches labeled non-attribution |
| PRD-04 | Reconcile purchase, receipt, journal movement, reservation, consumption, return, adjustment, and availability. | Python reconciliation plus `queries/stock.sql`; negative, over-reserved, and mismatched-cost cases reject |
| PRD-05 | Separate fleet account, opportunity, proposal, contract, maintenance, service delivery, downtime, SLA, invoice, and collection. | fleet analysis/report and `queries/fleet_pipeline.sql`; unknown coverage excluded from measured SLA |
| PRD-06 | Analyze tow milestones and human-evidence completeness without deciding safety or dispatch. | grúas report, tow exceptions, agent boundary and adversarial tests |
| PRD-07 | Keep quote, authorized/fulfilled work, issued invoice, payment, receivable, expense, and cash distinct. | administration report, Python/SQL cross-check, `queries/finance.sql` |
| PRD-08 | Represent workshop state counts without calling them a temporal funnel or utilization history. | `queries/workshop.sql`, WIP report wording, lifecycle-evidence grade |
| PRD-09 | Produce four separate Markdown reports, a printable executive HTML report, and reproducible charts. | report completeness tests and artifact receipt |
| PRD-10 | Produce quality, exception, timeline, analysis, and proposal JSON with resolvable evidence and explicit limitations. | schema/agent/evidence tests; receipt manifest |
| PRD-11 | Make every generated proposal pending, approval-required, and unable to execute externally. | `contracts/action_proposal.schema.json`, agent grader, no execution adapter |
| PRD-12 | Preserve source immutability, reject an existing destination, build in staging, and publish receipt last. | four pipeline E2E tests and controlled-failure artifact |
| PRD-13 | Produce deterministic content hashes for identical input while excluding runtime-only variability from the content digest. | repeated pipeline runs and `verify-receipt` |
| PRD-14 | Run locally after dependency preparation, including a clean wheelhouse-based offline setup. | `Setup.ps1 -Offline` clean-environment check and verification receipt |
| PRD-15 | Scan bounded publication sources for credential/private-path patterns and neutralize spreadsheet formula text on CSV export. | publication sentinel and importer/exporter tests |
| PRD-16 | Reject any cutoff other than the fixed synthetic `DEMO_NOW`. | cutoff regressions; no arbitrary time-travel projection |

## 5. Required output package

One successful run contains:

- `dataset.json`, per-entity `csv/`, and `milenio.sqlite`;
- `analysis.json`, `quality.json`, `exceptions.json`, `timeline.json`, and `proposals.json`;
- `reports/particulares.md`, `flotillas.md`, `gruas.md`, and `administracion.md`;
- `reports/informe_ejecutivo.html` and `reports/charts/`;
- root `receipt.json` with checks, source/input identity, artifact hashes, and limitations.

The four fixed SQL query sets independently cross-check finance, fleet pipeline, stock, and workshop snapshots in read-only/query-only mode. They complement, rather than replace, Python reconciliation.

## 6. Analytical requirements by module

### Particular customers and workshop

Report current-state lead/quote/appointment/work-order distributions, candidate matches, follow-up exceptions, WIP, waiting parts, rework, and snapshot bay occupancy. Do not infer conversion attribution from customer/vehicle coincidence or call current-state occupancy historical utilization.

### Parts and inventory

Report on-hand, reserved, available, reorder exposure, and waiting-order evidence. Ordered purchases do not count as stock. Returns must reconcile quantity and valuation against the same part/work/cost basis.

### Fleets and growth

Separate open commercial pipeline from contracted service. Report captured versus declared fleet coverage, maintenance, delivered eligible services, open SLA status, unknown coverage, and receivables. Targeting is a transparent research heuristic, not purchase propensity; public-source research does not authorize contact.

### Towing

Report open/closed status, request-to-close duration where observable, and presence of human safety/approval references. Request-to-close is not response or arrival time. Missing evidence becomes review/exception, never software authorization.

### Administration

Report quotes, invoices, payments, receivables, expenses, and net cash as separate measures. The output is managerial demonstration data, not recognized revenue, tax reporting, or bank reconciliation.

## 7. History and cutoff contract

The built-in demo may generate fictional synthetic lifecycle events to exercise state-history validation. Their provenance must be declared fictional. An imported snapshot without a supplied, validated history has unknown transition coverage; the toolkit must not invent past events from current state.

Only `DEMO_NOW` is supported. A different cutoff is rejected because the snapshot cannot support arbitrary point-in-time reconstruction. Future temporal analysis requires a validated event source and a new contract.

## 8. Non-functional requirements

- Windows and Python 3.12+ supported; dependencies pinned and locally cacheable.
- No mandatory SaaS, paid API, secret, network connection, or external inference at runtime.
- Outputs deterministic for the same source, policy, and environment contract.
- Input copied before processing; fixed destination protected from overwrite.
- SQLite queries read-only; generated SQL identifiers come only from code-owned contracts.
- Reports readable in Markdown/browser/print without becoming an interactive product.
- Publication artifacts contain only synthetic or deliberately reviewed public material.

## 9. Definition of done and current acceptance

Done requires the complete artifact package, four report lenses, cross-reconciliations, governed proposals, controlled failure, clean offline setup, bilingual documentation, final full verification, bounded publication scan, orchestration record, and resolved adversarial findings.

The machine-readable authority for the released source state is `artifacts/final-verification.json`. CI platform/commit evidence and the bounded completion statement are recorded in `docs/COMPLETION.md`. Those artifacts supersede intermediate counts in planning notes; this PRD deliberately does not duplicate a test count that can drift.

## 10. Deferred work

Owner/operator discovery, validated metric targets, real-data pilot, authentication/authorization for sensitive files, production operations, messaging, integrations, dispatch, fiscal accounting, and impact/adoption measurement are separate future phases requiring explicit authority.
