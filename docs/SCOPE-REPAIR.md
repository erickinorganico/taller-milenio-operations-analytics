# Scope repair: from thin demo to inspectable decision system

## Why this repair exists

The first delivery proved a reproducible batch and reports, but it did not make the intended operating model visible enough. Its generic JSON document store could be mistaken for “25 tables,” named agents looked richer than their deterministic rules, process state was thin, and some coverage/metric language depended on interpretation rather than formal traceability.

This repair does not hide those limits and does not expand into a live application. It adds the missing specification layer for the same offline analytical decision toolkit.

## V1 assessment

| V1 gap | Candid interpretation | Repair |
|---|---|---|
| Generic `entities` store plus views | V1 had one physical JSON store, not 25 relational business tables | V2 studio builds 27 typed source tables (25 entities plus lifecycle events/journey links), `schema.sql`, catalog and six marts |
| Named “agents” | deterministic Python rules, not LLM reasoning or autonomous staff | `specs/agents.md` defines nine triggers, evidence, fallbacks and prohibitions |
| Thin process visibility | state dictionaries existed but ownership, decisions and exceptions were implicit | six executable process JSONs plus Mermaid/SOP/RACI/acceptance |
| Metrics in code/reports | correct calculations were hard to trace to business decision and fallback | metric IDs, formulas, grain, unknown rules and requirement links |
| Synthetic scenarios | useful for regression, not observed Taller Milenio behavior | V2 provides explicit events and 160 linked synthetic journeys for case attribution; imports without links/events stay `unknown` |
| Four reports | useful outputs but not a complete product specification | product/data/agent/analytics/acceptance specs and REQ traceability |

## New formal surfaces

1. `specs/process.schema.json`: shared executable shape.
2. `specs/process_catalog.json`: stable render metadata/API mapping for the studio.
3. `processes/*.json`: six process graphs with lanes, roles, owners, evidence, controls, metrics, agents and test IDs.
4. `processes/*.md`: readable Mermaid, SOP, exceptions, RACI and acceptance.
5. `specs/requirements.json`: REQ-to-process/entity/agent/metric/acceptance trace.
6. `specs/product.md`, `data.md`, `agents.md`, `analytics.md`, `acceptance.md`: normative boundaries, including cycle/wait formulas and fallbacks.
7. V2 warehouse/studio: typed source tables, six marts, Excel, dossier and evidence-bearing agent runs.
8. `tests/test_process_specs.py`: referential and graph integrity checks.

## Scope that remains unchanged

- synthetic fixed-cut data only;
- offline batch analytics and read-only consulting outputs;
- no live app, CRM, ERP, workflow execution or dispatch;
- no outbound messages, payments, prices, diagnosis or state mutation;
- no claim that the process maps represent observed Taller Milenio practice;
- owner/operator discovery and a governed real-data pilot remain future work.

## Integration contract for the studio

The studio should read `specs/process_catalog.json`, then load the referenced JSON for cards/graphs and Markdown for detailed narrative. JSON is authoritative for nodes and traceability; Mermaid is a human-readable projection. Requirement/detail views resolve IDs from `specs/requirements.json`. The studio must label these as **analytical process definitions** and must not expose transition buttons or imply operational execution.

## Acceptance of the repair

The repair is accepted when all six processes load, their graph decisions/terminal paths are valid, every entity/agent/metric/acceptance reference resolves, and requirements cover each process. Passing these checks proves specification integrity, not real-process validity or business impact.
