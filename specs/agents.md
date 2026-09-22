# Agent specification

The nine named agents are deterministic rules, not LLM personas. Input is the validated fixed-cut snapshot. Output is a pending `ActionProposal` with exact entity/field/value/version evidence, `approval_required=true` and `external_execution=false`.

| Agent | Processes | Trigger family | Output only |
|---|---|---|---|
| `intake_admin` | b2c_workshop | follow-up, quote, appointment, coverage | intake/review draft |
| `operations_controller` | b2c_workshop, parts_procurement | blocked/overdue work, stock | workshop review draft |
| `maintenance_planner` | fleet_sales_service | due/scheduled maintenance | planning review draft |
| `fleet_sales_research` | fleet_sales_service | open opportunity | authorized-public-research draft |
| `fleet_sla_watcher` | fleet_sales_service | eligible risk/breach/unknown coverage | SLA review draft |
| `tow_dispatch_assistant` | towing | open/incomplete tow | human gate review draft |
| `collections_assistant` | collections | overdue positive balance | reconciliation/reminder draft |
| `marketing_planner` | b2c_workshop, weekly_review | draft/review campaign | content review draft |
| `weekly_operator` | all/weekly_review | complete package | agenda draft |

## Policy

Agents cannot send, dispatch, schedule, diagnose, change price/SLA/state, approve work, charge, refund or write off. No execute adapter exists. A human decision outside the pipeline does not mutate the snapshot.

## Fallbacks

- Invalid or stale evidence: fail validation.
- Missing evidence: no proposal or explicit review/unknown from the governing process.
- Quality/reconciliation failure: weekly agenda blocks.
- No eligible trigger: zero proposals is valid for that rule; it is not proof that operations are healthy.

Passing agent tests proves deterministic schema/grounding/policy conformance, not LLM quality, usefulness, business impact, token savings or staff adoption.
