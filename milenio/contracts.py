"""Single source of truth for the local command and record contract.

Money is integer MXN cents. Dates are UTC ISO-8601. All records are synthetic.
The mutable demo is intentionally unsuitable for real dispatch or accounting.
"""
SCHEMA_VERSION = 1
DEMO_NOW = "2026-09-21T18:00:00Z"

# field: type; '?' means optional. refs are enforced by the domain service.
FIELDS = {
    "customers": {"name": "str", "segment": "enum:particular,fleet", "consent": "bool", "contact": "str?"},
    "vehicles": {"customer_id": "ref:customers", "label": "str", "plate": "str", "odometer_km": "int"},
    "leads": {"customer_id": "ref:customers", "vehicle_id": "ref:vehicles?", "need": "str", "channel": "str", "follow_up_at": "date", "status": "state"},
    "quotes": {"customer_id": "ref:customers", "vehicle_id": "ref:vehicles", "description": "str", "amount_cents": "money", "valid_until": "date", "authorization_ref": "str?", "status": "state"},
    "appointments": {"customer_id": "ref:customers", "vehicle_id": "ref:vehicles", "starts_at": "date", "reason": "str", "status": "state"},
    "technicians": {"name": "str", "specialty": "str"},
    "bays": {"name": "str"},
    "work_orders": {"customer_id": "ref:customers", "vehicle_id": "ref:vehicles", "quote_id": "ref:quotes?", "contract_id": "ref:contracts?", "technician_id": "ref:technicians?", "bay_id": "ref:bays?", "description": "str", "due_at": "date", "opened_at": "date", "completed_at": "date?", "inspection": "str?", "authorization_ref": "str?", "qc_ref": "str?", "block_reason": "str?", "status": "state"},
    "suppliers": {"name": "str", "contact": "str?"},
    "parts": {"sku": "str", "name": "str", "supplier_id": "ref:suppliers", "unit_cost_cents": "money", "reorder_point": "int"},
    "purchases": {"part_id": "ref:parts", "quantity": "positive", "unit_cost_cents": "money", "expected_at": "date", "status": "state"},
    "stock_moves": {"part_id": "ref:parts", "work_order_id": "ref:work_orders?", "purchase_id": "ref:purchases?", "move_type": "enum:receive,consume,return,adjust", "quantity": "signed", "unit_cost_cents": "money", "reason": "str"},
    "reservations": {"part_id": "ref:parts", "work_order_id": "ref:work_orders", "quantity": "positive", "status": "enum:reserved,consumed,released"},
    "fleet_accounts": {"customer_id": "ref:customers", "industry": "str", "fleet_size": "positive", "owner": "str"},
    "contacts": {"fleet_account_id": "ref:fleet_accounts", "name": "str", "role": "str", "contact": "str", "consent": "bool"},
    "opportunities": {"fleet_account_id": "ref:fleet_accounts", "title": "str", "value_cents": "money", "next_step": "str", "follow_up_at": "date", "status": "state"},
    "contracts": {"fleet_account_id": "ref:fleet_accounts", "name": "str", "sla_hours": "positive", "starts_at": "date", "ends_at": "date", "approval_ref": "str?", "status": "state"},
    "maintenance": {"vehicle_id": "ref:vehicles", "contract_id": "ref:contracts", "service": "str", "due_at": "date", "due_km": "int", "work_order_id": "ref:work_orders?", "status": "state"},
    "tow_units": {"name": "str", "capability": "str"},
    "tows": {"customer_id": "ref:customers", "vehicle_id": "ref:vehicles", "pickup": "str", "destination": "str", "conditions": "str", "requested_at": "date", "due_at": "date", "closed_at": "date?", "amount_cents": "money?", "unit_id": "ref:tow_units?", "safety_ref": "str?", "human_approval_ref": "str?", "status": "state"},
    "invoices": {"customer_id": "ref:customers", "work_order_id": "ref:work_orders?", "tow_id": "ref:tows?", "amount_cents": "money", "due_at": "date", "status": "state"},
    "payments": {"invoice_id": "ref:invoices", "amount_cents": "positive", "method": "enum:cash,transfer,card", "reference": "str", "paid_at": "date"},
    "expenses": {"description": "str", "amount_cents": "positive", "category": "enum:parts,rent,payroll,utilities,other", "method": "enum:cash,transfer,card", "paid_at": "date"},
    "campaigns": {"name": "str", "audience": "enum:particular,fleet", "objective": "str", "draft": "str", "status": "state"},
    "proposals": {"agent": "str", "title": "str", "rationale": "str", "evidence": "list", "approval_required": "bool", "external_execution": "bool", "status": "enum:pending,approved,rejected", "decision_note": "str?"},
}

FLOWS = {
    "leads": {"new": ["qualified", "lost"], "qualified": ["quoted", "lost"], "quoted": ["won", "lost"], "won": [], "lost": []},
    "quotes": {"draft": ["sent", "cancelled"], "sent": ["accepted", "rejected", "expired"], "accepted": [], "rejected": [], "expired": [], "cancelled": []},
    "appointments": {"pending": ["confirmed", "cancelled"], "confirmed": ["arrived", "no_show", "cancelled"], "arrived": [], "no_show": [], "cancelled": []},
    "work_orders": {"received": ["inspected", "cancelled"], "inspected": ["authorized", "cancelled"], "authorized": ["scheduled", "waiting_parts", "cancelled"], "waiting_parts": ["scheduled", "cancelled"], "scheduled": ["in_service", "waiting_parts", "cancelled"], "in_service": ["quality_check", "waiting_parts"], "quality_check": ["ready", "rework"], "rework": ["in_service"], "ready": ["delivered", "rework"], "delivered": [], "cancelled": []},
    "purchases": {"draft": ["ordered", "cancelled"], "ordered": ["received", "cancelled"], "received": [], "cancelled": []},
    "opportunities": {"research": ["qualified", "lost"], "qualified": ["proposal", "lost"], "proposal": ["negotiation", "lost"], "negotiation": ["won", "lost"], "won": [], "lost": []},
    "contracts": {"draft": ["active", "cancelled"], "active": ["expired", "suspended"], "suspended": ["active", "cancelled"], "expired": [], "cancelled": []},
    "maintenance": {"due": ["scheduled", "cancelled"], "scheduled": ["completed", "cancelled"], "completed": [], "cancelled": []},
    "tows": {"requested": ["assessed", "cancelled"], "assessed": ["quoted", "cancelled"], "quoted": ["assigned", "cancelled"], "assigned": ["accepted", "cancelled"], "accepted": ["en_route", "cancelled"], "en_route": ["arrived"], "arrived": ["transporting"], "transporting": ["closed"], "closed": [], "cancelled": []},
    "invoices": {"draft": ["issued", "void"], "issued": ["void"], "void": []},
    "campaigns": {"draft": ["review", "archived"], "review": ["approved", "archived"], "approved": ["archived"], "archived": []},
}
INITIAL = {kind: next(iter(flow)) for kind, flow in FLOWS.items()}
MANAGED = {"stock_moves", "reservations", "payments", "proposals"}
TERMINAL_WORK = {"delivered", "cancelled"}
BUSY_WORK = {"scheduled", "in_service", "quality_check", "rework"}
