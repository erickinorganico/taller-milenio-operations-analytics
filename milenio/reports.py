"""Read-only projections and deterministic, evidence-bearing agent drafts."""
import copy
from datetime import timedelta

from .contracts import DEMO_NOW, FIELDS, FLOWS, SCHEMA_VERSION, BUSY_WORK, TERMINAL_WORK
from .domain import date_value, stock_totals, paid_amount, validate_dataset, DomainError, require
from .storage import digest


AGENTS = {
    "intake_admin": "Asistente de recepción",
    "operations_controller": "Control de taller",
    "maintenance_planner": "Planificador de mantenimiento",
    "fleet_sales_research": "Investigación comercial de flotillas",
    "fleet_sla_watcher": "Vigilancia de SLA",
    "tow_dispatch_assistant": "Asistente de grúas",
    "collections_assistant": "Asistente de cobranza",
    "marketing_planner": "Planificador de marketing",
    "weekly_operator": "Resumen de operación",
}


def reference(kind, rec, field):
    return {"entity_type": kind, "entity_id": rec["id"], "field": field, "value": rec.get(field), "version": rec["version"]}


def projections(data, now=DEMO_NOW):
    require(date_value(now) == date_value(DEMO_NOW), "Esta versión analiza solo el corte sintético fijo; otro corte necesita snapshot validado")
    out = copy.deepcopy(data)
    at = date_value(now)
    contracts = {r["id"]: r for r in data["contracts"]}
    for part in out["parts"]:
        part.update(stock_totals(data, part["id"]))
    for invoice in out["invoices"]:
        paid = paid_amount(data, invoice["id"])
        balance = invoice["amount_cents"] - paid if invoice["status"] == "issued" else 0
        invoice.update(paid_cents=paid, balance_cents=balance,
                       payment_status="not_issued" if invoice["status"] != "issued" else "paid" if balance == 0 else "partial" if paid else "unpaid")
    for work in out["work_orders"]:
        start = date_value(work["opened_at"])
        end = date_value(work["completed_at"]) if work.get("completed_at") else at
        work["downtime_hours"] = round(max(0, (end - start).total_seconds() / 3600), 1)
        contract = contracts.get(work.get("contract_id"))
        status, deadline = "not_applicable", None
        if contract:
            if work["status"] == "cancelled":
                status = "excluded"
            elif not contract.get("approval_ref") or not (date_value(contract["starts_at"]) <= start < date_value(contract["ends_at"])) or contract["status"] not in {"active", "expired"}:
                status = "unknown"
            else:
                due = start + timedelta(hours=contract["sla_hours"])
                deadline = due.isoformat().replace("+00:00", "Z")
                status = "breached" if end > due else "met" if work["status"] == "delivered" else "at_risk" if due - at <= timedelta(hours=4) else "on_track"
        work.update(sla_status=status, sla_due_at=deadline)
    return out


