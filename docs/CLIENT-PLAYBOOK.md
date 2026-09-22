# Client playbook

This playbook is for a local analytics review using authorized exports. Every
recommendation remains a draft until a human owner approves it.

## Before the first review

- Name the process owner, data owner, reviewer, and acceptance approver.
- Complete `examples/consulting/data-request-checklist.csv` and mark missing,
  stale, restricted, or unknown fields.
- Keep a fixed snapshot cutoff and an immutable copy of the supplied export.
- Confirm consent and anonymization treatment before using customer, vehicle, or
  contact data.

## Weekly operating review

Use `examples/consulting/weekly-operating-review.md`. Confirm the source cutoff,
row counts, freshness, reconciliation checks, and unresolved evidence first.
Review exceptions by owner and due date. Add actions to
`decision-action-tracker.csv`; record only observed outcomes. A blank realized
outcome means unknown, not zero or success.

## B2B research boundary

Use `public-b2b-research.csv` only for public sources that a reviewer can open
and verify. Record the source URL, retrieval date, evidence for fleet size,
permission state, and `ready_for_human_review`. Do not scrape, contact, enrich,
or infer a person’s permission from a public page.

## Approval and handover

Every proposed external or business action goes into `approval-log.csv` with
scope, exact action, approver, expiry, and pending/approved/rejected status.
Approval does not execute an action automatically. Finish with
`client-handover-acceptance.md`, including accepted deliverables, limitations,
open evidence, retention, and the next owner.

The synthetic demo proves data contracts and reproducible reports. It provides
no evidence of real market demand, service quality, ROI, adoption, or safety.

## Offline handoff

After extracting a release, change into its `source/` directory. If the archive
contains `source/.runtime/wheels`, the Windows offline setup can use that
wheelhouse with Python 3.12:

```powershell
Set-Location .\source
.\Setup.ps1 -Offline
```

The optional bundle is at `source/artifacts/demo/` and includes its verified
synthetic receipt. Keep the extracted package separate from any real client
exports and retain the release manifest with the handover record.
