"""Atomic, audited write boundary for daily workshop operations."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Max, Sum
from django.utils import timezone

from .models import (
    AuditEvent, Inspection, Invoice, Part, Payment, PurchaseLine, PurchaseOrder,
    QualityCheck, Quote, QuoteLine, Reservation, StockMovement, TimeEntry,
    TowService, WorkOrder, ZERO,
)


DomainError = ValidationError
CENT = Decimal("0.01")
THREE = Decimal("0.001")


def _actor(actor, capability):
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "is_active", False):
        raise DomainError("Se requiere un usuario activo autenticado.")
    groups = set(actor.groups.values_list("name", flat=True))
    allowed = {
        "reception": {"advisor", "manager"},
        "work": {"technician", "advisor", "manager"},
        "stock": {"parts", "manager"},
        "finance": {"finance", "manager"},
    }[capability]
    if not actor.is_superuser and not groups.intersection(allowed):
        raise DomainError("El usuario no tiene permiso para esta operación.")


def _decimal(value, *, name, quantum=THREE, positive=False, nonzero=False):
    try:
        parsed = Decimal(str(value))
        if not parsed.is_finite() or parsed != parsed.quantize(quantum):
            raise InvalidOperation
    except (InvalidOperation, ValueError, TypeError):
        raise DomainError(f"{name} debe ser un número decimal válido con precisión {quantum}.")
    if positive and parsed <= 0 or nonzero and parsed == 0:
        raise DomainError(f"{name} debe ser {'positivo' if positive else 'distinto de cero'}.")
    return parsed


def _money(value, *, name, positive=False):
    result = _decimal(value, name=name, quantum=CENT, positive=positive)
    if result < 0:
        raise DomainError(f"{name} no puede ser negativo.")
    return result


def _text(value, name):
    result = str(value or "").strip()
    if not result:
        raise DomainError(f"{name} es obligatorio.")
    return result


def _choice(value, choices, name):
    if value not in choices.values:
        raise DomainError(f"{name} no es válido.")
    return value


def _audit(actor, entity, action, before=None, after=None):
    return AuditEvent.objects.create(
        actor=actor, entity_type=type(entity).__name__, entity_id=str(entity.pk),
        action=action, before=before or {}, after=after or {},
    )


def _lock_order(order):
    return WorkOrder.objects.select_for_update().get(pk=order.pk)


def _work_actor(actor, order):
    _actor(actor, "work")
    groups = set(actor.groups.values_list("name", flat=True))
    if (not actor.is_superuser and not groups.intersection({"manager", "advisor"})
            and order.assigned_to_id != actor.pk):
        raise DomainError("El técnico solo puede modificar órdenes asignadas a él.")


def _approved_quote(order):
    return Quote.objects.filter(work_order=order, status=Quote.Status.APPROVED).first()


TRANSITIONS = {
    WorkOrder.Status.INTAKE: {WorkOrder.Status.INSPECTION},
    WorkOrder.Status.INSPECTION: {WorkOrder.Status.AWAITING_APPROVAL},
    WorkOrder.Status.AWAITING_APPROVAL: {WorkOrder.Status.APPROVED},
    WorkOrder.Status.APPROVED: {WorkOrder.Status.IN_PROGRESS},
    WorkOrder.Status.IN_PROGRESS: {WorkOrder.Status.WAITING_PARTS, WorkOrder.Status.QUALITY},
    WorkOrder.Status.WAITING_PARTS: {WorkOrder.Status.IN_PROGRESS},
    WorkOrder.Status.QUALITY: {WorkOrder.Status.READY, WorkOrder.Status.IN_PROGRESS},
    WorkOrder.Status.READY: {WorkOrder.Status.DELIVERED, WorkOrder.Status.IN_PROGRESS},
    WorkOrder.Status.DELIVERED: set(),
    WorkOrder.Status.CANCELLED: set(),
}


@transaction.atomic
def create_work_order(*, actor, vehicle, complaint, number=None, assigned_to=None,
                      promised_at=None, odometer=None):
    _actor(actor, "reception")
    complaint = _text(complaint, "Motivo de la orden")
    if not getattr(vehicle, "pk", None):
        raise DomainError("El vehículo debe existir.")
    if odometer is not None and (not isinstance(odometer, int) or odometer < 0):
        raise DomainError("Odómetro inválido.")
    number = _text(number or f"WO-{timezone.now():%Y%m%d}-{uuid4().hex[:8].upper()}", "Folio")
    if WorkOrder.objects.filter(number=number).exists():
        raise DomainError("El folio ya existe.")
    order = WorkOrder.objects.create(vehicle=vehicle, number=number, complaint=complaint,
                                     assigned_to=assigned_to, promised_at=promised_at,
                                     odometer=odometer)
    _audit(actor, order, "created", after={"status": order.status, "number": order.number})
    return order


@transaction.atomic
def transition_work_order(*, actor, work_order, status, expected_version=None):
    order = _lock_order(work_order)
    if status in {WorkOrder.Status.DELIVERED, WorkOrder.Status.CANCELLED}:
        _actor(actor, "reception")
    else:
        _work_actor(actor, order)
    _choice(status, WorkOrder.Status, "Etapa")
    if expected_version is not None and order.version != expected_version:
        raise DomainError("La orden cambió desde que se abrió; actualice la pantalla.")
    if status == WorkOrder.Status.CANCELLED:
        if order.status in {WorkOrder.Status.DELIVERED, WorkOrder.Status.CANCELLED} or Invoice.objects.filter(work_order=order).exists():
            raise DomainError("No se puede cancelar una orden entregada, cancelada o facturada.")
        if order.reservations.filter(quantity__gt=0).exists():
            raise DomainError("Libere las reservas antes de cancelar.")
    elif status not in TRANSITIONS[order.status]:
        raise DomainError(f"Transición no permitida: {order.status} → {status}.")
    if status == WorkOrder.Status.AWAITING_APPROVAL and not order.inspections.exists():
        raise DomainError("Registre al menos una inspección antes de cotizar.")
    if status in {WorkOrder.Status.APPROVED, WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.WAITING_PARTS,
                  WorkOrder.Status.QUALITY, WorkOrder.Status.READY, WorkOrder.Status.DELIVERED} and not _approved_quote(order):
        raise DomainError("El trabajo requiere una cotización autorizada.")
    if status == WorkOrder.Status.READY:
        latest = order.quality_checks.order_by("-created_at", "-pk").first()
        stage = AuditEvent.objects.filter(entity_type="WorkOrder", entity_id=str(order.pk),
                                          action="status_changed", after__status="quality").order_by("-created_at", "-pk").first()
        if not latest or latest.result != QualityCheck.Result.PASS or not stage or latest.created_at < stage.created_at:
            raise DomainError("Se requiere un control de calidad aprobado.")
    if status == WorkOrder.Status.DELIVERED and order.reservations.filter(quantity__gt=F("consumed")).exists():
        raise DomainError("Libere o consuma las refacciones reservadas antes de entregar.")
    before = {"status": order.status, "version": order.version}
    order.status = status
    order.version += 1
    order.save(update_fields=["status", "version", "updated_at"])
    _audit(actor, order, "status_changed", before, {"status": status, "version": order.version})
    return order


@transaction.atomic
def add_inspection(*, actor, work_order, area, result, notes="", photo=None):
    order = _lock_order(work_order)
    _work_actor(actor, order)
    if order.status != WorkOrder.Status.INSPECTION:
        raise DomainError("La inspección solo se registra en la etapa de inspección.")
    _choice(result, Inspection.Result, "Resultado de inspección")
    inspection = Inspection.objects.create(work_order=order, area=_text(area, "Área"),
                                           result=result, notes=notes, photo=photo, created_by=actor)
    _audit(actor, inspection, "created", after={"work_order_id": order.pk, "result": result})
    return inspection


@transaction.atomic
def create_quote(*, actor, work_order, tax_rate=Decimal("0")):
    _actor(actor, "reception")
    order = _lock_order(work_order)
    if order.status not in {WorkOrder.Status.INSPECTION, WorkOrder.Status.AWAITING_APPROVAL}:
        raise DomainError("La cotización se prepara durante inspección o espera de autorización.")
    rate = _decimal(tax_rate, name="Tasa de impuesto", quantum=Decimal("0.0001"))
    if rate < 0 or rate > 1:
        raise DomainError("La tasa de impuesto debe estar entre 0 y 1.")
    if order.quotes.filter(status=Quote.Status.APPROVED).exists():
        raise DomainError("No se modifica una cotización autorizada.")
    prior = order.quotes.filter(status__in=[Quote.Status.DRAFT, Quote.Status.SENT])
    for quote in prior.select_for_update():
        previous = quote.status
        quote.status = Quote.Status.SUPERSEDED
        quote.save(update_fields=["status"])
        _audit(actor, quote, "superseded", {"status": previous}, {"status": quote.status})
    version = (order.quotes.aggregate(value=Max("version"))["value"] or 0) + 1
    quote = Quote.objects.create(work_order=order, version=version, tax_rate=rate)
    _audit(actor, quote, "created", after={"work_order_id": order.pk, "version": version})
    return quote


@transaction.atomic
def add_quote_line(*, actor, quote, description, kind, quantity, unit_price,
                   unit_cost=None, part=None):
    _actor(actor, "reception")
    quote = Quote.objects.select_for_update().get(pk=quote.pk)
    if quote.status != Quote.Status.DRAFT:
        raise DomainError("Solo se editan líneas de una cotización borrador.")
    _choice(kind, QuoteLine.Kind, "Tipo de línea")
    if (kind == QuoteLine.Kind.PART) != (part is not None):
        raise DomainError("Una línea de refacción requiere una parte; otras líneas no la usan.")
    line = QuoteLine.objects.create(
        quote=quote, description=_text(description, "Descripción"), kind=kind,
        quantity=_decimal(quantity, name="Cantidad", positive=True),
        unit_price=_money(unit_price, name="Precio unitario"),
        unit_cost=None if unit_cost is None else _money(unit_cost, name="Costo unitario"), part=part,
    )
    _audit(actor, line, "created", after={"quote_id": quote.pk, "kind": kind,
                                           "quantity": str(line.quantity), "unit_price": str(line.unit_price)})
    return line


@transaction.atomic
def send_quote(*, actor, quote):
    _actor(actor, "reception")
    quote = Quote.objects.select_for_update().get(pk=quote.pk)
    if quote.status != Quote.Status.DRAFT or not quote.lines.exists():
        raise DomainError("Solo se envía una cotización borrador con líneas.")
    quote.status = Quote.Status.SENT
    quote.save(update_fields=["status"])
    _audit(actor, quote, "sent", {"status": "draft"}, {"status": "sent"})
    return quote


@transaction.atomic
def approve_quote(*, actor, quote, approval_name, approval_reference):
    _actor(actor, "reception")
    quote = Quote.objects.select_for_update().get(pk=quote.pk)
    order = _lock_order(quote.work_order)
    if quote.status != Quote.Status.SENT or order.status != WorkOrder.Status.AWAITING_APPROVAL:
        raise DomainError("Solo se autoriza una cotización enviada de una orden en espera.")
    if not quote.lines.exists() or order.quotes.filter(status=Quote.Status.APPROVED).exists():
        raise DomainError("La orden requiere una única cotización con líneas.")
    quote.approval_name = _text(approval_name, "Nombre de quien autoriza")
    quote.approval_reference = _text(approval_reference, "Referencia de autorización")
    quote.authorized_at = timezone.now()
    quote.status = Quote.Status.APPROVED
    quote.save(update_fields=["approval_name", "approval_reference", "authorized_at", "status"])
    _audit(actor, quote, "approved", {"status": "sent"},
           {"status": "approved", "approval_name": quote.approval_name,
            "approval_reference": quote.approval_reference})
    order.status = WorkOrder.Status.APPROVED
    order.version += 1
    order.save(update_fields=["status", "version", "updated_at"])
    _audit(actor, order, "status_changed", {"status": "awaiting_approval"},
           {"status": "approved", "version": order.version})
    return quote


@transaction.atomic
def reject_quote(*, actor, quote, reason=""):
    _actor(actor, "reception")
    quote = Quote.objects.select_for_update().get(pk=quote.pk)
    if quote.status != Quote.Status.SENT:
        raise DomainError("Solo se rechaza una cotización enviada.")
    quote.status = Quote.Status.REJECTED
    quote.save(update_fields=["status"])
    _audit(actor, quote, "rejected", {"status": "sent"},
           {"status": "rejected", "reason": str(reason).strip()})
    return quote


def _authorized_part_quantity(order, part):
    quote = _approved_quote(order)
    if not quote:
        return ZERO
    return sum((line.quantity for line in quote.lines.filter(kind=QuoteLine.Kind.PART, part=part)), ZERO)


@transaction.atomic
def create_purchase_order(*, actor, supplier, number):
    _actor(actor, "stock")
    number = _text(number, "Folio de compra")
    if PurchaseOrder.objects.filter(number=number).exists():
        raise DomainError("El folio de compra ya existe.")
    purchase = PurchaseOrder.objects.create(supplier=supplier, number=number)
    _audit(actor, purchase, "created", after={"number": number, "status": purchase.status})
    return purchase


@transaction.atomic
def add_purchase_line(*, actor, purchase_order, part, quantity, unit_cost):
    _actor(actor, "stock")
    purchase = PurchaseOrder.objects.select_for_update().get(pk=purchase_order.pk)
    if purchase.status != PurchaseOrder.Status.DRAFT:
        raise DomainError("Las líneas de compra solo se editan en borrador.")
    line = PurchaseLine.objects.create(
        purchase_order=purchase, part=part,
        quantity=_decimal(quantity, name="Cantidad", positive=True),
        unit_cost=_money(unit_cost, name="Costo unitario"),
    )
    _audit(actor, line, "created", after={"purchase_order_id": purchase.pk,
                                           "part_id": part.pk, "quantity": str(line.quantity)})
    return line


@transaction.atomic
def place_purchase_order(*, actor, purchase_order):
    _actor(actor, "stock")
    purchase = PurchaseOrder.objects.select_for_update().get(pk=purchase_order.pk)
    if purchase.status != PurchaseOrder.Status.DRAFT or not purchase.lines.exists():
        raise DomainError("Solo se marca pedida una compra borrador con líneas.")
    purchase.status = PurchaseOrder.Status.ORDERED
    purchase.save(update_fields=["status"])
    _audit(actor, purchase, "ordered", {"status": "draft"}, {"status": "ordered"})
    return purchase


@transaction.atomic
def reserve_part(*, actor, work_order, part, quantity):
    _actor(actor, "stock")
    order = _lock_order(work_order)
    if order.status not in {WorkOrder.Status.APPROVED, WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.WAITING_PARTS}:
        raise DomainError("La orden debe estar autorizada y abierta para reservar.")
    part = Part.objects.select_for_update().get(pk=part.pk)
    amount = _decimal(quantity, name="Cantidad", positive=True)
    reservation, _ = Reservation.objects.select_for_update().get_or_create(
        work_order=order, part=part, defaults={"quantity": ZERO})
    if reservation.quantity + amount > _authorized_part_quantity(order, part):
        raise DomainError("La cantidad supera las refacciones autorizadas en la cotización.")
    if part.stock - part.reserved < amount:
        raise DomainError("Stock disponible insuficiente.")
    reservation.quantity += amount
    reservation.save(update_fields=["quantity"])
    part.reserved += amount
    part.save(update_fields=["reserved"])
    _audit(actor, reservation, "reserved", after={"quantity": str(reservation.quantity),
                                                  "part_id": part.pk, "work_order_id": order.pk})
    return reservation


@transaction.atomic
def consume_reservation(*, actor, reservation, quantity):
    _actor(actor, "stock")
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    order = _lock_order(reservation.work_order)
    if order.status not in {WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.WAITING_PARTS}:
        raise DomainError("El consumo requiere trabajo en curso.")
    part = Part.objects.select_for_update().get(pk=reservation.part_id)
    amount = _decimal(quantity, name="Cantidad", positive=True)
    if amount > reservation.quantity - reservation.consumed or amount > part.reserved:
        raise DomainError("Consumo sin reserva suficiente.")
    part.stock -= amount
    part.reserved -= amount
    reservation.consumed += amount
    part.save(update_fields=["stock", "reserved"])
    reservation.save(update_fields=["consumed"])
    movement = StockMovement.objects.create(part=part, work_order=order,
                                             kind=StockMovement.Kind.CONSUME,
                                             quantity=-amount, unit_cost=part.cost, created_by=actor)
    _audit(actor, movement, "consumed", after={"quantity": str(-amount), "part_id": part.pk,
                                               "reservation_id": reservation.pk})
    return reservation


@transaction.atomic
def release_reservation(*, actor, reservation, quantity):
    _actor(actor, "stock")
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    part = Part.objects.select_for_update().get(pk=reservation.part_id)
    amount = _decimal(quantity, name="Cantidad", positive=True)
    if amount > reservation.quantity - reservation.consumed:
        raise DomainError("Liberación superior a la reserva pendiente.")
    reservation.quantity -= amount
    part.reserved -= amount
    reservation.save(update_fields=["quantity"])
    part.save(update_fields=["reserved"])
    _audit(actor, reservation, "released", after={"quantity": str(reservation.quantity),
                                                  "released": str(amount)})
    return reservation


@transaction.atomic
def return_consumed_part(*, actor, reservation, quantity):
    _actor(actor, "stock")
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    part = Part.objects.select_for_update().get(pk=reservation.part_id)
    amount = _decimal(quantity, name="Cantidad", positive=True)
    if amount > reservation.consumed - reservation.returned:
        raise DomainError("Devolución superior al consumo neto.")
    reservation.returned += amount
    part.stock += amount
    reservation.save(update_fields=["returned"])
    part.save(update_fields=["stock"])
    movement = StockMovement.objects.create(part=part, work_order=reservation.work_order,
                                             kind=StockMovement.Kind.RETURN, quantity=amount,
                                             unit_cost=part.cost, created_by=actor)
    _audit(actor, movement, "returned", after={"quantity": str(amount),
                                               "reservation_id": reservation.pk})
    return reservation


@transaction.atomic
def receive_purchase_line(*, actor, line, quantity, reference=""):
    _actor(actor, "stock")
    line = PurchaseLine.objects.select_for_update().get(pk=line.pk)
    order = PurchaseOrder.objects.select_for_update().get(pk=line.purchase_order_id)
    reference = _text(reference, "Referencia de recepción")
    movement_ref = f"line:{line.pk}:{reference}"
    amount = _decimal(quantity, name="Cantidad", positive=True)
    existing = StockMovement.objects.filter(purchase_order=order,
                                            kind=StockMovement.Kind.RECEIPT,
                                            reference=movement_ref).first()
    if existing:
        if existing.quantity != amount:
            raise DomainError("La referencia ya fue recibida con otra cantidad.")
        return line
    if order.status not in {PurchaseOrder.Status.ORDERED, PurchaseOrder.Status.PARTIAL}:
        raise DomainError("Solo se recibe una compra pedida o parcial.")
    if line.received + amount > line.quantity:
        raise DomainError("La recepción supera la cantidad pedida.")
    part = Part.objects.select_for_update().get(pk=line.part_id)
    part.stock += amount
    part.save(update_fields=["stock"])
    line.received += amount
    line.save(update_fields=["received"])
    movement = StockMovement.objects.create(part=part, purchase_order=order,
                                             kind=StockMovement.Kind.RECEIPT, quantity=amount,
                                             unit_cost=line.unit_cost, reference=movement_ref,
                                             created_by=actor)
    pending = order.lines.filter(received__lt=F("quantity")).exists()
    order.status = PurchaseOrder.Status.PARTIAL if pending else PurchaseOrder.Status.RECEIVED
    order.save(update_fields=["status"])
    _audit(actor, movement, "received", after={"quantity": str(amount), "line_id": line.pk,
                                               "reference": reference})
    return line


@transaction.atomic
def adjust_stock(*, actor, part, quantity, reason):
    _actor(actor, "stock")
    part = Part.objects.select_for_update().get(pk=part.pk)
    amount = _decimal(quantity, name="Ajuste", nonzero=True)
    reason = _text(reason, "Motivo de ajuste")
    if part.stock + amount < part.reserved:
        raise DomainError("El ajuste dejaría stock negativo o reservas sin respaldo.")
    old = part.stock
    part.stock += amount
    part.save(update_fields=["stock"])
    movement = StockMovement.objects.create(part=part, kind=StockMovement.Kind.ADJUSTMENT,
                                             quantity=amount, unit_cost=part.cost,
                                             reference=reason, created_by=actor)
    _audit(actor, movement, "adjusted", before={"stock": str(old)},
           after={"stock": str(part.stock), "reason": reason})
    return movement


@transaction.atomic
def add_time_entry(*, actor, work_order, minutes, notes=""):
    order = _lock_order(work_order)
    _work_actor(actor, order)
    if order.status not in {WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.WAITING_PARTS}:
        raise DomainError("El tiempo se registra durante trabajo en curso.")
    if type(minutes) is not int or minutes <= 0 or minutes > 1440:
        raise DomainError("Minutos deben estar entre 1 y 1440.")
    entry = TimeEntry.objects.create(work_order=order, technician=actor, minutes=minutes, notes=notes)
    _audit(actor, entry, "created", after={"work_order_id": order.pk, "minutes": minutes})
    return entry


@transaction.atomic
def record_quality_check(*, actor, work_order, result, notes=""):
    order = _lock_order(work_order)
    _work_actor(actor, order)
    if order.status != WorkOrder.Status.QUALITY:
        raise DomainError("Control de calidad fuera de etapa.")
    _choice(result, QualityCheck.Result, "Resultado de calidad")
    check = QualityCheck.objects.create(work_order=order, result=result, notes=notes,
                                        checked_by=actor)
    _audit(actor, check, "created", after={"work_order_id": order.pk, "result": result})
    return check


@transaction.atomic
def issue_invoice(*, actor, work_order, number, due_at):
    _actor(actor, "finance")
    order = _lock_order(work_order)
    if order.status != WorkOrder.Status.DELIVERED:
        raise DomainError("El comprobante administrativo requiere entrega y calidad aprobada.")
    if Invoice.objects.filter(work_order=order).exists():
        raise DomainError("La orden ya tiene comprobante.")
    quote = _approved_quote(order)
    if not quote:
        raise DomainError("No hay cotización autorizada.")
    number = _text(number, "Folio de comprobante")
    if Invoice.objects.filter(number=number).exists():
        raise DomainError("El folio de comprobante ya existe.")
    now = timezone.now()
    if due_at is None or timezone.is_naive(due_at) or due_at < now:
        raise DomainError("La fecha de vencimiento debe ser posterior a la emisión y tener zona horaria.")
    subtotal = sum((line.quantity * line.unit_price for line in quote.lines.all()), ZERO).quantize(CENT, rounding=ROUND_HALF_UP)
    tax = (subtotal * quote.tax_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    invoice = Invoice.objects.create(work_order=order, number=number, subtotal=subtotal,
                                     tax=tax, total=subtotal + tax, issued_at=now, due_at=due_at)
    _audit(actor, invoice, "issued", after={"work_order_id": order.pk, "total": str(invoice.total)})
    return invoice


@transaction.atomic
def record_payment(*, actor, invoice, amount, method, reference, idempotency_key,
                   received_at=None):
    _actor(actor, "finance")
    amount = _money(amount, name="Pago", positive=True)
    method = _text(method, "Método")
    reference = _text(reference, "Referencia de pago")
    idempotency_key = _text(idempotency_key, "Clave de idempotencia")
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.voided_at:
        raise DomainError("El comprobante fue anulado.")
    supplied_received_at = received_at
    if received_at is not None and timezone.is_naive(received_at):
        raise DomainError("La fecha del pago requiere zona horaria.")
    prior = Payment.objects.filter(idempotency_key=idempotency_key).first()
    if prior:
        if (prior.invoice_id != invoice.pk or prior.amount != amount or
            prior.method != method or prior.reference != reference or
            (supplied_received_at is not None and prior.received_at != supplied_received_at)):
            raise DomainError("Clave de idempotencia usada con otros datos.")
        return prior
    paid = invoice.payments.aggregate(value=Sum("amount"))["value"] or ZERO
    if paid + amount > invoice.total:
        raise DomainError("El pago supera el saldo pendiente.")
    payment = Payment.objects.create(invoice=invoice, amount=amount, method=method,
                                     reference=reference, idempotency_key=idempotency_key,
                                     received_at=supplied_received_at or timezone.now(), created_by=actor)
    _audit(actor, payment, "received", after={"invoice_id": invoice.pk,
                                              "amount": str(amount), "reference": reference})
    return payment


@transaction.atomic
def create_tow_service(*, actor, customer, origin, destination, vehicle=None, notes=""):
    _actor(actor, "reception")
    if vehicle is not None and vehicle.customer_id != customer.pk:
        raise DomainError("El vehículo no pertenece al cliente indicado.")
    tow = TowService.objects.create(customer=customer, vehicle=vehicle,
                                    origin=_text(origin, "Origen"),
                                    destination=_text(destination, "Destino"), notes=notes)
    _audit(actor, tow, "created", after={"status": tow.status})
    return tow


TOW_TRANSITIONS = {
    TowService.Status.REQUESTED: {TowService.Status.ASSIGNED, TowService.Status.CANCELLED},
    TowService.Status.ASSIGNED: {TowService.Status.EN_ROUTE, TowService.Status.CANCELLED},
    TowService.Status.EN_ROUTE: {TowService.Status.ARRIVED, TowService.Status.CANCELLED},
    TowService.Status.ARRIVED: {TowService.Status.COMPLETED, TowService.Status.CANCELLED},
    TowService.Status.COMPLETED: set(),
    TowService.Status.CANCELLED: set(),
}


@transaction.atomic
def transition_tow_service(*, actor, tow_service, status, operator_name="", safety_reference=""):
    _actor(actor, "reception")
    tow = TowService.objects.select_for_update().get(pk=tow_service.pk)
    _choice(status, TowService.Status, "Estado de grúa")
    if status not in TOW_TRANSITIONS[tow.status]:
        raise DomainError("Transición de grúa no permitida.")
    if status == TowService.Status.ASSIGNED:
        tow.operator_name = _text(operator_name, "Operador")
        tow.safety_reference = _text(safety_reference, "Referencia humana de seguridad")
    if status == TowService.Status.ARRIVED:
        tow.arrived_at = timezone.now()
    if status == TowService.Status.COMPLETED:
        if not tow.operator_name or not tow.safety_reference or not tow.arrived_at:
            raise DomainError("Faltan hitos y evidencia humana para cerrar la grúa.")
        tow.completed_at = timezone.now()
    previous = tow.status
    tow.status = status
    tow.save()
    _audit(actor, tow, "status_changed", {"status": previous}, {"status": status})
    return tow
