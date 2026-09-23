from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Sum
from django.test import TestCase, override_settings

from workshop.analytics import build_analytics_dashboard
from workshop.models import (
    AnalyticsSnapshot, AuditEvent, Customer, Invoice, Part, PurchaseLine,
    StockMovement, WorkOrder,
)


class AnalyticsDemoSeedTests(TestCase):
    def setUp(self):
        self.out = StringIO()

    def seed(self):
        call_command("seed_analytics_demo", demo=True, stdout=self.out)

    @override_settings(MILENIO_MODE="live")
    def test_live_mode_and_missing_explicit_flag_are_rejected(self):
        get_user_model().objects.create_superuser("demo-guard", password="test-only", email="")
        with self.assertRaises(CommandError):
            self.seed()
        with override_settings(MILENIO_MODE="demo"):
            with self.assertRaises(CommandError):
                call_command("seed_analytics_demo", stdout=self.out)
        self.assertEqual(WorkOrder.objects.count(), 0)
        self.assertEqual(AnalyticsSnapshot.objects.count(), 0)

    @override_settings(MILENIO_MODE="demo")
    def test_requires_existing_active_superuser(self):
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(Customer.objects.count(), 0)

    @override_settings(MILENIO_MODE="demo")
    def test_fresh_launcher_seed_includes_v6_and_disables_temporary_actor(self):
        call_command("seed_workshop", demo=True, stdout=self.out)
        self.assertEqual(WorkOrder.objects.count(), 38)
        self.assertEqual(WorkOrder.objects.filter(number__startswith="WO-V6DEMO-").count(), 36)
        self.assertEqual(AnalyticsSnapshot.objects.count(), 1)
        dashboard = build_analytics_dashboard()
        self.assertGreater(int(dashboard["kpis"]["opened"]["value"]), 0)
        self.assertGreater(int(dashboard["kpis"]["opened"]["previous"]), 0)
        self.assertGreaterEqual(len(dashboard["rankings"]["services"]), 5)
        actor = get_user_model().objects.get(username="demo_admin")
        self.assertFalse(actor.is_active)
        self.assertFalse(actor.is_superuser)
        self.assertFalse(actor.has_usable_password())
        with self.assertRaises(CommandError):
            call_command("seed_workshop", demo=True, stdout=self.out)
        self.assertEqual(WorkOrder.objects.count(), 38)

    @override_settings(MILENIO_MODE="demo")
    def test_idempotent_scenario_preserves_existing_demo_and_reconciles_stock(self):
        get_user_model().objects.create_superuser("demo-analytics", password="test-only", email="")
        existing = Customer.objects.create(name="Existing demo record")
        self.seed()
        first_snapshot = AnalyticsSnapshot.objects.latest("pk")
        self.assertEqual(WorkOrder.objects.filter(number__startswith="WO-V6DEMO-").count(), 36)
        self.assertEqual(Invoice.objects.filter(number__startswith="ADM-V6DEMO-").count(), 29)
        self.assertEqual(Part.objects.filter(sku__startswith="V6DEMO-").count(), 4)
        self.assertTrue(Customer.objects.filter(pk=existing.pk).exists())
        for part in Part.objects.filter(sku__startswith="V6DEMO-"):
            movement_sum = (StockMovement.objects.filter(part=part).aggregate(value=Sum("quantity"))["value"]
                            or Decimal("0"))
            self.assertEqual(part.stock, movement_sum)
            self.assertEqual(PurchaseLine.objects.get(part=part).received, Decimal("100.000"))
        for invoice in Invoice.objects.filter(number__startswith="ADM-V6DEMO-"):
            self.assertEqual(invoice.total, invoice.subtotal + invoice.tax)
            self.assertEqual(invoice.tax, (invoice.subtotal * Decimal("0.16")).quantize(Decimal("0.01")))
        self.seed()
        self.assertEqual(WorkOrder.objects.filter(number__startswith="WO-V6DEMO-").count(), 36)
        self.assertEqual(AnalyticsSnapshot.objects.count(), 1)
        self.assertEqual(AnalyticsSnapshot.objects.latest("pk").pk, first_snapshot.pk)
        self.assertIn("sin cambios", self.out.getvalue())

    @override_settings(MILENIO_MODE="demo")
    def test_multi_period_dashboard_has_real_movement_and_audited_journeys(self):
        get_user_model().objects.create_superuser("demo-analytics", password="test-only", email="")
        self.seed()
        snapshot = AnalyticsSnapshot.objects.latest("pk")
        dashboard = build_analytics_dashboard(snapshot=snapshot)
        self.assertGreater(Decimal(dashboard["kpis"]["opened"]["value"]), 0)
        self.assertGreater(Decimal(dashboard["kpis"]["opened"]["previous"]), 0)
        self.assertGreater(Decimal(dashboard["kpis"]["delivered"]["value"]), 0)
        self.assertGreater(Decimal(dashboard["kpis"]["invoiced"]["value"]), 0)
        self.assertGreater(Decimal(dashboard["kpis"]["payments"]["value"]), 0)
        self.assertGreater(Decimal(dashboard["kpis"]["open_balance_current"]["value"]), 0)
        self.assertGreater(dashboard["kpis"]["wip_current"]["value"], 0)
        self.assertGreater(dashboard["kpis"]["median_delivery_hours"]["value"], 0)
        self.assertGreater(dashboard["kpis"]["median_parts_wait_hours"]["value"], 0)
        self.assertEqual(len(dashboard["rankings"]["parts"]), 4)
        self.assertEqual(len(dashboard["rankings"]["services"]), 5)
        self.assertEqual(AuditEvent.objects.filter(entity_type="WorkOrder", action="status_changed",
                                                   after__status="delivered").count(), 29)
        individual = build_analytics_dashboard(snapshot=snapshot, segment="individual")
        fleet = build_analytics_dashboard(snapshot=snapshot, segment="fleet")
        self.assertGreater(int(individual["kpis"]["opened"]["value"]), 0)
        self.assertGreater(int(fleet["kpis"]["opened"]["value"]), 0)
