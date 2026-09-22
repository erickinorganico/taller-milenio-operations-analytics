# Taller Milenio · Analytics Workbench V2

A local, reproducible delivery for reviewing operations, growth, and management controls with evidence. Start with the [V2 dossier](artifacts/workbench-v2/DOSSIER.html): it connects SQL tables, six formal processes, longitudinal metrics, an Excel workbook, and nine human-review agent profiles.

> **Synthetic data only.** The 90-day scenario, 170 work orders, 160 linked histories, amounts, SLAs, and results were fabricated to test the mechanism. They do not describe Taller Milenio's real operation or prove business impact. The processes remain hypotheses until validated through interviews.

[Versión en español](README.md) · [Delivery inventory](ENTREGA-MILENIO.md) · [Practical walkthrough](docs/V2-WALKTHROUGH.md)

## Delivered surfaces

| Surface | Reviewable content |
|---|---|
| Dossier | `DOSSIER.html`, a printable local entry point for decisions, tables, processes, and evidence |
| Workbook | `Milenio_Analisis.xlsx`, 36 sheets: cover, 33 tables, agent catalog, and process catalog |
| SQL | `warehouse.sqlite` with 33 physical tables: 25 entities, `lifecycle_events`, `journey_links`, and six marts |
| Processes | six JSON definitions, six SVG maps, and six SOPs with decisions, exceptions, RACI, and acceptance |
| Specifications | five normative contracts and 18 requirements traced to processes, entities, agents, metrics, and tests |
| Agents | nine review profiles; reproducible `rules` mode and opt-in two-stage `native_codex` mode |
| Decisions | `DECISIONES.md` and `review_queue.csv`, with pending proposals and blank human fields |
| Evidence | per-table CSV, catalog, DDL, analysis, process replay, workbook checks, and hashed receipt |

The six analytical marts are `mart_service_journey`, `mart_receivables`, `mart_daily_operations`, `mart_fleet_scorecard`, `mart_inventory`, and `mart_process_waits`.

The current integrated suite passes with no failures or errors; the exact count belongs in the verification receipt for the same source state so documentation does not freeze a stale number. Excel COM opened and recalculated all 36 sheets: six formulas, zero formula errors, and SQL-reconciled results.

The data cutoff remains fixed at `2026-09-21T18:00:00Z`. Native executions ran on 2026-09-22 and do not advance, rewrite, or make the scenario data current.

## Build the workbench

Python 3.12+ is required.

Windows:

```powershell
.\Setup.ps1
.\Run-Studio.cmd
```

Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m milenio studio --output artifacts/workbench-v2 --days 90
```

`Run-Studio.cmd` opens the existing dossier in `artifacts/workbench-v2` first. If it does not exist, the launcher builds that delivery; when it finishes, run the launcher again or open `DOSSIER.html`. To preserve the published workbench and create another one, use a new folder:

```powershell
.\.venv\Scripts\python.exe -m milenio studio --output artifacts/workbench-review-02 --days 90
```

`studio` never overwrites a supplied folder. It works in staging and publishes the final directory only after SQL, marts, baseline agents, workbook, and supporting artifacts complete.

### Reanalyze synthetic input

The delivery exports `dataset.json`, `events.json`, and `journeys.json`. Rebuild them into a new destination:

```powershell
.\.venv\Scripts\python.exe -m milenio studio `
  --input artifacts/workbench-v2/dataset.json `
  --events artifacts/workbench-v2/events.json `
  --journeys artifacts/workbench-v2/journeys.json `
  --output artifacts/reanalisis
```

A complete directory of 25 synthetic CSV files is also accepted:

```powershell
.\.venv\Scripts\python.exe -m milenio studio `
  --input artifacts/demo/csv `
  --output artifacts/reanalisis-csv
