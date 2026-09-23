"""Live operational marts and immutable dashboard reads.

Every refresh reads the workshop's operational tables and stores the extracted
facts. Date filters apply to event dates; open work and balances are explicitly
current at the snapshot's real recording time. No historical backfill is implied.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from statistics import median

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from . import models


MARTS = {
    "daily_operations": "Orders opened and auditable deliveries by local day",
    "service_lines": "Lines on the latest approved quote for each order",
    "part_usage": "Signed consumption and return movements; purchases and reservations excluded",
    "receivables": "Non-void invoices and payments retained with their separate event dates",
    "order_journeys": "Current order state and audited delivery and parts-wait intervals",
    "inventory": "Part stock, reservation, price and cost as observed at refresh",
}
OPEN_STATES = {
    "intake", "inspection", "awaiting_approval", "approved", "in_progress",
    "waiting_parts", "quality", "ready",
}
SEGMENTS = {"all", "individual", "fleet"}
MAX_DAYS = 366
ZERO = Decimal("0")


def _day(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return timezone.localtime(value).date().isoformat()
    return value.isoformat()


def _amount(value):
    return str(value) if value is not None else None


def _number(value):
    return Decimal(str(value or "0"))


def _ref(model, pk):
    return {"model": model, "id": pk}


def _add(rows, mart, key, data):
    rows.append((mart, key, data))


def _event_status(event):
    if event.action != "status_changed" or event.entity_type.lower().replace("_", "").replace("-", "") != "workorder":
        return None
    before = event.before if isinstance(event.before, dict) else {}
    after = event.after if isinstance(event.after, dict) else {}
    return before.get("status"), after.get("status")


@transaction.atomic
def refresh_analytics(actor=None, trigger="manual"):
    """Record one real-time extract; earlier snapshots are never updated."""
    trigger = str(trigger).strip()[:32]
    if not trigger:
        raise ValidationError("A refresh trigger is required.")
    recorded_at = timezone.now()
    rows = []
    source_refs = {}
    source_counts = {}

    def capture(name, queryset):
        items = list(queryset.order_by("pk"))
        source_counts[name] = len(items)
        source_refs[name] = [item.pk for item in items]
        return items

    orders = capture("WorkOrder", models.WorkOrder.objects.select_related("vehicle__customer"))
    quotes = capture("Quote", models.Quote.objects.all())
    quote_lines = capture("QuoteLine", models.QuoteLine.objects.all())
    movements = capture("StockMovement", models.StockMovement.objects.select_related("part", "work_order__vehicle__customer"))
    invoices = capture("Invoice", models.Invoice.objects.select_related("work_order__vehicle__customer"))
    payments = capture("Payment", models.Payment.objects.select_related("invoice__work_order__vehicle__customer"))
    parts = capture("Part", models.Part.objects.all())
    events = capture("AuditEvent", models.AuditEvent.objects.filter(created_at__lte=recorded_at))
    source_counts["Customer"] = models.Customer.objects.count()
    source_counts["Vehicle"] = models.Vehicle.objects.count()
    source_counts["Reservation"] = models.Reservation.objects.count()
    source_counts["TimeEntry"] = models.TimeEntry.objects.count()

    order_by_id = {order.pk: order for order in orders}
    invoice_by_order = {invoice.work_order_id: invoice for invoice in invoices}
    invoice_by_id = {invoice.pk: invoice for invoice in invoices}
    payments_by_invoice = defaultdict(list)
    for payment in payments:
        payments_by_invoice[payment.invoice_id].append(payment)
    transitions = defaultdict(list)
    for event in events:
        statuses = _event_status(event)
        if statuses and statuses[1] and event.entity_id.isdecimal():
            transitions[int(event.entity_id)].append((event, *statuses))
    for timeline in transitions.values():
        timeline.sort(key=lambda item: (item[0].created_at, item[0].pk))

    daily = defaultdict(lambda: {"opened": 0, "delivered": 0, "opened_ids": [], "delivered_ids": []})
    for order in orders:
        kind = order.vehicle.customer.kind
        created_day = _day(order.created_at)
        if created_day:
            cell = daily[(created_day, kind)]
            cell["opened"] += 1
            cell["opened_ids"].append(order.pk)
        delivered_event = None
        wait_start = None
        completed_waits = []
        status_refs = []
        for event, before, after in transitions.get(order.pk, []):
            if event.created_at < order.created_at:
                continue
            status_refs.append(event.pk)
            if after == "waiting_parts" and before != "waiting_parts":
                wait_start = event
            elif before == "waiting_parts" and after != "waiting_parts" and wait_start is not None:
                hours = (event.created_at - wait_start.created_at).total_seconds() / 3600
                if hours >= 0:
                    completed_waits.append({"start_day": _day(wait_start.created_at), "end_day": _day(event.created_at),
                                            "hours": round(hours, 3), "start_event_id": wait_start.pk, "end_event_id": event.pk})
                wait_start = None
            if after == "delivered" and before != "delivered" and delivered_event is None:
                delivered_event = event
        current_wait_hours = ((recorded_at - wait_start.created_at).total_seconds() / 3600
                              if wait_start is not None and order.status == "waiting_parts" else None)
        delivered_day = _day(delivered_event.created_at) if delivered_event else None
        if delivered_day:
            cell = daily[(delivered_day, kind)]
            cell["delivered"] += 1
            cell["delivered_ids"].append(order.pk)
        cycle_hours = ((delivered_event.created_at - order.created_at).total_seconds() / 3600
                       if delivered_event else None)
        _add(rows, "order_journeys", str(order.pk), {
            "work_order_id": order.pk, "number": order.number, "customer_kind": kind,
            "status": order.status, "created_day": created_day, "promised_day": _day(order.promised_at),
            "promised_at": order.promised_at.isoformat() if order.promised_at else None,
            "delivered_day": delivered_day, "cycle_hours": round(cycle_hours, 3) if cycle_hours is not None and cycle_hours >= 0 else None,
            "waiting_parts_hours": round(sum(item["hours"] for item in completed_waits) + (current_wait_hours or 0), 3)
            if completed_waits or current_wait_hours is not None else None,
            "completed_wait_intervals": completed_waits,
            "current_wait_hours": round(current_wait_hours, 3) if current_wait_hours is not None else None,
            "invoice_id": invoice_by_order[order.pk].pk if order.pk in invoice_by_order else None,
            "source_refs": [_ref("WorkOrder", order.pk)] + [_ref("AuditEvent", pk) for pk in status_refs],
        })

    for (day, kind), values in sorted(daily.items()):
        _add(rows, "daily_operations", f"{day}:{kind}", {
            "day": day, "customer_kind": kind, "opened": values["opened"], "delivered": values["delivered"],
            "source_refs": [_ref("WorkOrder", pk) for pk in sorted(set(values["opened_ids"] + values["delivered_ids"]))],
        })

    latest_approved = {}
    quote_by_id = {quote.pk: quote for quote in quotes}
    for quote in quotes:
        if quote.status == "approved" and (quote.work_order_id not in latest_approved or
                                           (quote.version, quote.pk) > (latest_approved[quote.work_order_id].version,
                                                                         latest_approved[quote.work_order_id].pk)):
            latest_approved[quote.work_order_id] = quote
    for line in quote_lines:
        candidate = quote_by_id.get(line.quote_id)
        quote = latest_approved.get(candidate.work_order_id) if candidate else None
        if quote is None or quote.pk != line.quote_id:
            continue
        order = order_by_id.get(quote.work_order_id)
        if order is None:
            continue
        invoice = invoice_by_order.get(order.pk)
        billed_invoice = invoice if invoice and invoice.voided_at is None else None
        description = " ".join(line.description.split())
        _add(rows, "service_lines", str(line.pk), {
            "quote_line_id": line.pk, "quote_id": quote.pk, "quote_version": quote.version,
            "work_order_id": order.pk, "customer_kind": order.vehicle.customer.kind,
            "kind": line.kind, "description": description, "normalized_description": description.casefold(),
            "quantity": _amount(line.quantity), "unit_price": _amount(line.unit_price),
            "authorized_value": _amount(line.quantity * line.unit_price),
            "unit_cost_known": line.unit_cost is not None,
            "authorized_day": _day(quote.authorized_at), "invoice_id": billed_invoice.pk if billed_invoice else None,
            "billed_day": _day(billed_invoice.issued_at) if billed_invoice else None,
            "source_refs": [_ref("QuoteLine", line.pk), _ref("Quote", quote.pk), _ref("WorkOrder", order.pk)] +
                           ([_ref("Invoice", billed_invoice.pk)] if billed_invoice else []),
        })

    for movement in movements:
        if movement.kind not in {"consume", "return"}:
            continue
        order = order_by_id.get(movement.work_order_id)
        quantity = -movement.quantity  # consume is negative, return is positive
        _add(rows, "part_usage", str(movement.pk), {
            "movement_id": movement.pk, "part_id": movement.part_id, "sku": movement.part.sku,
            "part_name": movement.part.name, "unit": movement.part.unit,
            "work_order_id": movement.work_order_id, "customer_kind": order.vehicle.customer.kind if order else None,
            "kind": movement.kind, "day": _day(movement.created_at),
            "net_quantity": _amount(quantity), "unit_cost": _amount(movement.unit_cost),
            "net_cost": _amount(quantity * movement.unit_cost),
            "source_refs": [_ref("StockMovement", movement.pk), _ref("Part", movement.part_id)] +
                           ([_ref("WorkOrder", order.pk)] if order else []),
        })

    for invoice in invoices:
        order = order_by_id.get(invoice.work_order_id)
        issued_as_of = invoice.issued_at <= recorded_at
        voided_as_of = bool(invoice.voided_at and invoice.voided_at <= recorded_at)
        paid = sum((payment.amount for payment in payments_by_invoice[invoice.pk]
                    if payment.received_at <= recorded_at), ZERO)
        _add(rows, "receivables", f"invoice:{invoice.pk}", {
            "type": "invoice", "invoice_id": invoice.pk, "number": invoice.number,
            "work_order_id": invoice.work_order_id, "customer_kind": order.vehicle.customer.kind if order else None,
            "issued_day": _day(invoice.issued_at), "due_day": _day(invoice.due_at),
            "due_at": invoice.due_at.isoformat(), "issued_as_of": issued_as_of, "voided": voided_as_of,
            "subtotal": _amount(invoice.subtotal), "tax": _amount(invoice.tax), "total": _amount(invoice.total),
            "paid": _amount(paid), "open_balance": _amount(max(invoice.total - paid, ZERO)) if issued_as_of and not voided_as_of else None,
            "source_refs": [_ref("Invoice", invoice.pk)] + [_ref("Payment", payment.pk) for payment in payments_by_invoice[invoice.pk]],
        })
    for payment in payments:
        invoice = invoice_by_id[payment.invoice_id]
        order = order_by_id.get(invoice.work_order_id)
        _add(rows, "receivables", f"payment:{payment.pk}", {
            "type": "payment", "payment_id": payment.pk, "invoice_id": invoice.pk,
            "work_order_id": invoice.work_order_id, "customer_kind": order.vehicle.customer.kind if order else None,
            "received_day": _day(payment.received_at), "amount": _amount(payment.amount),
            "received_as_of": payment.received_at <= recorded_at,
            "invoice_voided": bool(invoice.voided_at and invoice.voided_at <= recorded_at),
            "source_refs": [_ref("Payment", payment.pk), _ref("Invoice", invoice.pk)],
        })

    for part in parts:
        _add(rows, "inventory", str(part.pk), {
            "part_id": part.pk, "sku": part.sku, "name": part.name, "unit": part.unit,
            "stock": _amount(part.stock), "reserved": _amount(part.reserved),
            "reorder_point": _amount(part.reorder_point), "cost": _amount(part.cost),
            "sale_price": _amount(part.sale_price), "source_refs": [_ref("Part", part.pk)],
        })

    canonical = json.dumps(sorted(rows, key=lambda value: (value[0], value[1])), sort_keys=True,
                           ensure_ascii=False, separators=(",", ":"))
    fingerprint = sha256(canonical.encode("utf-8")).hexdigest()
    latest_event = max(events, key=lambda event: (event.created_at, event.pk)) if events else None
    snapshot = models.AnalyticsSnapshot.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        trigger=trigger, recorded_at=recorded_at, source_fingerprint=fingerprint,
        audit_cursor=max((event.pk for event in events), default=0), source_counts=source_counts,
        source_refs=source_refs,
        freshness={"recorded_at": recorded_at.isoformat(),
                   "latest_audit_at": latest_event.created_at.isoformat() if latest_event else None,
                   "latest_audit_id": latest_event.pk if latest_event else None,
                   "audit_age_minutes": round((recorded_at - latest_event.created_at).total_seconds() / 60, 1)
                   if latest_event else None},
        summary={"mart_counts": {mart: sum(item[0] == mart for item in rows) for mart in MARTS},
                 "scope": "single_workshop", "historical_state": "recorded_at_only"},
    )
    models.AnalyticsRow.objects.bulk_create([
        models.AnalyticsRow(snapshot=snapshot, mart=mart, key=key, data=data)
        for mart, key, data in rows
    ], batch_size=500)
    return snapshot


def _validated_period(start, end, snapshot):
    today = timezone.localtime(snapshot.recorded_at).date()

    def parse(value, label):
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            raise ValidationError(f"{label} must be a local calendar date.")
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except (TypeError, ValueError):
            raise ValidationError(f"{label} must use YYYY-MM-DD.") from None

    finish = parse(end, "end") or today
    begin = parse(start, "start") or (finish - timedelta(days=29))
    days = (finish - begin).days + 1
    if days < 1 or days > MAX_DAYS or finish > today or begin > today:
        raise ValidationError("Choose an ordered date range of at most 366 days ending by the snapshot day.")
    previous_end = begin - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    return begin.isoformat(), finish.isoformat(), previous_start.isoformat(), previous_end.isoformat(), days


def _metric(current, previous, *, unit="count", population=None, reason=None):
    current = _number(current)
    previous = _number(previous)
    return {
        "value": str(current), "previous": str(previous), "unit": unit,
        "change_percent": round((current - previous) / previous * 100, 2) if previous else None,
        "comparison_status": "measured" if previous else "unknown",
        "population": population, "reason": reason if population == 0 else None,
    }


def build_analytics_dashboard(start=None, end=None, snapshot=None, segment="all"):
    """Read only persisted facts; returns no live operational queries."""
    if snapshot is None:
        snapshot = models.AnalyticsSnapshot.objects.first()
    elif isinstance(snapshot, int) or isinstance(snapshot, str):
        snapshot = models.AnalyticsSnapshot.objects.get(pk=snapshot)
    if snapshot is None:
        return {"status": "no_snapshot", "snapshot": None, "message": "Refresh analytics to create the first recorded snapshot.",
                "marts": MARTS, "filters": {"start": start, "end": end, "segment": segment}}
    if segment not in SEGMENTS:
        raise ValidationError("segment must be all, individual, or fleet.")
    begin, finish, prior_begin, prior_finish, days = _validated_period(start, end, snapshot)
    rows = defaultdict(list)
    for row in snapshot.rows.all().iterator():
        if segment == "all" or row.mart == "inventory" or row.data.get("customer_kind") == segment:
            rows[row.mart].append(row.data)

    def inside(day, first=begin, last=finish):
        return bool(day and first <= day <= last)

    def period_sum(mart, date_field, amount_field, first, last, *, predicate=lambda row: True):
        return sum((_number(row.get(amount_field)) for row in rows[mart]
                    if inside(row.get(date_field), first, last) and predicate(row)), ZERO)

    def period_count(mart, date_field, first, last, *, predicate=lambda row: True):
        return sum(1 for row in rows[mart] if inside(row.get(date_field), first, last) and predicate(row))

    valid_invoice = lambda row: row.get("type") == "invoice" and row.get("issued_as_of") and not row.get("voided")
    valid_payment = lambda row: row.get("type") == "payment" and row.get("received_as_of") and not row.get("invoice_voided")
    financial = {
        "invoiced": _metric(period_sum("receivables", "issued_day", "total", begin, finish, predicate=valid_invoice),
                            period_sum("receivables", "issued_day", "total", prior_begin, prior_finish, predicate=valid_invoice), unit="MXN",
                            population=period_count("receivables", "issued_day", begin, finish, predicate=valid_invoice),
                            reason="No non-void invoices issued in this period."),
        "payments": _metric(period_sum("receivables", "received_day", "amount", begin, finish, predicate=valid_payment),
                            period_sum("receivables", "received_day", "amount", prior_begin, prior_finish, predicate=valid_payment), unit="MXN",
                            population=period_count("receivables", "received_day", begin, finish, predicate=valid_payment),
                            reason="No payments received in this period."),
    }
    operations = {
        "opened": _metric(period_sum("daily_operations", "day", "opened", begin, finish),
                          period_sum("daily_operations", "day", "opened", prior_begin, prior_finish)),
        "delivered": _metric(period_sum("daily_operations", "day", "delivered", begin, finish),
                             period_sum("daily_operations", "day", "delivered", prior_begin, prior_finish)),
    }
    wip = [row for row in rows["order_journeys"] if row["status"] in OPEN_STATES]
    late = [row for row in wip if row.get("promised_at") and datetime.fromisoformat(row["promised_at"]) < snapshot.recorded_at]
    active_invoices = [row for row in rows["receivables"] if valid_invoice(row)]
    balance = sum((_number(row["open_balance"]) for row in active_invoices), ZERO)

    deliveries = [row["cycle_hours"] for row in rows["order_journeys"]
                  if inside(row.get("delivered_day")) and row.get("cycle_hours") is not None]
    waits = []
    for row in rows["order_journeys"]:
        completed = [interval["hours"] for interval in row.get("completed_wait_intervals", [])
                     if inside(interval["end_day"])]
        if completed:
            waits.append(sum(completed))

    ranked_parts = defaultdict(lambda: {"quantity": ZERO, "cost": ZERO,
                                      "order_net": defaultdict(lambda: ZERO), "movement_ids": []})
    for row in rows["part_usage"]:
        if not inside(row["day"]):
            continue
        key = (row["part_id"], row["sku"], row["part_name"], row["unit"])
        target = ranked_parts[key]
        target["quantity"] += _number(row["net_quantity"])
        target["cost"] += _number(row["net_cost"])
        if row.get("work_order_id"):
            target["order_net"][row["work_order_id"]] += _number(row["net_quantity"])
        target["movement_ids"].append(row["movement_id"])
    parts_rank = [{"part_id": key[0], "sku": key[1], "name": key[2], "unit": key[3],
                   "net_quantity": str(value["quantity"]), "net_cost_mxn": str(value["cost"]),
                   "orders": sum(quantity > 0 for quantity in value["order_net"].values()),
                   "movement_ids": value["movement_ids"],
                   "source_refs": [_ref("StockMovement", pk) for pk in value["movement_ids"]]}
                  for key, value in ranked_parts.items()]
    # Different part units cannot be compared as one quantity scale.
    parts_rank.sort(key=lambda row: (-row["orders"], row["sku"], row["part_id"]))

    service_rank = defaultdict(lambda: {"authorized_quantity": ZERO, "authorized_value": ZERO,
                                        "billed_quote_quantity": ZERO, "billed_quote_value": ZERO,
                                        "authorized_orders": set(), "billed_orders": set(), "line_ids": []})
    for row in rows["service_lines"]:
        if row["kind"] not in {"labor", "service"}:
            continue
        key = (row["kind"], row["normalized_description"])
        target = service_rank[key]
        if inside(row.get("authorized_day")):
            target["authorized_quantity"] += _number(row["quantity"])
            target["authorized_value"] += _number(row["authorized_value"])
            target["authorized_orders"].add(row["work_order_id"])
            target["line_ids"].append(row["quote_line_id"])
        if row.get("invoice_id") and inside(row.get("billed_day")):
            target["billed_quote_quantity"] += _number(row["quantity"])
            target["billed_quote_value"] += _number(row["authorized_value"])
            target["billed_orders"].add(row["work_order_id"])
            target["line_ids"].append(row["quote_line_id"])
    services_rank = [{"kind": key[0], "description": key[1], "authorized_quantity": str(value["authorized_quantity"]),
                      "authorized_orders": len(value["authorized_orders"]), "authorized_value_mxn": str(value["authorized_value"]),
                      "billed_quote_quantity": str(value["billed_quote_quantity"]),
                      "billed_orders": len(value["billed_orders"]), "billed_quote_value_mxn": str(value["billed_quote_value"]),
                      "quote_line_ids": sorted(set(value["line_ids"])),
                      "source_refs": [_ref("QuoteLine", pk) for pk in sorted(set(value["line_ids"]))]}
                     for key, value in service_rank.items() if value["line_ids"]]
    services_rank.sort(key=lambda row: (-row["authorized_orders"],
                                        -_number(row["authorized_quantity"]),
                                        -_number(row["authorized_value_mxn"]), row["description"]))

    trend = []
    for offset in range(days):
        day = (date.fromisoformat(begin) + timedelta(days=offset)).isoformat()
        trend.append({"day": day,
                      "opened": int(period_sum("daily_operations", "day", "opened", day, day)),
                      "delivered": int(period_sum("daily_operations", "day", "delivered", day, day)),
                      "invoiced_mxn": str(period_sum("receivables", "issued_day", "total", day, day, predicate=valid_invoice)),
                      "payments_mxn": str(period_sum("receivables", "received_day", "amount", day, day, predicate=valid_payment))})

    return {
        "status": "ready", "snapshot": {"id": snapshot.pk, "recorded_at": snapshot.recorded_at.isoformat(),
                                           "source_fingerprint": snapshot.source_fingerprint,
                                           "audit_cursor": snapshot.audit_cursor, "freshness": snapshot.freshness,
                                           "source_counts": snapshot.source_counts},
        "filters": {"start": begin, "end": finish, "previous_start": prior_begin,
                    "previous_end": prior_finish, "days": days, "segment": segment},
        "kpis": {**operations, **financial,
                 "wip_current": {"value": len(wip), "as_of": snapshot.recorded_at.isoformat(), "source_refs": [r["source_refs"][0] for r in wip]},
                 "late_current": {"value": len(late), "as_of": snapshot.recorded_at.isoformat(), "known_promises": sum(bool(r.get("promised_at")) for r in wip),
                                  "source_refs": [r["source_refs"][0] for r in late]},
                 "open_balance_current": {"value": str(balance), "unit": "MXN", "as_of": snapshot.recorded_at.isoformat(),
                                          "source_refs": [_ref("Invoice", r["invoice_id"]) for r in active_invoices if _number(r["open_balance"]) > 0]},
                 "median_delivery_hours": {"value": round(median(deliveries), 2) if deliveries else None, "observed": len(deliveries), "unit": "hours"},
                 "median_parts_wait_hours": {"value": round(median(waits), 2) if waits else None, "observed": len(waits), "unit": "hours"}},
        "trend": trend, "rankings": {"parts": parts_rank, "services": services_rank},
        "coverage": {
            "delivered_without_audit": sum(row["status"] == "delivered" and not row.get("delivered_day") for row in rows["order_journeys"]),
            "open_orders_without_promise": sum(not row.get("promised_at") for row in wip),
            "approved_lines_without_authorization_day": sum(not row.get("authorized_day") for row in rows["service_lines"]),
            "approved_lines_without_unit_cost": sum(not row.get("unit_cost_known") for row in rows["service_lines"]),
            "void_invoices_excluded": sum(row.get("type") == "invoice" and row.get("voided") for row in rows["receivables"]),
            "delivery_audit_required": True,
            "ongoing_parts_waits": sum(row.get("current_wait_hours") is not None for row in rows["order_journeys"]),
            "margin_note": "Actual labor, overhead and complete costs are unavailable; quote unit costs alone do not establish realized margin.",
            "billed_quote_note": "Billed service values are approved quote line values associated with non-void invoices, not invoice line allocations.",
        },
        "marts": {name: {"description": description, "rows": snapshot.summary.get("mart_counts", {}).get(name, 0)}
                  for name, description in MARTS.items()},
        "explorer": {"snapshot_id": snapshot.pk, "marts": list(MARTS),
                     "columns": {"source_refs": "Stable model and primary-key references captured at refresh"}},
    }
