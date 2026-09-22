# Agent and ActionProposal contracts

## What “agent” means here

There are two explicit modes with the same nine role IDs:

- **V1 deterministic proposals:** Python rules inspect one validated synthetic snapshot and return schema-bound `ActionProposal` drafts. This historical pipeline path does not call an LLM.
- **V2 governed workbench:** `milenio.agent_runtime` supports the same deterministic `rules` baseline plus opt-in `native_codex`. Native mode uses the locally authenticated Codex subscription CLI in two model calls: bounded evidence/metric selection, then a final diagnosis and review package. It has no browser, inbox, CRM, dispatch, payment, arbitrary SQL, or outbound tool.

Evaluation proves schema, grounding, policy invariants and bounded tool behavior. It is **not** proof of LLM quality, human utility, latency improvement, token or dollar savings, operational performance, or business impact.

## Agent catalog

| Agent ID | Purpose | May produce | Must never do |
|---|---|---|---|
| `intake_admin` | surface incomplete intake/follow-up evidence | review draft tied to lead/customer/vehicle fields | contact customer or infer consent |
| `operations_controller` | surface blocked/WIP/parts/QC conditions | workshop review draft | change priority, work state, price, or promise |
| `maintenance_planner` | surface maintenance due/overdue evidence | planning review draft | schedule or authorize real work |
| `fleet_sales_research` | surface open fleet research/next-step candidates | public-research/value-proposition draft | scrape/contact/send or claim buying intent |
| `fleet_sla_watcher` | surface eligible SLA/coverage evidence | SLA review draft | change contract terms or assert unknown coverage met/breached |
| `tow_dispatch_assistant` | surface incomplete/open tow records | human safety/price/unit/dispatch review draft | decide safety, choose a real unit, promise ETA, or dispatch |
| `collections_assistant` | surface receivable evidence | reconciliation/reminder draft | send reminder, charge, refund, write off, or move money |
| `marketing_planner` | surface synthetic campaign/follow-up candidates | human-reviewed content/plan draft | publish or send marketing |
| `weekly_operator` | summarize cross-module exceptions | review agenda draft | mutate source, close exceptions, or execute recommendations |

## ActionProposal schema

Every generated proposal must match `contracts/action_proposal.schema.json` exactly:

```json
{
  "id": "AP-<20 lowercase hex characters>",
  "agent": "<one of nine agent IDs>",
  "title": "<non-empty text>",
  "rationale": "<non-empty text>",
  "evidence": [
    {
      "entity_type": "<contracted entity>",
      "entity_id": "<existing ID>",
      "field": "<existing field>",
      "value": "<exact snapshot value>",
      "version": 1
    }
  ],
  "approval_required": true,
  "external_execution": false,
  "status": "pending"
}
```

No additional fields are allowed. Evidence has 1–100 items. `value` must canonically equal the referenced snapshot field and `version` must match the source record. IDs are deterministic digests of agent/title/evidence inputs.

## V1 proposal lifecycle

The only generated `ActionProposal` status is `pending`. The public output contains no apply, execute, send, dispatch, charge, or mutate adapter.

V2 adds a local `review` annotation (`approved`, `rejected`, or `needs_information`) to an agent run. This records a human decision beside the evidence package; it does not promote the proposal into an executable action or change source data.

## V2 native runtime contract

Native mode is open-ended reasoning inside a bounded evidence envelope:

1. The first model call sees profile-scoped candidate cases and selects 1–12 exact evidence reads plus allowed metric IDs.
2. Code validates every selected table, field, ID and metric. Metric SQL remains fixed and code-owned.
3. The second model call receives only the validated evidence and canned metric results, then returns diagnosis, alternatives, manual next steps, missing information, sensitivity, workplan and review-only drafts.
4. Completion rereads evidence and versions, checks the source hash and validates the structured response. Only matching successful receipts for both calls can set `model_invoked=true`.

A failed native stage is preserved as a blocked run with its available evidence. It does not receive a success receipt, does not silently fall back to rules and is not deleted as if it never happened.

## Input requirements

Agents run only after the full dataset passes domain validation. Source proposal records included in a snapshot are also validated: known agent, required policy flags, and full field/value/version evidence. Record-only or invented evidence is rejected.

Imported snapshots without validated lifecycle events do not gain fictional observed history. The agent may use current snapshot evidence but must preserve unknown transition coverage. Only fixed `DEMO_NOW` is supported.

## V1 evaluation contract

`evaluate_proposals` checks:

- exact object keys and schema-compatible values;
- recognized agent ID;
- unique deterministic-format proposal ID;
- non-empty title/rationale;
- pending status;
- mandatory human approval and disabled execution;
- non-empty evidence list;
- existing entity, ID, field, exact value, and version.

The result reports `mode=deterministic_read_only`, zero external tools, agents exercised, proposal count, and critical policy violations. Passing means the generated set met this bounded contract for that fixture.

## V1 failure behavior

Unknown agents, invented/stale evidence, extra keys, duplicate IDs, empty text/evidence, `approval_required=false`, `external_execution=true`, or any non-pending generated status fail validation and prevent a successful pipeline receipt.

## Laya position

V2 now has an actual repeated two-stage model caller for open-ended evidence review. Exact schema validation, metric computation, scope checking and reconciliation remain deterministic because they are not classification or ranking problems.

No suitable bounded, repeatedly invoked classification/ranking decision has been validated for replacement by Laya. Therefore no Laya execution or integration was performed, and no inference-, token- or cost-saving claim is made. If a future bounded classifier is identified, it must first run as an evaluated shadow suggestion with multilingual/adversarial cases, an explicit `REVIEW` state and deterministic fallback. It may never gain authority over diagnosis, price, towing, contact, dispatch or money.
