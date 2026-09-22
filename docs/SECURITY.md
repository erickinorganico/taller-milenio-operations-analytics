# Security, privacy, and trust model

## Scope and data posture

The current toolkit processes generated synthetic records in a local batch. No real Taller Milenio customer, employee, vehicle, fleet, contract, location, payment, or tow data was imported. No operator discovery or live-system pilot occurred.

The public repository may contain source, templates, deliberately synthetic fixtures, and reviewed sample outputs. Real exports, working databases, credentials, logs, and sensitive artifacts must remain outside Git.

## Assets

- source and schema integrity;
- input snapshots and any future sensitive extracts;
- analysis/report correctness and provenance;
- artifact and verification receipts;
- local Python environment and wheelhouse;
- approval boundaries around messaging, money, contracts, and towing.

## Trust boundaries

1. **Public source boundary:** repository contents are public and must contain no secrets/private workstation paths/real sensitive data.
2. **Input boundary:** JSON/CSV/snapshot files are untrusted until contract validation and reconciliation pass.
3. **Local process boundary:** Python, SQLite, plotting libraries, and scripts run under the current OS account.
4. **Artifact boundary:** a completed directory is evidence for one input/code execution, not an authenticated business record.
5. **Human-action boundary:** proposals and reports stop before contact, dispatch, pricing commitment, diagnosis, fiscal action, or payment.

Other users and processes on the same operating system are **not authenticated or isolated by this toolkit**. File permissions, device encryption, malware protection, account security, and backup protection belong to the host environment.

## Threats, controls, and residual risk

| Threat | Implemented control | Residual risk / interpretation |
|---|---|---|
| secret or private path published | bounded publication regex scan across source/templates/docs | heuristic only; not anonymization or secret-detection certification |
| malicious or malformed input | strict fields/types/enums/IDs/refs/invariants; deep copy; fail-closed staging | a valid-looking synthetic assertion may still be false |
| spreadsheet formula injection | exported text beginning with formula-like characters is escaped | downstream software/user may transform files again |
| SQL injection or data mutation | fixed code-owned metrics/identifiers; source connection uses SQLite `query_only=ON` | this is read-only enforcement in the connection, not SQLite immutable mode; a same-OS actor can replace code/database outside the process |
| partial/corrupt package | new destination required; staging; receipt written after success; receipt verification rejects missing/extra/edited artifacts | interruption may leave a staging directory, not a successful delivery |
| artifact tampering | SHA-256 manifest/content digest and root-only receipt exemption | tamper-evident, not tamperproof; malicious author can rewrite files and manifest |
| false historical reconstruction | synthetic event provenance declared; imported snapshot without events grades history unknown | current-state snapshots cannot prove transition timing |
| future-data leakage/time travel | fixed `DEMO_NOW`; other cutoffs reject | genuine temporal reporting needs an authoritative event source |
| financial conflation | separate quote/invoice/payment/receivable/expense/cash measures; Python/SQL reconciliation | not fiscal accounting, bank proof, or revenue recognition |
| unsafe tow automation | no dispatch/safety tool or adapter; missing human refs create review | reports cannot verify real scene, unit, operator, insurance, or legality |
| outbound action from proposal | `pending`, `approval_required=true`, `external_execution=false`; no execute adapter | a human could manually misuse a recommendation outside the toolkit |
| dependency drift/compromise | exact pinned versions, local wheelhouse, installed-version check | pinning does not eliminate upstream/supply-chain risk |

## Privacy principles

- collect only fields needed for an approved analytical question;
- prefer definitions and blank/redacted artifacts during discovery;
- replace direct identifiers in a future pilot and remove unnecessary free text;
- document source, purpose, owner, cutoff, retention, deletion, and access;
- separate contact/location/vehicle/safety/contract/payment data;
- never interpret `synthetic=true` as proof of anonymization;
- never publish a future real-data artifact without separate review and authorization.

## Financial and towing boundaries

There are no real payment, bank, invoice-issuance, accounting, pricing, mapping, telephony, messaging, unit-assignment, or dispatch tools. The SQLite file stores an analytical snapshot. The tow analysis measures recorded completeness and timing only; it does not provide mechanical or road-safety advice.

## Agent boundary

The historical V1 proposal path and V2 `rules` mode are deterministic. V2 also offers opt-in `native_codex`, which invokes the locally authenticated Codex subscription CLI twice: first to select bounded evidence/metrics, then to draft a review package. It has no browser, messaging, dispatch, payment, arbitrary SQL or outbound interface. Exact metrics remain code-owned.

Every selected reference must resolve to an allowed table, field and ID; completed output evidence must match an existing value and version. Native failures remain blocked artifacts without a success receipt or silent deterministic fallback. A proposal or local review annotation cannot be promoted into an executable action by this codebase.

## Integrity versus authenticity

Hash chaining and artifact hashes detect change relative to the manifest being checked. They do not prove who created the input, whether it was truthful, whether the machine was uncompromised, or whether the manifest itself came from a trusted signer. The release does not use a digital signature or external transparency log.

## Incident response for local artifacts

If a hash, publication scan, reconciliation, dependency, or invariant fails:

1. stop publication/use of that package;
2. preserve the input and failed evidence without editing final outputs;
3. identify whether source, code, dependency, or artifact changed;
4. correct upstream and run into a new output directory;
5. rerun full verification and publication scan;
6. never relabel an older receipt as covering new code.

## Future real-data gate

Before any real pilot: complete process discovery, approve the minimal extract, establish role-based access and host security, define retention/deletion, test rollback, reconcile source control totals, review fiscal and towing implications with qualified owners, and keep external actions disabled. See `REAL-DATA.md`.

## Verified and unverified claims

Verified locally: contract checks, controlled failure, overwrite protection, source-snapshot preservation, reproducible content hashes, fixed cutoff, formula escaping, read-only SQL checks, proposal evidence boundaries, publication sentinel, and synthetic artifact generation. Excel COM verification recalculated all six formula cells in the 36-sheet workbook with zero formula errors and reconciled results to SQL.

Unverified: anonymity of arbitrary imports, resistance to a malicious same-OS actor, production scale, operational adoption, real SLA/capacity/financial correctness, towing safety, and business impact.
