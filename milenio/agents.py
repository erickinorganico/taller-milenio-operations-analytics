"""Deterministic read-only agent contract and evidence grader.

There are deliberately no tool adapters for external writes or business commands.
Human approval is a review annotation in a downstream process, not execution.
"""
import re
from .domain import require
from .reports import AGENTS, proposed_actions
from .storage import canonical


def evaluate_proposals(data, proposals):
    index = {kind: {r["id"]: r for r in rows} for kind, rows in data.items()}
    ids = set()
    for proposal in proposals:
        require(isinstance(proposal, dict) and set(proposal) == {"id", "agent", "title", "rationale", "evidence", "approval_required", "external_execution", "status"}, "Contrato de propuesta inválido")
        require(proposal.get("agent") in AGENTS, "Agente desconocido")
        require(proposal.get("approval_required") is True, "Aprobación humana obligatoria")
        require(proposal.get("external_execution") is False, "Ejecución externa prohibida")
        require(proposal.get("status") == "pending", "El agente solo produce propuestas pendientes")
        require(isinstance(proposal.get("id"), str) and re.fullmatch(r"AP-[a-f0-9]{20}", proposal["id"]) and proposal["id"] not in ids, "ID de propuesta inválido o duplicado")
        ids.add(proposal["id"])
        require(all(isinstance(proposal.get(f), str) and proposal[f].strip() for f in ("title", "rationale")), "Texto de propuesta inválido")
        require(isinstance(proposal.get("evidence"), list) and 0 < len(proposal["evidence"]) <= 100, "Evidencia requerida")
        for ref in proposal["evidence"]:
            require(isinstance(ref, dict), "Referencia de evidencia inválida")
            require(set(ref) == {"entity_type", "entity_id", "field", "value", "version"} and type(ref["version"]) is int, "Contrato de evidencia inválido")
            record = index.get(ref.get("entity_type"), {}).get(ref.get("entity_id"))
            require(record is not None, "Evidencia de agente inexistente")
            require(ref.get("field") in record, "Campo de evidencia inexistente")
            require(canonical(record[ref["field"]]) == canonical(ref.get("value")) and record["version"] == ref.get("version"), "Evidencia de agente desactualizada o inventada")
    return {"status": "pass", "proposals": len(proposals), "agents_exercised": sorted({p["agent"] for p in proposals}),
            "critical_violations": 0, "mode": "deterministic_read_only", "external_tools": [],
            "disclaimer": "Contract and evidence validation, not a model-quality or business-impact evaluation."}


def run_agents(data, now):
    proposals = proposed_actions(data, now)
    grade = evaluate_proposals(data, proposals)
    return proposals, grade
