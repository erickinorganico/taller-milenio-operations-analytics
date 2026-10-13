from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from workshop import models as m
from workshop.capture_inbox import inbox_context
from workshop.capture_views import capture_index
from workshop.tests.test_document_capture import photo


class CaptureInboxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_superuser("inbox-manager", first_name="Recepción")
        cls.other = User.objects.create_user("inbox-other", first_name="Otra persona")

    def setUp(self):
        cache.set("capture:codex-availability", {"available": False, "message": "Lector opcional sin conectar"}, 60)
        self.client.force_login(self.manager)

    def document(self, **values):
        defaults = dict(title="Foto de prueba", uploaded_by=self.manager, status="review",
            fingerprint=f"inbox-{m.DocumentCapture.objects.count()}", photo="synthetic.jpg",
            data={"order_number": "FOTO-01", "complaint": "Ruido", "odometer": "0"})
        return m.DocumentCapture.objects.create(**{**defaults, **values})

    def ids(self, **params):
        return [row["capture"].pk for row in inbox_context(params)["capture_rows"]]

    def test_exception_categories_use_receipts_required_fields_and_queue_age(self):
        failed = self.document(extraction={"error_type": "TimeoutError"})
        empty = self.document(extraction={"completion_observed": False})
        interrupted = self.document(reading_note="La lectura se interrumpió. Reintenta o captura manualmente.")
        reading = self.document(status="reading", reading_started_at=timezone.now() - timedelta(minutes=4))
        no_clock = self.document(status="reading")
        queued = self.document(status="pending", created_at=timezone.now() - timedelta(minutes=4))
        missing = self.document(data={"order_number": "  ", "services": "Aceite"})
        request_missing = self.document(data={"order_number": "OK"})
        good = self.document(service_items=[{"description": "Aceite", "quantity": None, "unit_price": None, "unit_cost": None}])
        confirmed = self.document(status="confirmed", extraction={"error_type": "OldError"})
        applied = self.document(status="applied", data={})
        self.assertCountEqual(self.ids(issue="failed"), [failed.pk, empty.pk, interrupted.pk])
        self.assertCountEqual(self.ids(issue="stalled"), [reading.pk, no_clock.pk, queued.pk])
        self.assertCountEqual(self.ids(issue="missing"), [missing.pk, request_missing.pk])
        self.assertEqual(len(self.ids(issue="exceptions")), 8)
        self.assertFalse(set(self.ids(issue="exceptions")) & {good.pk, confirmed.pk, applied.pk})

    def test_json_null_is_missing_and_structured_services_supply_the_request(self):
        null = self.document(data={"order_number": None, "complaint": "Ruido"})
        valid = self.document(data={"order_number": "OK", "complaint": None, "services": None}, service_items=[{"description": "Frenos"}])
        self.assertEqual(self.ids(issue="missing"), [null.pk])
        self.assertIn(valid.pk, self.ids())

    def test_manual_fallback_is_not_mislabelled_as_a_reader_failure(self):
        manual = self.document(reading_note="Captura manual: completa los campos comparando con la foto.",
            extraction={"error_type": "OldError"}, data={})
        self.assertEqual(self.ids(issue="failed"), [])
        self.assertEqual(self.ids(issue="missing"), [manual.pk])

    def test_retry_resets_wait_age_using_existing_audit_history(self):
        doc = self.document(status="pending", created_at=timezone.now() - timedelta(days=5))
        event = m.AuditEvent.objects.create(actor=self.manager, entity_type="DocumentCapture", entity_id=str(doc.pk), action="retry")
        self.assertEqual(self.ids(issue="stalled"), [])
        m.AuditEvent.objects.filter(pk=event.pk).update(created_at=timezone.now() - timedelta(minutes=4))
        self.assertEqual(self.ids(issue="stalled"), [doc.pk])

    def test_combined_filters_and_summary_are_over_the_selection_not_the_page(self):
        for _ in range(27):
            self.document(title="Frenos", kind="service", data={})
        self.document(title="Frenos", kind="service", uploaded_by=self.other, status="confirmed")
        self.document(title="Motor")
        result = inbox_context({"q": "Frenos", "kind": "service", "uploader": str(self.manager.pk), "issue": "exceptions", "page": "2"})
        self.assertEqual(result["counts"], {"total": 27, "exceptions": 27, "review": 27, "ready": 0})
        self.assertEqual(len(result["capture_rows"]), 2)
        self.assertEqual(result["page"].paginator.count, 27)
        self.assertEqual(parse_qs(result["filter_query"])["issue"], ["exceptions"])
        self.assertEqual(parse_qs(urlsplit(result["all_url"]).query)["uploader"], [str(self.manager.pk)])

    def test_search_folio_customer_plate_and_linked_order(self):
        doc = self.document(data={"order_number": "OLD-35", "customer_name": "Cliente prueba", "vehicle_plate": "ABC003", "services": "Frenos"})
        for query in ("OLD-35", "Cliente prueba", "ABC003"):
            self.assertEqual(self.ids(q=query), [doc.pk])
        customer = m.Customer.objects.create(name="Sintético")
        vehicle = m.Vehicle.objects.create(customer=customer, plate="SYN1")
        order = m.WorkOrder.objects.create(vehicle=vehicle, number="LINKED-4")
        doc.work_order = order
        doc.save(update_fields=["work_order"])
        self.assertEqual(self.ids(q="LINKED-4"), [doc.pk])

    def test_date_end_includes_late_evening_in_tijuana(self):
        zone = ZoneInfo("America/Tijuana")
        inside = self.document(created_at=datetime(2026, 10, 13, 23, 59, tzinfo=zone))
        self.document(created_at=datetime(2026, 10, 14, 0, 0, tzinfo=zone))
        self.document(created_at=datetime(2026, 10, 12, 23, 59, tzinfo=zone))
        with timezone.override(zone):
            self.assertEqual(self.ids(start="2026-10-13", end="2026-10-13"), [inside.pk])

    def test_invalid_filters_render_errors_and_no_unintended_results(self):
        self.document()
        for params in ({"status": "bad"}, {"uploader": "999999"}, {"issue": "bad"},
                       {"start": "oops"}, {"start": "2026-10-14", "end": "2026-10-13"}, {"end": "9999-12-31"}):
            with self.subTest(params=params):
                response = self.client.get("/capture/", params)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["filters"].errors)
                self.assertEqual(response.context["page"].paginator.count, 0)

    def test_get_is_read_only_and_lists_next_actions(self):
        doc = self.document(data={}, extraction={"completion_observed": False})
        before = list(m.DocumentCapture.objects.values())
        audits = m.AuditEvent.objects.count()
        with patch("workshop.document_capture.process_one") as process:
            response = self.client.get("/capture/", {"issue": "exceptions"})
        process.assert_not_called()
        self.assertContains(response, "Resolver lectura")
        self.assertEqual(list(m.DocumentCapture.objects.values()), before)
        self.assertEqual(m.AuditEvent.objects.count(), audits)
        self.assertEqual(m.WorkOrder.objects.count(), 0)
        self.assertContains(response, f"/capture/{doc.pk}/")
        self.assertEqual(response.context["form"].initial["provider"], "local")

    def test_heartbeat_absent_stale_and_recent_are_distinct(self):
        for worker, expected in (({"recent": False, "state": "unknown"}, "Estado del lector sin comprobar"),
            ({"recent": False, "age_seconds": 800}, "Sin señal reciente del lector"),
            ({"recent": True, "age_seconds": 3}, "Señal reciente del lector")):
            with patch("milenio_web.worker_health.status", return_value={"workers": {"documents": worker}}):
                self.assertContains(self.client.get("/capture/"), expected)

    def test_unavailable_upload_provider_keeps_the_filtered_inbox_and_error(self):
        self.document()
        with patch("workshop.capture_vision.provider_status", return_value={"available": False, "message": "Lector no disponible"}):
            response = self.client.post("/capture/?status=review", {"provider": "codex", "photo": photo()})
        self.assertContains(response, "Lector no disponible")
        self.assertEqual(response.context["page"].paginator.count, 1)
        self.assertEqual(m.DocumentCapture.objects.count(), 1)

    def test_role_guards_and_query_escaping(self):
        self.document(title="<script>alert(1)</script>")
        response = self.client.get("/capture/")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        for role in ("viewer", "technician", "finance"):
            user = User.objects.create_user("denied-" + role)
            user.groups.add(Group.objects.get_or_create(name=role)[0])
            self.client.force_login(user)
            self.assertEqual(self.client.get("/capture/", {"issue": "exceptions"}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get("/capture/").status_code, 302)

    def test_queries_are_bounded_as_visible_rows_grow(self):
        self.document()
        request = RequestFactory().get("/capture/")
        request.user = self.manager
        with CaptureQueriesContext(connection) as single:
            self.assertEqual(capture_index(request).status_code, 200)
        for _ in range(24):
            self.document(data={})
        with CaptureQueriesContext(connection) as full:
            self.assertEqual(capture_index(request).status_code, 200)
        self.assertEqual(len(single), len(full))
        self.assertLessEqual(len(full), 5)
