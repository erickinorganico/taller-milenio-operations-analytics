# Local decision opportunity review

## Current decision surfaces

The current source has two distinct kinds of repeated decisions:

1. Exact contract decisions remain deterministic: field typing/ranges, state transitions, references, inventory arithmetic, capacity uniqueness, SLA eligibility, payment reconciliation, evidence scope and approval gates.
2. V2 `native_codex` is a real, open-ended two-stage review caller. The first model call selects bounded evidence and code-owned metric IDs; the second drafts diagnosis, alternatives and manual next steps. It is review assistance, not a classifier, ranker or business-action executor.

All nine profiles have technically completed both native stages through the pinned official CLI `0.155.1`: 18 observed `turn.completed` events, final `verified_two_stage_local_cli` receipts and zero external actions. This proves the caller executed under its controls. It does not prove quality, savings or business impact. Review already found an effectiveness defect in collections evidence selection, which is being corrected and rerun.

## Laya assessment

There is no suitable validated bounded classification/ranking decision to replace with Laya in the current implementation. The native workbench task is open-ended evidence review, while the exact decisions require authoritative deterministic outcomes. Therefore:

- no Laya runtime or checkpoint was installed;
- no Laya inference was executed;
- no token, cost, latency, quality or supervision saving is claimed;
- the current native caller is not silently relabeled as a Laya opportunity.

A future candidate could be bounded triage of a free-text intake note into `particular`, `fleet`, `tow` or `review`, but that caller and a real labeled dataset do not exist. Before any shadow experiment, predeclare Spanish/English labels, ambiguous/adversarial cases, the `review` fallback, baseline quality, cold/warm latency, retries and human supervision cost. It must have no authority to dispatch, contact, diagnose, price or move money.

Decision: **no current Laya integration**. Revisit only after a concrete repeated classifier/ranker and evaluation set exist. See [docs/PROJECT-EFFICIENCY.md](docs/PROJECT-EFFICIENCY.md) for the broader build/runtime efficiency record.
