# Deterministic agent and ActionProposal contract

## What “agent” means here

The nine agents are deterministic Python rules that inspect one validated synthetic snapshot and return evidence-bearing drafts. They do not call an LLM, API, browser, inbox, CRM, dispatch system, payment system, or external tool.

The evaluation proves schema, grounding, policy invariants, and deterministic behavior. It is **not** an LLM-quality, human-utility, latency, token-saving, dollar-saving, operational-performance, or business-impact evaluation.

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

## Lifecycle

The only generated status is `pending`. The public output contains no approve, reject, apply, execute, send, dispatch, charge, or mutate adapter. Human review occurs outside the execution path. If a future product records a decision, it requires a separate contract and still must not equate approval with external execution.

## Input requirements

Agents run only after the full dataset passes domain validation. Source proposal records included in a snapshot are also validated: known agent, required policy flags, and full field/value/version evidence. Record-only or invented evidence is rejected.

Imported snapshots without validated lifecycle events do not gain fictional observed history. The agent may use current snapshot evidence but must preserve unknown transition coverage. Only fixed `DEMO_NOW` is supported.

## Evaluation contract

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

## Failure behavior

Unknown agents, invented/stale evidence, extra keys, duplicate IDs, empty text/evidence, `approval_required=false`, `external_execution=true`, or any non-pending generated status fail validation and prevent a successful pipeline receipt.

## Laya and LLM position

No repeated LLM caller exists in the implemented path, so no Laya inference was run or integrated. Deterministic rules are the correct baseline for exact contracts. Any future classifier must begin as a separately evaluated shadow suggestion with multilingual/adversarial cases, `REVIEW`, deterministic fallback, and no authority over diagnosis, price, towing, contact, dispatch, or money.