def exceptions(data, now=DEMO_NOW):
    at = date_value(now)
    out = []

    def add(category, severity, title, detail, kind, record, field, action):
        out.append({"id": category + ":" + record["id"], "category": category, "severity": severity,
                    "title": title, "detail": detail, "entity_type": kind, "entity_id": record["id"],
                    "evidence": [reference(kind, record, field)], "action": action})

    for lead in data["leads"]:
        if lead["status"] not in {"won", "lost"} and date_value(lead["follow_up_at"]) <= at:
            add("follow_up", "medium", "Seguimiento pendiente", lead["need"], "leads", lead, "follow_up_at", "Preparar seguimiento y revisar consentimiento")
    for quote in data["quotes"]:
        if quote["status"] == "sent":
            add("quote", "high" if date_value(quote["valid_until"]) < at else "medium", "Cotización sin respuesta", quote["description"], "quotes", quote, "status", "Revisar vigencia y preparar borrador")
    for app in data["appointments"]:
        if app["status"] == "pending" and date_value(app["starts_at"]) <= at + timedelta(days=1):
            add("appointment", "medium", "Cita por confirmar", app["reason"], "appointments", app, "status", "Revisar disponibilidad y consentimiento")
    for work in data["work_orders"]:
        if work["status"] == "waiting_parts" or work.get("block_reason") and work["status"] not in TERMINAL_WORK:
            add("blocked_work", "high", "Orden detenida", work.get("block_reason") or "Espera refacciones", "work_orders", work, "status", "Verificar compra y disponibilidad real")
        elif work["status"] not in TERMINAL_WORK and date_value(work["due_at"]) < at:
            add("work_overdue", "high", "Entrega objetivo vencida", work["description"], "work_orders", work, "due_at", "Revisar capacidad y plan de entrega")
        if work.get("sla_status") in {"breached", "at_risk", "unknown"}:
            add("sla", "high" if work["sla_status"] == "breached" else "medium", "SLA: " + work["sla_status"], "Evaluado desde recepción con horas del contrato; sin promesa automática", "work_orders", work, "contract_id", "Revisar contrato y evidencia del servicio")
    for part in data["parts"]:
        if part.get("available", 0) <= part["reorder_point"]:
            add("stock", "high" if part.get("available", 0) == 0 else "medium", "Revisar reposición", part["name"], "parts", part, "reorder_point", "Preparar compra para revisión")
    vehicles = {r["id"]: r for r in data["vehicles"]}
    for item in data["maintenance"]:
        if item["status"] in {"due", "scheduled"} and (date_value(item["due_at"]) <= at + timedelta(days=7) or vehicles[item["vehicle_id"]]["odometer_km"] >= item["due_km"]):
            add("maintenance", "medium", "Mantenimiento próximo", item["service"], "maintenance", item, "due_at", "Preparar propuesta de programación")
    for tow in data["tows"]:
        if tow["status"] not in {"closed", "cancelled"}:
            add("tow", "high" if date_value(tow["due_at"]) < at else "medium", "Solicitud de grúa abierta", tow["pickup"] + " → " + tow["destination"], "tows", tow, "status", "Revisión humana de seguridad, precio, unidad y despacho")
    for inv in data["invoices"]:
        if inv["status"] == "issued" and inv.get("balance_cents", 0) > 0 and date_value(inv["due_at"]) < at:
            add("collections", "high", "Saldo vencido", "Saldo gerencial pendiente; no es comprobante fiscal", "invoices", inv, "due_at", "Conciliar pagos y preparar recordatorio")
    return sorted(out, key=lambda x: (0 if x["severity"] == "high" else 1, x["id"]))


def metrics(data, now=DEMO_NOW):
    issued = [r for r in data["invoices"] if r["status"] == "issued"]
    occupied = {r["bay_id"] for r in data["work_orders"] if r["status"] in BUSY_WORK}
    return {
        "open_work_orders": sum(r["status"] not in TERMINAL_WORK for r in data["work_orders"]),
        "waiting_parts": sum(r["status"] == "waiting_parts" for r in data["work_orders"]),
        "bay_utilization_pct": round(100 * len(occupied) / len(data["bays"]), 1) if data["bays"] else None,
        "active_contracts": sum(r["status"] == "active" and date_value(r["starts_at"]) <= date_value(now) < date_value(r["ends_at"]) for r in data["contracts"]),
        "active_tows": sum(r["status"] not in {"closed", "cancelled"} for r in data["tows"]),
        "invoiced_cents": sum(r["amount_cents"] for r in issued),
        "paid_cents": sum(r["amount_cents"] for r in data["payments"]),
        "receivable_cents": sum(r["balance_cents"] for r in issued),
        "overdue_cents": sum(r["balance_cents"] for r in issued if date_value(r["due_at"]) < date_value(now)),
        "cash_net_cents": sum(r["amount_cents"] for r in data["payments"] if r["method"] == "cash") - sum(r["amount_cents"] for r in data["expenses"] if r["method"] == "cash"),
        "expenses_cents": sum(r["amount_cents"] for r in data["expenses"]),
        "quote_pipeline_cents": sum(r["amount_cents"] for r in data["quotes"] if r["status"] in {"draft", "sent"}),
        "sla_breaches": sum(r["sla_status"] == "breached" for r in data["work_orders"]),
        "sla_at_risk": sum(r["sla_status"] == "at_risk" for r in data["work_orders"]),
        "parts_consumed_cost_cents": sum(r["quantity"] * r["unit_cost_cents"] * (1 if r["move_type"] == "consume" else -1) for r in data["stock_moves"] if r["move_type"] in {"consume", "return"}),
    }


