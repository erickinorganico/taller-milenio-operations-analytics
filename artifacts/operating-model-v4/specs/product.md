# Product specification

This document governs the full synthetic V2 workbench. The separate minimal
client input and weekly review path is governed by [client-delivery.md](client-delivery.md).
V3 accepts explicitly marked private client copies and arbitrary declared cutoffs
without changing the V2 synthetic contract or authorizing access to real systems.

## Product boundary

The product is an offline analytical decision toolkit. Input is a validated synthetic snapshot (JSON or the complete CSV entity set). Output is a versioned evidence package, process studio metadata, metrics, exceptions, deterministic proposals, reports and receipts. It is not a live application, workflow engine, CRM, ERP or dispatch system.

## User outcomes

1. An analyst can explain how a record moves through six formal analytical processes.
2. A manager can trace a metric or proposal to source entity/field/version evidence.
3. A functional owner can see exception rules, state authority, unknown fallbacks and acceptance criteria.
4. A reviewer can compare the process JSON, Mermaid/SOP, requirement trace and generated artifact.

## Required surfaces

- Process catalog: six definitions with lanes, nodes, decisions, evidence, controls, metrics, agents and tests.
- Requirement explorer: REQ IDs linked to processes/entities/agents/metrics/acceptance.
- Table dictionary: 25 contracted entity tables plus `lifecycle_events` and `journey_links`, with reference edges and state authority.
- Analytical layer: six named marts for service journeys, receivables, daily operations, fleet scorecard, inventory and process waits.
- Scenario view: normal and failure paths from synthetic fixtures; no claim of observed real history.
- Agent registry: nine deterministic proposal producers and their no-execution policy.
- Report bundle: four analytical lenses, executive HTML, charts and receipts.

## Functional rules

- A process definition is renderable solely from JSON; prose is explanatory.
- Every decision has at least two outgoing conditions and every node can reach an end.
- Every referenced entity/agent/metric/evidence/control/acceptance ID resolves.
- Current-state state machines come from `FLOWS`. The 160 linked synthetic cases have explicit fictional events and journey links; imported snapshot history and attribution are unknown unless those sources are supplied and validated.
- No state mutation, outbound action or arbitrary cutoff is exposed through process metadata.

## Evidence states

`measured` means calculated on the exact snapshot. `unknown` means insufficient evidence. `review` means a human decision is required. `blocked` means a control prevents a responsible conclusion. `synthetic` means no real-business claim is supported.
