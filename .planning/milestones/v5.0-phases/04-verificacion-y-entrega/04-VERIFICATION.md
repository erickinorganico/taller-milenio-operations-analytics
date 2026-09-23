---
phase: 04-verificacion-y-entrega
verified: 2026-09-23T03:55:05Z
status: passed
score: 4/4 technical must-haves verified
overrides_applied: 0
human_verification:
  - test: "Instalación y recuperación desde el ZIP final en Windows"
    expected: "Una instalación vacía y demo separada inician siguiendo el manual; el respaldo restaura registros, archivos y saldos en una segunda instancia con hashes e integridad válidos."
    why_human: "Al corte de este informe no había un recibo del ensayo del ZIP final extraído ni conciliación de saldos restaurados; las pruebas existentes usan fixtures y comprobaciones parciales."
  - test: "Recorrido de pantallas por cada rol en escritorio y teléfono"
    expected: "Los usuarios completan sus acciones autorizadas y entienden estados vacíos, errores, fuentes, métricas y propuestas siguiendo los manuales V5."
    why_human: "La apariencia, facilidad de uso y correspondencia operativa en navegador real requieren observación humana."
---

# Phase 4: Verificación y entrega local — Verification Report

**Phase goal:** El producto se puede instalar, recuperar y comprobar con un recorrido completo y manuales fieles al software.
**Status:** human_needed. No prior `04-VERIFICATION.md` or phase SUMMARY was present. This is an initial verification of the current code, not an assertion of client acceptance.

## Goal achievement

| # | Roadmap success criterion | Result | Code and execution evidence |
| --- | --- | --- | --- |
| 1 | Exportar, respaldar, restaurar y comprobar integridad | VERIFIED, with acceptance limit | `workshop/views.py` exports source CSV; `backup_workshop.py` uses SQLite backup API and hashes database/media; `restore_workshop.py` verifies manifest, integrity, migration set, hashes and mode before replacement, keeps the previous state and clears sessions. `RecoveryTests` passed. Its fixture restores one order and photo; a final extracted-package rehearsal comparing financial counts and balances remains pending. |
| 2 | Recorrido desechable de recepción a saldo y métricas | VERIFIED | `test_end_to_end_http_from_capture_to_partial_collection` drives actual Django HTTP routes through inspection, versioned approval, reservation/consumption, time, quality, delivery, invoice, partial payment, balance and `/metrics/?export=json`; it checks `626.40` invoiced and `526.40` open balance. Service methods use transactions and ORM persistence. |
| 3 | Rechazos sin corrupción de roles, CSRF y entradas inválidas | VERIFIED, bounded by tests | `test_domain.py`, `test_web.py`, `test_intelligence.py`, `test_recovery.py` cover role/CSRF denial, transition guards, duplicate receipts/payments, stock, overpayment, quality/evidence prerequisites and stale proposals. Tests inspect affected records for representative failures. Not every rejected HTTP path separately compares the audit-event count before and after; that is a test-depth limitation, not an observed corruption. |
| 4 | Manuales por rol, instalación, fuentes, métricas y agentes corresponden al producto entregado | UNCERTAIN — WARNING | `docs/V5-MANUAL.md`, `V5-INSTALACION.md`, `V5-PROCESOS.md`, `V5-DATOS.md`, `V5-METRICAS.md`, `specs/v5-domain-api.md` and `specs/v5-intelligence.md` describe the implemented Django routes/models. `scripts/package_web.py` collects these V5 docs and verifies per-entry SHA-256; `_collect()` returned 86 source entries including all five V5 docs and the intelligence contract. The final extracted ZIP/manual walkthrough had not been observed at this report's cutoff. |

**Score:** 3/4 truths verified, one warning requiring a final operator check. No failed must-have or override was found.

## Required artifacts and key links

| Artifact / connection | Level 1–2 | Wiring / data flow |
| --- | --- | --- |
| `backup_workshop.py` and `restore_workshop.py` | Substantive validation, staging, rollback and session handling | Management commands resolve `settings.DATA_DIR`, SQLite and `MEDIA_ROOT`; restore runs validation before switching active files. Recovery tests passed. |
| `tests/test_web.py`, `test_domain.py`, `test_intelligence.py`, `test_recovery.py` | Substantive end-to-end and negative tests | Django test runner discovers and executes them against a disposable test DB. |
| `views.py` → `services.py` → ORM models | Substantive route handlers and atomic services | Order HTTP actions call stateful service functions, which write `WorkOrder`, `Quote`, `Reservation`, `StockMovement`, `Invoice`, `Payment` and `AuditEvent`; no static fixture feeds the production journey. |
| `insight_views.py` → `intelligence.py` → ORM → metric template/JSON | Substantive dashboard with 18 definitions, values, coverage and references | `build_dashboard()` queries current operational models; `/metrics/` renders them and `/metrics/?export=json` returns the same calculation. End-to-end test checks financial values. |
| `scripts/run_web.py` → Django/Waitress | Substantive local launcher, migration, separated demo/live data and loopback binding | `.cmd` launchers call `Setup-Web.ps1` then `run_web.py`; runtime smoke tests exist, but were not executed by this verifier because verification instructions prohibit starting servers. |
| `scripts/package_web.py` → V5 docs and source | Substantive manifest and content hash verification | `_collect()` includes all five `docs/V5*.md` plus `specs/v5-intelligence.md`; package fixture test passed. Final release ZIP and offline installation receipt remain outside this verifier's observed evidence. |

The dynamic UI has real ORM sources: order/customer/stock rows come from queries in `views.py`; metric cards and source links come from `build_dashboard()` and `SOURCE_MODELS`; agent runs/proposals/tasks come from persisted `AgentRun`, `Proposal`, and `ActionTask` rows. The repaired agent selector now exposes the `operations` option as a valid HTML `<option>`.

