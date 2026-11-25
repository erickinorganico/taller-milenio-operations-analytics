from datetime import datetime
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone

from workshop import models as m


class OrderFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_superuser("filter-manager")
        cls.tech = User.objects.create_user("filter-tech", first_name="Técnico de prueba")
        cls.other = User.objects.create_user("filter-other", first_name="Otra persona privada")
        cls.tech.groups.add(Group.objects.create(name="technician"))
        customer = m.Customer.objects.create(name="Cliente sintético")
        cls.vehicle = m.Vehicle.objects.create(customer=customer, plate="FILTER01")

    def setUp(self):
        self.client.force_login(self.manager)

    def order(self, **values):
        defaults = dict(vehicle=self.vehicle, number=f"FILTER-{m.WorkOrder.objects.count()}", assigned_to=self.tech)
        return m.WorkOrder.objects.create(**{**defaults, **values})

    def ids(self, **params):
        return [order.pk for order in self.client.get("/orders/", params).context["page"]]

    def test_owner_stage_search_and_reception_dates_combine(self):
        zone = ZoneInfo("America/Tijuana")
        target = self.order(status="in_progress", created_at=datetime(2026, 10, 13, 23, 59, tzinfo=zone))
        self.order(status="ready", created_at=target.created_at)
        self.order(assigned_to=self.other, status="in_progress", created_at=target.created_at)
        self.order(status="in_progress", created_at=datetime(2026, 10, 14, 0, 0, tzinfo=zone))
        with timezone.override(zone):
            self.assertEqual(self.ids(q="FILTER01", owner=str(self.tech.pk), status="in_progress", start="2026-10-13", end="2026-10-13"), [target.pk])

    def test_promised_date_range_does_not_use_reception_date_or_undated_orders(self):
        zone = ZoneInfo("America/Tijuana")
        target = self.order(promised_at=datetime(2026, 10, 13, 23, 59, tzinfo=zone), created_at=datetime(2026, 10, 1, tzinfo=zone))
        self.order(created_at=target.promised_at)
        self.order(promised_at=datetime(2026, 10, 14, tzinfo=zone))
        with timezone.override(zone):
            self.assertEqual(self.ids(date_field="promised", start="2026-10-13", end="2026-10-13"), [target.pk])

    def test_attention_and_owner_choices_preserve_existing_open_order_rules(self):
        target = self.order(assigned_to=None)
        self.order(assigned_to=None, status="delivered")
        self.order()
        self.assertEqual(self.ids(owner="unassigned", attention="unassigned"), [target.pk])

    def test_technician_cannot_expand_visibility_with_owner_or_date_filters(self):
        target = self.order()
        self.order(assigned_to=self.other)
        self.client.force_login(self.tech)
        response = self.client.get("/orders/")
        self.assertEqual([order.pk for order in response.context["page"]], [target.pk])
        self.assertNotContains(response, self.other.first_name)
        denied = self.client.get("/orders/", {"owner": str(self.other.pk)})
        self.assertEqual(denied.context["page"].paginator.count, 0)
        self.assertTrue(denied.context["list_filter_form"].errors)

    def test_page_links_preserve_all_active_filters_and_sort_ties_stably(self):
        zone = ZoneInfo("America/Tijuana")
        same_time = datetime(2026, 10, 13, 10, tzinfo=zone)
        orders = [self.order(status="ready", created_at=same_time) for _ in range(27)]
        response = self.client.get("/orders/", {"q": "FILTER", "owner": str(self.tech.pk), "status": "ready", "start": "2026-10-13", "end": "2026-10-13", "page": "2"})
        self.assertEqual([order.pk for order in response.context["page"]], [orders[1].pk, orders[0].pk])
        params = parse_qs(response.context["filter_query"])
        self.assertEqual(params["owner"], [str(self.tech.pk)])
        self.assertEqual(params["start"], ["2026-10-13"])
        self.assertContains(response, "q=FILTER&amp;page=1")

    def test_invalid_filter_is_visible_without_broadening_results(self):
        self.order()
        for params in ({"start": "not-a-date"}, {"date_field": "arbitrary"}, {"owner": "invalid"}, {"status": "invalid"}):
            with self.subTest(params=params):
                response = self.client.get("/orders/", params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["count"], 0)
                self.assertTrue(response.context["list_filter_form"].errors)

    def test_mine_still_works_and_read_does_not_change_orders(self):
        own = self.order(assigned_to=self.manager)
        self.order()
        before = list(m.WorkOrder.objects.values())
        self.assertEqual(self.ids(mine="1"), [own.pk])
        self.assertEqual(list(m.WorkOrder.objects.values()), before)
