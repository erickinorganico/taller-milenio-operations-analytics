# Taller Milenio Operations & Growth Analytics

A turnkey, local, read-only Analytics and agentic-consulting toolkit that models private-customer, fleet, and towing journeys; analyzes follow-up, capacity, service, inventory, SLA, and collections; and produces evidence-backed recommendations requiring human approval.

**All initial results are synthetic.** Taller Milenio's real process has not been validated. This is not an app, CRM, ERP, frontend/backend, or dispatch system. It does not send messages, diagnose, set prices, dispatch, issue fiscal invoices, or move money.

## Quick start

Download the [release](https://github.com/erickinorganico/taller-milenio-operations-analytics/releases/latest), extract it and enter `source/`. The Windows x64 offline bundle includes Python 3.12 dependency wheels; Python itself is a prerequisite. Run `Setup.ps1 -Offline`, then open `artifacts/demo/reports/informe_ejecutivo.html` or run `Run-Demo.cmd` for a fresh batch. See the [consulting kit](docs/COMMERCIAL-KIT.md), [client playbook](docs/CLIENT-PLAYBOOK.md) and [editable templates](examples/consulting/).

Python 3.12+ is required.

Windows:

```powershell
.\Setup.ps1
.\.venv\Scripts\python.exe -m milenio demo --output artifacts/my-demo
```

Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m milenio demo --output artifacts/my-demo
```

To prove a clean offline installation after preparing the wheelhouse:

```powershell
.\Setup.ps1 -Offline -EnvironmentPath .runtime/clean-env
```

The run creates `dataset.json`, SQLite and CSV snapshots, analysis/quality/exceptions/timeline JSON, four separate reports, a printable executive HTML report, PNG/SVG charts, governed proposals, and a hashed receipt.

## Reanalyze the exported CSV directory

The complete CSV export can be fed back into the pipeline:

```powershell
.\.venv\Scripts\python.exe -m milenio analyze --input artifacts/demo/csv --output artifacts/from-csv
```

Use a new output path. The importer requires the full contracted entity set and keeps lifecycle coverage `unknown` when CSV inputs do not contain validated history.

## Verify

```powershell
.\.venv\Scripts\python.exe -m milenio verify --output artifacts/verification.json
```

Tests run without network or production data. A green run verifies the mechanism for that input; it does not prove real workshop outcomes.

## Four consulting lenses

- **Private customers:** conversion, appointments, follow-up, authorization, delivery/rework, and recurrence.
- **Fleets:** pipeline versus contract, maintenance, downtime, SLA, invoicing, and collections.
- **Towing:** recorded journey/timing, human-gate completeness, and exceptions; never safety or dispatch decisions.
- **Administration:** capacity, blocked work, inventory, costs/expenses, invoices, payments, receivables, and cash as distinct facts.

## Documentation

- [Synthetic process and interviews](docs/PROCESS.md)
- [Plan and E2E](docs/PLAN.md)
- [Batch architecture](docs/ARCHITECTURE.md)
- [Runbook](docs/RUNBOOK.md)
- [Future real-data path](docs/REAL-DATA.md)

The demo only accepts the frozen cutoff `2026-09-21T18:00:00Z`; any other cutoff is rejected so outputs cannot imply currentness. Metrics, thresholds, and SLAs are test assumptions. The toolkit can demonstrate a commercial consulting offer, but it does not prove a real deployment, adoption, or business results.

Authorized public repository: `erickinorganico/taller-milenio-operations-analytics`. MIT licensed.
