"""Synthetic seed for explicit demo launches only; never used in live mode."""

import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from workshop import services as svc
from workshop.models import (
    ActionTask, AgentRun, Appointment, Customer, FleetContract, MaintenancePlan,
    Part, Proposal, PurchaseLine, PurchaseOrder, Supplier, Vehicle, WorkOrder,
)


class Command(BaseCommand):
    help = "Crea una demostración sintética en una base MILENIO_MODE=demo vacía"

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Confirmación explícita de datos ficticios")

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["demo"] or settings.MILENIO_MODE != "demo":
            raise CommandError("Se requiere --demo y MILENIO_MODE=demo. Nunca use esta semilla en live.")
        if Customer.objects.exists() or WorkOrder.objects.exists() or Part.objects.exists():
            raise CommandError("La base demo contiene datos; no se mezcla ni duplica una semilla.")

        for name in ("manager", "advisor", "technician", "parts", "finance", "viewer"):
            Group.objects.get_or_create(name=name)
        actor = User.objects.filter(is_superuser=True, is_active=True).first()
        temporary_password = None
        if actor is None:
            temporary_password = secrets.token_urlsafe(20)
            actor = User.objects.create_superuser(username="demo_admin", email="", password=temporary_password)

        individual = Customer.objects.create(name="María Ejemplo · DEMO", phone="5550000101",
                                             email="demo@example.invalid", notes="Dato ficticio")
        fleet = Customer.objects.create(name="Flotilla Ejemplo · DEMO", kind="fleet",
                                        phone="5550000202", email="fleet@example.invalid")
        car = Vehicle.objects.create(customer=individual, plate="DEMO-001", vin="DEMO000000000001",
                                     make="Marca Demo", model="Sedán", year=2020, odometer=48500)
        van = Vehicle.objects.create(customer=fleet, plate="DEMO-002", vin="DEMO000000000002",
                                     make="Marca Demo", model="Van", year=2022, odometer=32000)
        Appointment.objects.create(vehicle=van, scheduled_at=timezone.now() + timedelta(days=3),
                                   reason="Servicio preventivo · demo")
        FleetContract.objects.create(customer=fleet, name="Mantenimiento demo",
                                     start_date=timezone.localdate() - timedelta(days=30),
                                     end_date=timezone.localdate() + timedelta(days=335),
                                     monthly_fee=Decimal("1200.00"), sla_hours=48,
                                     status="active")
        MaintenancePlan.objects.create(vehicle=van, description="Servicio de 35,000 km · demo",
                                       due_date=timezone.localdate() + timedelta(days=20),
                                       due_odometer=35000)

        supplier = Supplier.objects.create(name="Refacciones Ejemplo · DEMO", phone="5550000303")
        brake = Part.objects.create(sku="DEMO-BRK", name="Pastillas demo", cost=Decimal("200.00"),
                                    sale_price=Decimal("350.00"), reorder_point=Decimal("2"))
        filter_part = Part.objects.create(sku="DEMO-FLT", name="Filtro demo", cost=Decimal("90.00"),
                                          sale_price=Decimal("150.00"), reorder_point=Decimal("3"))
        purchase = PurchaseOrder.objects.create(supplier=supplier, number="PO-DEMO-1", status="ordered")
        brake_line = PurchaseLine.objects.create(purchase_order=purchase, part=brake,
                                                 quantity=Decimal("5"), unit_cost=brake.cost)
        filter_line = PurchaseLine.objects.create(purchase_order=purchase, part=filter_part,
                                                  quantity=Decimal("5"), unit_cost=filter_part.cost)
        svc.receive_purchase_line(actor=actor, line=brake_line, quantity=5, reference="ALB-DEMO-1")
        svc.receive_purchase_line(actor=actor, line=filter_line, quantity=5, reference="ALB-DEMO-1")

        completed = svc.create_work_order(actor=actor, vehicle=car, complaint="Revisión de frenos · demo",
                                          number="WO-DEMO-1", odometer=48500)
        svc.transition_work_order(actor=actor, work_order=completed, status="inspection")
        svc.add_inspection(actor=actor, work_order=completed, area="Frenos", result="watch",
                           notes="Ejemplo sintético, sin diagnóstico real")
        svc.transition_work_order(actor=actor, work_order=completed, status="awaiting_approval")
        quote = svc.create_quote(actor=actor, work_order=completed, tax_rate=Decimal("0.16"))
        svc.add_quote_line(actor=actor, quote=quote, description="Mano de obra demo", kind="labor",
                           quantity=Decimal("2"), unit_price=Decimal("300.00"), unit_cost=Decimal("120.00"))
        svc.add_quote_line(actor=actor, quote=quote, description="Pastillas demo", kind="part",
                           quantity=Decimal("1"), unit_price=brake.sale_price,
                           unit_cost=brake.cost, part=brake)
        svc.send_quote(actor=actor, quote=quote)
        svc.approve_quote(actor=actor, quote=quote, approval_name="María Ejemplo · DEMO",
                          approval_reference="APROBACIÓN-FICTICIA-1")
        reservation = svc.reserve_part(actor=actor, work_order=completed, part=brake, quantity=1)
        svc.transition_work_order(actor=actor, work_order=completed, status="in_progress")
        svc.consume_reservation(actor=actor, reservation=reservation, quantity=1)
        svc.add_time_entry(actor=actor, work_order=completed, minutes=95,
                           notes="Tiempo sintético")
        svc.transition_work_order(actor=actor, work_order=completed, status="quality")
        svc.record_quality_check(actor=actor, work_order=completed, result="pass",
                                 notes="Control sintético")
        svc.transition_work_order(actor=actor, work_order=completed, status="ready")
        svc.transition_work_order(actor=actor, work_order=completed, status="delivered")
        invoice = svc.issue_invoice(actor=actor, work_order=completed, number="ADM-DEMO-1",
                                    due_at=timezone.now() + timedelta(days=14))
        svc.record_payment(actor=actor, invoice=invoice, amount="300.00", method="transfer",
                           reference="PAGO-FICTICIO-1", idempotency_key="demo-payment-1")

        open_order = svc.create_work_order(actor=actor, vehicle=van,
                                           complaint="Servicio preventivo · demo",
                                           number="WO-DEMO-2", promised_at=timezone.now() + timedelta(days=5))
        svc.transition_work_order(actor=actor, work_order=open_order, status="inspection")
        svc.add_inspection(actor=actor, work_order=open_order, area="Motor", result="watch")
        svc.transition_work_order(actor=actor, work_order=open_order, status="awaiting_approval")
        pending_quote = svc.create_quote(actor=actor, work_order=open_order)
        svc.add_quote_line(actor=actor, quote=pending_quote, description="Revisión preventiva",
                           kind="labor", quantity=1, unit_price="500.00")
        svc.send_quote(actor=actor, quote=pending_quote)
        ActionTask.objects.create(work_order=open_order, title="Confirmar autorización · DEMO",
                                  description="Tarea sintética de seguimiento interno",
                                  assigned_to=actor, due_at=timezone.now() + timedelta(days=2))
        tow = svc.create_tow_service(actor=actor, customer=individual, vehicle=car,
                                     origin="Origen ficticio", destination="Taller ficticio",
                                     notes="Solicitud sintética, sin despacho")
        # Example run is explicitly a fixture. Its proposal remains stale and cannot be accepted.
        run = AgentRun.objects.create(agent="demo_fixture", mode="demo_fixture", status="completed",
                                      finished_at=timezone.now(), evidence=[{"synthetic": True}],
                                      output={"note": "Ejemplo, no inferencia"},
                                      source_fingerprint="demo-fixture", model_invoked=False)
        Proposal.objects.create(run=run, kind="demo", title="Ejemplo de propuesta no vigente",
                                body="Verifique la fuente antes de usar una propuesta real.",
                                evidence=[{"synthetic": True}], status="stale", entity_type="WorkOrder",
                                entity_id=str(open_order.pk), fingerprint="demo-fixture")

        self.stdout.write(self.style.SUCCESS(
            f"Demo sintética creada: 2 órdenes, 2 clientes, 2 vehículos, 1 grúa ({tow.pk}), "
            "1 comprobante administrativo con pago parcial."
        ))
        if temporary_password:
            actor.set_unusable_password()
            actor.is_active = False
            actor.is_superuser = False
            actor.is_staff = False
            actor.save(update_fields=["password", "is_active", "is_superuser", "is_staff"])
            self.stdout.write("Abre /setup/ para crear tu cuenta de demostración. El actor de siembra queda desactivado.")
