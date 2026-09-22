"""Deterministic, synthetic demonstration data for Taller Milenio.

The fixture intentionally contains both healthy and exception paths.  It is
safe to reset and regenerate because every identifier and timestamp is stable.
"""
from __future__ import annotations

from copy import deepcopy

from .contracts import DEMO_NOW, FIELDS, SCHEMA_VERSION


def _record(kind: str, ident: str, **values):
    row = {"id": ident, "version": 1, "synthetic": True,
           "created_at": DEMO_NOW, "updated_at": DEMO_NOW}
    row.update(values)
    # Keep every contract field present, with None for optional values.
    for field, spec in FIELDS[kind].items():
        row.setdefault(field, None if spec.endswith("?") else "")
    return row


def make_fixture(seed: int = 42) -> dict[str, list[dict]]:
    """Return a reproducible synthetic operation (``seed`` is API-compatible).

    The seed is deliberately not used for randomness: stable IDs and values
    make demo screenshots and regression tests comparable across runs.
    """
    if not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    d: dict[str, list[dict]] = {k: [] for k in FIELDS}
    add = lambda kind, ident, **kw: d[kind].append(_record(kind, ident, **kw))

    customers = [
        ("C-001", "Ana López", "particular", True), ("C-002", "Bruno Ruiz", "particular", True),
        ("C-003", "Carla Méndez", "particular", False), ("C-004", "Diego Soto", "particular", True),
        ("C-005", "Elena Vega", "particular", True), ("C-006", "Fabián Cruz", "particular", True),
        ("C-007", "Graciela Mora", "particular", True), ("C-008", "Héctor Luna", "particular", True),
        ("C-009", "Logística Norte SA", "fleet", True), ("C-010", "Servicios Delta", "fleet", True),
    ]
    for ident, name, segment, consent in customers:
        add("customers", ident, name="Demo " + name, segment=segment, consent=consent,
            contact=None if ident == "C-003" else f"{ident.lower()}@demo.milenio.local")
    for i, cid in enumerate(["C-001", "C-002", "C-003", "C-004", "C-005", "C-006", "C-007", "C-008", "C-009", "C-009", "C-010", "C-010"], 1):
        add("vehicles", f"V-{i:03d}", customer_id=cid, label=f"Demo unidad {i:02d}",
            plate=f"DEMO-{i:03d}", odometer_km=18000 + i * 430)
    for i, (cid, vid, status) in enumerate([
        ("C-001", "V-001", "new"), ("C-002", "V-002", "qualified"),
        ("C-003", "V-003", "quoted"), ("C-004", "V-004", "lost"),
        ("C-009", "V-009", "won"), ("C-010", "V-011", "new")], 1):
        add("leads", f"L-{i:03d}", customer_id=cid, vehicle_id=vid, need="Servicio demo", channel="web", follow_up_at="2026-09-20T17:00:00Z" if i == 1 else "2026-09-25T17:00:00Z", status=status)
    for i in range(1, 5):
        add("technicians", f"T-{i:03d}", name="Demo " + ["María", "Joel", "Nora", "Pablo"][i-1], specialty=["diagnóstico", "frenos", "eléctrico", "carrocería"][i-1])
    for i in range(1, 5):
        add("bays", f"B-{i:03d}", name=f"Bahía {i}")
    for i, (cid, vid, amount, status, auth) in enumerate([
        ("C-001", "V-001", 185000, "accepted", "AUTH-C001"), ("C-002", "V-002", 92000, "accepted", "AUTH-C002"),
        ("C-003", "V-003", 47500, "accepted", "AUTH-C003"), ("C-004", "V-004", 210000, "accepted", "AUTH-C004"),
        ("C-009", "V-009", 300000, "accepted", "AUTH-FLEET-01"), ("C-006", "V-006", 125000, "accepted", "AUTH-C006"),
        ("C-008", "V-008", 110000, "accepted", "AUTH-C008"), ("C-010", "V-011", 99000, "accepted", "AUTH-C010"),
        ("C-005", "V-005", 65000, "sent", None), ("C-007", "V-007", 72000, "sent", None)], 1):
        add("quotes", f"Q-{i:03d}", customer_id=cid, vehicle_id=vid, description="Mantenimiento preventivo demo", amount_cents=amount, valid_until="2026-09-20T00:00:00Z" if i == 10 else "2026-10-15T00:00:00Z", authorization_ref=auth, status=status)
    for i, (cid, vid, status) in enumerate([("C-001", "V-001", "arrived"), ("C-002", "V-002", "pending"), ("C-009", "V-009", "cancelled")], 1):
        add("appointments", f"A-{i:03d}", customer_id=cid, vehicle_id=vid, starts_at="2026-09-22T16:00:00Z", reason="Servicio demo", status=status)
    for i, (cid, vid, qid, tid, bid, status, done) in enumerate([
        ("C-001", "V-001", "Q-001", "T-001", "B-001", "delivered", "2026-09-20T20:00:00Z"),
        ("C-002", "V-002", "Q-002", "T-002", "B-002", "in_service", None), ("C-003", "V-003", "Q-003", None, None, "waiting_parts", None),
        ("C-004", "V-004", "Q-004", "T-003", "B-003", "rework", None), ("C-005", "V-005", None, None, None, "cancelled", None),
        ("C-006", "V-006", "Q-006", "T-004", "B-001", "quality_check", None), ("C-007", "V-007", None, None, None, "received", None),
        ("C-008", "V-008", "Q-007", None, None, "authorized", None), ("C-009", "V-009", "Q-005", "T-001", "B-002", "delivered", "2026-09-21T17:00:00Z"),
        ("C-010", "V-011", "Q-008", "T-001", "B-004", "scheduled", None)], 1):
        add("work_orders", f"WO-{i:03d}", customer_id=cid, vehicle_id=vid, quote_id=qid, contract_id="CT-001" if cid == "C-009" else None, technician_id=tid, bay_id=bid, description="Orden sintética", due_at="2026-09-23T20:00:00Z", opened_at="2026-09-18T16:00:00Z", completed_at=done, inspection="Inspección demo" if status not in ("received", "cancelled") else None, authorization_ref="AUTH-WO" if status in ("authorized", "scheduled", "in_service", "quality_check", "waiting_parts", "rework", "ready", "delivered") else None, qc_ref="QC-001" if status == "delivered" else None, block_reason="Falta filtro" if status == "waiting_parts" else None, status=status)
    for i in range(1, 4):
        add("suppliers", f"S-{i:03d}", name="Demo " + ["Refacciones Centro", "Motores del Pacífico", "Partes Ruta 1"][i-1], contact=f"proveedor{i}@demo.local")
    for i, sid in enumerate(["S-001", "S-001", "S-002", "S-003", "S-002", "S-003"], 1):
        add("parts", f"P-{i:03d}", sku=f"SKU-{i:03d}", name=f"Refacción demo {i}", supplier_id=sid, unit_cost_cents=1200 + i * 350, reorder_point=2)
    for i, (pid, status) in enumerate([("P-001", "received"), ("P-002", "ordered"), ("P-003", "cancelled")], 1):
        add("purchases", f"PO-{i:03d}", part_id=pid, quantity=8, unit_cost_cents=1800, expected_at="2026-09-24T18:00:00Z", status=status)
    moves = [("SM-001", "P-001", "receive", 8, "PO-001", None), ("SM-002", "P-001", "consume", 2, None, "WO-001"), ("SM-003", "P-001", "return", 1, None, "WO-001"), ("SM-004", "P-002", "receive", 5, "PO-002", None), ("SM-005", "P-003", "adjust", 1, None, None)]
    for ident, pid, typ, qty, po, wo in moves:
        add("stock_moves", ident, part_id=pid, work_order_id=wo, purchase_id=po, move_type=typ, quantity=qty, unit_cost_cents=1800, reason="Recepción/consumo demo")
    for i, (pid, wo, qty, status) in enumerate([("P-001", "WO-001", 2, "consumed"), ("P-002", "WO-002", 1, "reserved"), ("P-003", "WO-003", 1, "released")], 1):
        add("reservations", f"RS-{i:03d}", part_id=pid, work_order_id=wo, quantity=qty, status=status)
    add("fleet_accounts", "FA-001", customer_id="C-009", industry="logística", fleet_size=12, owner="Laura Campos")
    add("fleet_accounts", "FA-002", customer_id="C-010", industry="servicios", fleet_size=8, owner="Mario León")
    for i, fa in enumerate(["FA-001", "FA-001", "FA-002"], 1):
        add("contacts", f"CTC-{i:03d}", fleet_account_id=fa, name=f"Contacto {i}", role="Operaciones", contact=f"contacto{i}@demo.local", consent=True)
    add("opportunities", "OP-001", fleet_account_id="FA-001", title="Mantenimiento anual", value_cents=1250000, next_step="Enviar propuesta", follow_up_at="2026-09-26T18:00:00Z", status="proposal")
    add("opportunities", "OP-002", fleet_account_id="FA-002", title="Servicio de flotilla", value_cents=780000, next_step="Calificar", follow_up_at="2026-09-28T18:00:00Z", status="qualified")
    add("contracts", "CT-001", fleet_account_id="FA-001", name="SLA demo Norte", sla_hours=48, starts_at="2026-01-01T00:00:00Z", ends_at="2026-12-31T23:59:59Z", approval_ref="APP-CT-001", status="active")
    add("contracts", "CT-002", fleet_account_id="FA-002", name="Contrato vencido demo", sla_hours=72, starts_at="2025-01-01T00:00:00Z", ends_at="2025-12-31T23:59:59Z", approval_ref="APP-CT-002", status="expired")
    for i, (vid, ct, status) in enumerate([("V-009", "CT-001", "scheduled"), ("V-010", "CT-001", "due"), ("V-011", "CT-002", "due")], 1):
        add("maintenance", f"M-{i:03d}", vehicle_id=vid, contract_id=ct, service="Revisión 10,000 km", due_at="2026-09-25T18:00:00Z" if i == 1 else "2026-09-30T18:00:00Z", due_km=30000, work_order_id=None, status=status)
    for i, cap in enumerate(["plataforma", "arrastre", "plataforma", "rescate"], 1):
        add("tow_units", f"TU-{i:03d}", name=f"Grúa demo {i}", capability=cap)
    for i, vals in enumerate([
        ("C-006", "V-006", "closed", "TU-001", "2026-09-20T21:00:00Z", 85000), ("C-007", "V-007", "en_route", "TU-002", None, 65000),
        ("C-008", "V-008", "requested", None, None, None), ("C-002", "V-002", "cancelled", None, None, 65000), ("C-009", "V-009", "closed", "TU-003", "2026-09-18T23:00:00Z", 125000)], 1):
        status = vals[2]
        add("tows", f"TW-{i:03d}", customer_id=vals[0], vehicle_id=vals[1], pickup="Av. Demo 100", destination="Taller Milenio", conditions="Tráfico normal", requested_at="2026-09-18T18:00:00Z" if i == 5 else "2026-09-20T18:00:00Z", due_at="2026-09-20T22:00:00Z", closed_at=vals[4], amount_cents=vals[5], unit_id=vals[3], safety_ref="SAFE-HUMAN-001" if status in ("closed", "en_route") else None, human_approval_ref="HUMAN-APP-001" if status in ("closed", "en_route") else None, status=status)
    for i, (cid, wo, tw, amount, status) in enumerate([("C-001", "WO-001", None, 185000, "issued"), ("C-009", "WO-009", None, 300000, "issued"), ("C-006", None, "TW-001", 85000, "issued"), ("C-009", None, "TW-005", 125000, "issued")], 1):
        add("invoices", f"INV-{i:03d}", customer_id=cid, work_order_id=wo, tow_id=tw, amount_cents=amount, due_at="2026-09-20T00:00:00Z" if i == 1 else "2026-10-01T00:00:00Z", status=status)
    add("payments", "PAY-001", invoice_id="INV-001", amount_cents=100000, method="transfer", reference="DEMO-TRANSFER-001", paid_at="2026-09-21T15:00:00Z")
    add("payments", "PAY-002", invoice_id="INV-003", amount_cents=85000, method="card", reference="DEMO-CARD-002", paid_at="2026-09-20T22:00:00Z")
    add("expenses", "EXP-001", description="Compra de consumibles demo", amount_cents=24000, category="parts", method="transfer", paid_at="2026-09-18T18:00:00Z")
    add("expenses", "EXP-002", description="Servicios del local demo", amount_cents=18000, category="utilities", method="cash", paid_at="2026-09-15T18:00:00Z")
    add("campaigns", "CAM-001", name="Recordatorio mantenimiento", audience="particular", objective="Recurrencia", draft="Borrador sintético", status="review")
    add("campaigns", "CAM-002", name="Flotillas septiembre", audience="fleet", objective="Pipeline B2B", draft="Borrador sintético", status="approved")
    add("proposals", "PR-001", agent="operations_controller", title="Revisar pieza faltante", rationale="Orden esperando pieza", evidence=[{"entity_type": "work_orders", "entity_id": "WO-003", "field": "status", "value": "waiting_parts", "version": 1}], approval_required=True, external_execution=False, status="pending", decision_note=None)
    add("proposals", "PR-002", agent="fleet_sla_watcher", title="Revisar mantenimiento vencido", rationale="Mantenimiento en estado due", evidence=[{"entity_type": "maintenance", "entity_id": "M-002", "field": "status", "value": "due", "version": 1}], approval_required=True, external_execution=False, status="pending", decision_note=None)
    return deepcopy(d)


__all__ = ["make_fixture", "DEMO_NOW", "SCHEMA_VERSION"]
