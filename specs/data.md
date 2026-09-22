# Data and state specification

## Authority

`milenio.contracts.FIELDS` is the entity/field/type authority. `FLOWS` is the current-state transition vocabulary for leads, quotes, appointments, work orders, purchases, opportunities, contracts, maintenance, tows, invoices and campaigns. Process definitions may reference only those entity and field names.

The V2 studio materializes a physical SQLite warehouse with one typed table per contracted entity plus `lifecycle_events` and `journey_links` (27 physical source tables in the current contract). Foreign keys, checks and indexes are emitted in `schema.sql`; `catalog.json` reports actual columns, references and row counts. Six analytical marts are then built: `mart_service_journey`, `mart_receivables`, `mart_daily_operations`, `mart_fleet_scorecard`, `mart_inventory` and `mart_process_waits`.

The earlier V1 generic `entities` document store remains relevant only to the legacy batch evidence path; it is not the physical model claimed by the studio. Foreign/reference, dataset and cross-entity invariants are enforced before artifact publication.

## Grain and keys

- Each entity row has `id`, `version`, `synthetic`, `created_at`, `updated_at` plus its contracted fields.
- IDs are unique within entity. `ref:*` fields resolve to an existing target.
- Money is integer MXN cents; dates are timezone-aware ISO-8601.
- The only supported analytical cutoff is `DEMO_NOW`.
- A CSV snapshot must include one file per entity and must round-trip contracted types.

## State authority and history

`status` is the state observed at snapshot cutoff. By itself it does not prove how or when the entity arrived there. The V2 synthetic scenario supplies explicit fictional `lifecycle_events` and 160 `journey_links`; these support synthetic case attribution and time-in-state marts because the link/event provenance is explicit. For imported JSON/CSV without those sources, lifecycle and attribution coverage remain `unknown`; no path is backfilled from `FLOWS` and no candidate match is promoted to attribution.

## Critical reconciliations

- Inventory: on-hand from stock movements; reserved from active reservations; available = on-hand − reserved; ordered purchase is excluded until receipt.
- Finance: issued invoice = payments + receivable; quotes and expenses excluded from that identity; cash net uses only cash-method payments/expenses.
- SLA: service must have qualifying contract evidence and dates; cancelled is excluded; insufficient evidence is unknown.
- Towing: human refs are presence evidence only; they do not establish safe/legal dispatch.
- Capacity: duplicate active bay or technician assignments reject; occupancy is a snapshot, not utilization hours.

## Fail-closed behavior

Unknown fields, missing required values, invalid states, bad references, negative/over-reserved inventory, valuation mismatch, impossible timestamps, invoice/source mismatch, overpayment, invented proposal evidence, incomplete entity set or unsupported cutoff prevent a successful receipt.
