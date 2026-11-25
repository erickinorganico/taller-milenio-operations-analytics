from contextlib import closing
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from PIL import Image

from workshop.models import AuditEvent, Customer, Inspection, Vehicle, WorkOrder


class MobileInspectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_superuser("gerencia")
        cls.tech = User.objects.create_user("tecnico")
        cls.tech.groups.add(Group.objects.create(name="technician"))
        cls.viewer = User.objects.create_user("consulta")
        cls.viewer.groups.add(Group.objects.create(name="viewer"))
        car = Vehicle.objects.create(customer=Customer.objects.create(name="Prueba"),
                                     plate="PRUEBA", make="Marca", model="Modelo")
        cls.order = WorkOrder.objects.create(vehicle=car, number="QA-100", assigned_to=cls.tech,
                                              status="inspection", complaint="Inspección sintética")

    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.media = Path(temp.name)
        media = override_settings(MEDIA_ROOT=self.media)
        media.enable()
        self.addCleanup(media.disable)
        self.mobile = Client()
        self.mobile.force_login(self.tech)
        self.desk = Client()
        self.desk.force_login(self.manager)
        self.order_url = f"/orders/{self.order.pk}/"
        self.feed = self.order_url + "inspection-feed/"
        self.upload = self.order_url + "inspection/"
        self.key = str(uuid4())

    def payload(self, name="photo", **updates):
        output = BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = "Autor de prueba"
        Image.new("RGB", (40, 18), "blue").save(output, "JPEG", exif=exif)
        photo = SimpleUploadedFile("archivo-privado.jpg", output.getvalue(), "image/jpeg")
        return {"area": "Frenos", "result": "watch", "notes": "Delantero", "submission_key": self.key,
                name: photo, **updates}

    def send(self, data):
        return self.mobile.post(self.upload, data, HTTP_ACCEPT="application/json")

    def test_phone_to_separate_desk_private_oriented_and_replayed_after_stage_change(self):
        page = self.mobile.get(self.order_url)
        self.assertContains(page, 'capture="environment"')
        self.assertContains(page, 'name="gallery_photo"')
        with closing(self.mobile.get("/static/workshop/inspection.js")) as js:
            self.assertEqual(js.status_code, 200)
        start = self.desk.get(self.feed).json()
        self.assertEqual(self.desk.get(self.feed, {"revision": start["revision"]}).status_code, 204)
        result = self.send(self.payload())
        self.assertEqual(result.status_code, 200, result.content)
        record = Inspection.objects.get()
        photo_url = f"/inspection/{record.pk}/photo/"
        self.assertNotIn("archivo", record.photo.name)
        with closing(self.desk.get(photo_url)) as response:
            self.assertEqual(response["Content-Type"], "image/jpeg")
            self.assertIn("no-store", response["Cache-Control"])
            with Image.open(BytesIO(b"".join(response.streaming_content))) as stored:
                self.assertEqual(stored.size, (18, 40))
                self.assertFalse(stored.getexif())
        update = self.desk.get(self.feed, {"revision": start["revision"]}).json()
        self.assertIn("Delantero", update["html"])
        self.assertIn(photo_url, update["html"])
        self.assertEqual(self.desk.get(self.feed, {"revision": update["revision"]}).status_code, 204)
        WorkOrder.objects.filter(pk=self.order.pk).update(status="awaiting_approval")
        replay = self.send(self.payload())
        self.assertEqual(replay.json()["id"], result.json()["id"])
        self.assertEqual(Inspection.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.filter(entity_type="Inspection").count(), 1)
        self.assertEqual(len(list(self.media.rglob("*.jpg"))), 1)
        self.assertEqual(self.send(self.payload(notes="Diferentes")).status_code, 400)
        self.assertEqual(self.desk.get(self.feed, {"revision":update["revision"]}).json()["stage"], "awaiting_approval")
        self.assertEqual(Client().get(photo_url).status_code, 302)
        WorkOrder.objects.filter(pk=self.order.pk).update(assigned_to=self.manager)
        self.assertEqual(self.mobile.get(self.feed).status_code, 404)
        self.assertEqual(self.mobile.get(photo_url).status_code, 404)

    def test_gallery_invalid_fallback_role_and_no_photo(self):
        file = SimpleUploadedFile("prueba.heic", b"archivo ilegible")
        invalid = self.mobile.post(self.upload, self.payload(name="gallery_photo", gallery_photo=file))
        self.assertContains(invalid, 'value="Frenos"')
        self.assertContains(invalid, self.key)
        self.assertContains(invalid, "No se pudo leer la foto")
        bad = self.send(self.payload(submission_key="invalid"))
        self.assertEqual(bad.status_code, 400)
        self.assertFalse(Inspection.objects.exists())
        self.assertEqual(self.send(self.payload(name="gallery_photo")).status_code, 200)
        wrong_actor = self.desk.post(self.upload, self.payload(submission_actor=self.tech.pk), HTTP_ACCEPT="application/json")
        self.assertEqual(wrong_actor.status_code, 409)
        self.mobile.force_login(self.viewer)
        self.assertEqual(self.send(self.payload()).status_code, 403)
        self.mobile.force_login(self.tech)
        resp = self.mobile.post(self.upload, {"area": "Motor", "result": "okay"})
        self.assertRedirects(resp, self.order_url)
        self.assertEqual(Inspection.objects.count(), 2)

    def test_failed_write_removes_private_file_and_allows_retry(self):
        with patch("workshop.services._audit", side_effect=RuntimeError("fallo de prueba")):
            with self.assertRaises(RuntimeError):
                self.send(self.payload())
        self.assertFalse(Inspection.objects.exists())
        self.assertEqual(list(self.media.rglob("*.jpg")), [])
        self.assertEqual(self.send(self.payload()).status_code, 200)
        self.assertEqual(Inspection.objects.count(), 1)
