"""Guard against queries growing for each visible service or navigation item."""
from django.contrib.auth.models import Group, User
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext

from workshop import models as m
from workshop.access import CAPABILITIES, can, navigation
from workshop.views import data_table


class PagePerformanceTests(TestCase):
    def test_services_page_queries_do_not_grow_with_the_number_of_rows(self):
        manager = User.objects.create_superuser("performance-manager")
        customer = m.Customer.objects.create(name="Cliente")
        vehicle = m.Vehicle.objects.create(customer=customer, plate="PERF1")
        order = m.WorkOrder.objects.create(vehicle=vehicle, number="PERF-1")
        quote = m.Quote.objects.create(work_order=order, version=1)
        line = dict(quote=quote, description="Servicio de prueba de rendimiento", kind="service", quantity=1, unit_price=100)
        m.QuoteLine.objects.create(**line)
        request = RequestFactory().get("/data/services/")
        request.user = manager
        with CaptureQueriesContext(connection) as single:
            self.assertEqual(data_table(request, "services").status_code, 200)
        m.QuoteLine.objects.bulk_create([m.QuoteLine(**line) for _ in range(24)])
        with CaptureQueriesContext(connection) as full:
            response = data_table(request, "services")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(single), len(full))
        self.assertLessEqual(len(full), 3)
        self.assertContains(response, "Servicio de prueba de rendimiento", count=25)

    def test_navigation_reads_roles_once_and_observes_later_role_changes(self):
        user = User.objects.create_user("performance-viewer")
        user.groups.add(Group.objects.create(name="viewer"))
        request = RequestFactory().get("/")
        request.user = user
        with self.assertNumQueries(1):
            actual = navigation(request)["cap"]
        self.assertEqual(actual, {key: can(user, key) for key in CAPABILITIES})
        user.groups.clear()
        with self.assertNumQueries(1):
            self.assertFalse(any(navigation(request)["cap"].values()))
