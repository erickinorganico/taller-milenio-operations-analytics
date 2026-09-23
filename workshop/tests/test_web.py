"""Browser-level acceptance of persisted operations and access boundaries."""

import csv
import io
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from PIL import Image

from workshop import models as m
from workshop import services as svc
from workshop.catalog import CATALOG, SOURCE_MODELS


class FirstRunAndAccessTests(TestCase):
    def test_setup_login_logout_and_real_csrf(self):
        browser = Client(enforce_csrf_checks=True)
        self.assertRedirects(browser.get("/"), "/setup/", fetch_redirect_response=False)
        page = browser.get("/setup/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Crea el acceso")
        signup = {"username": "dueño", "first_name": "Dueño", "password1": "ClaveDemoSegura!2026",
                  "password2": "ClaveDemoSegura!2026"}
        self.assertEqual(browser.post("/setup/", signup).status_code, 403)
        self.assertFalse(User.objects.exists())
        signup["csrfmiddlewaretoken"] = browser.cookies[settings.CSRF_COOKIE_NAME].value
        response = browser.post("/setup/", signup)
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertTrue(User.objects.get(username="dueño").is_superuser)
        self.assertEqual(browser.get("/").status_code, 200)
        self.assertEqual(browser.get("/logout/").status_code, 405)
        self.assertRedirects(browser.post("/logout/", {"csrfmiddlewaretoken": browser.cookies[settings.CSRF_COOKIE_NAME].value}),
                             "/login/", fetch_redirect_response=False)
        self.assertRedirects(browser.get("/"), "/login/", fetch_redirect_response=False)
        self.assertEqual(browser.get("/login/").status_code, 200)
        response = browser.post("/login/", {"username": "dueño", "password": "ClaveDemoSegura!2026",
                                              "csrfmiddlewaretoken": browser.cookies[settings.CSRF_COOKIE_NAME].value})
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_setup_is_unavailable_after_manager_exists_and_private_routes_require_login(self):
        User.objects.create_superuser("owner", password="LocalPassword!2026")
        browser = Client()
        self.assertRedirects(browser.get("/setup/"), "/", fetch_redirect_response=False)
        for route in ("/", "/orders/", "/inventory/", "/finance/", "/data/", "/team/"):
            self.assertRedirects(browser.get(route), "/login/", fetch_redirect_response=False)
        self.assertEqual(browser.get("/health/").status_code, 200)


class WorkshopHttpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_superuser("manager", password="LocalPassword!2026")
        for name in ("manager", "advisor", "technician", "parts", "finance", "viewer"):
            Group.objects.create(name=name)
        cls.manager.groups.add(Group.objects.get(name="manager"))
        cls.technician = User.objects.create_user("tech", password="LocalPassword!2026")
        cls.technician.groups.add(Group.objects.get(name="technician"))
        cls.finance = User.objects.create_user("finance", password="LocalPassword!2026")
        cls.finance.groups.add(Group.objects.get(name="finance"))
        cls.viewer = User.objects.create_user("viewer", password="LocalPassword!2026")
        cls.viewer.groups.add(Group.objects.get(name="viewer"))

    def setUp(self):
        self.client.force_login(self.manager)

    def post_redirect(self, path, data):
        response = self.client.post(path, data)
        self.assertEqual(response.status_code, 302, f"{path}: {response.status_code}; {response.content[:400]!r}")
        return response

    def make_customer_vehicle(self):
        self.post_redirect("/records/customers/new/", {
            "name": "Cliente HTTP", "phone": "5550000101", "email": "cliente@example.invalid",
            "kind": "individual", "notes": "Recorrido de prueba",
        })
        customer = m.Customer.objects.get(name="Cliente HTTP")
        self.post_redirect("/records/vehicles/new/", {
            "customer": customer.pk, "plate": "http-001", "vin": "", "make": "Marca",
            "model": "Sedán", "year": 2021, "odometer": 50000,
        })
        vehicle = m.Vehicle.objects.get(customer=customer)
        self.assertEqual(vehicle.plate, "HTTP-001")
        return customer, vehicle

    def change_stage(self, order, status):
        order.refresh_from_db()
        self.post_redirect(f"/orders/{order.pk}/transition/",
                           {"status": status, "version": order.version})
        order.refresh_from_db()
        self.assertEqual(order.status, status)

    def test_end_to_end_http_from_capture_to_partial_collection(self):
        customer, vehicle = self.make_customer_vehicle()
        self.post_redirect("/records/parts/new/", {
            "sku": "HTTP-BRK", "name": "Pastillas", "unit": "pieza", "cost": "20.00",
            "sale_price": "40.00", "reorder_point": "1",
        })
        part = m.Part.objects.get(sku="HTTP-BRK")
        self.post_redirect(f"/inventory/{part.pk}/adjust/",
                           {"quantity": "3", "reason": "Inventario inicial de prueba"})
        self.post_redirect("/orders/new/", {
            "vehicle": vehicle.pk, "complaint": "Revisar frenos", "assigned_to": self.technician.pk,
            "promised_at": "", "odometer": 50000,
        })
        order = m.WorkOrder.objects.get(vehicle=vehicle)
        self.assertEqual(order.status, "intake")
        self.assertEqual(self.client.get(f"/orders/{order.pk}/").status_code, 200)
        self.change_stage(order, "inspection")
        self.post_redirect(f"/orders/{order.pk}/inspection/", {
            "area": "Frenos", "result": "watch", "notes": "Desgaste observado",
        })
        self.assertEqual(order.inspections.count(), 1)
        self.change_stage(order, "awaiting_approval")
        self.post_redirect(f"/orders/{order.pk}/new-quote/", {"tax_rate": "0.16"})
        quote = order.quotes.get()
        self.post_redirect(f"/orders/{order.pk}/quote-line/", {
            "quote": quote.pk, "description": "Mano de obra", "kind": "labor",
            "quantity": "2", "unit_price": "250.00", "unit_cost": "137.77", "part": "",
        })
        self.post_redirect(f"/orders/{order.pk}/quote-line/", {
            "quote": quote.pk, "description": "Pastillas", "kind": "part",
            "quantity": "1", "unit_price": "40.00", "unit_cost": "23.45", "part": part.pk,
        })
        self.assertEqual(quote.lines.count(), 2)
        self.post_redirect(f"/orders/{order.pk}/send-quote/", {"quote": quote.pk})
        self.post_redirect(f"/orders/{order.pk}/approve-quote/", {
            "quote": quote.pk, "approval_name": "Cliente HTTP",
            "approval_reference": "Firma recibida HTTP-1",
        })
        quote.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(quote.status, "approved")
        self.assertEqual(order.status, "approved")
        self.post_redirect(f"/orders/{order.pk}/reserve/", {"part": part.pk, "quantity": "1"})
        reservation = order.reservations.get(part=part)
        self.change_stage(order, "in_progress")
        self.post_redirect(f"/orders/{order.pk}/consume/", {"reservation": reservation.pk, "quantity": "1"})
        self.post_redirect(f"/orders/{order.pk}/time/", {"minutes": "45", "notes": "Trabajo realizado"})
        self.change_stage(order, "quality")
        self.post_redirect(f"/orders/{order.pk}/quality/", {"result": "pass", "notes": "Prueba final"})
        self.change_stage(order, "ready")
        self.change_stage(order, "delivered")
        due = timezone.localtime(timezone.now() + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M")
        self.post_redirect(f"/orders/{order.pk}/invoice/", {"number": "ADM-HTTP-1", "due_at": due})
        invoice = m.Invoice.objects.get(work_order=order)
        self.assertEqual(invoice.total, Decimal("626.40"))
        self.post_redirect(f"/orders/{order.pk}/payment/", {
            "amount": "100.00", "method": "transfer", "reference": "TRANSFER-1",
            "idempotency_key": "web-pay-1",
        })
        self.assertEqual(invoice.payments.count(), 1)
        self.assertEqual(invoice.total - invoice.payments.get().amount, Decimal("526.40"))
        part.refresh_from_db()
        self.assertEqual((part.stock, part.reserved), (Decimal("2"), Decimal("0")))
        self.assertGreaterEqual(m.AuditEvent.objects.filter(entity_type="WorkOrder",
                                                              entity_id=str(order.pk)).count(), 8)
        self.assertContains(self.client.get("/finance/"), "ADM-HTTP-1")
        self.assertContains(self.client.get(f"/orders/{order.pk}/"), "TRANSFER-1")
        self.assertContains(self.client.get("/data/orders/"), order.number)
        metrics = {item["metric_id"]: item for item in self.client.get("/metrics/?export=json").json()["metrics"]}
        self.assertEqual(Decimal(str(metrics["FIN-INVOICED"]["value"])), Decimal("626.40"))
        self.assertEqual(Decimal(str(metrics["FIN-OPEN-BALANCE"]["value"])), Decimal("526.40"))
        self.assertEqual((metrics["OPS-WIP"]["status"], metrics["OPS-WIP"]["value"]), ("measured", 0))

        quote_url = f"/documents/quote/{quote.pk}/"
        invoice_url = f"/documents/invoice/{invoice.pk}/"
        order_page = self.client.get(f"/orders/{order.pk}/")
        self.assertContains(order_page, quote_url)
        self.assertContains(order_page, invoice_url)
        before = (m.Quote.objects.count(), m.QuoteLine.objects.count(), m.Invoice.objects.count(),
                  m.Payment.objects.count(), m.AuditEvent.objects.count())
        quote_doc = self.client.get(quote_url)
        invoice_doc = self.client.get(invoice_url)
        for document in (quote_doc, invoice_doc):
            self.assertEqual(document.status_code, 200)
            self.assertContains(document, "Mano de obra")
            self.assertContains(document, "$250.00")
            self.assertContains(document, "$500.00")
            self.assertContains(document, "$540.00")
            self.assertContains(document, "$86.40")
            self.assertContains(document, "$626.40")
            self.assertNotContains(document, "$137.77")
            self.assertNotContains(document, "$23.45")
            self.assertNotContains(document, "Costo unitario")
        self.assertContains(quote_doc, "Firma recibida HTTP-1")
        self.assertContains(quote_doc, "Cliente HTTP")
        self.assertContains(invoice_doc, "Comprobante administrativo")
        self.assertContains(invoice_doc, "TRANSFER-1")
        self.assertContains(invoice_doc, "$100.00")
        self.assertContains(invoice_doc, "$526.40")
        self.assertEqual(before, (m.Quote.objects.count(), m.QuoteLine.objects.count(), m.Invoice.objects.count(),
                                  m.Payment.objects.count(), m.AuditEvent.objects.count()))
        advisor = User.objects.create_user("document-advisor", password="LocalPassword!2026")
        advisor.groups.add(Group.objects.get(name="advisor"))
        self.client.force_login(advisor)
        self.assertEqual(self.client.get(quote_url).status_code, 200)
        self.assertEqual(self.client.get(invoice_url).status_code, 403)
        self.client.force_login(self.technician)
        self.assertEqual(self.client.get(quote_url).status_code, 403)
        self.assertEqual(self.client.get(invoice_url).status_code, 403)

    def test_roles_and_error_inputs_do_not_mutate_records_or_return_500(self):
        _, vehicle = self.make_customer_vehicle()
        self.post_redirect("/orders/new/", {"vehicle": vehicle.pk, "complaint": "Revisar",
                                              "assigned_to": "", "promised_at": "", "odometer": ""})
        order = m.WorkOrder.objects.get(vehicle=vehicle)
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get("/orders/").status_code, 200)
        self.assertEqual(self.client.post("/records/customers/new/", {"name": "No autorizado"}).status_code, 403)
        self.assertEqual(self.client.post(f"/orders/{order.pk}/transition/",
                                          {"status": "inspection", "version": order.version}).status_code, 403)
        self.client.force_login(self.technician)
        self.post_redirect(f"/orders/{order.pk}/transition/", {"status": "inspection", "version": order.version})
        order.refresh_from_db()
        self.assertEqual(order.status, "intake")  # not assigned to this technician
        self.client.force_login(self.finance)
        self.assertEqual(self.client.post("/inventory/999/adjust/", {"quantity": "1", "reason": "X"}).status_code, 403)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get("/orders/999999/").status_code, 404)
        self.assertEqual(self.client.post("/orders/999999/transition/", {"status": "inspection"}).status_code, 404)
        self.post_redirect(f"/orders/{order.pk}/time/", {"minutes": "not-an-int", "notes": "X"})
        self.post_redirect(f"/orders/{order.pk}/invoice/", {"number": "INV-X", "due_at": "bad-date"})
        part = m.Part.objects.create(sku="BAD-QTY", name="Validación")
        self.post_redirect(f"/inventory/{part.pk}/adjust/", {"quantity": "NaN", "reason": "Dato inválido"})
        bad_date = self.client.post("/records/appointments/new/", {
            "vehicle": vehicle.pk, "scheduled_at": "fecha-inválida", "reason": "Cita",
            "status": "scheduled",
        })
        self.assertEqual(bad_date.status_code, 200)
        part.refresh_from_db()
        self.assertEqual(part.stock, Decimal("0"))
        self.assertFalse(m.TimeEntry.objects.exists())
        self.assertFalse(m.Invoice.objects.exists())
        self.assertFalse(m.Appointment.objects.exists())

    def test_source_csv_escapes_spreadsheet_formulas_and_auth_table_excluded(self):
        m.Customer.objects.create(name="=HYPERLINK(\"https://invalid.example\")", kind="individual")
        response = self.client.get("/data/customers/?export=csv")
        self.assertEqual(response.status_code, 200)
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertTrue(rows[1][1].startswith("'=HYPERLINK"))
        self.assertEqual(self.client.get("/data/auth-user/").status_code, 404)
        self.assertContains(self.client.get("/data/"), "Clientes")
        customer, vehicle = self.make_customer_vehicle()
        self.assertContains(self.client.get(f"/data/vehicles/?id={vehicle.pk}"),
                            f"/data/customers/?id={customer.pk}")

    def test_purchase_http_requires_draft_lines_order_then_idempotent_receipts(self):
        self.post_redirect("/records/suppliers/new/", {
            "name": "Proveedor HTTP", "phone": "5550000202", "email": "supplier@example.invalid",
        })
        supplier = m.Supplier.objects.get(name="Proveedor HTTP")
        self.post_redirect("/records/parts/new/", {
            "sku": "FILTER-HTTP", "name": "Filtro", "unit": "pieza",
            "cost": "10.00", "sale_price": "20.00", "reorder_point": "2",
        })
        part = m.Part.objects.get(sku="FILTER-HTTP")
        self.post_redirect("/records/purchases/new/", {"supplier": supplier.pk, "number": "PO-HTTP-1"})
        purchase = m.PurchaseOrder.objects.get(number="PO-HTTP-1")
        self.assertEqual(purchase.status, "draft")
        self.post_redirect(f"/purchases/{purchase.pk}/", {
            "part": part.pk, "quantity": "5", "unit_cost": "10.00",
        })
        line = purchase.lines.get()
        self.post_redirect(f"/purchase-lines/{line.pk}/receive/", {
            "quantity": "2", "reference": "ALB-HTTP-1",
        })
        part.refresh_from_db()
        self.assertEqual(part.stock, Decimal("0"))
        self.post_redirect(f"/purchases/{purchase.pk}/place/", {})
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "ordered")
        rejected_line = self.client.post(f"/purchases/{purchase.pk}/", {
            "part": part.pk, "quantity": "1", "unit_cost": "10.00",
        })
        self.assertEqual(rejected_line.status_code, 200)
        self.assertEqual(purchase.lines.count(), 1)
        self.post_redirect(f"/purchase-lines/{line.pk}/receive/", {
            "quantity": "2", "reference": "ALB-HTTP-1",
        })
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "partial")
        self.post_redirect(f"/purchase-lines/{line.pk}/receive/", {
            "quantity": "2", "reference": "ALB-HTTP-1",
        })
        self.post_redirect(f"/purchase-lines/{line.pk}/receive/", {
            "quantity": "3", "reference": "ALB-HTTP-1",
        })
        part.refresh_from_db()
        self.assertEqual(part.stock, Decimal("2"))
        self.post_redirect(f"/purchase-lines/{line.pk}/receive/", {
            "quantity": "3", "reference": "ALB-HTTP-2",
        })
        purchase.refresh_from_db()
        part.refresh_from_db()
        self.assertEqual((purchase.status, part.stock), ("received", Decimal("5")))
        self.assertEqual(m.StockMovement.objects.filter(purchase_order=purchase, kind="receipt").count(), 2)
        self.assertContains(self.client.get(f"/purchases/{purchase.pk}/"), "FILTER-HTTP")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.post(f"/purchases/{purchase.pk}/place/", {}).status_code, 403)

    def test_csrf_blocks_a_real_authenticated_write(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.manager)
        before = m.Customer.objects.count()
        response = browser.post("/records/customers/new/", {
            "name": "CSRF bypass", "kind": "individual", "phone": "", "email": "", "notes": "",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(m.Customer.objects.count(), before)

    def test_collections_rule_review_creates_one_persisted_internal_task(self):
        _, vehicle = self.make_customer_vehicle()
        order = svc.create_work_order(actor=self.manager, vehicle=vehicle, complaint="Servicio")
        svc.transition_work_order(actor=self.manager, work_order=order, status="inspection")
        svc.add_inspection(actor=self.manager, work_order=order, area="General", result="okay")
        svc.transition_work_order(actor=self.manager, work_order=order, status="awaiting_approval")
        quote = svc.create_quote(actor=self.manager, work_order=order)
        svc.add_quote_line(actor=self.manager, quote=quote, description="Servicio", kind="labor",
                           quantity=1, unit_price="100.00")
        svc.send_quote(actor=self.manager, quote=quote)
        svc.approve_quote(actor=self.manager, quote=quote, approval_name="Cliente HTTP",
                          approval_reference="Firma de prueba")
        svc.transition_work_order(actor=self.manager, work_order=order, status="in_progress")
        svc.transition_work_order(actor=self.manager, work_order=order, status="quality")
        svc.record_quality_check(actor=self.manager, work_order=order, result="pass")
        svc.transition_work_order(actor=self.manager, work_order=order, status="ready")
        svc.transition_work_order(actor=self.manager, work_order=order, status="delivered")
        invoice = svc.issue_invoice(actor=self.manager, work_order=order, number="ADM-AGENT-1",
                                    due_at=timezone.now() + timedelta(days=7))
        svc.record_payment(actor=self.manager, invoice=invoice, amount="20.00", method="cash",
                           reference="REC-AGENT-1", idempotency_key="agent-payment-1")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.post("/agents/run/", {"mode": "rules", "agent": "collections"}).status_code, 403)
        self.client.force_login(self.manager)
        self.post_redirect("/agents/run/", {"mode": "rules", "agent": "collections"})
        run = m.AgentRun.objects.get(agent="collections")
        self.assertEqual((run.status, run.mode, run.model_invoked), ("completed", "rules", False))
        proposal = m.Proposal.objects.get(run=run)
        self.assertEqual((proposal.status, proposal.entity_type, proposal.entity_id),
                         ("pending", "Invoice", str(invoice.pk)))
        self.assertContains(self.client.get("/agents/"), "Saldo administrativo pendiente")
        self.post_redirect(f"/proposals/{proposal.pk}/review/",
                           {"decision": "accept", "note": "Revisado por gerencia"})
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "accepted")
        self.assertEqual(m.ActionTask.objects.filter(proposal=proposal).count(), 1)
        self.post_redirect(f"/proposals/{proposal.pk}/review/",
                           {"decision": "accept", "note": "Reintento"})
        self.assertEqual(m.ActionTask.objects.filter(proposal=proposal).count(), 1)
        task = proposal.action_task
        self.post_redirect(f"/tasks/{task.pk}/update/",
                           {"action": "assign", "assigned_to": self.manager.pk, "due_at": ""})
        self.post_redirect(f"/tasks/{task.pk}/update/",
                           {"action": "complete", "outcome": "Saldo revisado; esperar confirmación."})
        task.refresh_from_db()
        self.assertEqual((task.status, task.assigned_to_id), ("completed", self.manager.pk))
        self.assertIsNotNone(task.completed_at)

    def test_every_current_get_surface_renders_for_manager(self):
        _, vehicle = self.make_customer_vehicle()
        order = m.WorkOrder.objects.create(vehicle=vehicle, number="WO-GET-1", complaint="Revisión")
        supplier = m.Supplier.objects.create(name="Proveedor")
        purchase = m.PurchaseOrder.objects.create(supplier=supplier, number="PO-GET-1")
        routes = ["/", "/orders/", "/orders/new/", f"/orders/{order.pk}/",
                  "/inventory/", f"/purchases/{purchase.pk}/", "/finance/", "/fleets/",
                  "/towing/", "/towing/new/", "/data/", "/team/", "/guide/",
                  "/metrics/", "/agents/",
                  "/static/workshop/app.css", "/static/workshop/app.js"]
        routes += [f"/records/{key}/" for key in CATALOG]
        routes += [f"/records/{key}/new/" for key in CATALOG]
        routes += [f"/data/{key}/" for key in SOURCE_MODELS]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200, f"{route}: {response.status_code}")

    def test_technician_reads_only_assigned_orders_and_their_photos(self):
        _, vehicle = self.make_customer_vehicle()
        other = User.objects.create_user("other-tech", password="LocalPassword!2026")
        other.groups.add(Group.objects.get(name="technician"))
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            own = svc.create_work_order(actor=self.manager, vehicle=vehicle, complaint="Propia",
                                        number="WO-TECH-OWN", assigned_to=self.technician)
            foreign = svc.create_work_order(actor=self.manager, vehicle=vehicle, complaint="Ajena",
                                            number="WO-TECH-OTHER", assigned_to=other)
            images = []
            for order in (own, foreign):
                svc.transition_work_order(actor=self.manager, work_order=order, status="inspection")
                data = io.BytesIO()
                Image.new("RGB", (2, 2), "white").save(data, format="PNG")
                images.append(svc.add_inspection(
                    actor=self.manager, work_order=order, area="Visual", result="watch",
                    photo=SimpleUploadedFile(f"{order.number}.png", data.getvalue(), content_type="image/png"),
                ))
            self.client.force_login(self.technician)
            listing = self.client.get("/orders/")
            self.assertContains(listing, "WO-TECH-OWN")
            self.assertNotContains(listing, "WO-TECH-OTHER")
            self.assertContains(self.client.get("/"), "WO-TECH-OWN")
            self.assertNotContains(self.client.get("/"), "WO-TECH-OTHER")
            self.assertEqual(self.client.get(f"/orders/{own.pk}/").status_code, 200)
            self.assertIn(self.client.get(f"/orders/{foreign.pk}/").status_code, (403, 404))
            own_photo = self.client.get(f"/inspection/{images[0].pk}/photo/")
            try:
                self.assertEqual(own_photo.status_code, 200)
            finally:
                own_photo.close()
            other_photo = self.client.get(f"/inspection/{images[1].pk}/photo/")
            try:
                self.assertIn(other_photo.status_code, (403, 404))
            finally:
                other_photo.close()

    def test_technician_cannot_read_global_business_data_while_viewer_can(self):
        restricted = ["/finance/", "/data/", "/data/customers/?export=csv", "/metrics/",
                      "/agents/", "/fleets/", "/towing/"]
        restricted += [f"/records/{key}/" for key in CATALOG]
        self.client.force_login(self.technician)
        self.assertEqual(self.client.get("/inventory/").status_code, 200)
        for route in restricted:
            with self.subTest(role="technician", route=route):
                self.assertIn(self.client.get(route).status_code, (403, 404))
        self.client.force_login(self.viewer)
        for route in restricted:
            with self.subTest(role="viewer", route=route):
                self.assertEqual(self.client.get(route).status_code, 200)
        self.assertEqual(self.client.post("/records/customers/new/", {"name": "No"}).status_code, 403)

    def test_technician_home_and_inventory_hide_unrelated_business_details(self):
        customer, vehicle = self.make_customer_vehicle()
        m.Appointment.objects.create(vehicle=vehicle, scheduled_at=timezone.now(), reason="Cita privada de recepción")
        m.ActionTask.objects.create(title="Tarea técnica propia", assigned_to=self.technician)
        m.ActionTask.objects.create(title="Tarea gerencial ajena", assigned_to=self.manager)
        m.Part.objects.create(sku="PRIVATE-COST", name="Filtro de prueba", cost="123.45",
                              sale_price="456.78", stock="2", reserved="0", reorder_point="1")
        self.client.force_login(self.technician)
        home = self.client.get("/")
        self.assertContains(home, "Tarea técnica propia")
        self.assertNotContains(home, "Tarea gerencial ajena")
        self.assertNotContains(home, "Cita privada de recepción")
        self.assertNotContains(home, "Por cobrar")
        inventory = self.client.get("/inventory/")
        self.assertContains(inventory, "Filtro de prueba")
        self.assertNotContains(inventory, "123.45")
        self.assertNotContains(inventory, "456.78")
        self.assertNotContains(inventory, "Compras recientes")

    def test_viewer_assigned_legacy_task_cannot_close_it_but_technician_can_close_own(self):
        legacy = m.ActionTask.objects.create(title="Tarea heredada de consulta", assigned_to=self.viewer)
        own = m.ActionTask.objects.create(title="Tarea operativa", assigned_to=self.technician)
        self.client.force_login(self.viewer)
        agents = self.client.get("/agents/")
        self.assertContains(agents, legacy.title)
        self.assertNotContains(agents, f'action="/tasks/{legacy.pk}/update/"')
        self.assertNotContains(self.client.get("/"), f'action="/tasks/{legacy.pk}/update/"')
        self.assertEqual(self.client.post(f"/tasks/{legacy.pk}/update/", {
            "action": "complete", "outcome": "Cierre sin autoridad"
        }).status_code, 403)
        legacy.refresh_from_db()
        self.assertEqual((legacy.status, legacy.outcome, legacy.completed_at), ("open", "", None))
        self.client.force_login(self.technician)
        self.assertContains(self.client.get("/"), f'action="/tasks/{own.pk}/update/"')
        self.post_redirect(f"/tasks/{own.pk}/update/", {"action": "complete", "outcome": "Trabajo revisado"})
        own.refresh_from_db()
        self.assertEqual((own.status, own.outcome), ("completed", "Trabajo revisado"))

    def test_technician_ready_order_has_no_delivery_option_and_cannot_deliver(self):
        _, vehicle = self.make_customer_vehicle()
        order = m.WorkOrder.objects.create(vehicle=vehicle, number="WO-READY-TECH", complaint="Trabajo listo",
                                           assigned_to=self.technician, status="ready")
        self.client.force_login(self.technician)
        page = self.client.get(f"/orders/{order.pk}/")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("delivered", page.context["next_statuses"])
        self.assertNotIn("cancelled", page.context["next_statuses"])
        self.assertNotContains(page, '<option value="delivered">')
        self.assertEqual(self.client.post(f"/orders/{order.pk}/transition/", {
            "status":"delivered", "version":order.version
        }).status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.status, "ready")

    def test_team_edit_deactivates_other_user_without_erasing_history_or_secrets(self):
        _, vehicle = self.make_customer_vehicle()
        order = svc.create_work_order(actor=self.manager, vehicle=vehicle, complaint="Trabajo con responsable",
                                      number="WO-TEAM-HISTORY", assigned_to=self.technician)
        prior_event = m.AuditEvent.objects.create(actor=self.technician, entity_type="WorkOrder",
                                                  entity_id=str(order.pk), action="observed", after={"status":"intake"})
        old_hash = self.technician.password
        self.post_redirect(f"/team/{self.technician.pk}/edit/", {
            "first_name":"Técnico anterior", "role":"technician", "password1":"", "password2":""
        })
        self.technician.refresh_from_db()
        order.refresh_from_db()
        self.assertFalse(self.technician.is_active)
        self.assertEqual(self.technician.password, old_hash)
        self.assertEqual(order.assigned_to_id, self.technician.pk)
        self.assertEqual(prior_event.actor_id, self.technician.pk)
        event = m.AuditEvent.objects.get(entity_type="User", entity_id=str(self.technician.pk), action="account_updated")
        self.assertEqual(event.after["active"], False)
        self.assertNotIn(old_hash, str(event.before) + str(event.after))
        self.assertNotIn("LocalPassword!2026", str(event.before) + str(event.after))
        self.assertEqual(self.client.get(f"/team/{self.technician.pk}/edit/").status_code, 200)

    def test_team_edit_rejects_self_or_administrator_deactivation_and_nonmanager_access(self):
        payload = {"first_name":"Manager", "role":"manager", "password1":"", "password2":""}
        response = self.client.post(f"/team/{self.manager.pk}/edit/", payload)
        self.assertEqual(response.status_code, 200)
        self.manager.refresh_from_db()
        self.assertTrue(self.manager.is_active)
        other_admin = User.objects.create_superuser("second-admin", password="StrongPassword!2026")
        response = self.client.post(f"/team/{other_admin.pk}/edit/", payload)
        self.assertEqual(response.status_code, 200)
        other_admin.refresh_from_db()
        self.assertTrue(other_admin.is_active)
        self.assertFalse(m.AuditEvent.objects.filter(entity_type="User", entity_id=str(other_admin.pk),
                                                      action="account_updated").exists())
        self.client.force_login(self.technician)
        self.assertEqual(self.client.get(f"/team/{other_admin.pk}/edit/").status_code, 403)
        self.assertEqual(self.client.post(f"/team/{other_admin.pk}/edit/", payload).status_code, 403)

    def test_user_changes_own_password_without_auditing_password_or_hash(self):
        self.client.force_login(self.technician)
        self.assertEqual(self.client.get("/account/").status_code, 200)
        response = self.client.post("/account/", {"old_password":"LocalPassword!2026",
                                                 "new_password1":"NewLocalPassword!2026",
                                                 "new_password2":"NewLocalPassword!2026"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.technician.refresh_from_db()
        self.assertTrue(self.technician.check_password("NewLocalPassword!2026"))
        self.assertEqual(self.client.get("/account/").status_code, 200)
        event = m.AuditEvent.objects.get(entity_type="User", entity_id=str(self.technician.pk), action="password_changed")
        audited = str(event.before) + str(event.after)
        for secret in ("LocalPassword!2026", "NewLocalPassword!2026", self.technician.password):
            self.assertNotIn(secret, audited)
        self.client.post("/logout/")
        self.assertEqual(self.client.post("/login/", {"username":"tech", "password":"LocalPassword!2026"}).status_code, 200)
        self.assertRedirects(self.client.post("/login/", {"username":"tech", "password":"NewLocalPassword!2026"}),
                             "/", fetch_redirect_response=False)

    def test_vehicle_identity_with_history_and_fleet_kind_cannot_be_reassigned(self):
        original = m.Customer.objects.create(name="Propietario A", kind="individual")
        replacement = m.Customer.objects.create(name="Propietario B", kind="individual")
        for index, kind in enumerate(("order", "appointment", "maintenance", "tow"), start=1):
            with self.subTest(history=kind):
                vehicle = m.Vehicle.objects.create(customer=original, plate=f"HIST-{index}",
                                                    vin=f"HISTORYVIN{index:07d}", make="Marca", model="Modelo")
                if kind == "order":
                    m.WorkOrder.objects.create(vehicle=vehicle, number=f"WO-HIST-{index}", complaint="Trabajo")
                elif kind == "appointment":
                    m.Appointment.objects.create(vehicle=vehicle, scheduled_at=timezone.now(), reason="Cita")
                elif kind == "maintenance":
                    m.MaintenancePlan.objects.create(vehicle=vehicle, description="Mantenimiento",
                                                     due_date=timezone.localdate())
                else:
                    m.TowService.objects.create(customer=original, vehicle=vehicle,
                                                origin="Origen", destination="Destino")
                fields = {"customer": replacement.pk, "plate": vehicle.plate, "vin": vehicle.vin,
                          "make": vehicle.make, "model": vehicle.model, "year": "", "odometer": ""}
                response = self.client.post(f"/records/vehicles/{vehicle.pk}/edit/", fields)
                self.assertIn(response.status_code, (200, 302))
                vehicle.refresh_from_db()
                self.assertEqual(vehicle.customer_id, original.pk)
                fields["customer"] = original.pk
                fields["vin"] = f"CHANGEDVIN{index:07d}"
                response = self.client.post(f"/records/vehicles/{vehicle.pk}/edit/", fields)
                self.assertIn(response.status_code, (200, 302))
                vehicle.refresh_from_db()
                self.assertEqual(vehicle.vin, f"HISTORYVIN{index:07d}")
        fleet = m.Customer.objects.create(name="Flotilla histórica", kind="fleet")
        m.FleetContract.objects.create(customer=fleet, name="Contrato vigente",
                                       start_date=timezone.localdate(),
                                       end_date=timezone.localdate() + timedelta(days=30),
                                       monthly_fee=Decimal("100.00"), status="active")
        response = self.client.post(f"/records/customers/{fleet.pk}/edit/", {
            "name": fleet.name, "phone": "", "email": "", "kind": "individual", "notes": "",
        })
        self.assertIn(response.status_code, (200, 302))
        fleet.refresh_from_db()
        self.assertEqual(fleet.kind, "fleet")
