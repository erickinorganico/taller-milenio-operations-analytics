# Agent workspace

`milenio.agent_workspace.build_agent_workspace(database, metric_registry, runs_root, historical_runs_root=None)` assembles the role view used by the Studio. It reads completed run artifacts, the supplied code-owned registry, and the agent/process contract. It does not start a run, call a model, or alter a source file.

## Evidence path

The workspace connects six governed process definitions to the nine existing agent profiles. `specs/agent_operating_contract.json` defines each role's process IDs, trigger families, owner role, proposal category, and permitted `M-*` metric IDs. The profiles retain their original metric aliases for compatibility. `query_metrics` accepts either those legacy IDs or a canonical ID present in the role contract; canonical results pass through unchanged from `milenio.metric_registry`, including value, denominator, status, reason, source fields, bounded evidence, and limitations. Agents cannot supply SQL.

Each run is tied to the supplied SQLite file's SHA-256. A completed run can appear in the current slot only when its recorded warehouse hash matches, the runtime marked that hash verified, the result backend matches the run, and external execution is false. A stale run is labeled `stale` and produces no current decisions. Runs found under `historical_runs_root` remain historical even when their source hash happens to match. Native status comes only from the stored runtime result receipt; rules runs remain labeled deterministic and externally supplied responses remain unverified.

Current decisions represent actual drafts returned by each run. A draft without explicit case attribution remains a run-level review proposal; it is never copied into a separate action for every cited record. Exact table/id/field/value/version references are checked against the bounded input packet, profile scope and current read-only database before a proposal is emitted. A mismatch blocks the run in the workspace. Each decision is compatible with the local client action workbook and carries a pending `action_proposal`, role/process/metric references, source identity, `approval_required=true` and `external_execution=false`. IDs are stable for the same role, source identity and draft position. No price, financial exposure, urgency rank, approval or execution result is inferred. The workbook's owner, status, date, note and outcome evidence remain human annotations.

## Limits and operation

The current data and demonstrations are synthetic. A successful native run means that the local Codex CLI completed the configured structured-response flow and the runtime accepted its result; it does not show staff adoption, decision usefulness, operational execution, or business impact. Model choice is controlled by `MILENIO_CODEX_MODEL` in the existing installed Codex subscription CLI. There is no paid API fallback. A blocked native call stays blocked; the workspace does not retry it or substitute a rules result.

Use the builder with a metric registry already calculated from the same database:

```python
from milenio.agent_workspace import build_agent_workspace
from milenio.metric_registry import build_metric_registry

metrics = build_metric_registry("artifacts/workbench-v2/warehouse.sqlite")
workspace = build_agent_workspace(
    "artifacts/workbench-v2/warehouse.sqlite",
    metrics,
    "artifacts/workbench-v2/agent_runs",
    historical_runs_root="artifacts/agent-run-history",
)
```

The result contains `source`, `agents`, `decisions`, and `limitations`. Each agent includes its profile, process contract, permitted metric objects, missing metric IDs, current run status/tool trace, historical run summaries, and current proposals. Historical runs never feed the current `decisions` list.
