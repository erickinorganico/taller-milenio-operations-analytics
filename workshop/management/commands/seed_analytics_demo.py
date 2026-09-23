"""Add a dated, explicitly fictitious analytics scenario to an existing demo.

This command writes only to MILENIO_MODE=demo with --demo. It intentionally
keeps the original seed_workshop records and never creates login credentials.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from workshop import analytics
from workshop.models import (
    AuditEvent, Customer, Invoice, Part, Payment, PurchaseLine, PurchaseOrder,
    Quote, QuoteLine, StockMovement, Supplier, Vehicle, WorkOrder,
)


ORDER_COUNT = 36
SERVICES = (
    ("Diagnóstico eléctrico", "service", Decimal("450.00"), Decimal("190.00")),
    ("Servicio de frenos", "service", Decimal("620.00"), Decimal("240.00")),
    ("Afinación preventiva", "service", Decimal("720.00"), Decimal("310.00")),
    ("Cambio de aceite", "labor", Decimal("360.00"), Decimal("150.00")),
    ("Revisión de suspensión", "labor", Decimal("540.00"), Decimal("230.00")),
)
PARTS = (
    ("V6DEMO-FLT", "Filtro de aceite V6DEMO", "pieza", "95.00", "175.00"),
    ("V6DEMO-BRK", "Pastillas de freno V6DEMO", "juego", "280.00", "490.00"),
    ("V6DEMO-OIL", "Aceite V6DEMO", "litro", "85.00", "155.00"),
    ("V6DEMO-SUS", "Buje de suspensión V6DEMO", "pieza", "170.00", "310.00"),
)


def _at(day, hour=12):
    return timezone.make_aware(datetime.combine(day, time(hour, 0)), timezone.get_current_timezone())


def _audit(actor, order, at, before, after):
    AuditEvent.objects.create(actor=actor, entity_type="WorkOrder", entity_id=str(order.pk),
                              action="status_changed", before={"status": before},
                              after={"status": after}, created_at=at)


class Command(BaseCommand):
    help = "Añade 36 órdenes ficticias V6DEMO con hechos fechados para el dashboard demo"

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Confirma explícitamente la semilla ficticia")

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["demo"] or settings.MILENIO_MODE != "demo":
            raise CommandError("Se requiere --demo y MILENIO_MODE=demo; esta semilla nunca corre en live.")

        expected = {f"WO-V6DEMO-{index:02d}" for index in range(1, ORDER_COUNT + 1)}
        existing = set(WorkOrder.objects.filter(number__startswith="WO-V6DEMO-").values_list("number", flat=True))
        if existing:
            if (existing == expected and Part.objects.filter(sku__startswith="V6DEMO-").count() == len(PARTS)
                    and Invoice.objects.filter(number__startswith="ADM-V6DEMO-").count() == 29):
                self.stdout.write("La semilla analítica V6DEMO ya existe; sin cambios.")
                return
            raise CommandError("Se encontraron datos V6DEMO incompletos; no se sobrescriben ni duplican.")
        if (Customer.objects.filter(name__startswith="V6DEMO").exists()
                or Part.objects.filter(sku__startswith="V6DEMO-").exists()
                or PurchaseOrder.objects.filter(number="PO-V6DEMO-1").exists()):
            raise CommandError("Hay identificadores V6DEMO parciales; revise la demo antes de sembrar.")

        actor = get_user_model().objects.filter(is_active=True, is_superuser=True).order_by("pk").first()
        if actor is None:
            raise CommandError("Se requiere un superusuario activo existente; esta semilla no crea credenciales.")

        today = timezone.localdate()
        individual = Customer.objects.create(name="V6DEMO Particular ficticio", kind="individual")
        fleet = Customer.objects.create(name="V6DEMO Flotilla ficticia", kind="fleet")
        vehicles = [
            Vehicle.objects.create(customer=individual, plate="V6DEMO-I1", make="Demo", model="Sedán"),
            Vehicle.objects.create(customer=fleet, plate="V6DEMO-F1", make="Demo", model="Van"),
            Vehicle.objects.create(customer=individual, plate="V6DEMO-I2", make="Demo", model="Hatchback"),
            Vehicle.objects.create(customer=fleet, plate="V6DEMO-F2", make="Demo", model="Pickup"),
        ]
        supplier = Supplier.objects.create(name="V6DEMO Proveedor ficticio")
        purchase = PurchaseOrder.objects.create(supplier=supplier, number="PO-V6DEMO-1",
                                                status=PurchaseOrder.Status.RECEIVED,
                                                created_at=_at(today - timedelta(days=65)))
        parts = []
        for sku, name, unit, cost, sale_price in PARTS:
            part = Part.objects.create(sku=sku, name=name, unit=unit, cost=Decimal(cost),
                                       sale_price=Decimal(sale_price), stock=Decimal("100.000"),
                                       reorder_point=Decimal("8.000"))
            PurchaseLine.objects.create(purchase_order=purchase, part=part, quantity=Decimal("100.000"),
                                        received=Decimal("100.000"), unit_cost=part.cost)
            StockMovement.objects.create(part=part, purchase_order=purchase,
                                         kind=StockMovement.Kind.RECEIPT, quantity=Decimal("100.000"),
                                         unit_cost=part.cost, reference="V6DEMO recepción ficticia",
                                         created_by=actor, created_at=_at(today - timedelta(days=64)))
            parts.append(part)

        for index in range(ORDER_COUNT):
            age = 59 - round(index * 58 / (ORDER_COUNT - 1))
            opened = _at(today - timedelta(days=age), 9)
            number = f"WO-V6DEMO-{index + 1:02d}"
            delivered = index < 29
            vehicle = vehicles[index % len(vehicles)]
            promised = opened + timedelta(days=5 if index % 3 == 0 else 8)
            status = (WorkOrder.Status.DELIVERED if delivered else
                      WorkOrder.Status.WAITING_PARTS if index < 33 else
                      WorkOrder.Status.READY if index == 34 else WorkOrder.Status.IN_PROGRESS)
            order = WorkOrder.objects.create(vehicle=vehicle, number=number, status=status,
                                             complaint="Servicio ficticio V6DEMO",
                                             promised_at=promised, created_at=opened)

            timeline = [
                (1, "intake", "inspection"),
                (2, "inspection", "awaiting_approval"),
                (3, "awaiting_approval", "approved"),
                (4, "approved", "in_progress"),
            ]
            if delivered:
                if index % 3 == 0:
                    timeline.extend([(5, "in_progress", "waiting_parts"),
                                     (14, "waiting_parts", "in_progress")])
                timeline.extend([(24, "in_progress", "quality"), (28, "quality", "ready"),
                                 (48, "ready", "delivered")])
            elif status == WorkOrder.Status.WAITING_PARTS:
                timeline.append((5, "in_progress", "waiting_parts"))
            elif status == WorkOrder.Status.READY:
                timeline.extend([(24, "in_progress", "quality"), (28, "quality", "ready")])
            for hours, before, after in timeline:
                _audit(actor, order, opened + timedelta(hours=hours), before, after)

            service_name, service_kind, service_price, service_cost = SERVICES[index % len(SERVICES)]
            if index % 4 == 0:
                prior = Quote.objects.create(work_order=order, version=1,
                                             status=Quote.Status.SUPERSEDED,
                                             created_at=opened + timedelta(hours=2))
                QuoteLine.objects.create(quote=prior, description="V6DEMO propuesta reemplazada",
                                         kind=QuoteLine.Kind.SERVICE, quantity=Decimal("1.000"),
                                         unit_price=Decimal("999.00"))
                version = 2
            else:
                version = 1
            quote = Quote.objects.create(work_order=order, version=version, status=Quote.Status.APPROVED,
                                         tax_rate=Decimal("0.1600"), authorized_at=opened + timedelta(hours=3),
                                         created_at=opened + timedelta(hours=2))
            # Whitespace and casing vary while preserving the exact same service meaning.
            description = service_name.upper() if index % 5 == 0 else f"  {service_name}  " if index % 7 == 0 else service_name
            service_qty = Decimal("2.000") if index % 6 == 0 else Decimal("1.000")
            QuoteLine.objects.create(quote=quote, description=description, kind=service_kind,
                                     quantity=service_qty, unit_price=service_price,
                                     unit_cost=service_cost if index % 9 else None)
            part = parts[index % len(parts)]
            part_qty = Decimal("2.000") if index % 7 == 0 else Decimal("1.000")
            QuoteLine.objects.create(quote=quote, description=part.name, kind=QuoteLine.Kind.PART,
                                     quantity=part_qty, unit_price=part.sale_price,
                                     unit_cost=part.cost, part=part)

            consumed = part_qty if delivered or status != WorkOrder.Status.READY else Decimal("0.000")
            if consumed:
                StockMovement.objects.create(part=part, work_order=order, kind=StockMovement.Kind.CONSUME,
                                             quantity=-consumed, unit_cost=part.cost,
                                             reference="V6DEMO consumo ficticio", created_by=actor,
                                             created_at=opened + timedelta(hours=6))
                part.stock -= consumed
                if index % 8 == 0:
                    returned = Decimal("1.000")
                    StockMovement.objects.create(part=part, work_order=order, kind=StockMovement.Kind.RETURN,
                                                 quantity=returned, unit_cost=part.cost,
                                                 reference="V6DEMO devolución ficticia", created_by=actor,
                                                 created_at=opened + timedelta(hours=18))
                    part.stock += returned
                part.save(update_fields=["stock"])

            if delivered:
                subtotal = service_qty * service_price + part_qty * part.sale_price
                tax = (subtotal * quote.tax_rate).quantize(Decimal("0.01"))
                issued_at = opened + timedelta(days=3)
                invoice = Invoice.objects.create(work_order=order, number=f"ADM-V6DEMO-{index + 1:02d}",
                                                 subtotal=subtotal, tax=tax, total=subtotal + tax,
                                                 issued_at=issued_at, due_at=issued_at + timedelta(days=14))
                if index % 5 != 0:
                    amount = (invoice.total * (Decimal("0.50") if index % 4 == 0 else Decimal("1.00"))).quantize(Decimal("0.01"))
                    Payment.objects.create(invoice=invoice, amount=amount, method="transfer",
                                           reference=f"V6DEMO-PAGO-{index + 1:02d}",
                                           idempotency_key=f"v6demo-payment-{index + 1:02d}",
                                           received_at=issued_at + timedelta(days=2 + index % 3), created_by=actor)

        snapshot = analytics.refresh_analytics(actor=actor, trigger="demo_seed")
        self.stdout.write(self.style.SUCCESS(
            f"V6DEMO: {ORDER_COUNT} órdenes ficticias, {len(PARTS)} refacciones, "
            f"29 comprobantes; corte analítico #{snapshot.pk}."
        ))
