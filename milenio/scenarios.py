"""Longitudinal synthetic operating scenarios for warehouse demonstrations."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from .contracts import DEMO_NOW
from .fixtures import make_fixture
from .domain import validate_dataset


def _iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def make_operating_scenario(days=90, seed=42):
    if days < 30 or days > 365:
        raise ValueError("days must be between 30 and 365")
    data = deepcopy(make_fixture(seed))
    now = datetime.fromisoformat(DEMO_NOW.replace("Z", "+00:00"))
    events = []
    journeys = []
    for i in range(1, 161):
        vehicle = data["vehicles"][(i - 1) % len(data["vehicles"])]
        customer_id, vehicle_id = vehicle["customer_id"], vehicle["id"]
        opened = now - timedelta(hours=12 + ((i * 13) % (days * 24 - 36)))
        duration = timedelta(hours=(54 + i % 12) if i % 9 == 0 else 6 + (i % 7) * 2)
        completed = opened + duration
        if completed >= now:
            completed = now - timedelta(hours=1)
            opened = completed - duration
        qid, wid, iid = f"Q-H{i:03d}", f"WO-H{i:03d}", f"INV-H{i:03d}"
        lid, aid = f"L-H{i:03d}", f"A-H{i:03d}"
        data["leads"].append({"id": lid, "version": 1, "synthetic": True, "created_at": DEMO_NOW, "updated_at": DEMO_NOW, "customer_id": customer_id, "vehicle_id": vehicle_id, "need": "Servicio histórico sintético", "channel": "referral", "follow_up_at": _iso(opened), "status": "won"})
        data["appointments"].append({"id": aid, "version": 1, "synthetic": True, "created_at": DEMO_NOW, "updated_at": DEMO_NOW, "customer_id": customer_id, "vehicle_id": vehicle_id, "starts_at": _iso(opened), "reason": "Servicio histórico sintético", "status": "arrived"})
        journeys.append({"id": f"J-H{i:03d}", "lead_id": lid, "quote_id": qid, "appointment_id": aid, "work_order_id": wid})
        amount = 65000 + (i % 11) * 12500
        data["quotes"].append({"id": qid, "version": 1, "synthetic": True, "created_at": DEMO_NOW, "updated_at": DEMO_NOW, "customer_id": customer_id, "vehicle_id": vehicle_id, "description": "Servicio histórico sintético", "amount_cents": amount, "valid_until": _iso(completed + timedelta(days=14)), "authorization_ref": f"AUTH-H{i:03d}", "status": "accepted"})
        contract_id = "CT-001" if customer_id == "C-009" else "CT-002" if customer_id == "C-010" else None
        data["work_orders"].append({"id": wid, "version": 1, "synthetic": True, "created_at": DEMO_NOW, "updated_at": DEMO_NOW, "customer_id": customer_id, "vehicle_id": vehicle_id, "quote_id": qid, "contract_id": contract_id, "technician_id": data["technicians"][(i - 1) % 4]["id"], "bay_id": data["bays"][(i - 1) % 4]["id"], "description": "Servicio histórico sintético", "due_at": _iso(completed), "opened_at": _iso(opened), "completed_at": _iso(completed), "inspection": "Inspección histórica sintética", "authorization_ref": f"AUTH-H{i:03d}", "qc_ref": f"QC-H{i:03d}", "block_reason": None, "status": "delivered"})
        data["invoices"].append({"id": iid, "version": 1, "synthetic": True, "created_at": DEMO_NOW, "updated_at": DEMO_NOW, "customer_id": customer_id, "work_order_id": wid, "tow_id": None, "amount_cents": amount, "due_at": _iso(completed + timedelta(days=7)), "status": "issued"})
        paid = amount if i % 3 else amount // 2
        data["payments"].append({"id": f"PAY-H{i:03d}", "version": 1, "synthetic": True, "created_at": DEMO_NOW, "updated_at": DEMO_NOW, "invoice_id": iid, "amount_cents": paid, "method": ("transfer", "card", "cash")[i % 3], "reference": f"DEMO-H{i:03d}", "paid_at": _iso(min(completed + timedelta(days=2), now))})
        data["stock_moves"].append({"id": f"SM-H{i:03d}", "version": 1, "synthetic": True, "created_at": DEMO_NOW, "updated_at": DEMO_NOW, "part_id": "P-002", "work_order_id": wid, "purchase_id": None, "move_type": "consume", "quantity": 1, "unit_cost_cents": 1800, "reason": "Consumo histórico sintético"})
        data["reservations"].append({"id": f"RS-H{i:03d}", "version": 1, "synthetic": True, "created_at": DEMO_NOW, "updated_at": DEMO_NOW, "part_id": "P-002", "work_order_id": wid, "quantity": 1, "status": "consumed"})
        states = [("initial", "received"), ("received", "inspected"), ("inspected", "authorized"), ("authorized", "scheduled"), ("scheduled", "in_service"), ("in_service", "quality_check"), ("quality_check", "ready"), ("ready", "delivered")]
        if i % 10 == 0:
            states = [("initial", "received"), ("received", "inspected"), ("inspected", "authorized"), ("authorized", "waiting_parts"), ("waiting_parts", "scheduled"), ("scheduled", "in_service"), ("in_service", "quality_check"), ("quality_check", "rework"), ("rework", "in_service"), ("in_service", "quality_check"), ("quality_check", "ready"), ("ready", "delivered")]
        for j, (before, after) in enumerate(states):
            fraction = j / (len(states) - 1)
            events.append({"event_id": f"EV-H{i:03d}-{j:02d}", "entity_type": "work_orders", "entity_id": wid, "from_state": before, "to_state": after, "at": _iso(opened + (completed - opened) * fraction), "actor": "Operador demo", "process_id": f"PROC-H{i:03d}", "synthetic": True})
    # Add stock received for the historical consumption and retain v1 open cases.
    data["purchases"][1]["quantity"] = 205
    data["stock_moves"][3]["quantity"] = 205
    for i in range(1, 7):
        data["expenses"].append({"id": f"EXP-H{i:03d}", "version": 1, "synthetic": True, "created_at": DEMO_NOW, "updated_at": DEMO_NOW, "description": "Gasto histórico sintético", "amount_cents": 9000 + i * 1000, "category": "parts" if i % 2 else "utilities", "method": "transfer", "paid_at": _iso(now - timedelta(days=i * 10))})
    validate_dataset(data)
    manifest = {"scenario": "operating_90_day", "seed": seed, "days": days, "synthetic": True, "record_counts": {kind: len(rows) for kind, rows in data.items()}, "event_count": len(events), "cutoff": DEMO_NOW}
    manifest["journey_count"] = len(journeys)
    return {"dataset": data, "events": events, "journeys": journeys, "manifest": manifest}


__all__ = ["make_operating_scenario"]
