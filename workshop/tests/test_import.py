"""Disposable browser checks for the CSV catalog import boundary."""
import csv
import io

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import path

from workshop import models as m
from workshop.import_views import FIELDS, import_catalog


urlpatterns = [path("import/", import_catalog)]


def upload(entity, rows, header=None):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    header = header or FIELDS[entity]
    writer.writerow(header)
    for row in rows:
        writer.writerow([row.get(key, "") for key in header])
    return SimpleUploadedFile("anything.csv", stream.getvalue().encode("utf-8"), content_type="text/csv")


@override_settings(ROOT_URLCONF=__name__)
class CatalogImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_superuser("manager", password="LocalPassword!2026")
        cls.advisor = User.objects.create_user("advisor", password="LocalPassword!2026")
        group = Group.objects.create(name="advisor")
        cls.advisor.groups.add(group)

    def setUp(self):
        self.client.force_login(self.manager)

    def preview(self, entity, rows, *, header=None):
        return self.client.post("/import/", {"stage": "preview", "entity": entity,
                                             "file": upload(entity, rows, header)})

    def confirm(self, preview, entity):
        return self.client.post("/import/", {"stage": "commit", "entity": entity,
                                             "receipt": preview.context["receipt"]})

    def test_template_preview_commit_and_replay_are_append_only(self):
        template = self.client.get("/import/?template=customers")
        self.assertEqual(template.status_code, 200)
        self.assertEqual(template["Content-Disposition"], 'attachment; filename="milenio-customers.csv"')
        self.assertIn("name,phone,email,kind,notes", template.content.decode("utf-8-sig"))
        rows = [{"name": "Ana", "phone": "5550101", "email": "ana@example.invalid",
                 "kind": "individual", "notes": "Llamar por la mañana"},
                {"name": "Flota Norte", "phone": "", "email": "", "kind": "fleet", "notes": ""}]
        response = self.preview("customers", rows)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(m.Customer.objects.count(), 0)
        self.assertContains(response, "La vista previa no guarda")
        token = response.context["receipt"]
        self.assertTrue(token)
        committed = self.confirm(response, "customers")
        self.assertEqual(committed.status_code, 302)
        self.assertEqual(m.Customer.objects.count(), 2)
        receipt = m.AuditEvent.objects.get(entity_type="CatalogImport")
        self.assertEqual(receipt.after["count"], 2)
        second = self.client.post("/import/", {"stage": "commit", "entity": "customers", "receipt": token})
        self.assertEqual(second.status_code, 400)
        self.assertEqual(m.Customer.objects.count(), 2)

    def test_vehicle_unique_customer_lookup_and_parts_stock_not_importable(self):
        m.Customer.objects.create(name="Ana")
        vehicle = {"customer_name": "Ana", "plate": "ab-123", "vin": "",
                   "make": "Marca", "model": "Modelo", "year": "2022", "odometer": "1200"}
        preview = self.preview("vehicles", [vehicle])
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(m.Vehicle.objects.count(), 0)
        self.assertEqual(self.confirm(preview, "vehicles").status_code, 302)
        saved = m.Vehicle.objects.get()
        self.assertEqual((saved.plate, saved.customer.name), ("AB-123", "Ana"))
        part = {"sku": "p-1", "name": "Pastilla", "unit": "pieza",
                "cost": "10.00", "sale_price": "20.00", "reorder_point": "2.000"}
        preview = self.preview("parts", [part])
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(self.confirm(preview, "parts").status_code, 302)
        saved_part = m.Part.objects.get()
        self.assertEqual((saved_part.sku, saved_part.stock), ("P-1", 0))
        invalid = self.preview("parts", [{**part, "stock": "99"}], header=list(FIELDS["parts"]) + ["stock"])
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(m.Part.objects.count(), 1)

    def test_stale_preview_and_duplicate_rows_abort_entire_file(self):
        rows = [{"name": "Uno", "phone": "", "email": "", "kind": "individual", "notes": ""},
                {"name": "Dos", "phone": "", "email": "", "kind": "individual", "notes": ""}]
        preview = self.preview("customers", rows)
        m.Customer.objects.create(name="Dos")
        self.assertEqual(self.confirm(preview, "customers").status_code, 409)
        self.assertFalse(m.Customer.objects.filter(name="Uno").exists())
        self.assertEqual(m.AuditEvent.objects.filter(entity_type="CatalogImport").count(), 0)
        duplicate = self.preview("customers", [rows[0], {**rows[0], "name": "uno"}])
        self.assertEqual(duplicate.status_code, 400)
        self.assertFalse(m.Customer.objects.filter(name="Uno").exists())

    def test_bad_rows_and_literals_never_execute(self):
        invalid = self.preview("parts", [{"sku": "A", "name": "A", "unit": "pieza",
                                         "cost": "NaN", "sale_price": "10", "reorder_point": "0"}])
        self.assertEqual(invalid.status_code, 400)
        self.assertContains(invalid, "finito", status_code=400)
        self.assertEqual(m.Part.objects.count(), 0)
        bad_vehicle = self.preview("vehicles", [{"customer_name": "nadie", "plate": "", "vin": "",
                                                  "make": "A", "model": "B", "year": "-1", "odometer": "0"}])
        self.assertEqual(bad_vehicle.status_code, 400)
        formula = '=HYPERLINK("https://example.invalid","click")<script>alert(1)</script>'
        preview = self.preview("customers", [{"name": "Literal", "phone": "", "email": "",
                                               "kind": "individual", "notes": formula}])
        self.assertEqual(preview.status_code, 200)
        self.assertNotIn("<script>", preview.content.decode())
        self.assertIn("&lt;script&gt;", preview.content.decode())
        self.confirm(preview, "customers")
        self.assertEqual(m.Customer.objects.get().notes, formula)

    def test_limits_and_invalid_headers_leave_catalog_empty(self):
        row = {"name": "Cliente", "phone": "", "email": "", "kind": "individual", "notes": ""}
        wrong = self.preview("customers", [row], header=list(FIELDS["customers"]) + ["unknown"])
        self.assertEqual(wrong.status_code, 400)
        oversized = SimpleUploadedFile("large.csv", b"x" * (1024 * 1024 + 1), content_type="text/csv")
        self.assertEqual(self.client.post("/import/", {"stage": "preview", "entity": "customers",
                                                        "file": oversized}).status_code, 400)
        many = [{**row, "name": f"Cliente {number}"} for number in range(1001)]
        self.assertEqual(self.preview("customers", many).status_code, 400)
        self.assertEqual(m.Customer.objects.count(), 0)

    def test_roles_csrf_and_tampered_receipt(self):
        self.client.force_login(self.advisor)
        self.assertEqual(self.client.get("/import/").status_code, 403)
        self.assertEqual(self.preview("customers", []).status_code, 403)
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.manager)
        row = {"name": "CSRF", "phone": "", "email": "", "kind": "individual", "notes": ""}
        self.assertEqual(browser.post("/import/", {"stage": "preview", "entity": "customers",
                                                    "file": upload("customers", [row])}).status_code, 403)
        browser.get("/import/")
        response = browser.post("/import/", {"stage": "preview", "entity": "customers",
                                            "file": upload("customers", [row]),
                                            "csrfmiddlewaretoken": browser.cookies[settings.CSRF_COOKIE_NAME].value})
        self.assertEqual(response.status_code, 200)
        token = response.context["receipt"]
        self.assertEqual(browser.post("/import/", {"stage": "commit", "entity": "customers",
                                                  "receipt": token}).status_code, 403)
        tampered = browser.post("/import/", {"stage": "commit", "entity": "customers",
                                                "receipt": token + "x",
                                                "csrfmiddlewaretoken": browser.cookies[settings.CSRF_COOKIE_NAME].value})
        self.assertEqual(tampered.status_code, 400)
        self.assertEqual(m.Customer.objects.count(), 0)
