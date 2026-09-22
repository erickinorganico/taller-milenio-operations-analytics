"""Evidence-bearing analysis for the synthetic Taller Milenio dataset."""
from __future__ import annotations

from collections import Counter
from statistics import median
from datetime import timedelta

from .contracts import DEMO_NOW, TERMINAL_WORK
from .domain import date_value, paid_amount
from .reports import projections, reference


def _ratio(n, d):
    return {"numerator": n, "denominator": d, "rate": round(n / d, 4) if d else None,
            "status": "measured" if d else "unknown"}


def _refs(kind, rows, field="status"):
    return [reference(kind, r, field) for r in rows]

def _median(values):
    return round(median(values), 2) if values else None


def analyze(data: dict, now: str = DEMO_NOW) -> dict:
    """Return deterministic descriptive metrics; absence is represented as unknown, never zero."""
    d = projections(data, now)
    at = date_value(now)
    customers = {x["id"]: x for x in d["customers"]}
    vehicles = {x["id"]: x for x in d["vehicles"]}
    particular = {x["id"] for x in d["customers"] if x["segment"] == "particular"}
    fleet = {x["id"] for x in d["customers"] if x["segment"] == "fleet"}
    leads = [x for x in d["leads"] if x["customer_id"] in particular]
    quotes = [x for x in d["quotes"] if x["customer_id"] in particular]
    appointments = [x for x in d["appointments"] if x["customer_id"] in particular]
    won = [x for x in leads if x["status"] == "won"]
    quote_links = [x for x in won if any(q["customer_id"] == x["customer_id"] and q["vehicle_id"] == x.get("vehicle_id") for q in quotes)]
    works = d["work_orders"]
    open_work = [x for x in works if x["status"] not in TERMINAL_WORK]
    parts_wait = [x for x in works if x["status"] == "waiting_parts"]
    busy = [x for x in works if x["status"] in {"scheduled", "in_service", "quality_check", "rework"}]
    accounts = {x["id"]: x for x in d["fleet_accounts"]}
    opps = d["opportunities"]
    contracts = d["contracts"]
    fleet_work = [x for x in works if x["customer_id"] in fleet]
    delivered_fleet = [x for x in fleet_work if x["status"] == "delivered"]
    sla = [x for x in fleet_work if x.get("contract_id")]
    tows = d["tows"]
    closed_tows = [x for x in tows if x["status"] == "closed"]
    review_tows = [x for x in tows if x["status"] not in {"closed", "cancelled"}]
    issued = [x for x in d["invoices"] if x["status"] == "issued"]
    paid = sum(x["amount_cents"] for x in d["payments"])
    invoiced = sum(x["amount_cents"] for x in issued)
    balance = sum(x["balance_cents"] for x in issued)
    aging={"current":0,"1_30":0,"31_60":0,"61_90":0,"90_plus":0}
    for inv in issued:
        days=(at-date_value(inv["due_at"])).days
        bucket="current" if days<=0 else "1_30" if days<=30 else "31_60" if days<=60 else "61_90" if days<=90 else "90_plus"
        aging[bucket]+=inv["balance_cents"]
    sla_eligible=[x for x in sla if x["sla_status"] not in {"unknown","not_applicable","excluded"}]
    sla_completed=[x for x in sla_eligible if x["status"]=="delivered"]
    result = {
        "meta": {"synthetic": True, "as_of": now, "currency": "MXN cents", "method": "descriptive snapshot; no causal or target claims"},
        "particulares": {"journey": {"type":"estado observado; no es un embudo temporal ni conversión atribuida", "leads": len(leads), "qualified_or_later": _ratio(sum(x["status"] not in {"new", "lost"} for x in leads), len(leads)), "won": _ratio(len(won), len(leads)), "won_with_candidate_quote_match": _ratio(len(quote_links), len(won)), "observed_lead_to_quote_conversion":"unknown: no existe llave de atribución lead→quote", "quote_pipeline_cents": sum(x["amount_cents"] for x in quotes if x["status"] in {"draft", "sent"}), "pending_appointments": len([x for x in appointments if x["status"] == "pending"])}, "coverage": {"leads_without_vehicle": _ratio(sum(not x.get("vehicle_id") for x in leads), len(leads)), "customers_without_consent": _ratio(sum(not customers[x["customer_id"]]["consent"] for x in leads), len(leads))}, "workshop_context":{"particular_open_orders":sum(x["customer_id"] in particular for x in open_work),"candidate_quote_match_note":"cliente y vehículo coincidentes; no prueba causalidad"}, "evidence": _refs("leads", leads)},
        "taller": {"wip": {"open_orders": len(open_work), "waiting_parts": _ratio(len(parts_wait), len(open_work)), "rework": _ratio(sum(x["status"] == "rework" for x in works), len(works)), "median_open_hours": _median([x["downtime_hours"] for x in open_work]), "occupied_bays_instant": _ratio(len({x["bay_id"] for x in busy if x.get("bay_id")}), len(d["bays"])), "capacity_note":"ocupación instantánea al corte; no es utilización por horas"}, "parts": {"available_at_or_below_reorder": _ratio(sum(x.get("available", 0) <= x["reorder_point"] for x in d["parts"]), len(d["parts"])), "waiting_order_evidence": _refs("work_orders", parts_wait, "block_reason")}, "evidence": _refs("work_orders", open_work)},
        "flotillas": {"commercial": {"open_opportunities": len([x for x in opps if x["status"] not in {"won", "lost"}]), "pipeline_cents": sum(x["value_cents"] for x in opps if x["status"] not in {"won", "lost"}), "account_coverage": _ratio(len({x["fleet_account_id"] for x in opps}), len(accounts))}, "contracted": {"active": len([x for x in contracts if x["status"] == "active" and date_value(x["starts_at"]) <= at < date_value(x["ends_at"])]), "delivered": _ratio(len(delivered_fleet), len(fleet_work)), "sla_eligibility":_ratio(len(sla_eligible),len(sla)), "sla_completed_met":_ratio(sum(x["sla_status"]=="met" for x in sla_completed),len(sla_completed)), "sla_open_at_risk":_ratio(sum(x["sla_status"] in {"at_risk","breached"} for x in sla_eligible if x["status"]!="delivered"),len([x for x in sla_eligible if x["status"]!="delivered"])), "sla_unknown": _ratio(sum(x["sla_status"] == "unknown" for x in sla), len(sla))}, "targeting": [{"fleet_account_id": a["id"], "priority":"alta" if any(x["fleet_account_id"]==a["id"] and x["status"] not in {"won","lost"} for x in opps) else "revisar", "heuristic":"Cuenta con oportunidad comercial abierta" if any(x["fleet_account_id"]==a["id"] and x["status"] not in {"won","lost"} for x in opps) else "Sin oportunidad abierta", "sensitivity":"La prioridad cambia si la oportunidad se cierra; no usa tamaño de flotilla como puntaje ni predice compra."} for a in accounts.values()], "evidence": _refs("opportunities", opps)},
        "gruas": {"timing": {"closed": len(closed_tows), "closed_with_duration": _ratio(sum(bool(x.get("closed_at")) for x in closed_tows), len(closed_tows)), "median_request_to_close_hours": _median([(date_value(x["closed_at"])-date_value(x["requested_at"])).total_seconds()/3600 for x in closed_tows if x.get("closed_at")]), "scope":"duración solicitud→cierre; no mide respuesta ni llegada"}, "human_review": {"open_requests": len(review_tows), "complete_human_refs": _ratio(sum(bool(x.get("safety_ref")) and bool(x.get("human_approval_ref")) for x in tows), len(tows)), "rule": "Toda solicitud abierta requiere revisión humana; este análisis no asigna ni despacha."}, "evidence": _refs("tows", tows)},
        "administracion": {"money": {"quotes_cents": sum(x["amount_cents"] for x in d["quotes"]), "invoiced_cents": invoiced, "paid_cents": paid, "receivable_cents": balance, "cash_net_cents": sum(x["amount_cents"] for x in d["payments"] if x["method"] == "cash")-sum(x["amount_cents"] for x in d["expenses"] if x["method"] == "cash"), "expense_cents":sum(x["amount_cents"] for x in d["expenses"]), "note":"pagado es cobro registrado, no ingreso reconocido; gasto es costo gerencial observado"}, "aging": {"buckets_cents":aging,"overdue_cents": sum(x["balance_cents"] for x in issued if date_value(x["due_at"]) < at), "issued_with_balance": _ratio(sum(x["balance_cents"] > 0 for x in issued), len(issued))}, "evidence": _refs("invoices", issued)},
        "assumptions": ["Los datos son sintéticos y reproducibles.", "Una tasa con denominador cero se informa como unknown.", "Las cotizaciones, facturas, pagos y efectivo son conceptos separados."]}

    result["administracion"]["money"]["parts_net_standard_cost_cents"] = sum(
        r["quantity"] * r["unit_cost_cents"] * (1 if r["move_type"] == "consume" else -1)
        for r in data["stock_moves"] if r["move_type"] in {"consume", "return"})
    result["flotillas"]["contracted"]["contract_link_coverage"] = _ratio(len(sla), len(fleet_work))
    fleet_open = [x for x in fleet_work if x["status"] not in TERMINAL_WORK]
    result["flotillas"]["contracted"]["median_open_downtime_hours"] = _median([x["downtime_hours"] for x in fleet_open])
    pending_maintenance = [x for x in d["maintenance"] if x["status"] in {"due", "scheduled"}]
    result["flotillas"]["maintenance"] = {"pending": len(pending_maintenance), "due_within_seven_days_or_mileage": sum(
        date_value(x["due_at"]) <= at + timedelta(days=7) or vehicles[x["vehicle_id"]]["odometer_km"] >= x["due_km"]
        for x in pending_maintenance), "evidence": _refs("maintenance", pending_maintenance)}
    source_groups = {
        "particulares": ["customers", "vehicles", "leads", "quotes", "appointments", "work_orders"],
        "taller": ["work_orders", "parts", "purchases", "stock_moves", "reservations", "bays", "technicians"],
        "flotillas": ["customers", "vehicles", "fleet_accounts", "opportunities", "contracts", "maintenance", "work_orders"],
        "gruas": ["tows", "tow_units"],
        "administracion": ["quotes", "invoices", "payments", "expenses", "stock_moves"],
    }
    result["source_evidence"] = {section: [{"entity_type": kind, "entity_id": r["id"], "version": r["version"]}
        for kind in kinds for r in data[kind]] for section, kinds in source_groups.items()}
    return result
