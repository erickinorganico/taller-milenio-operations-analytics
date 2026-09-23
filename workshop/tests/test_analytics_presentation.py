from copy import deepcopy
from unittest import TestCase

from django.test import TestCase as DjangoTestCase

from workshop.analytics import build_analytics_dashboard, refresh_analytics
from workshop.analytics_presentation import build_presentation
from workshop.models import Customer, Vehicle, WorkOrder


class AnalyticsPresentationTests(TestCase):
    def test_sparklines_and_chart_follow_dashboard_trend_with_finite_coordinates(self):
        dashboard = {"filters": {"segment": "all"}, "trend": [
            {"day": "2026-09-20", "opened": 1, "delivered": 0,
             "invoiced_mxn": "1500.50", "payments_mxn": "0"},
            {"day": "2026-09-21", "opened": 2, "delivered": 1,
             "invoiced_mxn": "0", "payments_mxn": "450.25"},
        ], "rankings": {"services": []}}
        result = build_presentation(dashboard, [])

        self.assertEqual(result["cards"]["opened"]["trend_value"], "2")
        self.assertEqual(len(result["cards"]["payments"]["sparkline"]), 2)
        self.assertEqual(result["chart"]["points"][0]["invoiced_mxn"], "1500.50")
        self.assertEqual(result["chart"]["points"][1]["payments_mxn"], "450.25")
        self.assertEqual(result["chart"]["x_ticks"][0]["label"], "sep 20")
        self.assertTrue(result["chart"]["series"]["invoice"]["area"].startswith("48,150"))
        for series in result["chart"]["series"].values():
            self.assertNotIn("NaN", series["points"] + series["area"])
            self.assertNotIn(",,", series["points"] + series["area"])

    def test_current_states_use_frozen_snapshot_rows_and_selected_segment(self):
        frozen = [
            {"mart": "order_journeys", "data": {"status": "in_progress", "customer_kind": "individual"}},
            {"mart": "order_journeys", "data": {"status": "delivered", "customer_kind": "individual"}},
            {"mart": "order_journeys", "data": {"status": "waiting_parts", "customer_kind": "fleet"}},
        ]
        dashboard = {"filters": {"segment": "individual"}, "trend": [], "rankings": {"services": []}}
        frozen_copy = deepcopy(frozen)
        result = build_presentation(dashboard, frozen)

        # A later live-state change does not alter the presentation already built from the cut.
        frozen[0]["data"]["status"] = "delivered"
        self.assertEqual(result["order_states"], [
            {"key": "delivered", "label": "Entregada", "count": 1, "percent": 50.0},
            {"key": "in_progress", "label": "En trabajo", "count": 1, "percent": 50.0},
        ])
        self.assertNotEqual(frozen, frozen_copy)
        self.assertEqual(sum(row["count"] for row in result["order_states"]), 2)

    def test_service_share_denominator_is_authorized_order_service_occurrences(self):
        dashboard = {"filters": {"segment": "all"}, "trend": [], "rankings": {"services": [
            {"description": "Frenos", "authorized_orders": 2},
            {"description": "Afinación", "authorized_orders": 1},
        ]}}
        result = build_presentation(dashboard, {"order_journeys": []})
        self.assertEqual([(row["count"], row["percent"]) for row in result["service_mix"]],
                         [(2, 66.67), (1, 33.33)])
        self.assertEqual(sum(row["percent"] for row in result["service_mix"]), 100.0)

    def test_empty_and_zero_inputs_have_stable_geometry_and_zero_shares(self):
        result = build_presentation({"trend": [{"day": "2026-09-22", "opened": 0,
                                                  "delivered": 0, "invoiced_mxn": "0", "payments_mxn": "0"}],
                                     "filters": {"segment": "fleet"}, "rankings": {"services": []}}, None)
        self.assertEqual(result["chart"]["points"][0]["x"], 398.0)
        self.assertEqual(result["chart"]["points"][0]["invoice_y"], 150.0)
        self.assertEqual(result["chart"]["y_ticks"], [{"y": 150.0, "value": "0", "label": "MXN 0"}])
        self.assertEqual(result["order_states"], [])
        self.assertEqual(result["service_mix"], [])
        empty = build_presentation({}, None)
        self.assertEqual(empty["chart"]["points"], [])
        self.assertEqual(empty["cards"]["opened"]["sparkline"], [])


class AnalyticsPresentationSnapshotTests(DjangoTestCase):
    def test_status_breakdown_reads_frozen_snapshot_and_filters_segment(self):
        individual = Customer.objects.create(name="Individual snapshot", kind="individual")
        fleet = Customer.objects.create(name="Fleet snapshot", kind="fleet")
        individual_vehicle = Vehicle.objects.create(customer=individual, make="A", model="One")
        fleet_vehicle = Vehicle.objects.create(customer=fleet, make="B", model="Two")
        active = WorkOrder.objects.create(vehicle=individual_vehicle, number="PRES-1", complaint="Test",
                                          status="in_progress")
        delivered = WorkOrder.objects.create(vehicle=individual_vehicle, number="PRES-2", complaint="Test",
                                             status="delivered")
        fleet_order = WorkOrder.objects.create(vehicle=fleet_vehicle, number="PRES-3", complaint="Test",
                                               status="waiting_parts")
        snapshot = refresh_analytics()
        dashboard = build_analytics_dashboard(snapshot=snapshot, segment="individual")

        # Live edits after refresh must not change status counts derived from this cut.
        active.status = "delivered"
        active.save(update_fields=["status"])
        fleet_order.status = "ready"
        fleet_order.save(update_fields=["status"])
        cut_rows = list(snapshot.rows.values("mart", "data"))
        result = build_presentation(dashboard, cut_rows)

        self.assertEqual(result["order_states"], [
            {"key": "delivered", "label": "Entregada", "count": 1, "percent": 50.0},
            {"key": "in_progress", "label": "En trabajo", "count": 1, "percent": 50.0},
        ])
        self.assertEqual(result["order_states_as_of"], dashboard["snapshot"]["recorded_at"])
        self.assertTrue(result["order_states_scope"].startswith("Estado actual"))
        self.assertNotEqual(active.status, "in_progress")
        self.assertEqual(delivered.status, "delivered")