def proposed_actions(data, now=DEMO_NOW):
    """No model callers or outbound tools: input snapshot -> human-review drafts."""
    projected = projections(data, now)
    proposals = []
    agents_by_category = {"follow_up": "intake_admin", "quote": "intake_admin", "appointment": "intake_admin", "blocked_work": "operations_controller", "work_overdue": "operations_controller", "stock": "operations_controller", "maintenance": "maintenance_planner", "sla": "fleet_sla_watcher", "tow": "tow_dispatch_assistant", "collections": "collections_assistant"}

    def add(agent, title, rationale, evidence):
        proposals.append({"id": "AP-" + digest({"agent": agent, "title": title, "evidence": evidence})[:20], "agent": agent,
                          "title": title, "rationale": rationale, "evidence": evidence,
                          "approval_required": True, "external_execution": False, "status": "pending"})

    for exc in exceptions(projected, now):
        add(agents_by_category[exc["category"]], exc["title"], exc["action"] + ". Borrador sintético: requiere revisión humana; no ejecuta acciones.", exc["evidence"])
    for opp in data["opportunities"]:
        if opp["status"] not in {"won", "lost"}:
            add("fleet_sales_research", "Preparar investigación: " + opp["title"], "Validar tamaño de flotilla, zona, tipos de unidad, responsables y necesidad mediante fuentes públicas autorizadas. Preparar propuesta; no contactar ni prometer precios. Siguiente paso registrado: " + opp["next_step"], [reference("opportunities", opp, "status"), reference("opportunities", opp, "next_step")])
    for campaign in data["campaigns"]:
        if campaign["status"] in {"draft", "review"}:
            add("marketing_planner", "Revisar campaña: " + campaign["name"], "Verificar audiencia, consentimiento y contenido antes de cualquier publicación. Borrador: " + campaign["draft"], [reference("campaigns", campaign, "draft")])
    evidence = [reference("work_orders", r, "status") for r in data["work_orders"][:20]]
    if evidence:
        add("weekly_operator", "Preparar reunión de operación", "Revisar órdenes abiertas, bloqueos y retrabajos de esta muestra sintética. Definir responsables y próximos pasos; no inferir resultados del negocio real.", evidence)
    return proposals


def bootstrap(store, now=DEMO_NOW):
    with store.lock:
        raw = store.data()
        checks = []
        try:
            validate_dataset(raw)
            checks.append({"name": "Referencias, stock, capacidad, dinero y contratos", "ok": True, "detail": "Invariantes del modelo válidas"})
        except DomainError as exc:
            checks.append({"name": "Invariantes", "ok": False, "detail": str(exc)})
        checks.append({"name": "Cadena de auditoría y estado actual", "ok": store.verify_audit(), "detail": "SHA-256 y correspondencia de registros"})
        projected = projections(raw, now)
        summary = metrics(projected, now)
        checks.append({"name": "Facturación = pagos + saldo", "ok": summary["invoiced_cents"] == summary["paid_cents"] + summary["receivable_cents"], "detail": "Cotizaciones y efectivo se muestran por separado"})
        return {"meta": {"synthetic": True, "mode": "demo", "now": now, "schema_version": SCHEMA_VERSION, "revision": store.revision()},
                "data": projected, "metrics": summary, "exceptions": exceptions(projected, now),
                "proposals": raw["proposals"], "flows": FLOWS, "fields": FIELDS, "audit": store.audit(),
                "reconciliation": {"ok": all(c["ok"] for c in checks), "checks": checks}}
