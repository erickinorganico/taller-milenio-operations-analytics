"""Assemble current, hash-matched governed agent work for local review.

This module is a read-only adapter between the governed agent runtime, the
code-owned metric registry, and the existing client action workbook contract.
It never starts an agent run or executes a business action.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .agent_runtime import AgentRuntimeError, _readonly_connection, _validate_evidence, list_available_agents


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "specs" / "agent_operating_contract.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _contract_roles() -> dict[str, dict[str, Any]]:
    payload = _read_json(CONTRACT_PATH)
    if not payload or payload.get("schema_version") != "1.0" or not isinstance(payload.get("roles"), list):
        raise ValueError("agent operating contract is missing or invalid")
    return {item["agent_id"]: item for item in payload["roles"] if isinstance(item, dict) and isinstance(item.get("agent_id"), str)}


def _metric_index(metric_registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(metric_registry, dict) or not isinstance(metric_registry.get("metrics"), list):
        raise ValueError("metric_registry must contain a metrics list")
    index: dict[str, dict[str, Any]] = {}
    for metric in metric_registry["metrics"]:
        if isinstance(metric, dict) and isinstance(metric.get("metric_id"), str):
            index[metric["metric_id"]] = metric
    return index


def _run_source_hash(run: dict[str, Any], packet: dict[str, Any] | None) -> str | None:
    value = run.get("warehouse_sha256") or run.get("source_hash")
    if value is None and packet:
        value = packet.get("warehouse_sha256")
    return value if isinstance(value, str) else None


def _trace_summary(path: Path) -> list[dict[str, Any]]:
    trace = path / "tool_trace.jsonl"
    if not trace.is_file():
        return []
    events = []
    for line in trace.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        safe = {key: event[key] for key in ("at", "event", "tool", "mode", "status", "count", "backend", "model") if key in event}
        if safe:
            events.append(safe)
    return events[-60:]


def _verified_native(result_file: dict[str, Any] | None) -> bool:
    if not result_file or result_file.get("backend") != "native_codex" or result_file.get("execution_evidence") != "verified_two_stage_local_cli":
        return False
    for receipt, stage in ((result_file.get("plan_receipt"), "plan"), (result_file.get("native_receipt"), "final")):
        if not isinstance(receipt, dict) or receipt.get("kind") != "local_codex_cli" or receipt.get("stage") != stage:
            return False
        if receipt.get("cli_exit_code") != 0 or receipt.get("completion_observed") is not True or not isinstance(receipt.get("model_id"), str):
            return False
    return result_file.get("model_invoked") is True


def _inspect_current_run(run_dir: Path, agent_id: str, expected_hash: str, expected_as_of: str | None,
                         expected_synthetic: bool | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    run = _read_json(run_dir / "run.json")
    if run is None:
        return ({"status": "missing", "model_invoked": False, "external_execution": False}, None)
    packet = _read_json(run_dir / "input_packet.json")
    result_file = _read_json(run_dir / "result.json")
    source_hash = _run_source_hash(run, packet)
    model_invoked = _verified_native(result_file)
    summary: dict[str, Any] = {
        "agent_id": agent_id,
        "backend": run.get("backend"),
        "run_status": run.get("status", "unknown"),
        "source_hash": source_hash,
        "source_hash_matches": source_hash == expected_hash,
        "model_invoked": model_invoked,
        "external_execution": bool(run.get("external_execution", False) or (result_file or {}).get("external_execution", False)),
        "synthetic": bool((packet or {}).get("synthetic", run.get("synthetic", False))),
        "as_of": (packet or {}).get("as_of"),
        "run_path": str(run_dir),
        "tool_trace": _trace_summary(run_dir),
    }
    if source_hash != expected_hash:
        summary.update(status="stale", reason="run source hash does not match the supplied database")
        return summary, None
    packet_hash = packet.get("warehouse_sha256") if packet else None
    run_hash = run.get("warehouse_sha256") or run.get("source_hash")
    if packet_hash and run_hash and packet_hash != run_hash:
        summary.update(status="blocked", reason="run and input packet source hashes disagree")
        return summary, None
    if packet_hash and packet_hash != expected_hash:
        summary.update(status="stale", reason="input packet source hash does not match the supplied database")
        return summary, None
    if run.get("agent_id") != agent_id:
        summary.update(status="blocked", reason="run agent_id does not match its role folder")
        return summary, None
    if run.get("status") != "completed" or not run.get("source_hash_verified") or result_file is None:
        summary.update(status="blocked", reason=run.get("blocked_reason") or "run is incomplete or lacks verified source evidence")
        return summary, None
    if result_file.get("status") != "completed" or result_file.get("external_execution") is not False:
        summary.update(status="blocked", reason="result is incomplete or violates the no-external-execution boundary")
        return summary, None
    if result_file.get("backend") != run.get("backend"):
        summary.update(status="blocked", reason="result backend does not match run backend")
        return summary, None
    if expected_as_of and summary.get("as_of") and summary["as_of"] != expected_as_of:
        summary.update(status="blocked", reason="run cutoff does not match the supplied metric registry")
        return summary, None
    if expected_synthetic is not None and summary["synthetic"] != expected_synthetic:
        summary.update(status="blocked", reason="run synthetic flag does not match the supplied metric registry")
        return summary, None
    summary.update(status="current", execution_class="native_codex" if summary["model_invoked"] else "deterministic_or_unverified", mode_label=result_file.get("mode_label"), execution_evidence=result_file.get("execution_evidence"))
    # Preserve the exact packet used by this run for evidence revalidation. The
    # result's own context is not authoritative (it can be modified separately).
    return summary, {**result_file, "_workspace_packet": packet or {}}


def _historical_runs(root: Path | None, agent_id: str, expected_hash: str) -> list[dict[str, Any]]:
    if root is None or not root.exists():
        return []
    entries: list[dict[str, Any]] = []
    for run_path in root.rglob("run.json"):
        run = _read_json(run_path)
        if not run or run.get("agent_id") != agent_id:
            continue
        packet = _read_json(run_path.parent / "input_packet.json")
        source_hash = _run_source_hash(run, packet)
        if source_hash == expected_hash:
            classification = "archived_matching_hash"  # historical location is not promoted to the current-run slot
        else:
            classification = "historical_source"
        historical_result = _read_json(run_path.parent / "result.json")
        entries.append({
            "status": classification,
            "backend": run.get("backend"),
            "run_status": run.get("status", "unknown"),
            "source_hash": source_hash,
            "model_invoked": _verified_native(historical_result),
            "execution_evidence": (historical_result or {}).get("execution_evidence"),
            "as_of": (packet or {}).get("as_of"),
            "run_path": str(run_path.parent),
        })
    return sorted(entries, key=lambda item: item.get("run_path", ""))


def _stable_id(prefix: str, agent_id: str, entity_type: str, entity_id: str, length: int) -> str:
    digest = hashlib.sha256(f"{agent_id}\0{entity_type}\0{entity_id}".encode("utf-8")).hexdigest()[:length]
    return prefix + digest


def _proposal_decisions(agent_id: str, role: dict[str, Any], result_file: dict[str, Any], run_summary: dict[str, Any],
                        metric_objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = result_file.get("result")
    if not isinstance(result, dict):
        return []
    evidence = result.get("evidence")
    packet = result_file.get("_workspace_packet", {})
    context = packet.get("tool_context") if isinstance(packet, dict) else None
    if not isinstance(context, dict):
        return []
    cases = context.get("cases", []) if isinstance(context, dict) else []
    if not isinstance(evidence, list) or not isinstance(cases, list):
        return []
    visible = {(case.get("entity_type"), case.get("entity_id")): case for case in cases if isinstance(case, dict)}
    exact_refs: list[dict[str, Any]] = []
    for reference in evidence:
        if not isinstance(reference, dict) or set(reference) != {"entity_type", "entity_id", "field", "value", "version"}:
            return []
        key = (reference["entity_type"], reference["entity_id"])
        # Do not silently discard a malformed or out-of-packet reference.
        if key not in visible or reference not in context.get("evidence", []):
            return []
        exact_refs.append(reference)
    if not exact_refs:
        return []

    selected_metric_ids = set()
    plan = _read_json(Path(run_summary["run_path"]) / "plan.json")
    if plan and isinstance(plan.get("metric_ids"), list):
        selected_metric_ids = set(plan["metric_ids"])
    if not selected_metric_ids:
        selected_metric_ids = {item.get("metric_id") for item in metric_objects}
    selected_metrics = [item for item in metric_objects if item.get("metric_id") in selected_metric_ids]
    drafts = result.get("drafts", []) if isinstance(result.get("drafts"), list) else []
    next_steps = result.get("manual_next_steps", []) if isinstance(result.get("manual_next_steps"), list) else []
    missing = result.get("missing_information", []) if isinstance(result.get("missing_information"), list) else []
    diagnosis = result.get("diagnosis") if isinstance(result.get("diagnosis"), str) else "Revisión basada en evidencia del corte."
    decisions = []
    # Current result schemas do not associate drafts with a specific entity.
    # Emit one run-level action per explicit draft, grounded in the run's full
    # validated evidence set; never copy a generic draft onto every case row.
    for draft_index, draft in enumerate(drafts):
        if not isinstance(draft, dict) or not isinstance(draft.get("text"), str):
            continue
        draft_kind = draft.get("kind") if isinstance(draft.get("kind"), str) else "draft"
        title = f"Revisar borrador · {role['owner_role']} · {draft_kind}"
        refs = exact_refs
        exact_evidence = [{
            "entity_type": ref["entity_type"], "entity_id": ref["entity_id"], "field": ref["field"],
            "value": ref["value"], "version": ref["version"],
        } for ref in refs]
        # The action workbook accepts evidence mappings and keeps these immutable
        # origin fields apart from the human-entered review columns.
        workbook_evidence = [{
            "table": ref["entity_type"], "record_id": ref["entity_id"], "field": ref["field"],
            "value": ref["value"], "version": ref["version"], "snapshot_id": run_summary["source_hash"],
        } for ref in refs]
        process_evidence = [{"process_id": process_id, "source": "specs/agent_operating_contract.json"} for process_id in role["processes"]]
        rationale = diagnosis
        if run_summary.get("execution_class") != "native_codex":
            rationale = "Línea base determinística o respuesta no verificada; requiere criterio humano. " + rationale
        entities = sorted({(ref["entity_type"], ref["entity_id"]) for ref in refs})
        rationale += f" Borrador de corrida sin asignación explícita a un caso; sustentado por {len(refs)} referencias en {len(entities)} entidades."
        rationale += " Métricas relacionadas: " + (", ".join(item["metric_id"] for item in selected_metrics) or "ninguna disponible") + "."
        rationale += " Propuesta pendiente; no acredita aprobación ni ejecución."
        draft_copy = [{"kind": draft_kind, "text": draft["text"], "requires_human_review": True}]
        stable_key = f"{run_summary['source_hash']}:{draft_index}:{draft_kind}"
        action_id = _stable_id("AGT-", agent_id, "draft", stable_key, 16)
        proposal = {
            "id": _stable_id("AP-", agent_id, "draft", stable_key, 20),
            "agent": agent_id,
            "title": title,
            "rationale": rationale,
            "evidence": exact_evidence[:100],
            "approval_required": True,
            "external_execution": False,
            "status": "pending",
        }
        decisions.append({
            "action_id": action_id,
            "category": role["proposal_category"],
            "title": title,
            "priority": "review",
            "owner_role": role["owner_role"],
            "why_now": rationale,
            "recommended_next_step": next_steps[0] if next_steps else "Una persona revisora confirma evidencia, contexto y siguiente paso.",
            "amount_at_risk_cents": None,
            "evidence": workbook_evidence + process_evidence,
            "source_ids": [f"{table}:{entity_id}" for table, entity_id in entities],
            "source_snapshot": run_summary["source_hash"],
            "source_hash": run_summary["source_hash"],
            "as_of": run_summary.get("as_of"),
            "metric_ids": [item["metric_id"] for item in selected_metrics],
            "metric_evidence": selected_metrics,
            "process_ids": role["processes"],
            "drafts": draft_copy,
            "missing_evidence": missing,
            "review_status": "pending",
            "approval_required": True,
            "external_execution": False,
            "action_proposal": proposal,
        })
    return decisions


def build_agent_workspace(database: str | Path, metric_registry: dict[str, Any], runs_root: str | Path,
                          historical_runs_root: str | Path | None = None) -> dict[str, Any]:
    """Build role workspaces and review decisions from current hash-matched runs.

    Historical runs are displayed as historical context and never yield current
    proposals. Native status is reported from the stored receipt; this function
    does not invoke the Codex CLI.
    """
    database_path, run_root = Path(database).resolve(), Path(runs_root).resolve()
    if not database_path.is_file():
        raise ValueError("database must be an existing file")
    source_hash = _file_hash(database_path)
    registry_source_hash = metric_registry.get("source_sha256") or metric_registry.get("database_sha256")
    if registry_source_hash is not None and registry_source_hash != source_hash:
        raise ValueError("metric registry source hash does not match the supplied database")
    metric_index = _metric_index(metric_registry)
    contracts = _contract_roles()
    profiles = {item["id"]: item for item in list_available_agents()}
    if set(contracts) != set(profiles):
        raise ValueError("agent profiles and operating contract disagree")

    agents = []
    decisions = []
    connection = _readonly_connection(database_path)
    try:
        for agent_id, role in contracts.items():
            profile = profiles[agent_id]
            expected_metrics = role["metric_ids"]
            metric_objects = [metric_index[metric_id] for metric_id in expected_metrics if metric_id in metric_index]
            missing_metrics = [metric_id for metric_id in expected_metrics if metric_id not in metric_index]
            current, result_file = _inspect_current_run(run_root / agent_id, agent_id, source_hash,
                                                       metric_registry.get("as_of"), metric_registry.get("synthetic"))
            if result_file is not None:
                packet = result_file.get("_workspace_packet", {})
                context = packet.get("tool_context", {}) if isinstance(packet, dict) else {}
                result = result_file.get("result", {})
                try:
                    if not isinstance(context, dict) or not isinstance(context.get("cases"), list) or not isinstance(context.get("evidence"), list):
                        raise AgentRuntimeError("run packet has no bounded case and evidence context")
                    evidence = result.get("evidence") if isinstance(result, dict) else None
                    if not isinstance(evidence, list):
                        raise AgentRuntimeError("result has no evidence list")
                    _validate_evidence(connection, profile, evidence, context["evidence"])
                    visible = {(case.get("entity_type"), case.get("entity_id")) for case in context["cases"] if isinstance(case, dict)}
                    if any((ref.get("entity_type"), ref.get("entity_id")) not in visible for ref in evidence if isinstance(ref, dict)):
                        raise AgentRuntimeError("result evidence is outside the packet's visible cases")
                except (AgentRuntimeError, sqlite3.Error) as error:
                    current.update(status="blocked", reason=f"current result evidence failed database revalidation: {error}")
                    result_file = None
            role_decisions = _proposal_decisions(agent_id, role, result_file, current, metric_objects) if result_file is not None else []
            decisions.extend(role_decisions)
            agents.append({
                "agent_id": agent_id,
                "profile": profile,
                "contract": role,
                "metric_objects": metric_objects,
                "missing_metric_ids": missing_metrics,
                "current_run": current,
                "historical_runs": _historical_runs(Path(historical_runs_root).resolve() if historical_runs_root else None, agent_id, source_hash),
                "proposals": role_decisions,
            })
    finally:
        connection.close()
    return {
        "schema_version": 1,
        "source": {"database": database_path.name, "sha256": source_hash, "synthetic": bool(metric_registry.get("synthetic", True)), "as_of": metric_registry.get("as_of"),
                   "metric_registry_source_sha256": registry_source_hash,
                   "metric_registry_source_binding": "verified" if registry_source_hash == source_hash else "unverified_digest_unavailable"},
        "agents": agents,
        "decisions": decisions,
        "limitations": [
            "Only completed runs whose source hash matches this database can produce current proposals.",
            "Archived runs are historical context, including archived runs that happen to share a source hash.",
            "Native completion proves a local model turn and contract validation, not operational utility, approval, adoption, or business impact.",
            "No run, proposal, workbook annotation, or approval executes a business operation.",
        ],
    }


__all__ = ["build_agent_workspace"]
