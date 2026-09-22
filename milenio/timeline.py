"""Synthetic lifecycle source generation and strict observational event validation."""
from collections import deque
from datetime import timedelta

from .contracts import FLOWS, INITIAL, DEMO_NOW
from .domain import date_value, require


def _path(kind, final):
    pending = deque([[INITIAL[kind]]])
    while pending:
        path = pending.popleft()
        if path[-1] == final:
            return path
        for target in FLOWS[kind][path[-1]]:
            if target not in path:
                pending.append(path + [target])
    raise ValueError("Unreachable synthetic state")


def synthetic_history(data, now=DEMO_NOW):
    """Generate declared fictional paths; never infer observed history for imports."""
    rows = []
    for kind in FLOWS:
        for rec in data[kind]:
            path = _path(kind, rec["status"])
            if kind == "work_orders" and rec["status"] == "rework":
                path = ["received", "inspected", "authorized", "scheduled", "in_service", "quality_check", "rework"]
            end = date_value(rec.get("completed_at") or rec.get("closed_at") or now)
            start = date_value(rec.get("opened_at") or rec.get("requested_at") or (end - timedelta(days=3)).isoformat())
            require(start <= end, "Cronología sintética invertida")
            for i, state in enumerate(path):
                at = start + (end - start) * i / max(1, len(path) - 1)
                rows.append({"id": f"EV-{kind}-{rec['id']}-{i+1}", "entity_type": kind, "entity_id": rec["id"],
                             "sequence": i + 1, "from_state": path[i-1] if i else None, "to_state": state,
                             "at": at.isoformat().replace("+00:00", "Z"), "actor": "Synthetic scenario generator",
                             "synthetic": True, "provenance": "fictional_path_not_observed"})
    return rows


def validate_history(data, history, now=DEMO_NOW):
    require(isinstance(history, list), "Historial debe ser lista")
    expected = {(kind, r["id"]): r for kind in FLOWS for r in data[kind]}
    groups, seen = {}, set()
    for event in history:
        require(isinstance(event, dict), "Evento inválido")
        key = (event.get("entity_type"), event.get("entity_id"))
        require(key in expected, "Evento sin entidad o sin flujo")
        require(event.get("synthetic") is True, "Solo eventos sintéticos")
        require(isinstance(event.get("id"), str) and event["id"] not in seen, "ID de evento duplicado o ausente")
        seen.add(event["id"])
        require(type(event.get("sequence")) is int and event["sequence"] >= 1, "Secuencia inválida")
        require(isinstance(event.get("actor"), str) and bool(event["actor"].strip()), "Evento sin responsable")
        require(event.get("provenance") in {"fictional_path_not_observed", "synthetic_export"}, "Procedencia de evento no declarada")
        require(date_value(event.get("at")) <= date_value(now), "Evento posterior al corte")
        groups.setdefault(key, []).append(event)
    for (kind, entity_id), events in groups.items():
        events.sort(key=lambda e: e["sequence"])
        record = expected[(kind, entity_id)]
        first_field, last_field = ("opened_at", "completed_at") if kind == "work_orders" else ("requested_at", "closed_at") if kind == "tows" else (None, None)
        if first_field:
            require(date_value(events[0]["at"]) == date_value(record[first_field]), "Inicio de historial no coincide con evento de origen")
            if record.get(last_field):
                require(date_value(events[-1]["at"]) == date_value(record[last_field]), "Cierre de historial no coincide con evento de origen")
        previous, last_time = None, None
        for i, event in enumerate(events):
            require(event["sequence"] == i + 1, "Secuencia de evento incompleta/duplicada")
            require(event.get("from_state") == previous, "Estado previo del evento no coincide")
            state = event.get("to_state")
            require(state == INITIAL[kind] if i == 0 else state in FLOWS[kind].get(previous, []), "Transición histórica no permitida")
            at = date_value(event["at"])
            require(last_time is None or at >= last_time, "Fechas del historial fuera de orden")
            previous, last_time = state, at
        require(previous == expected[(kind, entity_id)]["status"], "Historial no coincide con snapshot final")
    return {"stateful_records": len(expected), "records_with_history": len(groups), "events": len(history),
            "coverage": round(len(groups) / len(expected), 4) if expected else None,
            "status": "complete" if expected and len(groups) == len(expected) else "partial" if groups else "unknown",
            "limitation": "Demo paths are explicitly fictional; imported snapshots do not imply observed transitions."}