```

Without `--events` or `--journeys`, the workbench still produces 36 sheets but keeps history and attribution `unknown`; it never invents transitions or links. This adapter accepts the synthetic contract and fixed `DEMO_NOW` cutoff only, not production data.

## Five-minute review

1. Open `artifacts/workbench-v2/DOSSIER.html` and inspect operations, receivables, fleet, inventory, processes, and agents.
2. Open `Milenio_Analisis.xlsx`: `INICIO` reconciles invoiced, collected, and outstanding amounts; the other 33 data sheets support filtering.
3. Find `WO-003` in `work_orders`: it is a synthetic `waiting_parts` order blocked by `Falta filtro`, with no QC or assignment. Compare it with the replay and service mart.
4. Open a `processes/*.svg` map and its matching `.md` SOP; the JSON is authoritative for validation and visualization, not an operational BPMN engine.
5. Inspect `receipt.json` and `workbook_check.json` before using any conclusion.
6. Open [DECISIONES.md](artifacts/workbench-v2/DECISIONES.md) and [review_queue.csv](artifacts/workbench-v2/review_queue.csv): every proposal starts as `pending`, and human-decision fields are blank rather than fabricated approvals.

See [docs/V2-WALKTHROUGH.md](docs/V2-WALKTHROUGH.md) for the complete review cycle.

## Agent workbench

List the nine profiles and their boundaries:

```powershell
.\.venv\Scripts\python.exe -m milenio agents
```

The local baseline invokes no model:

```powershell
.\.venv\Scripts\python.exe -m milenio agent `
  --warehouse artifacts/workbench-v2/warehouse.sqlite `
  --output artifacts/agent-runs/operations-rules `
  --id operations_controller `
  --backend rules
```

`native_codex` is opt-in. It uses the official CLI pinned at `0.155.1` through the already authenticated Codex account, without a separately billed API. `Setup-Agents.ps1` installs this runtime separately and sets `MILENIO_CODEX_BIN` for the current terminal:

```powershell
.\Setup-Agents.ps1
.\.venv\Scripts\python.exe -m milenio agent `
  --warehouse artifacts/workbench-v2/warehouse.sqlite `
  --output artifacts/agent-runs/operations-native `
  --id operations_controller `
  --backend native_codex `
  --timeout 300
```

The native path has two stages: bounded evidence and metric selection, followed by diagnosis, alternatives, and review drafts. All nine profiles completed that path through the official CLI: 18 observed `turn.completed` events, final `verified_two_stage_local_cli` receipts, and no external actions. This verifies execution and controls, not effectiveness. Review corrected invoice/payment relationships, fleet scope, and the distinction between a sample and the full population. Drafts still require human review.

To build a new delivery that runs all nine native profiles, run `Setup-Agents.ps1` and then `python -m milenio studio --native --output <new-folder>`. This is an opt-in, potentially long-running action and is never enabled silently.

Record a local review annotation with `python -m milenio review`. Review never contacts customers, schedules, dispatches, buys parts, changes business records, or moves money.

## Growth and governance

[docs/GROWTH-RESEARCH.md](docs/GROWTH-RESEARCH.md) defines a public-source research workflow and qualification score. It explicitly treats DENUE's employee stratum as establishment employment, never fleet size, and prohibits fabricated contacts or leads.

The workbench supports review of WIP, waits, receivables, eligible SLA evidence, inventory, and next questions. It does not operate a CRM, ERP, dispatch system, fiscal system, or messaging channel.

## V2 documentation

- [Delivery inventory and acceptance](ENTREGA-MILENIO.md)
- [Practical workbench walkthrough](docs/V2-WALKTHROUGH.md)
- [Growth research](docs/GROWTH-RESEARCH.md)
- [Project efficiency](docs/PROJECT-EFFICIENCY.md)
- [Physical model](docs/DATA-MODEL.md), [agent runtime](docs/AGENT-RUNTIME.md), and [process replay](docs/PROCESS-MINING.md)
- [Processes](processes/) and [specifications](specs/)

## Historical V1

The V1 batch remains for compatibility and tests (`demo`, `analyze`, Markdown/HTML reports). It is no longer the primary entry point. V2 adds typed physical tables, explicit history, marts, maps, specifications, an Excel workbook, and the agent workbench.

Authorized public repository: `erickinorganico/taller-milenio-operations-analytics`. MIT licensed.
