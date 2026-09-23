# V5 intelligence contract

## Purpose and boundary

`workshop.intelligence` builds a live operational read model and three role-specific
agent runs: `operations`, `collections`, and `data_quality`. Rules mode is ordinary
Python and is the default. It does not call a model. Native mode is optional and
requires `MILENIO_CODEX_ENABLED=1`; when enabled it uses only the local Codex CLI,
one bounded turn, temporary empty working directory, JSON schema output, read-only
sandbox, and disabled external/tool integrations. Paid provider API-key environment
variables are removed from the child process; no paid API or fallback inference
service is in this contract. An initial local preflight reported Codex CLI
`0.155.1` as “Not logged in” on 2026-09-22; a later authenticated run on the
synthetic V5 demo completed with GPT-6 Luna. The run #5 receipt in
`artifacts/v5-native-verification.json` records `turn.completed`, valid JSON,
`model_invoked=true`, no injected runner, no business-record mutation, and a valid
empty proposal list. Each installation still needs its own authenticated session;
failures are persisted visibly.

Neither rules nor native agents may alter workshop business records, diagnose a
vehicle, authorize work, send a message, order a part, dispatch a tow, or move
money. They can persist evidence-bound proposals. A human reviewer with the
`review` capability may accept one to create one `ActionTask`, reject it, or see it
marked stale if its cited database evidence changed. Task completion requires an
observed human outcome and stores a fresh deterministic check of the proposal's
trigger. That check is not proof of impact or causality.

## Python API

```python
build_metric_catalog() -> list[dict]
build_dashboard(as_of: datetime | None = None) -> dict
run_agents(actor, mode="rules", agent="all") -> list[AgentRun]
run_native_agent(actor, agent_id, *, existing_run=None,
                 base_findings=None, native_runner=None) -> AgentRun
review_proposal(proposal_id, actor, decision, note="") -> Proposal
complete_action_task(task_id, actor, outcome) -> ActionTask
```

`build_dashboard` returns `schema_version`, the calculation `as_of` time,
`generated_at`, a compact `headline`, the detailed `metrics` array, and global
limitations. Metric objects carry a stable `metric_id`, domain/definition/unit,
status (`measured` or `unknown`), value/reason, numerator/denominator values,
coverage, time boundary, up to 12 evidence rows, total evidence count, and
drilldown references. An empty eligible population is `unknown` with a reason,
never an asserted zero. `as_of` is a calculation cutoff, not a historical database
snapshot: ordinary record totals describe rows currently stored.

| ID | Meaning and calculation boundary |
| --- | --- |
| `OPS-WIP` | Count of work orders in the eight nonterminal operating statuses. Delivered and cancelled are excluded. Unknown until any work order exists. |
| `OPS-LATE` | Count of open work orders whose promised timestamp precedes `as_of`; coverage reports open work orders lacking a promise date. |
| `OPS-DELIVERY-CYCLE` | Median calendar hours from order creation to a matching audited transition to `delivered`; does not use `updated_at` or labor minutes. |
| `FIN-INVOICED` | Sum of non-voided administrative `Invoice.total`; not a CFDI or fiscal ledger. |
| `FIN-PAYMENTS` | Sum of locally recorded payments; does not prove bank settlement. |
| `FIN-OPEN-BALANCE` | Sum, by non-voided invoice, of `max(total - associated payments, 0)`. |
| `SALES-QUOTE-APPROVAL` | Percentage (0–100); per work order, latest decided quote version is the decision; approved / approved-or-rejected. Draft, sent, and superseded versions are excluded. |
| `FIN-DIRECT-MARGIN` | Estimated sum of invoice subtotal minus extended costs captured in the approved quote when every line has a known unit cost. It is not actual inventory cost. Excludes invoices with missing quote/lines/costs and excludes overhead/labor burden. |
| `DATA-LAST-EVENT` | Minutes since the latest stored audit event at or before `as_of`. Measures local recorded activity, not external system freshness. |
| `INV-LOW-STOCK` | Count of catalog SKUs where physical stock minus reserved stock is at or below configured reorder point. |
| `INV-STOCK-VALUE-COST` | Physical stock multiplied by positive catalog unit cost. Zero/nonpositive costs are excluded and reported as incomplete valuation coverage; this is not accounting valuation. |
| `OPS-HOURS-LOGGED` | Sum of recorded `TimeEntry.minutes` divided by 60. It does not estimate utilization, capacity, or missing hours. |
| `MAINT-OVERDUE-DATE` | Scheduled plans with `due_date` before the local cutoff date; coverage also reports scheduled plans without a date. |
| `MAINT-OVERDUE-ODOMETER` | Scheduled plans whose due odometer is reached/exceeded, among plans with a current vehicle odometer. Missing readings stay outside the evaluated denominator and are counted in coverage. |
| `FLEET-EXPIRING-30D` | Active contracts ending from the local cutoff date through 30 days later, inclusive. No SLA performance or renewal probability is inferred. |
| `TOW-OPEN` | Tow requests in `requested`, `assigned`, `en_route`, or `arrived`; completed and cancelled records are excluded. |
| `TOW-MEDIAN-ARRIVAL-MIN` | Median request-to-arrival duration using only known, nonnegative timestamp pairs. Negative intervals are excluded and counted. |
| `TOW-MEDIAN-COMPLETE-MIN` | Median request-to-completion duration using only known, nonnegative timestamp pairs. Negative intervals are excluded and counted. |

