from datetime import datetime, timezone
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils.timezone import override

from workshop.models import Customer, ReceptionReceipt, Vehicle, WorkOrder
from workshop.services import create_work_order


class ReceptionFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_superuser("gerencia")
        cls.advisor = User.objects.create_user("recepcion")
        cls.advisor.groups.add(Group.objects.create(name="advisor"))

    def setUp(self):
        self.client.force_login(self.advisor)

    def token(self, path):
        page = self.client.get(path)
        self.assertContains(page, 'name="reception_token"')
        return str(page.wsgi_request.reception_token)

    def test_empty_workshop_then_complete_reception_and_retry_each_step(self):
        start = self.client.get("/orders/new/")
        customer_path = "/records/customers/new/?flow=reception"
        self.assertContains(start, customer_path)
        self.assertNotContains(start, 'name="vehicle"')

        customer_data = {"name": "Sofía", "kind": "individual",
                         "reception_token": self.token(customer_path)}
        vehicle_path = self.client.post(customer_path, customer_data).url
        customer = Customer.objects.get()
        self.assertEqual(vehicle_path, f"/records/vehicles/new/?flow=reception&customer={customer.pk}")
        self.assertEqual(self.client.post(customer_path, customer_data).url, vehicle_path)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertContains(self.client.get("/orders/new/"), "/records/vehicles/new/?flow=reception")

        vehicle_token = self.token(vehicle_path)
        vehicle_data = {"customer": customer.pk, "make": "Nissan", "model": "Versa",
                        "reception_token": vehicle_token}
        invalid = self.client.post(vehicle_path, vehicle_data)
        self.assertContains(invalid, "Registra placas o VIN")
        self.assertContains(invalid, vehicle_token)
        self.assertFalse(Vehicle.objects.exists())
        self.assertEqual(ReceptionReceipt.objects.count(), 1)

        vehicle_data["plate"] = "pru-123"
        order_path = self.client.post(vehicle_path, vehicle_data).url
        self.assertEqual(self.client.post(vehicle_path, vehicle_data).url, order_path)
        vehicle = Vehicle.objects.get()
        self.assertEqual(order_path, f"/orders/new/?vehicle={vehicle.pk}")
        page = self.client.get(order_path)
        self.assertContains(page, f'value="{vehicle.pk}" selected')
        self.assertContains(page, "PRU-123 · Nissan Versa · Sofía")

        order_data = {"vehicle": vehicle.pk, "complaint": "Revisar vibración",
                      "reception_token": self.token(order_path)}
        detail = self.client.post(order_path, order_data).url
        replay = self.client.post(order_path, order_data, follow=True)
        self.assertContains(replay, "ya se guardó")
        self.assertEqual(detail, f"/orders/{WorkOrder.objects.get().pk}/")
        self.assertEqual(replay.redirect_chain, [(detail, 302)])
        self.assertEqual(ReceptionReceipt.objects.count(), 3)

        # A new visit can legitimately repeat the same work on the same car.
        order_data["reception_token"] = self.token(order_path)
        warning = self.client.post(order_path, order_data)
        self.assertContains(warning, f'href="{detail}"')
        self.assertEqual(WorkOrder.objects.count(), 1)
        self.assertContains(warning, "Revisar vibración")
        order_data["confirm_open_orders"] = warning.context["open_order_review"]["stamp"]
        self.assertNotEqual(self.client.post(order_path, order_data).url, detail)
        self.assertEqual(WorkOrder.objects.count(), 2)

    def test_new_tab_and_stale_confirmation_cannot_duplicate_a_visit(self):
        url = "/orders/new/"
        car = Vehicle.objects.create(customer=Customer.objects.create(name="Lucía"), plate="QA-1")
        first = {"vehicle": car.pk, "complaint": "Frenos", "reception_token": self.token(url)}
        second = {**first, "reception_token": self.token(url)}
        self.assertEqual(self.client.post(url, first).status_code, 302)
        review = self.client.post(url, second)
        second["confirm_open_orders"] = review.context["open_order_review"]["stamp"]
        third = {**second, "reception_token": self.token(url)}
        self.assertContains(self.client.post(url, third), "Es un trabajo distinto")
        create_work_order(actor=self.manager, vehicle=car, complaint="Otra visita")
        changed = self.client.post(url, second)
        self.assertEqual(len(changed.context["open_order_review"]["orders"]), 2)
        self.assertEqual(WorkOrder.objects.count(), 2)
        second["confirm_open_orders"] = changed.context["open_order_review"]["stamp"]
        result = self.client.post(url, second)
        self.assertEqual(self.client.post(url, second).url, result.url)
        self.assertEqual(WorkOrder.objects.count(), 3)
        WorkOrder.objects.filter(vehicle=car).update(status="delivered")
        self.assertEqual(self.client.post(url, third).status_code, 302)

    def test_token_is_scoped_to_user_and_step_and_catalog_keeps_its_destination(self):
        path = "/records/customers/new/"
        data = {"name": "Cliente HTTP", "kind": "individual", "reception_token": self.token(path)}
        self.assertEqual(self.client.post(path, data).url, "/records/customers/")
        self.assertEqual(self.client.post("/records/vehicles/new/", data).status_code, 400)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.post(path, data).status_code, 400)
        viewer = User.objects.create_user("consulta")
        viewer.groups.add(Group.objects.create(name="viewer"))
        self.client.force_login(viewer)
        self.assertEqual(self.client.post(path, data).status_code, 403)
        self.assertEqual(self.client.post("/orders/new/", data).status_code, 403)
        self.assertEqual(Customer.objects.count(), 1)

    def test_rolled_back_reception_can_be_retried(self):
        path = "/records/customers/new/?flow=reception"
        data = {"name": "Elena", "kind": "individual", "reception_token": self.token(path)}
        original_save = ReceptionReceipt.save

        def fail_after_business_write(receipt, *args, **kwargs):
            if receipt.next_url:
                raise RuntimeError("fallo simulado al guardar el recibo")
            return original_save(receipt, *args, **kwargs)

        with patch.object(ReceptionReceipt, "save", fail_after_business_write):
            with self.assertRaises(RuntimeError):
                self.client.post(path, data)
        self.assertFalse(Customer.objects.exists())
        self.assertFalse(ReceptionReceipt.objects.exists())
        self.assertEqual(self.client.post(path, data).status_code, 302)
        self.assertEqual(Customer.objects.count(), 1)

    def test_new_folio_uses_the_date_at_the_workshop_after_midnight_utc(self):
        car = Vehicle.objects.create(customer=Customer.objects.create(name="Ana"),
                                     plate="DEMO", make="Toyota", model="Corolla")
        utc_midnight = datetime(2026, 11, 25, 0, 33, tzinfo=timezone.utc)
        with override("America/Tijuana"), patch("django.utils.timezone.now", return_value=utc_midnight):
            order = create_work_order(actor=self.advisor, vehicle=car, complaint="Revisión")
            manual = create_work_order(actor=self.advisor, vehicle=car, complaint="Revisión", number="MI-FOLIO")
        self.assertRegex(order.number, r"^WO-20261124-[0-9A-F]{8}$")
        self.assertEqual(manual.number, "MI-FOLIO")
