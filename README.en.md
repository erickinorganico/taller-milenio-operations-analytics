# Taller Milenio Operations & Growth Analytics

A local Analytics and agentic-consulting toolkit that models private-customer, fleet, and towing journeys; analyzes follow-up, capacity, service, inventory, SLA, and collections; and produces evidence-backed recommendations requiring human approval.

**All initial results are synthetic.** Taller Milenio's real process has not been validated. This is not an app, CRM, ERP, frontend/backend, or dispatch system. It does not send messages, diagnose, set prices, dispatch, issue fiscal invoices, or move money.

## Quick start

Python 3.12+ is required. The first online installation downloads and preserves dependencies; the demo then runs without network access.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m milenio demo --output artifacts/demo
```

To prove a clean offline installation after preparing the wheelhouse:

```powershell
.\Setup.ps1 -Offline -EnvironmentPath .runtime/clean-env
```

The run creates `dataset.json`, SQLite and CSV snapshots, analysis/quality/exceptions/timeline JSON, four separate reports, a printable executive HTML report, PNG/SVG charts, governed proposals, and a hashed receipt.

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

The demo only accepts the frozen cutoff `2026-09-21T18:00:00Z`; any other cutoff is rejected so outputs cannot imply currentness. Metrics, thresholds, and SLAs are test assumptions, not business claims.

Authorized public repository: `erickinorganico/taller-milenio-operations-analytics`. MIT licensed.
