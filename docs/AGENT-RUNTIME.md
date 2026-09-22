# Governed agent workbench

`milenio.agent_runtime` adds a review-only workbench beside the existing deterministic proposal checks in `milenio.agents`. It does not replace or alter those checks.

Nine role profiles live in `agents/profiles.json`, with readable role prompts in `agents/*.md`: intake administration, workshop control, maintenance planning, fleet sales research, fleet SLA evidence review, tow dispatch review, collections review, marketing planning, and weekly operations facilitation. Each profile declares its persona, objective, visible SQLite tables, permitted read tools, expected deliverable, and role-specific criteria.

Use `list_available_agents()` to enumerate profile metadata. A run starts with:

```python
from milenio.agent_runtime import prepare_agent_run

run = prepare_agent_run("artifacts/workbench-v2/warehouse.sqlite", "artifacts/agent-runs/ops-001", "operations_controller")
```

The default `backend="rules"` runs an offline deterministic baseline. Its `result.json` says `model_invoked: false` and `mode_label: offline deterministic baseline; no LLM invoked`; it must never be represented as inference.

`backend="native_codex"` is an opt-in local invocation of the installed Codex subscription CLI, not a paid API provider. It makes at most two ephemeral `codex exec` calls with `--ignore-user-config`, `--json`, a read-only sandbox, no approval prompts, and a local output schema. First the model receives bounded visible cases and selects 1–12 exact evidence reads plus allowed metric IDs. The runtime rejects an invalid scope, unseen ID, field, duplicate, arbitrary SQL, or oversized request before making the final call. It then supplies only the selected evidence and canned metric results to the final model call. `MILENIO_CODEX_BIN` selects the installed local executable and `MILENIO_CODEX_MODEL` selects the explicit subscription model (default `gpt-5.6-luna`). Authentication, timeout, CLI, schema, plan, or response failures leave `run.json` as `blocked`; there is no fallback to rules or automatic retry. The run may also be completed after an externally obtained structured response:

The native command disables `shell_tool`, apps, browser, computer use, multi-agent, plugins, image generation, in-app browser, and web search. `native_config_receipt.json` records that mediated configuration without storing a host path. Provider events that identify a prohibited tool item, such as command execution or a browser call, fail the run before their output can be used.

```python
from milenio.agent_runtime import complete_agent_run

complete_agent_run("artifacts/agent-runs/ops-001", response_json, backend="native_codex")
```

The response must contain a concrete `diagnosis`, `alternatives`, `manual_next_steps`, review-only `drafts`, `missing_information`, a `sensitivity` assessment, `workplan`, and at least one exact evidence reference. The runtime rereads the SQLite source with `mode=ro` and `PRAGMA query_only=ON`, then verifies the source SHA-256 before accepting completion. It rejects unknown tables, fields, entity IDs, values, versions, stale source hashes, malformed output, and references outside the profile scope or the agent-selected evidence. Input fields are passed to the prompt as data and marked untrusted. An externally supplied JSON response (including a test fake) persists as `externally_supplied_unverified` with `model_invoked: false`. Only matching plan and final local-CLI receipts with model ID, zero exit, and observed completion events set `model_invoked: true`.

Each output directory contains `input_packet.json`, `prompt.md`, `tool_trace.jsonl`, `run.json`, and on completion `result.json`. Native runs also contain the selected `plan.json`, `plan_receipt.json`, `final_receipt.json`, separate schemas and last-message artifacts for each stage, and `final_prompt.md`. `input_packet.json` contains the bounded cases followed by the agent-selected evidence and canned metrics. Its warehouse reference is relative to the run directory, so a run and source can move together in a portable package without retaining a host path. The trace deliberately stores only provider event type, model ID, and numeric usage, never raw CLI stdout/stderr. `checkpoint_agent_run`, `resume_agent_run`, and `record_review_decision` append local review artifacts. A recorded approval is only a human annotation: it cannot send a message, contact anyone, dispatch, purchase, schedule, write business data, or execute an external action.

The only runtime tools are `inspect_scoped_cases`, `read_evidence`, and `query_metrics`. Metrics are a code-owned allowlist of canned SQLite queries; no prompt can supply SQL. The source connection uses SQLite `mode=ro` and `PRAGMA query_only=ON`, while the source SHA-256 is checked before and after the deterministic loop and before native completion.
