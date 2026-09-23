"""Inspectable, source-owned dictionary for the synthetic relational studio."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .contracts import FIELDS


DERIVED_KEYS = {
    "mart_service_journey": ("work_order_id",),
    "mart_receivables": ("invoice_id",),
    "mart_daily_operations": ("day",),
    "mart_fleet_scorecard": ("fleet_account_id",),
    "mart_inventory": ("part_id",),
    "mart_process_waits": ("entity_type", "stage"),
}
AUXILIARY_KEYS = {"lifecycle_events": ("event_id",), "journey_links": ("id",)}
SOURCE_NAMES = tuple(FIELDS) + tuple(AUXILIARY_KEYS)
DERIVED_NAMES = tuple(DERIVED_KEYS)
ALLOWED_NAMES = SOURCE_NAMES + DERIVED_NAMES

TABLE_INFO = {
    "customers": ("Clientes", "Un cliente", "Recepción"),
    "vehicles": ("Vehículos", "Un vehículo", "Recepción"),
    "leads": ("Solicitudes particulares", "Un lead", "Recepción"),
    "quotes": ("Cotizaciones", "Una cotización", "Recepción"),
    "appointments": ("Citas", "Una cita", "Recepción"),
    "technicians": ("Técnicos", "Un técnico", "Jefatura de taller"),
    "bays": ("Bahías", "Una bahía", "Jefatura de taller"),
    "work_orders": ("Órdenes de trabajo", "Una orden de trabajo", "Jefatura de taller"),
    "suppliers": ("Proveedores", "Un proveedor", "Responsable de partes"),
    "parts": ("Partes", "Una parte o SKU", "Responsable de partes"),
    "purchases": ("Compras", "Una orden de compra", "Responsable de partes"),
    "stock_moves": ("Movimientos de stock", "Un movimiento de inventario", "Responsable de partes"),
    "reservations": ("Reservas", "Una reserva de parte para orden", "Responsable de partes"),
    "fleet_accounts": ("Cuentas de flotilla", "Una cuenta de flotilla", "Comercial flotillas"),
    "contacts": ("Contactos de flotilla", "Un contacto", "Comercial flotillas"),
    "opportunities": ("Oportunidades", "Una oportunidad comercial", "Comercial flotillas"),
    "contracts": ("Contratos", "Un contrato", "Comercial flotillas"),
    "maintenance": ("Mantenimientos", "Un mantenimiento programado", "Planificación flotillas"),
    "tow_units": ("Unidades de grúa", "Una unidad de grúa", "Coordinación grúas"),
    "tows": ("Servicios de grúa", "Una solicitud de grúa", "Coordinación grúas"),
    "invoices": ("Facturas", "Una factura", "Administración"),
    "payments": ("Pagos", "Un pago vinculado a factura", "Administración"),
    "expenses": ("Gastos", "Un gasto registrado", "Administración"),
    "campaigns": ("Campañas", "Una campaña en revisión", "Marketing"),
    "proposals": ("Propuestas", "Una propuesta para revisión humana", "Gerencia"),
    "lifecycle_events": ("Eventos de estado", "Un cambio de estado de entidad", "Analista"),
    "journey_links": ("Vínculos de recorrido", "Un vínculo explícito lead-cotización-cita-orden", "Analista"),
    "mart_service_journey": ("Recorrido de servicio", "Una orden de trabajo", "Jefatura de taller"),
    "mart_receivables": ("Cartera por factura", "Una factura emitida", "Administración"),
    "mart_daily_operations": ("Operación diaria", "Un día UTC observado", "Analista"),
    "mart_fleet_scorecard": ("Resultado por flotilla", "Una cuenta de flotilla", "Comercial flotillas"),
    "mart_inventory": ("Inventario reconciliado", "Una parte", "Responsable de partes"),
    "mart_process_waits": ("Tiempos por estado", "Una pareja tipo de entidad y estado", "Analista"),
}

SPECIAL_FIELDS = {
    "id": "Identificador estable del registro dentro de esta entidad.",
    "event_id": "Identificador único del evento de estado.",
    "version": "Versión de fila usada para comprobar la evidencia.",
    "synthetic": "Marca que el registro pertenece al escenario ficticio.",
    "created_at": "Fecha de creación registrada en el fixture; no prueba creación operativa real.",
    "updated_at": "Última fecha registrada en el fixture; no demuestra historial completo.",
    "status": "Estado observado en el corte; no permite inferir transiciones pasadas.",
    "entity_type": "Tipo de entidad al que pertenece el evento o intervalo.",
    "entity_id": "Identificador de la entidad al que pertenece el evento.",
    "from_state": "Estado anterior declarado en el evento validado.",
    "to_state": "Estado siguiente declarado en el evento validado.",
    "stage": "Estado cuyo intervalo se calculó entre eventos consecutivos.",
    "at": "Instante del evento con zona horaria.",
    "actor": "Actor declarado en el evento sintético; no acredita identidad real.",
    "process_id": "Identificador del caso declarado por la fuente de eventos.",
    "lead_id": "Lead de un recorrido enlazado explícitamente.",
    "quote_id": "Cotización enlazada explícitamente; una coincidencia de cliente no basta.",
    "appointment_id": "Cita enlazada explícitamente al recorrido.",
    "work_order_id": "Orden de trabajo referenciada.",
    "invoice_id": "Factura referenciada para reconciliar pagos o saldos.",
    "customer_id": "Cliente referenciado por identificador, sin atribución causal implícita.",
    "vehicle_id": "Vehículo referenciado por identificador.",
    "fleet_account_id": "Cuenta de flotilla referenciada.",
    "part_id": "Parte o SKU referenciado.",
    "purchase_id": "Compra referenciada; una compra ordenada no aumenta existencia.",
    "bay_id": "Bahía asignada al corte; no mide horas de utilización.",
    "technician_id": "Técnico asignado al corte; no mide horas trabajadas.",
    "contract_id": "Contrato referenciado; elegibilidad SLA requiere más evidencia.",
    "tow_id": "Solicitud de grúa referenciada.",
    "unit_id": "Unidad de grúa referenciada; no autoriza despacho.",
    "supplier_id": "Proveedor referenciado.",
    "due_at": "Vencimiento o compromiso declarado con zona horaria; significado depende de tabla.",
    "opened_at": "Inicio declarado de la orden con zona horaria.",
    "completed_at": "Cierre declarado de la orden; ciclo medido exige eventos validados.",
    "requested_at": "Inicio declarado de solicitud de grúa con zona horaria.",
    "closed_at": "Cierre declarado; no equivale a llegada o respuesta.",
    "paid_at": "Fecha del pago o gasto con zona horaria.",
    "starts_at": "Inicio de vigencia o cita con zona horaria.",
    "ends_at": "Fin de vigencia con zona horaria.",
    "follow_up_at": "Fecha de seguimiento propuesta, sin mensaje ejecutado.",
    "expected_at": "Fecha esperada; no acredita recepción de partes.",
    "valid_until": "Vigencia declarada de la cotización.",
    "amount_cents": "Importe en centavos MXN; consultar el estado antes de agregar.",
    "value_cents": "Valor comercial hipotético en centavos MXN; no es ingreso.",
    "unit_cost_cents": "Costo unitario en centavos MXN.",
    "pipeline_cents": "Valor declarado de oportunidades abiertas en centavos MXN.",
    "invoiced_cents": "Importe de facturas emitidas en centavos MXN.",
    "paid_cents": "Pagos registrados en centavos MXN; no es ingreso reconocido.",
    "balance_cents": "Factura emitida menos pagos vinculados en centavos MXN.",
    "receivable_cents": "Saldo de facturas emitidas en centavos MXN.",
    "collected_cents": "Pagos registrados en el día en centavos MXN.",
    "expense_cents": "Gastos registrados en el día en centavos MXN.",
    "quantity": "Cantidad de unidades; el signo y efecto dependen del tipo de movimiento.",
    "move_type": "Clase de movimiento que determina el efecto sobre existencia.",
    "on_hand": "Existencia calculada a partir de movimientos registrados.",
    "reserved": "Unidades en reservas activas; todavía no son consumo.",
    "available": "Existencia menos reservas activas.",
    "reorder_point": "Umbral declarado de revisión; no es instrucción de compra.",
    "sla_hours": "Horas SLA declaradas en contrato sintético; no son términos validados.",
    "sla_status": "Clasificación calculada sólo con evidencia contractual suficiente.",
    "cycle_hours": "Horas calendario observadas en entregas con historial validado.",
    "age_hours": "Edad calendario al corte de orden todavía abierta.",
    "waiting_parts_hours": "Horas observadas en espera de partes entre eventos consecutivos.",
    "in_service_hours": "Horas de estado en servicio; no equivalen a mano de obra pagada.",
    "total_hours": "Horas acumuladas de intervalos observados para la pareja entidad-estado.",
    "mean_interval_hours": "Promedio de horas por intervalo observado.",
    "intervals": "Número de intervalos con evento de entrada y siguiente evento.",
    "cases": "Número de casos distintos que aportaron intervalos.",
    "approval_ref": "Referencia humana declarada; presencia no demuestra autenticidad.",
    "human_approval_ref": "Referencia humana declarada; no autoriza despacho por sí sola.",
    "safety_ref": "Referencia de revisión de seguridad; presencia no certifica seguridad.",
    "authorization_ref": "Referencia de autorización declarada; requiere revisión humana.",
    "qc_ref": "Referencia de control de calidad declarada.",
    "evidence": "Lista estructurada de evidencia de la propuesta.",
    "approval_required": "Bandera que exige aprobación humana antes de cualquier acción.",
    "external_execution": "Bandera de ejecución externa; las propuestas del toolkit deben ser no ejecutables.",
    "decision_note": "Nota de revisión humana declarada, no resultado observado automáticamente.",
}

TABLE_LIMITS = {
    "lifecycle_events": "Historia ficticia sólo para entidades con eventos provistos y validados; no se infiere desde status.",
    "journey_links": "Vínculos explícitos ficticios; sin filas, la atribución es desconocida.",
    "mart_service_journey": "Ciclo entregado desconocido sin historia validada; edad abierta es otra medida.",
    "mart_process_waits": "Sólo intervalos cerrados por un evento siguiente; no equivale a horas de mano de obra.",
    "mart_inventory": "Compras ordenadas no suman existencia hasta recepción registrada.",
    "mart_receivables": "Saldo requiere todos los pagos vinculados al corte y sólo facturas emitidas.",
    "mart_fleet_scorecard": "SLA sintético; contrato y referencias humanas no están validados por el dueño real.",
    "proposals": "Borradores para revisión; ninguna fila prueba acción ejecutada.",
    "tows": "Referencias humanas presentes no constituyen decisión de seguridad o despacho.",
}


def _field_description(name: str, *, table: str) -> str:
    if name in SPECIAL_FIELDS:
        return SPECIAL_FIELDS[name]
    if name.endswith("_cents"):
        return "Importe en centavos MXN; confirme población y estado antes de sumar."
    if name.endswith("_at"):
        return "Fecha y hora declaradas por la fuente con zona horaria."
    if name.endswith("_id"):
        return "Referencia por identificador a un registro relacionado."
    if name.endswith("_ref"):
        return "Referencia humana declarada; presencia no valida su contenido."
    if name.endswith("_hours"):
        return "Horas calendario calculadas o declaradas; consulte el grain de la tabla."
    if name in {"contact", "plate", "pickup", "destination", "conditions"}:
        return "Texto sintético de ejemplo; dato potencialmente sensible en un piloto real."
    if name in {"consent", "name", "description", "segment", "category", "method", "reason", "owner", "title", "industry", "service", "specialty", "capability", "audience", "objective", "draft", "rationale", "next_step", "inspection", "block_reason", "sku", "label", "role"}:
        return "Atributo declarado en la fuente sintética; no verificado con el negocio."
    return f"Campo «{name}» de {table}; interpretación sujeta al contrato de origen."


def _relationships(con: sqlite3.Connection, name: str) -> list[dict]:
    # PRAGMA returns actual enforced foreign keys, not inferred joins.
    groups: dict[int, dict] = {}
    for row in con.execute(f'PRAGMA foreign_key_list("{name}")'):
        foreign_id, position, target, source_field, target_field, *_ = row
        group = groups.setdefault(foreign_id, {"target_table": target, "from_fields": [], "to_fields": [], "enforced": True})
        group["from_fields"].append((position, source_field))
        group["to_fields"].append((position, target_field))
    return [{"target_table": group["target_table"],
             "from_fields": [field for _, field in sorted(group["from_fields"])],
             "to_fields": [field for _, field in sorted(group["to_fields"])],
             "enforced": True} for _, group in sorted(groups.items())]


def build_source_catalog(database: str | Path | sqlite3.Connection, metric_registry: dict) -> dict:
    """Read 27 sources and six marts, including complete stable ordered rows.

    Input names are a fixed allowlist; SQLite is opened read-only for path calls.
    A caller-provided connection is preserved. This function never writes.
    """
    if not isinstance(metric_registry, dict) or not isinstance(metric_registry.get("metrics"), list):
        raise ValueError("A measured metric registry is required")
    owned = not isinstance(database, sqlite3.Connection)
    con = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True) if owned else database
    try:
        actual = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        missing = set(ALLOWED_NAMES) - actual
        if missing:
            raise ValueError("Required source or mart tables missing: " + ", ".join(sorted(missing)))
        tables = []
        for name in ALLOWED_NAMES:
            columns = list(con.execute(f'PRAGMA table_info("{name}")'))
            column_names = [column[1] for column in columns]
            key = AUXILIARY_KEYS.get(name, DERIVED_KEYS.get(name, ("id",)))
            if not set(key).issubset(column_names):
                raise ValueError(f"Declared logical key not present in {name}")
            query = f'SELECT * FROM "{name}" ORDER BY ' + ",".join('"' + field + '"' for field in key)
            rows = [dict(zip(column_names, record)) for record in con.execute(query)]
            if name in SOURCE_NAMES and any(record.get("synthetic") != 1 for record in rows):
                raise ValueError(f"Non-synthetic row in synthetic source table {name}")
            physical_pk = [column[1] for column in sorted(columns, key=lambda c: c[5]) if column[5] > 0]
            label, grain, proposed_owner = TABLE_INFO[name]
            fields = [{"name": column[1], "type": column[2], "nullable": not bool(column[3]) and column[5] == 0,
                       "description": _field_description(column[1], table=name),
                       "null_count": sum(row[column[1]] is None for row in rows)} for column in columns]
            matching = sorted({metric["metric_id"] for metric in metric_registry["metrics"]
                               if name in metric.get("source_tables", []) or
                               isinstance(metric.get("query"), str) and re.search(r"\b" + re.escape(name) + r"\b", metric["query"], re.I)})
            tables.append({
                "name": name, "label": label, "kind": "physical_source" if name in SOURCE_NAMES else "derived_mart",
                "grain": grain, "logical_key": list(key), "primary_key": physical_pk,
                "owner_role": proposed_owner, "owner_status": "proposed_unvalidated",
                "source_status": "synthetic_example" if name in SOURCE_NAMES else "derived_from_synthetic",
                "source_authority": "milenio.contracts.FIELDS" if name in FIELDS else "milenio.warehouse" if name in AUXILIARY_KEYS else "milenio.studio_analytics",
                "source_file": f"tables/{name}.csv", "relationships": _relationships(con, name),
                "fields": fields, "row_count": len(rows), "rows": rows, "metric_ids": matching,
                "limitations": TABLE_LIMITS.get(name, "Escenario sintético; grain, cobertura y responsable reales aún requieren validación."),
            })
        return {"schema_version": 1, "source_status": "synthetic_example", "physical_source_tables": len(SOURCE_NAMES),
                "derived_marts": len(DERIVED_NAMES), "tables": tables,
                "limitations": "Las filas son ficticias. Los roles son propuestos; no se ha validado el proceso, dueño de fuente ni impacto del Taller Milenio."}
    finally:
        if owned:
            con.close()


__all__ = ["build_source_catalog"]
