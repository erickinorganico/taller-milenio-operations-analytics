from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from workshop.models import (
    AuditEvent, Customer, FleetContract, Invoice, MaintenancePlan, Part, Payment, PurchaseLine, PurchaseOrder,
    QualityCheck, Quote, QuoteLine, Reservation, StockMovement, Supplier,
    TowService, Vehicle, WorkOrder,
)
from workshop import services as svc


class DomainServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user("manager", password="test-only")
        cls.manager.groups.add(Group.objects.create(name="manager"))
        cls.viewer = User.objects.create_user("viewer", password="test-only")
        cls.viewer.groups.add(Group.objects.create(name="viewer"))
        cls.customer = Customer.objects.create(name="Cliente sintético", phone="000", kind="individual")
        cls.vehicle = Vehicle.objects.create(customer=cls.customer, plate="DEMO-001",
                                             make="Marca", model="Modelo", year=2020)

    def authorized_order(self, with_part=False):
        order = svc.create_work_order(actor=self.manager, vehicle=self.vehicle, complaint="Revisar frenos")
        svc.transition_work_order(actor=self.manager, work_order=order, status="inspection")
        svc.add_inspection(actor=self.manager, work_order=order, area="Frenos", result="watch")
        svc.transition_work_order(actor=self.manager, work_order=order, status="awaiting_approval")
        quote = svc.create_quote(actor=self.manager, work_order=order, tax_rate=Decimal("0.16"))
        svc.add_quote_line(actor=self.manager, quote=quote, description="Servicio", kind="labor",
                           quantity=Decimal("2"), unit_price=Decimal("250.00"),
                           unit_cost=Decimal("100.00"))
        part = None
        if with_part:
            part = Part.objects.create(sku="P-1", name="Pastillas", cost=Decimal("20.00"),
                                       sale_price=Decimal("40.00"))
            svc.adjust_stock(actor=self.manager, part=part, quantity=Decimal("3"), reason="Inventario inicial demo")
            svc.add_quote_line(actor=self.manager, quote=quote, description="Pastillas", kind="part",
                               quantity=Decimal("2"), unit_price=Decimal("40.00"), part=part)
        svc.send_quote(actor=self.manager, quote=quote)
        svc.approve_quote(actor=self.manager, quote=quote, approval_name="Cliente de prueba",
                          approval_reference="Autorización DEMO-1")
        return order, quote, part

    def delivered_order(self):
        order, quote, part = self.authorized_order(with_part=True)
        reservation = svc.reserve_part(actor=self.manager, work_order=order, part=part, quantity=2)
        svc.transition_work_order(actor=self.manager, work_order=order, status="in_progress")
        svc.consume_reservation(actor=self.manager, reservation=reservation, quantity=2)
        svc.add_time_entry(actor=self.manager, work_order=order, minutes=45)
        svc.transition_work_order(actor=self.manager, work_order=order, status="quality")
        svc.record_quality_check(actor=self.manager, work_order=order, result="pass")
        svc.transition_work_order(actor=self.manager, work_order=order, status="ready")
        svc.transition_work_order(actor=self.manager, work_order=order, status="delivered")
        return order, quote, part

    def test_full_journey_stock_invoice_partial_payment_and_audit(self):
        order, quote, part = self.delivered_order()
        invoice = svc.issue_invoice(actor=self.manager, work_order=order, number="ADM-1",
                                    due_at=timezone.now() + timedelta(days=14))
        self.assertEqual(invoice.subtotal, Decimal("580.00"))
        self.assertEqual(invoice.tax, Decimal("92.80"))
        self.assertEqual(invoice.total, Decimal("672.80"))
        part.refresh_from_db()
        self.assertEqual(part.stock, Decimal("1"))
        self.assertEqual(part.reserved, Decimal("0"))
        first = svc.record_payment(actor=self.manager, invoice=invoice, amount="200.00",
                                   method="transfer", reference="REF-1", idempotency_key="idem-1")
        self.assertEqual(first.pk, svc.record_payment(actor=self.manager, invoice=invoice,
                                                      amount="200.00", method="transfer",
                                                      reference="REF-1", idempotency_key="idem-1").pk)
        self.assertEqual(invoice.payments.count(), 1)
        self.assertEqual(invoice.total - first.amount, Decimal("472.80"))
        self.assertTrue(AuditEvent.objects.filter(actor=self.manager, entity_type="Payment",
                                                  entity_id=str(first.pk), action="received").exists())

    def test_no_work_without_named_approval_and_immutable_sent_quote(self):
        order = svc.create_work_order(actor=self.manager, vehicle=self.vehicle, complaint="Ruido")
        with self.assertRaises(ValidationError):
            svc.transition_work_order(actor=self.manager, work_order=order, status="in_progress")
        svc.transition_work_order(actor=self.manager, work_order=order, status="inspection")
        with self.assertRaises(ValidationError):
            svc.transition_work_order(actor=self.manager, work_order=order, status="awaiting_approval")
        svc.add_inspection(actor=self.manager, work_order=order, area="Motor", result="watch")
        svc.transition_work_order(actor=self.manager, work_order=order, status="awaiting_approval")
        quote = svc.create_quote(actor=self.manager, work_order=order)
        svc.add_quote_line(actor=self.manager, quote=quote, description="Diagnóstico", kind="labor",
                           quantity=1, unit_price="100.00")
        svc.send_quote(actor=self.manager, quote=quote)
        with self.assertRaises(ValidationError):
            svc.add_quote_line(actor=self.manager, quote=quote, description="Extra", kind="labor",
                               quantity=1, unit_price="1.00")
        with self.assertRaises(ValidationError):
            svc.approve_quote(actor=self.manager, quote=quote, approval_name="", approval_reference="R")
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quote.Status.SENT)

    def test_part_availability_authorization_consumption_release_and_return(self):
        order, _, part = self.authorized_order(with_part=True)
        with self.assertRaises(ValidationError):
            svc.reserve_part(actor=self.manager, work_order=order, part=part, quantity=3)
        reservation = svc.reserve_part(actor=self.manager, work_order=order, part=part, quantity=2)
        with self.assertRaises(ValidationError):
            svc.adjust_stock(actor=self.manager, part=part, quantity=-2, reason="Conteo")
        svc.transition_work_order(actor=self.manager, work_order=order, status="in_progress")
        svc.consume_reservation(actor=self.manager, reservation=reservation, quantity=1)
        with self.assertRaises(ValidationError):
            svc.consume_reservation(actor=self.manager, reservation=reservation, quantity=2)
        svc.release_reservation(actor=self.manager, reservation=reservation, quantity=1)
        svc.return_consumed_part(actor=self.manager, reservation=reservation, quantity=1)
        with self.assertRaises(ValidationError):
            svc.return_consumed_part(actor=self.manager, reservation=reservation, quantity=1)
        part.refresh_from_db()
        self.assertEqual(part.stock, Decimal("3"))
        self.assertEqual(part.reserved, Decimal("0"))
        self.assertEqual(StockMovement.objects.filter(part=part, kind="consume").count(), 1)

    def test_quality_must_pass_after_latest_rework(self):
        order, _, _ = self.authorized_order()
        svc.transition_work_order(actor=self.manager, work_order=order, status="in_progress")
        svc.transition_work_order(actor=self.manager, work_order=order, status="quality")
        svc.record_quality_check(actor=self.manager, work_order=order, result="pass")
        svc.transition_work_order(actor=self.manager, work_order=order, status="ready")
        svc.transition_work_order(actor=self.manager, work_order=order, status="in_progress")
        svc.transition_work_order(actor=self.manager, work_order=order, status="quality")
        with self.assertRaises(ValidationError):
            svc.transition_work_order(actor=self.manager, work_order=order, status="ready")
        svc.record_quality_check(actor=self.manager, work_order=order, result="fail")
        with self.assertRaises(ValidationError):
            svc.transition_work_order(actor=self.manager, work_order=order, status="ready")
        svc.record_quality_check(actor=self.manager, work_order=order, result="pass")
        svc.transition_work_order(actor=self.manager, work_order=order, status="ready")

    def test_payment_overage_key_conflict_duplicate_invoice_and_role(self):
        order, _, _ = self.delivered_order()
        with self.assertRaises(ValidationError):
            svc.issue_invoice(actor=self.viewer, work_order=order, number="INV-X",
                              due_at=timezone.now() + timedelta(days=1))
        invoice = svc.issue_invoice(actor=self.manager, work_order=order, number="INV-X",
                                    due_at=timezone.now() + timedelta(days=1))
        with self.assertRaises(ValidationError):
            svc.issue_invoice(actor=self.manager, work_order=order, number="INV-X2",
                              due_at=timezone.now() + timedelta(days=1))
        svc.record_payment(actor=self.manager, invoice=invoice, amount="100.00", method="cash",
                           reference="A", idempotency_key="key-A")
        with self.assertRaises(ValidationError):
            svc.record_payment(actor=self.manager, invoice=invoice, amount="101.00", method="cash",
                               reference="A", idempotency_key="key-A")
        with self.assertRaises(ValidationError):
            svc.record_payment(actor=self.manager, invoice=invoice, amount="999.00", method="cash",
                               reference="B", idempotency_key="key-B")
        self.assertEqual(Payment.objects.count(), 1)

    def test_partial_purchase_receipts_and_duplicate_reference(self):
        supplier = Supplier.objects.create(name="Proveedor sintético")
        part = Part.objects.create(sku="Z-1", name="Filtro")
        purchase = svc.create_purchase_order(actor=self.manager, supplier=supplier, number="PO-1")
        line = svc.add_purchase_line(actor=self.manager, purchase_order=purchase, part=part,
                                     quantity=Decimal("5"), unit_cost=Decimal("10.00"))
        with self.assertRaises(ValidationError):
            svc.receive_purchase_line(actor=self.manager, line=line, quantity=2, reference="ALB-0")
        svc.place_purchase_order(actor=self.manager, purchase_order=purchase)
        svc.receive_purchase_line(actor=self.manager, line=line, quantity=2, reference="ALB-1")
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "partial")
        svc.receive_purchase_line(actor=self.manager, line=line, quantity=2, reference="ALB-1")
        self.assertEqual(StockMovement.objects.filter(purchase_order=purchase, kind="receipt").count(), 1)
        with self.assertRaises(ValidationError):
            svc.receive_purchase_line(actor=self.manager, line=line, quantity=3, reference="ALB-1")
        with self.assertRaises(ValidationError):
            svc.receive_purchase_line(actor=self.manager, line=line, quantity=4, reference="ALB-2")
        svc.receive_purchase_line(actor=self.manager, line=line, quantity=3, reference="ALB-2")
        svc.receive_purchase_line(actor=self.manager, line=line, quantity=3, reference="ALB-2")
        purchase.refresh_from_db()
        part.refresh_from_db()
        self.assertEqual(purchase.status, "received")
        self.assertEqual(part.stock, Decimal("5"))

    def test_tow_requires_human_safety_reference(self):
        tow = svc.create_tow_service(actor=self.manager, customer=self.customer,
                                     origin="A", destination="B")
        with self.assertRaises(ValidationError):
            svc.transition_tow_service(actor=self.manager, tow_service=tow,
                                       status="assigned", operator_name="Operador")
        svc.transition_tow_service(actor=self.manager, tow_service=tow, status="assigned",
                                   operator_name="Operador", safety_reference="Humano-1")
        svc.transition_tow_service(actor=self.manager, tow_service=tow, status="en_route")
        svc.transition_tow_service(actor=self.manager, tow_service=tow, status="arrived")
        svc.transition_tow_service(actor=self.manager, tow_service=tow, status="completed")
        tow.refresh_from_db()
        self.assertEqual(tow.status, TowService.Status.COMPLETED)
        self.assertIsNotNone(tow.completed_at)

    def test_technician_requires_assignment_and_cannot_cancel_or_deliver(self):
        technician = User.objects.create_user("tech", password="test-only")
        technician.groups.add(Group.objects.create(name="technician"))
        order = svc.create_work_order(actor=self.manager, vehicle=self.vehicle, complaint="Revisar")
        with self.assertRaises(ValidationError):
            svc.transition_work_order(actor=technician, work_order=order, status="inspection")
        order.assigned_to = technician
        order.save(update_fields=["assigned_to"])
        svc.transition_work_order(actor=technician, work_order=order, status="inspection")
        svc.add_inspection(actor=technician, work_order=order, area="Motor", result="okay")
        with self.assertRaises(ValidationError):
            svc.transition_work_order(actor=technician, work_order=order, status="cancelled")
        svc.transition_work_order(actor=self.manager, work_order=order, status="cancelled")

    def test_fleet_contract_and_maintenance_validation_persist(self):
        fleet = Customer.objects.create(name="Flotilla", kind="fleet")
        van = Vehicle.objects.create(customer=fleet, make="Marca", model="Van")
        with self.assertRaises(ValidationError):
            FleetContract.objects.create(customer=self.customer, name="Mal cliente",
                                         start_date=timezone.localdate(),
                                         end_date=timezone.localdate() + timedelta(days=1),
                                         monthly_fee=Decimal("10"))
        with self.assertRaises(ValidationError):
            FleetContract.objects.create(customer=fleet, name="Mal tiempo",
                                         start_date=timezone.localdate(),
                                         end_date=timezone.localdate() - timedelta(days=1),
                                         monthly_fee=Decimal("-1"))
        with self.assertRaises(ValidationError):
            MaintenancePlan.objects.create(vehicle=van, description="Sin vencimiento")
        order = svc.create_work_order(actor=self.manager, vehicle=self.vehicle, complaint="Otro")
        with self.assertRaises(ValidationError):
            MaintenancePlan.objects.create(vehicle=van, description="Otro vehículo",
                                           due_date=timezone.localdate(), work_order=order)
        with self.assertRaises(ValidationError):
            MaintenancePlan.objects.create(vehicle=self.vehicle, description="Aún abierto",
                                           due_date=timezone.localdate(), work_order=order,
                                           status="completed")


class DemoSeedTests(TestCase):
    @override_settings(MILENIO_MODE="demo")
    def test_seed_is_explicit_synthetic_and_not_repeatable(self):
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command("seed_workshop", stdout=output)
        self.assertEqual(Customer.objects.count(), 0)
        call_command("seed_workshop", "--demo", stdout=output)
        self.assertEqual(WorkOrder.objects.count(), 2)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        seed_actor = User.objects.get(username="demo_admin")
        self.assertFalse(seed_actor.is_active)
        self.assertFalse(seed_actor.is_superuser)
        self.assertFalse(seed_actor.has_usable_password())
        self.assertRedirects(self.client.get("/"), "/setup/", fetch_redirect_response=False)
        with self.assertRaises(CommandError):
            call_command("seed_workshop", "--demo", stdout=output)

    def test_seed_rejects_live_even_with_flag(self):
        with self.assertRaises(CommandError):
            call_command("seed_workshop", "--demo", stdout=StringIO())
