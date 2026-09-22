"""Analytical record and cross-domain invariants; no operational commands."""
import re
from datetime import datetime, timezone

from .contracts import FIELDS, FLOWS, INITIAL, MANAGED, DEMO_NOW, BUSY_WORK, TERMINAL_WORK


class DomainError(ValueError):
    def __init__(self, message, code="validation", status=400):
        super().__init__(message)
        self.code, self.status = code, status


def require(condition, message, code="validation", status=400):
    if not condition:
        raise DomainError(message, code, status)


def date_value(value):
    require(isinstance(value, str), "Fecha inválida")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(result.tzinfo is not None, "La fecha requiere zona horaria")
        return result.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise DomainError("Fecha ISO-8601 inválida o sin zona horaria") from None


def validate_record(kind, rec):
    require(kind in FIELDS, "Tipo de registro desconocido")
    require(isinstance(rec, dict), "El registro debe ser un objeto")
    allowed = set(FIELDS[kind]) | {"id", "version", "synthetic", "created_at", "updated_at"}
    require(not (set(rec) - allowed), "Campos desconocidos: " + ", ".join(sorted(set(rec) - allowed)))
    require(isinstance(rec.get("id"), str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", rec["id"]), "ID inválido")
    require(rec.get("synthetic") is True, "Esta versión solo admite datos sintéticos")
    require(type(rec.get("version")) is int and rec["version"] > 0, "Versión inválida")
    for field in ("created_at", "updated_at"):
        date_value(rec.get(field))
    for field, typ in FIELDS[kind].items():
        value = rec.get(field)
        if value is None or value == "":
            require(typ.endswith("?"), f"Falta {field}")
            continue
        typ = typ.rstrip("?")
        if typ in {"str", "date", "state"} or typ.startswith(("ref:", "enum:")):
            require(isinstance(value, str) and 0 < len(value.strip()) <= 4000, f"Texto inválido: {field}")
        if typ == "date":
            date_value(value)
        elif typ in {"int", "money", "positive", "signed"}:
            require(type(value) is int and abs(value) <= 10**12, f"Entero inválido: {field}")
            if typ != "signed":
                require(value >= (1 if typ == "positive" else 0), f"Valor fuera de rango: {field}")
        elif typ == "bool":
            require(type(value) is bool, f"Booleano inválido: {field}")
        elif typ == "list":
            require(isinstance(value, list) and 0 < len(value) <= 100, f"Lista inválida: {field}")
        elif typ == "state":
            require(value in FLOWS[kind], f"Estado inválido: {value}")
        elif typ.startswith("enum:"):
            require(value in typ[5:].split(","), f"Opción inválida: {field}")


def stock_totals(data, part_id):
    moves = [r for r in data["stock_moves"] if r["part_id"] == part_id]
    on_hand = sum((-1 if r["move_type"] == "consume" else 1) * r["quantity"] for r in moves)
    reserved = sum(r["quantity"] for r in data["reservations"] if r["part_id"] == part_id and r["status"] == "reserved")
    return {"on_hand": on_hand, "reserved": reserved, "available": on_hand - reserved}


def paid_amount(data, invoice_id):
    return sum(r["amount_cents"] for r in data["payments"] if r["invoice_id"] == invoice_id)


def validate_dataset(data):
    require(isinstance(data, dict) and set(data) == set(FIELDS), "El conjunto de entidades está incompleto")
    for kind, records in data.items():
        require(isinstance(records, list), "Cada entidad debe ser una lista")
        for rec in records:
            validate_record(kind, rec)
    index = {kind: {r["id"]: r for r in records} for kind, records in data.items()}
    for kind, records in data.items():
        require(len(index[kind]) == len(records), "IDs duplicados")
        for rec in records:
            validate_record(kind, rec)
            for field, typ in FIELDS[kind].items():
                if typ.startswith("ref:") and rec.get(field):
                    require(rec[field] in index[typ[4:].rstrip("?")], f"Referencia inexistente: {kind}.{field}")
            if rec.get("customer_id") and rec.get("vehicle_id"):
                require(index["vehicles"][rec["vehicle_id"]]["customer_id"] == rec["customer_id"], "El vehículo no pertenece al cliente")
    for account in data["fleet_accounts"]:
        require(index["customers"][account["customer_id"]]["segment"] == "fleet", "La cuenta requiere cliente de flotilla")
    for contract in data["contracts"]:
        require(date_value(contract["starts_at"]) < date_value(contract["ends_at"]), "Vigencia de contrato inválida")
        if contract["status"] == "active":
            require(bool(contract.get("approval_ref")), "Contrato activo sin autorización")
    busy_bays, busy_techs = set(), set()
    assigned_quotes = set()
    for work in data["work_orders"]:
        require(date_value(work["opened_at"]) <= date_value(DEMO_NOW), "Recepción posterior al corte")
        if work.get("completed_at"):
            require(work["status"] == "delivered", "Fecha de entrega en orden no entregada")
            require(date_value(work["opened_at"]) <= date_value(work["completed_at"]) <= date_value(DEMO_NOW), "Duración de orden inválida")
        if work.get("quote_id"):
            quote = index["quotes"][work["quote_id"]]
            require((quote["customer_id"], quote["vehicle_id"]) == (work["customer_id"], work["vehicle_id"]), "Cotización de otro cliente o vehículo")
            if work["status"] != "cancelled":
                require(work["quote_id"] not in assigned_quotes, "Cotización vinculada a más de una orden")
                assigned_quotes.add(work["quote_id"])
        if work.get("contract_id"):
            contract = index["contracts"][work["contract_id"]]
            account = index["fleet_accounts"][contract["fleet_account_id"]]
            require(account["customer_id"] == work["customer_id"], "Contrato de otra flotilla")
        if work["status"] in BUSY_WORK:
            require(bool(work.get("bay_id")) and bool(work.get("technician_id")), "Orden activa sin bahía/técnico")
            require(work["bay_id"] not in busy_bays and work["technician_id"] not in busy_techs, "Bahía o técnico ocupado", "capacity", 409)
            busy_bays.add(work["bay_id"])
            busy_techs.add(work["technician_id"])
        if work["status"] not in {"received", "inspected", "cancelled"}:
            require(bool(work.get("authorization_ref")) and bool(work.get("quote_id")), "Orden sin autorización/cotización")
            require(index["quotes"][work["quote_id"]]["status"] == "accepted", "Cotización no aceptada")
        if work["status"] in {"ready", "delivered"}:
            require(bool(work.get("qc_ref")), "Falta control de calidad")
        if work["status"] == "delivered":
            require(bool(work.get("completed_at")), "Entrega sin fecha de cierre")
    for quote in data["quotes"]:
        if quote["status"] == "accepted":
            require(bool(quote.get("authorization_ref")), "Cotización aceptada sin evidencia")
    for part in data["parts"]:
        totals = stock_totals(data, part["id"])
        require(totals["on_hand"] >= 0 and totals["available"] >= 0, "Inventario insuficiente o sobrerreservado", "stock", 409)
    for move in data["stock_moves"]:
        require(move["quantity"] != 0, "Movimiento de cantidad cero")
        require(move["move_type"] == "adjust" or move["quantity"] > 0, "Cantidad inválida")
        if move["move_type"] == "receive":
            require(bool(move.get("purchase_id")), "Recepción sin compra")
            purchase = index["purchases"][move["purchase_id"]]
            require(purchase["part_id"] == move["part_id"], "Recepción de refacción distinta a la compra")
            require(purchase["status"] in {"ordered", "received"}, "Recepción contra compra no emitida")
            require(purchase["unit_cost_cents"] == move["unit_cost_cents"], "Costo de recepción no coincide con compra")
        else:
            require(not move.get("purchase_id"), "Solo recepción puede referir compra")
        if move["move_type"] in {"consume", "return"}:
            require(bool(move.get("work_order_id")), "Movimiento sin orden")
    stock_keys = {(m["part_id"], m.get("work_order_id")) for m in data["stock_moves"] if m["move_type"] in {"consume", "return"}}
    stock_keys |= {(r["part_id"], r["work_order_id"]) for r in data["reservations"] if r["status"] == "consumed"}
    for part_id, work_id in stock_keys:
        moves = [m for m in data["stock_moves"] if m["part_id"] == part_id and m.get("work_order_id") == work_id]
        consumed = sum(m["quantity"] for m in moves if m["move_type"] == "consume")
        returned = sum(m["quantity"] for m in moves if m["move_type"] == "return")
        reserved_consumed = sum(r["quantity"] for r in data["reservations"] if r["part_id"] == part_id and r["work_order_id"] == work_id and r["status"] == "consumed")
        require(returned <= consumed and consumed == reserved_consumed, "Consumo/reserva/devolución no reconcilian")
        net_cost = sum(m["quantity"] * m["unit_cost_cents"] * (1 if m["move_type"] == "consume" else -1 if m["move_type"] == "return" else 0) for m in moves)
        require(net_cost >= 0, "Costo devuelto excede costo consumido")
        for unit_cost in {m["unit_cost_cents"] for m in moves if m["move_type"] in {"consume", "return"}}:
            consumed_at_cost = sum(m["quantity"] for m in moves if m["move_type"] == "consume" and m["unit_cost_cents"] == unit_cost)
            returned_at_cost = sum(m["quantity"] for m in moves if m["move_type"] == "return" and m["unit_cost_cents"] == unit_cost)
            require(returned_at_cost <= consumed_at_cost, "Devolución sin consumo al mismo costo unitario")
    for reservation in data["reservations"]:
        if reservation["status"] == "reserved":
            require(index["work_orders"][reservation["work_order_id"]]["status"] not in TERMINAL_WORK, "Reserva activa en orden cerrada")
    for purchase in data["purchases"]:
        received = sum(m["quantity"] for m in data["stock_moves"] if m.get("purchase_id") == purchase["id"] and m["move_type"] == "receive")
        require(received <= purchase["quantity"], "Recepción excede compra")
        require(purchase["status"] != "received" or received == purchase["quantity"], "Compra recibida no reconciliada")
    for maintenance in data["maintenance"]:
        vehicle = index["vehicles"][maintenance["vehicle_id"]]
        contract = index["contracts"][maintenance["contract_id"]]
        require(index["fleet_accounts"][contract["fleet_account_id"]]["customer_id"] == vehicle["customer_id"], "Mantenimiento de otra flotilla")
        if maintenance.get("work_order_id"):
            work = index["work_orders"][maintenance["work_order_id"]]
            require(work["vehicle_id"] == vehicle["id"] and work.get("contract_id") == contract["id"], "Orden de mantenimiento incompatible")
    busy_units = set()
    for tow in data["tows"]:
        require(date_value(tow["requested_at"]) <= date_value(DEMO_NOW), "Solicitud de grúa posterior al corte")
        if tow.get("closed_at"):
            require(tow["status"] == "closed", "Fecha de cierre en grúa abierta/cancelada")
            require(date_value(tow["requested_at"]) <= date_value(tow["closed_at"]) <= date_value(DEMO_NOW), "Duración de grúa inválida")
        if tow["status"] == "closed":
            require(bool(tow.get("closed_at")), "Grúa cerrada sin fecha de cierre")
        if tow["status"] in {"assigned", "accepted", "en_route", "arrived", "transporting", "closed"}:
            require(all(tow.get(x) for x in ("unit_id", "safety_ref", "human_approval_ref")) and tow.get("amount_cents") is not None, "Grúa sin autorización humana completa")
        if tow["status"] in {"assigned", "accepted", "en_route", "arrived", "transporting"}:
            require(tow["unit_id"] not in busy_units, "Unidad de grúa ocupada", "capacity", 409)
            busy_units.add(tow["unit_id"])
    invoice_sources = set()
    for inv in data["invoices"]:
        require(bool(inv.get("work_order_id")) != bool(inv.get("tow_id")), "Factura requiere exactamente un servicio")
        source_kind = "work_orders" if inv.get("work_order_id") else "tows"
        source_id = inv.get("work_order_id") or inv["tow_id"]
        source = index[source_kind][source_id]
        require(source["customer_id"] == inv["customer_id"], "Factura de otro cliente")
        if inv["status"] == "issued":
            require(source["status"] in {"delivered", "closed"}, "No se puede facturar servicio pendiente")
            expected = index["quotes"][source["quote_id"]]["amount_cents"] if source_kind == "work_orders" else source["amount_cents"]
            require(inv["amount_cents"] == expected, "Factura no coincide con importe autorizado")
            key = (source_kind, source_id)
            require(key not in invoice_sources, "Servicio ya facturado")
            invoice_sources.add(key)
        paid = paid_amount(data, inv["id"])
        require(0 <= paid <= inv["amount_cents"], "Pago excede saldo")
        require(paid == 0 or inv["status"] == "issued", "Pago aplicado a factura no emitida")
    payment_refs = [p["reference"] for p in data["payments"]]
    require(len(payment_refs) == len(set(payment_refs)), "Referencia de pago duplicada")
    for payment in data["payments"] + data["expenses"]:
        require(date_value(payment["paid_at"]) <= date_value(DEMO_NOW), "Movimiento de dinero posterior al corte")
    for proposal in data["proposals"]:
        from .reports import AGENTS
        from .storage import canonical
        require(proposal["agent"] in AGENTS, "Agente fuente desconocido")
        require(proposal["approval_required"] is True and proposal["external_execution"] is False, "Contrato de agente inválido")
        for evidence in proposal["evidence"]:
            require(isinstance(evidence, dict) and evidence.get("entity_id") in index.get(evidence.get("entity_type"), {}), "Evidencia inexistente")
            require(set(evidence) == {"entity_type", "entity_id", "field", "value", "version"} and type(evidence["version"]) is int, "Evidencia fuente incompleta")
            referenced = index[evidence["entity_type"]][evidence["entity_id"]]
            require(evidence["field"] in referenced and canonical(referenced[evidence["field"]]) == canonical(evidence["value"]) and evidence["version"] == referenced["version"], "Evidencia fuente desactualizada o inventada")

