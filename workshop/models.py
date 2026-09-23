"""Persistent, single-workshop operational records.

Money is stored as Decimal MXN amounts. Services own all stateful writes.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


ZERO = Decimal("0.00")
MONEY = {"max_digits": 14, "decimal_places": 2}
QUANTITY = {"max_digits": 12, "decimal_places": 3}


class Customer(models.Model):
    class Kind(models.TextChoices):
        INDIVIDUAL = "individual", "Particular"
        FLEET = "fleet", "Flotilla"

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.INDIVIDUAL)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="vehicles")
    plate = models.CharField(max_length=32, blank=True)
    vin = models.CharField(max_length=32, blank=True, unique=True, null=True)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    odometer = models.PositiveIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Multiple vehicles may legitimately have an unknown VIN; SQLite's
        # unique NULL behavior preserves that, whereas repeated blank strings do not.
        self.vin = self.vin or None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plate or self.vin or self.pk} · {self.make} {self.model}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Programada"
        CONFIRMED = "confirmed", "Confirmada"
        COMPLETED = "completed", "Atendida"
        CANCELLED = "cancelled", "Cancelada"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="appointments")
    scheduled_at = models.DateTimeField()
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)


class WorkOrder(models.Model):
    class Status(models.TextChoices):
        INTAKE = "intake", "Recepción"
        INSPECTION = "inspection", "Inspección"
        AWAITING_APPROVAL = "awaiting_approval", "Espera autorización"
        APPROVED = "approved", "Autorizada"
        IN_PROGRESS = "in_progress", "En trabajo"
        WAITING_PARTS = "waiting_parts", "Espera refacciones"
        QUALITY = "quality", "Calidad"
        READY = "ready", "Lista"
        DELIVERED = "delivered", "Entregada"
        CANCELLED = "cancelled", "Cancelada"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="work_orders")
    number = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.INTAKE)
    complaint = models.TextField()
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_work_orders")
    promised_at = models.DateTimeField(null=True, blank=True)
    odometer = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.number


class Inspection(models.Model):
    class Result(models.TextChoices):
        OKAY = "okay", "Correcto"
        WATCH = "watch", "Vigilar"
        URGENT = "urgent", "Urgente"

    work_order = models.ForeignKey(WorkOrder, on_delete=models.PROTECT, related_name="inspections")
    area = models.CharField(max_length=120)
    result = models.CharField(max_length=8, choices=Result.choices)
    notes = models.TextField(blank=True)
    photo = models.ImageField(upload_to="inspections/%Y/%m/", blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)


class Quote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        SENT = "sent", "Enviada"
        APPROVED = "approved", "Autorizada"
        REJECTED = "rejected", "Rechazada"
        SUPERSEDED = "superseded", "Sustituida"

    work_order = models.ForeignKey(WorkOrder, on_delete=models.PROTECT, related_name="quotes")
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    approval_name = models.CharField(max_length=150, blank=True)
    approval_reference = models.CharField(max_length=200, blank=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=6, decimal_places=4, default=ZERO,
                                   validators=[MinValueValidator(0), MaxValueValidator(1)])
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["work_order", "version"], name="uniq_quote_order_version"),
            models.UniqueConstraint(fields=["work_order"], condition=Q(status="approved"), name="uniq_approved_quote_order"),
        ]


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class Part(models.Model):
    sku = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=30, default="pieza")
    cost = models.DecimalField(**MONEY, default=ZERO)
    sale_price = models.DecimalField(**MONEY, default=ZERO)
    reorder_point = models.DecimalField(**QUANTITY, default=ZERO)
    stock = models.DecimalField(**QUANTITY, default=ZERO)
    reserved = models.DecimalField(**QUANTITY, default=ZERO)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(stock__gte=0), name="part_stock_nonnegative"),
            models.CheckConstraint(condition=Q(reserved__gte=0), name="part_reserved_nonnegative"),
            models.CheckConstraint(condition=Q(stock__gte=models.F("reserved")), name="part_reservation_covered"),
        ]

    def __str__(self):
        return f"{self.sku} · {self.name}"


class QuoteLine(models.Model):
    class Kind(models.TextChoices):
        LABOR = "labor", "Mano de obra"
        PART = "part", "Refacción"
        SERVICE = "service", "Servicio"

    quote = models.ForeignKey(Quote, on_delete=models.PROTECT, related_name="lines")
    description = models.CharField(max_length=250)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    quantity = models.DecimalField(**QUANTITY)
    unit_price = models.DecimalField(**MONEY)
    unit_cost = models.DecimalField(**MONEY, null=True, blank=True)
    part = models.ForeignKey(Part, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name="quote_line_quantity_positive")]


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        ORDERED = "ordered", "Pedida"
        PARTIAL = "partial", "Parcial"
        RECEIVED = "received", "Recibida"
        CANCELLED = "cancelled", "Cancelada"

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(default=timezone.now)


class PurchaseLine(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="lines")
    part = models.ForeignKey(Part, on_delete=models.PROTECT)
    quantity = models.DecimalField(**QUANTITY)
    received = models.DecimalField(**QUANTITY, default=ZERO)
    unit_cost = models.DecimalField(**MONEY)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="purchase_line_quantity_positive"),
            models.CheckConstraint(condition=Q(received__gte=0), name="purchase_line_received_nonnegative"),
            models.CheckConstraint(condition=Q(quantity__gte=models.F("received")), name="purchase_line_received_bounded"),
        ]


class StockMovement(models.Model):
    class Kind(models.TextChoices):
        RECEIPT = "receipt", "Entrada"
        CONSUME = "consume", "Consumo"
        RETURN = "return", "Devolución"
        ADJUSTMENT = "adjustment", "Ajuste"

    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="movements")
    work_order = models.ForeignKey(WorkOrder, null=True, blank=True, on_delete=models.PROTECT)
    purchase_order = models.ForeignKey(PurchaseOrder, null=True, blank=True, on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    quantity = models.DecimalField(**QUANTITY)  # signed: consumption is negative
    unit_cost = models.DecimalField(**MONEY)
    reference = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)


class Reservation(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.PROTECT, related_name="reservations")
    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="reservations")
    quantity = models.DecimalField(**QUANTITY)
    consumed = models.DecimalField(**QUANTITY, default=ZERO)
    returned = models.DecimalField(**QUANTITY, default=ZERO)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["work_order", "part"], name="uniq_order_part_reservation"),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="reservation_quantity_nonnegative"),
            models.CheckConstraint(condition=Q(consumed__gte=0), name="reservation_consumed_nonnegative"),
            models.CheckConstraint(condition=Q(returned__gte=0), name="reservation_returned_nonnegative"),
            models.CheckConstraint(condition=Q(quantity__gte=models.F("consumed")), name="reservation_consumed_bounded"),
            models.CheckConstraint(condition=Q(consumed__gte=models.F("returned")), name="reservation_returned_bounded"),
        ]


class TimeEntry(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.PROTECT, related_name="time_entries")
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)


class QualityCheck(models.Model):
    class Result(models.TextChoices):
        PASS = "pass", "Aprobada"
        FAIL = "fail", "Rechazada"

    work_order = models.ForeignKey(WorkOrder, on_delete=models.PROTECT, related_name="quality_checks")
    result = models.CharField(max_length=4, choices=Result.choices)
    notes = models.TextField(blank=True)
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)


class Invoice(models.Model):
    work_order = models.OneToOneField(WorkOrder, on_delete=models.PROTECT, related_name="invoice")
    number = models.CharField(max_length=50, unique=True)
    subtotal = models.DecimalField(**MONEY)
    tax = models.DecimalField(**MONEY)
    total = models.DecimalField(**MONEY)
    issued_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField()
    voided_at = models.DateTimeField(null=True, blank=True)


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(**MONEY)
    method = models.CharField(max_length=30)
    reference = models.CharField(max_length=120)
    idempotency_key = models.CharField(max_length=128, unique=True)
    received_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="payment_positive")]


class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=80)
    action = models.CharField(max_length=100)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["entity_type", "entity_id", "created_at"])]


class FleetContract(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        ACTIVE = "active", "Activo"
        EXPIRED = "expired", "Vencido"
        CANCELLED = "cancelled", "Cancelado"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="fleet_contracts")
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_fee = models.DecimalField(**MONEY, default=ZERO)
    sla_hours = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    def clean(self):
        super().clean()
        errors = {}
        if self.customer_id and self.customer.kind != Customer.Kind.FLEET:
            errors["customer"] = "El contrato requiere un cliente de flotilla."
        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "El fin del contrato debe ser posterior al inicio."
        if self.monthly_fee is not None and self.monthly_fee < 0:
            errors["monthly_fee"] = "La cuota no puede ser negativa."
        if self.sla_hours is not None and self.sla_hours <= 0:
            errors["sla_hours"] = "Las horas SLA deben ser positivas."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class MaintenancePlan(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Programado"
        COMPLETED = "completed", "Completado"
        CANCELLED = "cancelled", "Cancelado"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="maintenance_plans")
    description = models.CharField(max_length=250)
    due_date = models.DateField(null=True, blank=True)
    due_odometer = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    work_order = models.ForeignKey(WorkOrder, null=True, blank=True, on_delete=models.PROTECT)

    def clean(self):
        super().clean()
        errors = {}
        if self.due_date is None and self.due_odometer is None:
            errors["due_date"] = "Indique fecha o kilometraje de vencimiento."
        if self.work_order_id and self.vehicle_id and self.work_order.vehicle_id != self.vehicle_id:
            errors["work_order"] = "La orden debe corresponder al mismo vehículo."
        if self.status == self.Status.COMPLETED:
            if not self.work_order_id:
                errors["work_order"] = "El mantenimiento completado requiere orden relacionada."
            elif self.work_order.status != WorkOrder.Status.DELIVERED:
                errors["work_order"] = "La orden debe estar entregada antes de completar el plan."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class TowService(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Solicitado"
        ASSIGNED = "assigned", "Asignado"
        EN_ROUTE = "en_route", "En camino"
        ARRIVED = "arrived", "En sitio"
        COMPLETED = "completed", "Completado"
        CANCELLED = "cancelled", "Cancelado"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="tow_services")
    vehicle = models.ForeignKey(Vehicle, null=True, blank=True, on_delete=models.PROTECT)
    origin = models.CharField(max_length=250)
    destination = models.CharField(max_length=250)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED)
    operator_name = models.CharField(max_length=150, blank=True)
    safety_reference = models.CharField(max_length=200, blank=True)
    requested_at = models.DateTimeField(default=timezone.now)
    arrived_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)


class AgentRun(models.Model):
    agent = models.CharField(max_length=80)
    mode = models.CharField(max_length=30, default="rules")
    status = models.CharField(max_length=20, default="pending")
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    evidence = models.JSONField(default=list)
    output = models.JSONField(default=dict)
    error = models.TextField(blank=True)
    source_fingerprint = models.CharField(max_length=128, blank=True)
    model_invoked = models.BooleanField(default=False)


class Proposal(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        ACCEPTED = "accepted", "Aceptada"
        REJECTED = "rejected", "Rechazada"
        STALE = "stale", "Obsoleta"

    run = models.ForeignKey(AgentRun, on_delete=models.PROTECT, related_name="proposals")
    kind = models.CharField(max_length=80)
    title = models.CharField(max_length=250)
    body = models.TextField()
    evidence = models.JSONField(default=list)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=80)
    fingerprint = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    reviewed_at = models.DateTimeField(null=True, blank=True)


class ActionTask(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Abierta"
        IN_PROGRESS = "in_progress", "En curso"
        COMPLETED = "completed", "Completada"
        DISMISSED = "dismissed", "Descartada"

    proposal = models.OneToOneField(Proposal, null=True, blank=True, on_delete=models.PROTECT, related_name="action_task")
    work_order = models.ForeignKey(WorkOrder, null=True, blank=True, on_delete=models.PROTECT, related_name="action_tasks")
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    outcome = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)


# Register the analytical and automation tables with the same Django app/database.
from .analytics_models import AnalyticsSnapshot, AnalyticsRow  # noqa: E402,F401
from .automation_models import AutomationPolicy, AutomationJob, AutomationWorkerState  # noqa: E402,F401
