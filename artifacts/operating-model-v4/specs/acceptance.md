# Acceptance specification

## Structural gates

1. Six JSON definitions validate the common required shape.
2. Node IDs, role owners, control/evidence/metric/agent references resolve.
3. Exactly one start and at least one end exist per process.
4. Every node is reachable from start and can reach an end.
5. Every decision has at least two outgoing transitions with non-empty distinct conditions.
6. Requirement process/entity/agent/metric/acceptance links resolve.

## Behavior gates

- B2C attribution requires explicit `journey_links`; candidate-only imports remain unknown.
- Service-cycle and process-wait metrics require validated lifecycle events; snapshot-only imports remain unknown.
- Purchases ordered but not received never enter on-hand.
- SLA with insufficient contract evidence is unknown and excluded.
- Tow refs never become software safety/dispatch authority.
- Non-issued invoices never enter receivable; overpayments reject.
- Weekly review blocks when quality/reconciliation fails.
- Proposals are pending, grounded, approval-required and non-executing.
- Imported snapshots without events keep lifecycle history unknown.

## Release evidence

`tests/test_process_specs.py` proves structural/traceability integrity. Existing domain, adversarial and E2E suites prove executable data/analysis behavior. Passing specs alone does not prove real process accuracy; owner/operator discovery remains required.
