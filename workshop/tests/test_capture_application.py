"""Images must really update business rows, with preview and concurrency guards."""
import tempfile
from unittest.mock import patch
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from workshop import models as m
from workshop.capture_application import preview, commit, service_rows
from workshop.document_capture import process_one


DATA = {"order_number":"FOTO-REAL-01","customer_name":"Cliente foto","phone":"000123","vehicle_plate":"FOTO123",
        "vehicle_vin":"","vehicle_make":"Nissan","vehicle_model":"Versa","vehicle_year":"2020","odometer":"85000",
        "complaint":"Revisar ruido en frenos","services":"Revisión de frenos\nCambio de aceite"}


class CaptureApplicationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_superuser("apply-manager")
        self.client.force_login(self.manager)

    def capture(self, **kwargs):
        key = str(m.DocumentCapture.objects.count())
        return m.DocumentCapture.objects.create(title="Hoja revisada",kind="order",photo="not-opened.jpg",fingerprint=key,
            uploaded_by=self.manager,reviewed_by=self.manager,reviewed_at=timezone.now(),status="confirmed",data={**DATA,**kwargs})

    def apply(self,capture,selection=None):
        plan,receipt = preview(capture,self.manager,selection or {})
        return commit(capture,self.manager,receipt),receipt

    def existing(self,status="intake"):
        customer = m.Customer.objects.create(name=DATA["customer_name"],phone="previous",email="valid@example.com",notes="Conservar",kind="fleet")
        vehicle = m.Vehicle.objects.create(customer=customer,plate=DATA["vehicle_plate"],make="Nissan",model="Versa",odometer=84000)
        order = m.WorkOrder.objects.create(vehicle=vehicle,number=DATA["order_number"],complaint="Solicitud anterior",status=status,
            assigned_to=self.manager,promised_at=timezone.now()+timedelta(days=1),odometer=84000)
        return customer,vehicle,order

    def test_preview_creates_nothing_and_commit_creates_real_linked_order_once(self):
        capture = self.capture()
        plan,receipt = preview(capture,self.manager,{})
        self.assertEqual([row["action"] for row in plan["changes"]], ["Crear"]*5)
        self.assertEqual((m.Customer.objects.count(),m.Vehicle.objects.count(),m.WorkOrder.objects.count(),m.CapturedService.objects.count(),m.AuditEvent.objects.count()),(0,0,0,0,0))
        result = commit(capture,self.manager,receipt)
        again = commit(capture,self.manager,receipt)
        self.assertEqual(result,again)
        self.assertEqual((m.Customer.objects.count(),m.Vehicle.objects.count(),m.WorkOrder.objects.count(),m.CapturedService.objects.count()),(1,1,1,2))
        capture.refresh_from_db()
        self.assertEqual(capture.status,"applied")
        self.assertEqual(capture.work_order_id,result["order_id"])
        order = m.WorkOrder.objects.get()
        self.assertEqual(order.status,"intake")
        self.assertEqual(order.vehicle.odometer,85000)
        self.assertIsNone(m.CapturedService.objects.first().unit_price)
        self.assertFalse(m.QuoteLine.objects.exists())
        self.assertFalse(m.Payment.objects.exists())
        self.assertTrue(m.AutomationJob.objects.filter(status="pending").exists())
        self.assertContains(self.client.get(f"/orders/{order.pk}/"),"Información recibida en fotos")
        self.assertContains(self.client.get("/data/orders/"),DATA["order_number"])

    def test_blank_fields_preserve_contacts_assignment_and_promised_date(self):
        customer,vehicle,order = self.existing()
        promise = order.promised_at
        capture = self.capture(phone="",vehicle_year="",vehicle_make="",vehicle_model="",services="")
        self.apply(capture)
        customer.refresh_from_db(); order.refresh_from_db()
        self.assertEqual((customer.phone,customer.email,customer.notes,customer.kind),("previous","valid@example.com","Conservar","fleet"))
        self.assertEqual((order.assigned_to_id,order.promised_at),(self.manager.pk,promise))
        self.assertEqual(order.complaint,DATA["complaint"])

    def test_other_photos_of_same_order_link_evidence_without_duplicate_services(self):
        first = self.capture()
        self.apply(first)
        second = self.capture()
        self.apply(second)
        self.assertEqual(m.WorkOrder.objects.count(),1)
        self.assertEqual(m.CapturedService.objects.count(),2)
        self.assertEqual(m.CapturedService.objects.first().documents.count(),2)
        self.assertEqual(m.DocumentCapture.objects.filter(status="applied").count(),2)

    def test_plan_rejects_changes_to_targets_since_preview_and_rolls_back_all_writes(self):
        customer,vehicle,order = self.existing()
        capture = self.capture()
        _,receipt = preview(capture,self.manager,{})
        order.complaint = "Cambio de otro usuario"
        order.save()
        audits = m.AuditEvent.objects.count()
        with self.assertRaisesRegex(ValidationError,"cambiaron"):
            commit(capture,self.manager,receipt)
        customer.refresh_from_db(); vehicle.refresh_from_db(); capture.refresh_from_db()
        self.assertEqual(customer.phone,"previous")
        self.assertEqual(vehicle.odometer,84000)
        self.assertEqual(capture.status,"confirmed")
        self.assertEqual(m.AuditEvent.objects.count(),audits)
        self.assertFalse(m.CapturedService.objects.exists())

    def test_closed_order_and_lower_mileage_do_not_partially_update_catalogs(self):
        customer,vehicle,order = self.existing(status="delivered")
        capture = self.capture()
        with self.assertRaisesRegex(ValidationError,"cerrada"):
            preview(capture,self.manager,{})
        customer.refresh_from_db()
        self.assertEqual(customer.phone,"previous")
        order.status = "intake"; order.save()
        capture.data["odometer"] = "50000"; capture.save()
        with self.assertRaisesRegex(ValidationError,"menor"):
            preview(capture,self.manager,{})
        self.assertEqual(m.AuditEvent.objects.count(),0)

    def test_conflicting_vehicle_and_ambiguous_customer_require_resolution(self):
        customer,vehicle,order = self.existing()
        capture = self.capture(vehicle_plate="DIFFERENT")
        with self.assertRaisesRegex(ValidationError,"no corresponden"):
            preview(capture,self.manager,{})
        order.delete(); vehicle.delete()
        other = m.Customer.objects.create(name=customer.name)
        capture.data = {**DATA}; capture.save()
        with self.assertRaisesRegex(ValidationError,"varias coincidencias"):
            preview(capture,self.manager,{})
        self.apply(capture,{"customer":customer.pk})
        self.assertEqual(m.Vehicle.objects.get().customer_id,customer.pk)

    def test_client_selection_cannot_update_unrelated_customer(self):
        wrong = m.Customer.objects.create(name="Otra persona",phone="unchanged")
        capture = self.capture()
        with self.assertRaisesRegex(ValidationError,"no coinciden"):
            preview(capture,self.manager,{"customer":wrong.pk})
        wrong.refresh_from_db()
        self.assertEqual(wrong.phone,"unchanged")

    def test_repeated_service_with_inconsistent_amounts_requires_resolution(self):
        capture = self.capture()
        capture.service_items = [{"description":"Aceite","kind":"part","part_sku":"SKU-A","quantity":"1","unit_price":"100"},
                                 {"description":"Aceite","kind":"part","part_sku":"SKU-A","quantity":"2","unit_price":"200"}]
        with self.assertRaisesRegex(ValidationError,"distintos"):
            service_rows(capture)

    def test_vehicle_identified_by_vin_can_gain_plate_and_explicit_duplicate_plate_is_resolved(self):
        customer,vehicle,order = self.existing()
        order.delete()
        vehicle.plate=""; vehicle.vin="VIN12345"; vehicle.save()
        capture = self.capture(vehicle_vin="VIN12345")
        self.apply(capture)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.plate,DATA["vehicle_plate"])
        m.Vehicle.objects.create(customer=customer,plate=vehicle.plate,make="Marca",model="Otro")
        second = self.capture(vehicle_vin="VIN12345")
        self.apply(second,{"vehicle":vehicle.pk})
        self.assertEqual(m.WorkOrder.objects.count(),1)

    def test_browser_preview_and_apply_real_database_flow(self):
        capture = self.capture()
        response=self.client.post(f"/capture/{capture.pk}/apply/",{})
        self.assertContains(response,"Revisa los cambios antes de aplicar")
        result=self.client.post(f"/capture/{capture.pk}/apply/",{"stage":"commit","receipt":response.context["receipt"]})
        self.assertEqual(result.status_code,302)
        capture.refresh_from_db()
        self.assertEqual(result.url,f"/orders/{capture.work_order_id}/")
        self.assertContains(self.client.get(result.url),DATA["complaint"])

    def test_same_description_with_distinct_skus_preserves_both_and_preview_prices(self):
        capture = self.capture(services="Aceite\nAceite")
        capture.service_items = [{"description":"Aceite","kind":"part","part_sku":"SKU-A","quantity":"1","unit_price":"100","unit_cost":None},
                                 {"description":"Aceite","kind":"part","part_sku":"SKU-B","quantity":"2","unit_price":"200","unit_cost":None}]
        capture.save()
        rows = service_rows(capture)
        self.assertEqual(len(rows),2)
        plan,receipt = preview(capture,self.manager,{})
        concepts = [row for row in plan["changes"] if row["entity"] == "Servicio solicitado"]
        self.assertEqual([row["fields"]["unit_price"]["after"] for row in concepts],["100","200"])
        commit(capture,self.manager,receipt)
        self.assertEqual(list(m.CapturedService.objects.order_by("part_sku").values_list("unit_price",flat=True)),[Decimal("100"),Decimal("200")])

    def test_wrong_actor_or_modified_receipt_is_rejected_and_applied_cannot_rereview(self):
        capture = self.capture()
        _,receipt = preview(capture,self.manager,{})
        other = User.objects.create_superuser("other-reviewer")
        with self.assertRaisesRegex(ValidationError,"otra captura"):
            commit(capture,other,receipt)
        with self.assertRaises(ValidationError):
            commit(capture,self.manager,receipt+"corrupt")
        commit(capture,self.manager,receipt)
        self.assertEqual(self.client.post(f"/capture/{capture.pk}/",{"version":capture.version,"order_number":"OTHER","complaint":"No","checked":"on"}).status_code,409)
        capture.refresh_from_db()
        self.assertEqual(capture.status,"applied")

    def test_reception_can_apply_but_viewer_cannot(self):
        capture = self.capture()
        advisor = User.objects.create_user("advisor-capture")
        advisor.groups.add(Group.objects.create(name="advisor"))
        plan,receipt = preview(capture,advisor,{})
        result = commit(capture,advisor,receipt)
        self.assertEqual(result["order_id"],m.WorkOrder.objects.get().pk)
        viewer = User.objects.create_user("viewer-capture")
        viewer.groups.add(Group.objects.create(name="viewer"))
        self.client.force_login(viewer)
        self.assertEqual(self.client.post(f"/capture/{capture.pk}/apply/",{"stage":"preview"}).status_code,403)

    def test_visual_result_is_persisted_and_incomplete_provider_has_manual_fallback(self):
        capture = self.capture()
        capture.status="pending"; capture.provider="codex"; capture.model_name="gpt-6-luna"; capture.save()
        with patch("workshop.capture_vision.extract_photo",return_value={"data":{**DATA},"service_items":[{"description":"Servicio visual","kind":"unknown","quantity":None,"unit_price":None,"unit_cost":None,"part_sku":None}],"warnings":[],"receipt":{"provider":"codex","model":"gpt-6-luna","completion_observed":True}}):
            process_one()
        capture.refresh_from_db()
        self.assertEqual(capture.data["services"],"Servicio visual")
        self.assertTrue(capture.extraction["completion_observed"])
        self.assertEqual(capture.status,"review")
        with patch("workshop.capture_vision.provider_status",return_value={"available":False,"message":"Requiere iniciar sesión"}):
            from workshop.tests.test_document_capture import photo
            response=self.client.post("/capture/",{"photo":photo(),"provider":"codex"})
        self.assertContains(response,"Requiere iniciar sesión")