Currency is the recorded MXN amount. Margin and collection balances are not
recommendations to collect or spend. Evidence is a capped sample with an uncapped
total; absence from the sample is not proof of absence from the full population.

## Deterministic agent findings

Rules findings are narrow trigger records with a primary entity, exact field
snapshots, a rule kind, a short explanation, and a safe human follow-up. Operations
flags overdue open orders, `waiting_parts`, `quality`, `ready`, low available
stock, and scheduled maintenance whose date and/or known odometer limit has passed.
Collections flags positive balances and separately marks due balances overdue.
Data quality flags active orders missing a promised date or assigned owner, and
maintenance plans that cannot be evaluated by odometer because the vehicle reading
is missing. Every finding is only a prompt for internal review, not an autonomous
action. Re-running unchanged rules suppresses duplicate pending proposals and
proposals with an accepted open task; changed evidence stales an older pending
proposal before opening a replacement.

Each `AgentRun` records its role, mode, started/finished timestamps, source
fingerprint, status, evidence and output. A rules run always has
`model_invoked=False`. Failures remain persisted as `failed` with a bounded error;
they are never translated into a successful empty result. Native proposals must
cite one or more indices in the packet, and at least one cited row must match the
declared entity type and key. Duplicate/out-of-range indices and malformed or
cross-entity claims are rejected.

For actual CLI inference, `model_invoked=True` is set only after the subprocess
returns successfully, the JSON event stream confirms `turn.completed`, the
structured output file exists, and the output passes schema and evidence checks.
On Windows, the resolver prefers the bundled native `.runtime/codex/.../codex.exe`
and rejects shell scripts such as `.cmd`, `.bat`, or `.ps1`; it can use a native
executable on PATH. The child keeps local CLI login state available while removing
`OPENAI_API_KEY`, `CODEX_API_KEY`, Azure OpenAI keys/endpoints, and OpenAI-compatible
base URL overrides. CLI config is ignored, apps/plugins, shell and web/browser tools
are disabled, and the working directory is empty.
The injectable runner exists for offline tests only; mocked runs retain
`model_invoked=False` and cannot be used as evidence that the model ran.

## Proposal review and follow-through

Proposal fingerprints cover the stored evidence object. Collection evidence
includes an aggregate fingerprint, count, and total over the entire invoice
payment set in addition to a capped row sample. A new payment that clears a
balance therefore invalidates the proposal even when prior payment rows are
unchanged. Before acceptance, the service confirms that the fingerprint still
matches, every referenced model and field is allowlisted, every exact cited value
still matches a current row, and a reference points to the proposal's declared entity. If evidence is stale, the
proposal is marked `stale` and no task is created. A reviewer without the `review`
capability is denied. Repeated acceptance returns the accepted proposal and the
one-to-one relationship guarantees at most one task.

An accepted proposal creates an internal task only; it does not update the
underlying order or financial record. Closing the task needs a nonempty observed
outcome from a reviewer or the person assigned to the task with `complete_task` capability (operational roles only); a read-only viewer remains forbidden even if previously assigned, and another technician
cannot close it. The service re-evaluates its deterministic trigger and appends that
result to the audit event. `not_detected` means only that this rule did not find
the original case on this local recheck.

## Validation and known boundaries

Focused tests cover empty/unknown populations, invoice/payment/balance separation,
audited delivery timing, cost completeness, inventory, logged labor, date and
odometer maintenance, fleet expiry, tow timestamp coverage, role runs and honest
model status, reviewer/assigned-technician authorization, related-payment staleness,
proposal deduplication, idempotent acceptance, human task outcomes, native failure
persistence, and adversarial entity references. The 18 intelligence tests use
mock runners to exercise failure paths; they are separate from the authenticated
real CLI turn recorded in `artifacts/v5-native-verification.json`. That single
synthetic run verifies the adapter and response validation, not business impact or
reliability across users and installations.

The current metrics cover available V5 operational models, but do not infer
utilization without a capacity denominator, an SLA not explicitly stored, actual
inventory cost beyond captured catalog cost, external payment settlement,
accounting valuation, mechanical diagnosis, or causal impact. Missing odometer and
timestamp pairs remain visible coverage gaps, not zeroes or estimates.