## Behavioral checks

| Check | Result |
| --- | --- |
| `MILENIO_MODE=test`, `MILENIO_DATA_DIR=private/verifier-test`, `.venv/Scripts/python.exe manage.py test workshop.tests.test_domain workshop.tests.test_web workshop.tests.test_intelligence workshop.tests.test_recovery.RecoveryTests --verbosity 1` | 50 tests passed; Django system checks found no issues. |
| `manage.py test workshop.tests.test_recovery.WebDeliveryTests.test_web_package_manifest_and_private_exclusion --verbosity 1` with the same disposable environment | 1 test passed. |
| `scripts.package_web._collect()` on current source | 86 entries; all five V5 docs and `specs/v5-intelligence.md` present. |
| Phase-declared probes | None. No `probe-*.sh` is declared for this phase. |

## Requirements coverage

| Requirement | Source plan | Assessment |
| --- | --- | --- |
| RUN-02 | 04-01 | Technically satisfied by CSV export plus validated backup/restore; final operator restoration drill remains a human check. |
| QA-01 | 04-01 | Satisfied by persisted HTTP journey and checked financial metrics. |
| QA-02 | 04-01 | Satisfied for representative invalid paths; audit-event before/after assertions are not universal. |
| DOC-01 | 04-02 | Documentation and package wiring exist; user walkthrough of final extracted package is pending, so the roadmap truth is UNCERTAIN. |

All four phase requirements appear in a plan; none is orphaned. No unreferenced `TBD`, `FIXME`, or `XXX` debt marker was found in the checked V5 code, scripts or docs. No later roadmap phase specifically defers a Phase 4 criterion.

## Evidence boundaries and human verification

The automated checks use synthetic or disposable records. A real client pilot, adoption, financial effect, and production support operation have not been observed. Optional native Codex inference is a separate Phase 3 capability: local CLI presence and mocked validation tests do not prove an authenticated live model turn; the documented local login state at this cutoff was **Not logged in**, and no inference was invoked for this verification.

1. Extract the final V5 ZIP on Windows and follow `README-WEB.md` and `docs/V5-INSTALACION.md` in a disposable `live` and `demo` setup. Confirm setup, role accounts, static assets, backup, second-instance restore, record counts, invoice/payment/balance reconciliation, media, hashes and SQLite integrity. Record the package hash and commands/results.
2. Follow `docs/V5-MANUAL.md` and `docs/V5-PROCESOS.md` with reception, technician, parts, finance, management and read-only accounts on desktop and phone. Confirm permissions, form errors, source links, metric coverage and agent proposal/task language against the rendered UI.

_Verified: 2026-09-23T02:49:55Z_
_Verifier: gsd-verifier_


## Addendum — root closure after the independent cutoff

The initial 3/4 assessment above is preserved as history. Later evidence closes the technical package/recovery warning: `artifacts/v5-installation-rehearsal.json` records a wheel-inclusive extracted candidate, Setup-Web.ps1 -Offline with PIP_NO_INDEX, six pinned dependencies, and Python 3.12.14/imports/Django setup from the newly created venv. Management-command migration/seed/backup/restore used the repository interpreter against extracted application code; this distinction remains explicit. All 24 domain table counts, invoice 1102.00, payments 300.00 and balance 802.00 matched; media hashes matched, sessions were purged, and the prior target DB survived.

Root browser checks observed responsive rendering, persisted approval/work after restart, 24 sources, 18 metrics, a printable quote, and a rules proposal→task→owner/due date→order correction→observed outcome closure. Mobile document width 375 equaled its client width 375 at viewport 390×844. `artifacts/v5-verification.json` then recorded 70 tests, zero skips/failures/errors, migrations clean. The final ZIP manifest verifies whether these tested runtime files match the delivery; documentation changes do not claim a new native invocation.

The technical Phase 4 criteria are satisfied locally. Real-person workshop usability, adoption and production acceptance remain human pilot checks; the overall milestone remains incomplete for AGT-03 native authentication/inference. No safety override or client acceptance is inferred from this addendum.

## Addendum — final local evidence after native verification (2026-09-23T03:55:05Z)

The preceding independent assessment and first addendum retain their original cutoffs as history. Later receipts supersede the then-open AGT-03 status: `artifacts/v5-native-verification.json` records an authenticated GPT-6 Luna CLI turn on synthetic demo data with `turn.completed`, valid structured output, `model_invoked=true`, no injected runner, an allowed empty proposal list and unchanged business-record counts. `artifacts/v5-verification.json` records 71/71 V5 tests with no failures, errors or skips, including 18 intelligence tests. This does not revise the independent verifier's original observation.

| Requirement ID | Final local evidence | Status |
| --- | --- | --- |
| RUN-02 | `artifacts/v5-installation-rehearsal.json` and `artifacts/v5-final-package-smoke.json`: backup/restore, integrity, counts, media and financial balance | passed |
| QA-01 | `test_web.py` persisted intake-to-partial-payment journey and `artifacts/v5-verification.json` | passed |
| QA-02 | `test_domain.py`, `test_web.py`, `test_intelligence.py`, `test_recovery.py`: role, CSRF, stock, payment and stale-evidence negatives | passed |
| DOC-01 | final-package smoke, manuals and the documentation-to-runtime comparison in `docs/V5-VERIFICACION.md` | passed |

The phase is `passed` for local technical verification only. The milestone remains `ready_for_audit`; it has not been formally closed or archived. A real client pilot, network deployment, CFDI, adoption and financial impact remain outside this evidence.
