"""Complete, deterministic review queue for the synthetic operating warehouse.

Every row in each relevant source is inspected.  Cases are suggestions for a
person to review; this module cannot approve, dispatch, collect, or purchase.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from .contracts import DEMO_NOW
from .domain import date_value
from .source_catalog import ALLOWED_NAMES, AUXILIARY_KEYS, DERIVED_KEYS, SOURCE_NAMES


POLICY = {
    "version": "operating-cases-1",
    "cutoff": DEMO_NOW,
    "priority_meaning": {
        "P1": "Revisión prioritaria propuesta por atraso, retrabajo o riesgo de servicio.",
        "P2": "Revisión operativa propuesta en el siguiente ciclo de trabajo.",
        "P3": "Completar evidencia antes de decidir una acción.",
    },
    "limitations": "Umbrales y prioridades heurísticos del demo; no son SLA pactados, aprobación ni acción ejecutada. Los importes son saldos de facturas vinculadas, nunca ROI.",
    "external_business_action": False,
}

# All identifiers are code-owned; no SQL identifier comes from a caller.
SOURCES = ALLOWED_NAMES
CASE_METRICS = {
    "work_orders": ("M-WIP-OPEN",),
    "invoices": ("M-AR-RECEIVABLE", "M-AR-OVERDUE"),
    "mart_inventory": ("M-STOCK-AVAILABLE", "M-STOCK-REORDER"),
    "maintenance": ("M-FLEET-MAINTENANCE",),
    "mart_service_journey": ("M-FLEET-SLA-ELIGIBILITY", "M-FLEET-SLA-RISK"),
    "opportunities": ("M-FLEET-OPEN-OPPS",),
    "tows": ("M-TOW-OPEN", "M-TOW-HUMAN-REFS"),
    "leads": ("M-B2C-LEADS",),
    "quotes": ("M-FIN-QUOTES",),
}


def _at(value):
    return date_value(value) if value else None


def _ref(table, row, field, *, key="id"):
    return {
        "table": table,
        "record_id": str(row[key]),
        "field": field,
        "value": row.get(field),
        "version": row.get("version"),
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_operating_cases(database: str | Path | sqlite3.Connection, metric_registry: dict) -> dict:
    """Read the local warehouse and return the full synthetic exception queue.

    A database path is opened with SQLite ``mode=ro``. A supplied connection is
    left open. Missing tables yield unknown coverage and suppress dependent
    cases; an empty present table is reported as an observed empty extract.
    """
    if not isinstance(metric_registry, dict) or not isinstance(metric_registry.get("metrics"), list):
        raise ValueError("A measured metric registry is required")
    if metric_registry.get("as_of") != DEMO_NOW:
        raise ValueError("Metric registry and operating cutoff must match DEMO_NOW")
    metric_by_id = {m["metric_id"]: m for m in metric_registry["metrics"]}
    if len(metric_by_id) != len(metric_registry["metrics"]):
        raise ValueError("Duplicate metric ID")
    owned = not isinstance(database, sqlite3.Connection)
    database_path = Path(database).resolve() if owned else None
    source_hash = _file_sha256(database_path) if database_path is not None else None
    source_hash_kind = "sqlite_file_sha256" if owned else "unverified_connection"
    metric_source_hash = metric_registry.get("source_sha256")
    if owned and metric_source_hash is not None and metric_source_hash != source_hash:
        raise ValueError("Metric registry source SHA-256 does not match operating warehouse")
    con = sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True) if owned else database
    try:
        existing = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        tables = {}
        for table in SOURCES:
            if table not in existing:
                tables[table] = None
                continue
            columns = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
            key = DERIVED_KEYS.get(table, AUXILIARY_KEYS.get(table, ("id",)))
            ordering = ",".join('"' + field + '"' for field in key)
            tables[table] = [dict(zip(columns, record)) for record in con.execute(f'SELECT * FROM "{table}" ORDER BY {ordering}')]
            if table in SOURCE_NAMES and any(row.get("synthetic") != 1 for row in tables[table]):
                raise ValueError(f"Non-synthetic row in synthetic operating source {table}")
        # This hash describes the decoded, ordered inputs. It is never passed
        # off as the SHA-256 of the SQLite file or as a verified connection ID.
        input_rows_sha256 = hashlib.sha256(json.dumps(tables, sort_keys=True, ensure_ascii=False,
                                                      separators=(",", ":")).encode("utf-8")).hexdigest()
        triggered = defaultdict(int)
        decisions = []
        cutoff = _at(DEMO_NOW)

        def emit(trigger, table, row, title, priority, owner, why, step, refs,
                 metric_ids, amount=None):
            if any(mid not in metric_by_id for mid in metric_ids):
                raise ValueError("Case references an unknown governed metric")
            if any(metric_by_id[mid]["status"] != "measured" for mid in metric_ids):
                return
            key = "part_id" if table == "mart_inventory" else "work_order_id" if table == "mart_service_journey" else "id"
            record_id = str(row[key])
            identity = f"{trigger}:{table}:{record_id}"
            action_id = "OPS-" + trigger.upper().replace("_", "-") + "-" + hashlib.sha256(identity.encode()).hexdigest()[:12]
            source_ids = list(dict.fromkeys(f"{r['table']}:{r['record_id']}" for r in refs))
            process_ids = sorted({pid for mid in metric_ids for pid in metric_by_id[mid].get("process_ids", [])})
            decisions.append({
                "action_id": action_id, "category": trigger, "title": title,
                "priority": priority, "owner_role": owner, "why_now": why,
                "recommended_next_step": step, "amount_at_risk_cents": amount,
                "source_ids": source_ids, "metric_ids": metric_ids,
                "process_ids": process_ids, "evidence": refs,
                "source_hash": source_hash, "source_hash_kind": source_hash_kind,
                "review_status": "pending",
                "external_business_action": False,
            })
            triggered[table] += 1

        if tables["work_orders"] is not None:
            for row in tables["work_orders"]:
                status = row["status"]
                open_order = status not in {"delivered", "cancelled"}
                due = _at(row.get("due_at"))
                late = bool(open_order and due and due < cutoff)
                base = [_ref("work_orders", row, f) for f in ("status", "due_at", "block_reason", "qc_ref")]
                mid = ["M-WIP-OPEN", "M-WIP-WAITING-PARTS"] if status == "waiting_parts" else ["M-WIP-OPEN"]
                if status == "waiting_parts":
                    emit("waiting_parts", "work_orders", row, f"Desbloquear partes · {row['id']}",
                         "P1" if late else "P2", "Jefatura de taller",
                         "La orden espera partes" + (" y su fecha comprometida pasó." if late else "."),
                         "Verificar qué parte falta, reservas y compras recibidas; acordar responsable y próxima revisión.", base, mid)
                elif status == "rework":
                    emit("rework", "work_orders", row, f"Revisar retrabajo · {row['id']}", "P1", "Jefatura de taller",
                         "La orden está en retrabajo; la causa y el control de calidad requieren revisión.",
                         "Confirmar la falla, responsable técnico y criterio de control de calidad antes de prometer entrega.", base, mid)
                elif status == "ready":
                    emit("ready", "work_orders", row, f"Revisar entrega · {row['id']}", "P1" if late else "P2", "Recepción",
                         "La orden figura lista y aún no entregada" + ("; fecha comprometida vencida." if late else "."),
                         "Verificar control de calidad, autorización y condiciones de entrega; coordinar contacto humano.", base, mid)
                elif late:
                    emit("past_due_work", "work_orders", row, f"Revisar atraso · {row['id']}", "P1", "Jefatura de taller",
                         "La orden permanece abierta después de la fecha comprometida.",
                         "Confirmar avance físico, causa y responsable; revisar la fecha con recepción.", base, mid)

        if tables["invoices"] is not None and tables["payments"] is not None:
            paid = defaultdict(int)
            by_invoice = defaultdict(list)
            for payment in tables["payments"]:
                paid[payment["invoice_id"]] += payment["amount_cents"]
                by_invoice[payment["invoice_id"]].append(payment)
            for row in tables["invoices"]:
                balance = row["amount_cents"] - paid[row["id"]]
                due = _at(row.get("due_at"))
                if row["status"] != "issued" or balance <= 0 or due is None or due >= cutoff:
                    continue
                days = max(0, (cutoff.date() - due.date()).days)
                refs = [_ref("invoices", row, f) for f in ("status", "amount_cents", "due_at")]
                for payment in by_invoice[row["id"]]:
                    refs.extend(_ref("payments", payment, f) for f in ("invoice_id", "amount_cents", "paid_at"))
                emit("overdue_ar", "invoices", row, f"Conciliar saldo vencido · {row['id']}",
                     "P1" if days >= 15 else "P2", "Administración",
                     f"Saldo positivo conciliado de {balance} centavos; {days} días calendario desde vencimiento.",
                     "Verificar pagos, disputa y acuerdo vigente; registrar el seguimiento autorizado con responsable y fecha.",
                     refs, ["M-AR-RECEIVABLE", "M-AR-OVERDUE"], balance)

        if tables["mart_inventory"] is not None:
            parts = {r["id"]: r for r in (tables["parts"] or [])}
            for row in tables["mart_inventory"]:
                if row["available"] > row["reorder_point"]:
                    continue
                refs = [_ref("mart_inventory", row, f, key="part_id") for f in ("on_hand", "reserved", "available", "reorder_point")]
                if row["part_id"] in parts:
                    refs.append(_ref("parts", parts[row["part_id"]], "reorder_point"))
                emit("reorder_review", "mart_inventory", row, f"Revisar parte · {row['part_id']}",
                     "P1" if row["available"] <= 0 else "P2", "Responsable de partes",
                     f"Disponibles {row['available']} unidades; punto de reposición {row['reorder_point']}.",
                     "Conciliar conteo y reservas; revisar compras y consumo esperado antes de solicitar autorización de compra.",
                     refs, ["M-STOCK-AVAILABLE", "M-STOCK-REORDER"])

        if tables["maintenance"] is not None and tables["vehicles"] is not None:
            vehicles = {r["id"]: r for r in tables["vehicles"]}
            for row in tables["maintenance"]:
                vehicle = vehicles.get(row["vehicle_id"])
                if row["status"] not in {"due", "scheduled"} or vehicle is None:
                    continue
                by_date = bool(_at(row.get("due_at")) and _at(row["due_at"]) <= cutoff)
                by_km = bool(row.get("due_km") is not None and vehicle.get("odometer_km") is not None and vehicle["odometer_km"] >= row["due_km"])
                if not (by_date or by_km):
                    continue
                refs = [_ref("maintenance", row, f) for f in ("status", "due_at", "due_km", "vehicle_id")]
                refs.append(_ref("vehicles", vehicle, "odometer_km"))
                emit("maintenance_due", "maintenance", row, f"Revisar mantenimiento · {row['id']}", "P2", "Planificación flotillas",
                     "Venció la fecha" if by_date else "El odómetro alcanzó el kilometraje programado",
                     "Confirmar lectura actual, cobertura contractual y disponibilidad con el cliente antes de programar.",
                     refs, ["M-FLEET-MAINTENANCE"])

        if tables["mart_service_journey"] is not None and tables["work_orders"] is not None:
            orders = {r["id"]: r for r in tables["work_orders"]}
            contracts = {r["id"]: r for r in (tables["contracts"] or [])}
            for row in tables["mart_service_journey"]:
                if row["segment"] != "fleet" or row["status"] in {"delivered", "cancelled"} or row["sla_status"] not in {"at_risk", "breached"} or not row["contract_id"]:
                    continue
                order = orders.get(row["work_order_id"])
                contract = contracts.get(row["contract_id"])
                if order is None or contract is None:
                    continue
                refs = [_ref("mart_service_journey", row, f, key="work_order_id") for f in ("segment", "status", "sla_status", "contract_id", "age_hours")]
                refs.extend(_ref("work_orders", order, f) for f in ("status", "opened_at", "contract_id"))
                refs.extend(_ref("contracts", contract, f) for f in ("approval_ref", "sla_hours", "starts_at", "ends_at"))
                emit("fleet_sla_risk", "mart_service_journey", row, f"Revisar SLA flotilla · {row['work_order_id']}",
                     "P1", "Coordinación flotillas", f"Servicio abierto con estado SLA calculado: {row['sla_status']}.",
                     "Verificar términos y pausas contractuales con coordinación; registrar plan de recuperación y comunicación humana.",
                     refs, ["M-FLEET-SLA-ELIGIBILITY", "M-FLEET-SLA-RISK"])

        if tables["opportunities"] is not None:
            for row in tables["opportunities"]:
                if row["status"] in {"won", "lost"} or not _at(row.get("follow_up_at")) or _at(row["follow_up_at"]) > cutoff:
                    continue
                emit("opportunity_followup", "opportunities", row, f"Revisar oportunidad · {row['id']}", "P2", "Comercial flotillas",
                     "La oportunidad abierta tiene seguimiento programado para hoy o antes.",
                     "Consultar último contacto y siguiente paso declarado; asignar seguimiento humano y registrar respuesta.",
                     [_ref("opportunities", row, f) for f in ("status", "follow_up_at", "next_step")], ["M-FLEET-OPEN-OPPS"])

        if tables["tows"] is not None:
            for row in tables["tows"]:
                if row["status"] in {"closed", "cancelled"}:
                    continue
                refs = [_ref("tows", row, f) for f in ("status", "requested_at", "due_at", "safety_ref", "human_approval_ref")]
                if not row.get("safety_ref") or not row.get("human_approval_ref"):
                    emit("tow_refs_review", "tows", row, f"Revisar referencias de grúa · {row['id']}", "P1", "Coordinación grúas",
                         "Solicitud abierta sin ambas referencias humanas declaradas.",
                         "Confirmar seguridad y autorización con una persona; documentar referencias válidas antes de considerar despacho.",
                         refs, ["M-TOW-OPEN", "M-TOW-HUMAN-REFS"])
                if _at(row.get("due_at")) and _at(row["due_at"]) < cutoff:
                    emit("tow_late_review", "tows", row, f"Revisar demora de grúa · {row['id']}", "P1", "Coordinación grúas",
                         "La solicitud sigue abierta después de la fecha objetivo declarada.",
                         "Confirmar situación, seguridad y comunicación con una persona; revisar el compromiso documentado.",
                         refs, ["M-TOW-OPEN"])

        if tables["leads"] is not None:
            customers = {r["id"]: r for r in (tables["customers"] or [])}
            for row in tables["leads"]:
                if row["status"] in {"won", "lost"} or not _at(row.get("follow_up_at")) or _at(row["follow_up_at"]) > cutoff:
                    continue
                customer = customers.get(row["customer_id"])
                if customer is None or customer["segment"] != "particular":
                    continue
                emit("intake_followup", "leads", row, f"Revisar solicitud · {row['id']}", "P2", "Recepción",
                     "Solicitud abierta con seguimiento pendiente según la fecha declarada.",
                     "Consultar historial y autorización de contacto; asignar seguimiento humano y registrar el resultado.",
                     [_ref("leads", row, f) for f in ("status", "follow_up_at", "channel")]
                     + [_ref("customers", customer, "segment")], ["M-B2C-LEADS"])

        if tables["quotes"] is not None:
            for row in tables["quotes"]:
                if row["status"] not in {"sent", "draft"} or not _at(row.get("valid_until")) or _at(row["valid_until"]) >= cutoff:
                    continue
                emit("quote_expired", "quotes", row, f"Revisar cotización caducada · {row['id']}", "P2", "Recepción",
                     "La vigencia declarada pasó y la cotización no consta aceptada.",
                     "Verificar si existe una versión vigente y confirmar condiciones antes de nuevo contacto o precio.",
                     [_ref("quotes", row, f) for f in ("status", "valid_until", "authorization_ref")], ["M-FIN-QUOTES"])

        decisions.sort(key=lambda d: (d["priority"], d["category"], d["action_id"]))
        coverage = []
        for name, rows in tables.items():
            unknown_metrics = [mid for mid in CASE_METRICS.get(name, ())
                               if mid not in metric_by_id or metric_by_id[mid]["status"] != "measured"]
            status = "unknown_missing_source" if rows is None else "partial_unknown_metric" if unknown_metrics else "scanned"
            coverage.append({"table": name, "status": status,
                             "scanned_rows": None if rows is None else len(rows),
                             "triggered_cases": None if rows is None else triggered[name],
                             "complete_case_count": None if rows is None or unknown_metrics else triggered[name],
                             "unknown_metric_ids": unknown_metrics})
        if database_path is not None and _file_sha256(database_path) != source_hash:
            raise RuntimeError("Operating warehouse changed during case calculation")
        return {"schema_version": 1, "as_of": DEMO_NOW, "synthetic": True,
                "source_hash": source_hash, "source_hash_kind": source_hash_kind,
                "input_rows_sha256": input_rows_sha256,
                "decisions": decisions, "coverage": coverage,
                "policy": POLICY,
                "limitations": "Cobertura limitada al corte sintético disponible; fuentes ausentes son desconocidas, no cero. Casos pendientes de revisión humana."}
    finally:
        if owned:
            con.close()


__all__ = ["build_operating_cases", "POLICY"]
