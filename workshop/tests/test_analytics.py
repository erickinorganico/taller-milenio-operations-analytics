from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from workshop.analytics import build_analytics_dashboard, refresh_analytics
from workshop.models import (
    AnalyticsRow, AnalyticsSnapshot, AuditEvent, Customer, Invoice, Part, Payment,
    Quote, QuoteLine, StockMovement, Vehicle, WorkOrder,
)


class LiveAnalyticsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("analytics-test", password="test-only")
        self.individual = Customer.objects.create(name="Individual", kind="individual")
        self.fleet = Customer.objects.create(name="Fleet", kind="fleet")
        self.car = Vehicle.objects.create(customer=self.individual, make="A", model="B")
        self.van = Vehicle.objects.create(customer=self.fleet, make="C", model="D")
        self.now = timezone.now()

    def order(self, number, *, vehicle=None, created_at=None, status="delivered", promised_at=None):
        return WorkOrder.objects.create(
            vehicle=vehicle or self.car, number=number, complaint="Test", status=status,
            created_at=created_at or self.now, promised_at=promised_at,
        )

    def quote_line(self, order, *, version, status="approved", description="Service", kind="service",
                   quantity="1", price="100", authorized_at=None):
        quote = Quote.objects.create(work_order=order, version=version, status=status,
                                     authorized_at=authorized_at or self.now)
        QuoteLine.objects.create(quote=quote, kind=kind, description=description,
                                 quantity=Decimal(quantity), unit_price=Decimal(price))
        return quote

    def invoice(self, order, number, *, issued_at=None, voided_at=None, total="100"):
        return Invoice.objects.create(work_order=order, number=number, subtotal=Decimal(total),
                                      tax=Decimal("0"), total=Decimal(total),
                                      issued_at=issued_at or self.now,
                                      due_at=self.now + timedelta(days=10), voided_at=voided_at)

    def test_date_boundaries_equal_previous_period_and_invalid_ranges(self):
        day = timezone.localdate()
        old = self.order("OLD", created_at=self.now - timedelta(days=1))
        current = self.order("NOW", created_at=self.now)
        snapshot = refresh_analytics()
        dashboard = build_analytics_dashboard(start=day.isoformat(), end=day.isoformat(), snapshot=snapshot)
        self.assertEqual(dashboard["kpis"]["opened"]["value"], "1")
        self.assertEqual(dashboard["kpis"]["opened"]["previous"], "1")
        self.assertEqual(dashboard["filters"]["previous_end"], (day - timedelta(days=1)).isoformat())
        self.assertEqual(dashboard["kpis"]["delivered"]["value"], "0")  # status alone is not an audit event
        for start, end in [((day + timedelta(days=1)).isoformat(), None),
                           (day.isoformat(), (day + timedelta(days=1)).isoformat()),
                           ((day - timedelta(days=400)).isoformat(), day.isoformat()),
                           (day.isoformat(), (day - timedelta(days=1)).isoformat()),
                           ("bad", day.isoformat())]:
            with self.subTest(start=start, end=end), self.assertRaises(ValidationError):
                build_analytics_dashboard(start=start, end=end, snapshot=snapshot)

    def test_latest_approved_quote_exact_text_and_billed_association(self):
        order = self.order("Q1")
        self.quote_line(order, version=1, status="superseded", description="  Brake   Check ", quantity="4", price="10")
        self.quote_line(order, version=2, status="rejected", description="Rejected", price="99")
        self.quote_line(order, version=3, description="brake check", quantity="2", price="20")
        other = self.order("Q2")
        self.quote_line(other, version=1, description="BRAKE CHECK", quantity="1", price="30")
        self.invoice(order, "INV-Q1")
        dashboard = build_analytics_dashboard(snapshot=refresh_analytics())
        ranking = dashboard["rankings"]["services"]
        self.assertEqual(len(ranking), 1)
        self.assertEqual(ranking[0]["authorized_quantity"], "3.000")
        self.assertEqual(ranking[0]["authorized_orders"], 2)
        self.assertEqual(ranking[0]["authorized_value_mxn"], "70.00000")
        self.assertEqual(ranking[0]["billed_orders"], 1)
        self.assertEqual(ranking[0]["billed_quote_value_mxn"], "40.00000")
        self.assertEqual(len(AnalyticsRow.objects.filter(mart="service_lines")), 2)

    def test_part_usage_is_signed_net_of_returns_and_excludes_receipts(self):
        order = self.order("P1")
        part = Part.objects.create(sku="SKU-1", name="Filter", cost=Decimal("8"))
        for kind, qty in [("consume", "-3"), ("return", "1"), ("receipt", "10"), ("adjustment", "5")]:
            StockMovement.objects.create(part=part, work_order=order if kind in ("consume", "return") else None,
                kind=kind, quantity=Decimal(qty), unit_cost=Decimal("8"), created_by=self.user,
                created_at=self.now)
        dashboard = build_analytics_dashboard(snapshot=refresh_analytics())
        row = dashboard["rankings"]["parts"][0]
        self.assertEqual(row["net_quantity"], "2.000")
        self.assertEqual(row["net_cost_mxn"], "16.00000")
        self.assertEqual(row["orders"], 1)
        self.assertEqual(len(row["movement_ids"]), 2)
        self.assertEqual(AnalyticsRow.objects.filter(mart="part_usage").count(), 2)

    def test_service_rank_uses_distinct_orders_before_quote_value(self):
        for index in range(2):
            self.quote_line(self.order(f"COMMON-{index}"), version=1,
                            description="Common service", price="10")
        self.quote_line(self.order("EXPENSIVE"), version=1,
                        description="Expensive service", price="1000")
        rank = build_analytics_dashboard(snapshot=refresh_analytics())["rankings"]["services"]
        self.assertEqual(rank[0]["description"], "common service")
        self.assertEqual(rank[0]["authorized_orders"], 2)
        self.assertEqual(rank[1]["authorized_orders"], 1)

    def test_invoice_and_payment_use_separate_dates_and_voids_are_excluded(self):
        order = self.order("F1")
        day = timezone.localdate()
        old_invoice = self.invoice(order, "INV-OLD", issued_at=self.now - timedelta(days=1))
        Payment.objects.create(invoice=old_invoice, amount=Decimal("40"), method="cash", reference="R",
                               idempotency_key="analytics-payment", received_at=self.now, created_by=self.user)
        Payment.objects.create(invoice=old_invoice, amount=Decimal("10"), method="cash", reference="FUTURE",
                               idempotency_key="analytics-future-payment",
                               received_at=self.now + timedelta(days=1), created_by=self.user)
        void_order = self.order("F2")
        self.invoice(void_order, "INV-VOID", voided_at=self.now, total="250")
        dashboard = build_analytics_dashboard(start=day, end=day, snapshot=refresh_analytics())
        self.assertEqual(dashboard["kpis"]["invoiced"]["value"], "0")
        self.assertEqual(dashboard["kpis"]["invoiced"]["previous"], "100.00")
        self.assertEqual(dashboard["kpis"]["payments"]["value"], "40.00")
        self.assertEqual(dashboard["kpis"]["open_balance_current"]["value"], "60.00")
        self.assertEqual(dashboard["coverage"]["void_invoices_excluded"], 1)

    def test_snapshot_is_immutable_and_references_stable_after_source_mutation(self):
        order = self.order("S1", status="in_progress")
        first = refresh_analytics(actor=self.user, trigger="manual")
        first_dashboard = build_analytics_dashboard(snapshot=first)
        first_row = AnalyticsRow.objects.get(snapshot=first, mart="order_journeys")
        order.status = "delivered"
        order.number = "CHANGED"
        order.save(update_fields=["status", "number"])
        second = refresh_analytics(trigger="scheduled")
        self.assertNotEqual(first.source_fingerprint, second.source_fingerprint)
        self.assertEqual(first_row.data["number"], "S1")
        self.assertEqual(build_analytics_dashboard(snapshot=first)["kpis"]["wip_current"]["value"], 1)
        self.assertEqual(build_analytics_dashboard(snapshot=second)["kpis"]["wip_current"]["value"], 0)
        self.assertEqual(first_row.data["source_refs"][0], {"model": "WorkOrder", "id": order.pk})
        self.assertEqual(first.recorded_at.isoformat(), first_dashboard["snapshot"]["recorded_at"])

    def test_audited_delivery_wait_and_customer_segmentation(self):
        prior = self.now - timedelta(days=2)
        order = self.order("J1", created_at=prior)
        other = self.order("J2", vehicle=self.van)
        AuditEvent.objects.create(actor=self.user, entity_type="WorkOrder", entity_id=str(order.pk),
                                  action="status_changed", before={"status": "in_progress"},
                                  after={"status": "waiting_parts"}, created_at=prior + timedelta(hours=2))
        AuditEvent.objects.create(actor=self.user, entity_type="WorkOrder", entity_id=str(order.pk),
                                  action="status_changed", before={"status": "waiting_parts"},
                                  after={"status": "ready"}, created_at=prior + timedelta(hours=5))
        AuditEvent.objects.create(actor=self.user, entity_type="WorkOrder", entity_id=str(order.pk),
                                  action="status_changed", before={"status": "ready"},
                                  after={"status": "delivered"}, created_at=self.now)
        snapshot = refresh_analytics()
        individual = build_analytics_dashboard(snapshot=snapshot, segment="individual")
        fleet = build_analytics_dashboard(snapshot=snapshot, segment="fleet")
        self.assertEqual(individual["kpis"]["median_delivery_hours"]["value"], 48.0)
        self.assertEqual(individual["kpis"]["median_parts_wait_hours"]["value"], 3.0)
        self.assertEqual(fleet["kpis"]["median_delivery_hours"]["value"], None)
        self.assertEqual(fleet["coverage"]["delivered_without_audit"], 1)
        self.assertEqual(individual["kpis"]["opened"]["value"], "1")
        self.assertEqual(fleet["kpis"]["opened"]["value"], "1")

    def test_missing_data_stays_explicit(self):
        self.assertEqual(build_analytics_dashboard()["status"], "no_snapshot")
        dashboard = build_analytics_dashboard(snapshot=refresh_analytics())
        self.assertIsNone(dashboard["kpis"]["median_delivery_hours"]["value"])
        self.assertIsNone(dashboard["kpis"]["opened"]["change_percent"])
        self.assertEqual(dashboard["kpis"]["opened"]["comparison_status"], "unknown")
        self.assertEqual(dashboard["snapshot"]["source_counts"]["WorkOrder"], 0)
        self.assertEqual(len(dashboard["marts"]), 6)
