import uuid
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import RequestFactory, TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from workshop import models as m
from workshop.ai_capture import (admission_problem, configure_photo_ai, finish_reading,
    photo_ai_settings, recover_readings, reserve_reading, usage_for_day)
from workshop.ai_capture_views import photo_ai_panel
from workshop.document_capture import process_one
from workshop.tests.test_document_capture import photo


class PhotoAIControlsTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_superuser("ai-controls-manager")
        self.advisor = User.objects.create_user("ai-controls-advisor")
        self.advisor.groups.add(Group.objects.get_or_create(name="advisor")[0])
        self.client.force_login(self.actor)
        cache.clear()

    def policy(self, **values):
        policy, _ = m.PhotoAISettings.objects.get_or_create(pk=1)
        for key, value in {"enabled": True, **values}.items():
            setattr(policy, key, value)
        policy.save()
        return policy

    def doc(self, **values):
        return m.DocumentCapture.objects.create(title="Hoja ficticia", fingerprint=uuid.uuid4().hex,
            photo="not-opened-synthetic.jpg", uploaded_by=self.actor,
            **{"provider": "codex", "model_name": "gpt-6-luna", **values})

    def reserve(self, doc=None):
        return reserve_reading(doc or self.doc(), uuid.uuid4().hex)

    def config(self, **values):
        return {"version": 1, "model": "gpt-6-luna", "daily_attempt_limit": 10, "per_document_limit": 2,
                "daily_token_budget": 25000, **values}

    def complete(self, reading, *, inputs=100, outputs=25):
        finish_reading(reading, {"usage": {"input_tokens": inputs, "output_tokens": outputs}})

    def test_get_panel_does_not_create_policy_authenticate_or_run_models(self):
        with patch("workshop.capture_vision.provider_status") as status, patch("workshop.capture_vision.extract_photo") as extract:
            response = self.client.get("/capture/ai/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sesión sin comprobar")
        self.assertContains(response, "Lecturas con IA pausadas")
        self.assertEqual(m.PhotoAISettings.objects.count(), 0)
        self.assertEqual(m.PhotoAIReading.objects.count(), 0)
        status.assert_not_called()
        extract.assert_not_called()

    def test_manager_updates_only_whitelisted_settings_and_audits_version(self):
        response = self.client.post("/capture/ai/configure/", self.config(enabled="on", model="gpt-6.1-sol", secret_token="do-not-store"))
        self.assertEqual(response.status_code, 302)
        policy = photo_ai_settings()
        self.assertTrue(policy.enabled)
        self.assertEqual(policy.model, "gpt-6.1-sol")
        self.assertEqual(policy.version, 2)
        self.assertEqual(policy.updated_by, self.actor)
        audit = m.AuditEvent.objects.get(entity_type="PhotoAISettings")
        self.assertNotIn("do-not-store", str(audit.after))
        stale = self.client.post("/capture/ai/configure/", self.config(enabled="on"))
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(photo_ai_settings().model, "gpt-6.1-sol")

    def test_limits_require_valid_positive_ranges_and_supported_models(self):
        for values in ({"daily_attempt_limit": 0}, {"per_document_limit": 6}, {"daily_token_budget": -1}, {"model": "other"}):
            with self.subTest(values=values):
                self.assertEqual(self.client.post("/capture/ai/configure/", self.config(**values)).status_code, 400)
        self.assertEqual(m.PhotoAISettings.objects.count(), 0)

    def test_advisor_can_inspect_but_not_change_or_verify_connection(self):
        self.client.force_login(self.advisor)
        self.assertEqual(self.client.get("/capture/ai/").status_code, 200)
        self.assertNotContains(self.client.get("/capture/ai/"), "Guardar configuración")
        for url in ("/capture/ai/configure/", "/capture/ai/check/"):
            self.assertEqual(self.client.post(url, self.config()).status_code, 403)
        with self.assertRaises(PermissionDenied):
            configure_photo_ai(actor=self.advisor, version=1, values={k:v for k,v in self.config(enabled=True).items() if k != "version"})

    def test_viewer_denied_and_post_routes_have_csrf_and_method_guards(self):
        viewer = User.objects.create_user("ai-controls-viewer")
        viewer.groups.add(Group.objects.get_or_create(name="viewer")[0])
        self.client.force_login(viewer)
        self.assertEqual(self.client.get("/capture/ai/").status_code, 403)
        self.client.force_login(self.actor)
        self.assertEqual(self.client.get("/capture/ai/configure/").status_code, 405)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.actor)
        self.assertEqual(csrf.post("/capture/ai/configure/", self.config()).status_code, 403)
        self.assertEqual(csrf.post("/capture/ai/check/").status_code, 403)

    def test_verifying_connection_does_not_consume_a_reading_or_enable_ai(self):
        with patch("workshop.capture_vision.provider_status", return_value={"available":True,"auth_method":"chatgpt","message":"Sesión comprobada"}) as status:
            response = self.client.post("/capture/ai/check/")
        self.assertEqual(response.status_code, 302)
        status.assert_called_once_with("codex")
        self.assertEqual(m.PhotoAIReading.objects.count(), 0)
        self.assertFalse(photo_ai_settings().enabled)
        self.assertTrue(cache.get("capture:codex-availability")["available"])

    def test_paused_default_blocks_worker_without_calling_model(self):
        doc = self.doc()
        with patch("workshop.capture_vision.extract_photo") as extract:
            self.assertTrue(process_one())
        extract.assert_not_called()
        doc.refresh_from_db()
        self.assertEqual(doc.status, "review")
        self.assertEqual(doc.extraction["error_type"], "AIControlBlocked")
        self.assertEqual(m.PhotoAIReading.objects.count(), 0)

    def test_daily_attempt_limit_is_durable_and_failed_attempts_are_not_refunded(self):
        self.policy(daily_attempt_limit=1)
        reading = self.reserve()
        finish_reading(reading, {"usage":{"input_tokens":0,"output_tokens":0}}, error_code="failed")
        self.assertEqual(usage_for_day()["attempts"], 1)
        with self.assertRaisesMessage(ValidationError, "límite diario"):
            self.reserve()
        self.assertEqual(m.PhotoAIReading.objects.count(), 1)

    def test_token_budget_blocks_next_reading_but_does_not_claim_to_cap_last_response(self):
        self.policy(daily_token_budget=50)
        self.complete(self.reserve(), inputs=100, outputs=30)
        self.assertEqual(usage_for_day()["known_tokens"], 130)
        with self.assertRaisesMessage(ValidationError, "presupuesto"):
            self.reserve()

    def test_missing_usage_keeps_unknown_values_and_blocks_more_reads(self):
        self.policy()
        reading = self.reserve()
        finish_reading(reading, {"usage": {"input_tokens":8}})
        reading.refresh_from_db()
        self.assertEqual(reading.input_tokens, 8)
        self.assertIsNone(reading.output_tokens)
        self.assertEqual(usage_for_day()["unknown"], 1)
        with self.assertRaisesMessage(ValidationError, "desconocido"):
            self.reserve()
        self.assertContains(self.client.get("/capture/ai/"), "Consumo no informado completamente")

    def test_one_in_flight_reading_blocks_another_admission_and_limits_never_reset_on_retry(self):
        self.policy(per_document_limit=1)
        doc = self.doc()
        reading = self.reserve(doc)
        with self.assertRaises(ValidationError):
            self.reserve()
        self.complete(reading)
        with self.assertRaisesMessage(ValidationError, "Esta foto"):
            self.reserve(doc)
        self.policy(model="gpt-6.1-sol")
        doc.model_name="gpt-6.1-sol"
        doc.save()
        with self.assertRaisesMessage(ValidationError, "Esta foto"):
            self.reserve(doc)

    def test_budget_changes_do_not_reset_usage_or_refund_started_work(self):
        self.policy()
        reading = self.reserve()
        self.complete(reading)
        self.client.post("/capture/ai/configure/", self.config(enabled="on", daily_attempt_limit=1))
        self.assertEqual(usage_for_day()["attempts"], 1)
        self.assertTrue(admission_problem(photo_ai_settings(), usage_for_day()))

    def test_interrupted_reading_stays_charged_with_unknown_consumption(self):
        self.policy()
        reading = self.reserve()
        m.PhotoAIReading.objects.filter(pk=reading.pk).update(started_at=timezone.now()-timedelta(minutes=4))
        recover_readings()
        reading.refresh_from_db()
        self.assertEqual(reading.state, "failed")
        self.assertEqual(usage_for_day()["attempts"], 1)
        self.assertEqual(usage_for_day()["unknown"], 1)

    def test_tijuana_day_rollover_preserves_history_and_reopens_daily_capacity(self):
        self.policy(daily_attempt_limit=1)
        zone=ZoneInfo("America/Tijuana")
        with timezone.override(zone), patch("workshop.ai_capture.timezone.localdate", return_value=datetime(2026,10,13).date()):
            reading=self.reserve()
            self.complete(reading)
        with timezone.override(zone), patch("workshop.ai_capture.timezone.localdate", return_value=datetime(2026,10,14).date()):
            self.assertEqual(usage_for_day()["attempts"],0)
            self.complete(self.reserve())
        self.assertEqual(m.PhotoAIReading.objects.count(),2)

    def test_blocked_external_upload_is_not_queued_but_local_ocr_still_works(self):
        with patch("workshop.capture_vision.provider_status") as status:
            response = self.client.post("/capture/", {"provider":"codex", "photo":photo()})
        status.assert_not_called()
        self.assertContains(response, "pausada")
        self.assertEqual(m.DocumentCapture.objects.count(),0)
        self.client.post("/capture/", {"provider":"local", "photo":photo()})
        self.assertTrue(process_one(reader=lambda path: "Orden: LOCAL-1\nSolicitud: Prueba"))
        self.assertEqual(m.PhotoAIReading.objects.count(),0)

    def test_service_denies_untrusted_keys_and_invalid_limits(self):
        for values in (dict(enabled=True, model="invalid", daily_attempt_limit=1, per_document_limit=1,daily_token_budget=1),
                       dict(enabled=True,model="gpt-6-luna",daily_attempt_limit=True,per_document_limit=1,daily_token_budget=1)):
            with self.assertRaises(ValidationError):
                configure_photo_ai(actor=self.actor,version=1,values=values)

    def test_tokens_reject_boolean_negative_or_unbounded_counts(self):
        self.policy()
        reading=self.reserve()
        finish_reading(reading, {"usage":{"input_tokens": True,"output_tokens":10**25}})
        reading.refresh_from_db()
        self.assertIsNone(reading.input_tokens)
        self.assertIsNone(reading.output_tokens)

    def test_panel_queries_do_not_grow_with_history_rows(self):
        self.policy()
        self.complete(self.reserve())
        request=RequestFactory().get("/capture/ai/")
        request.user=self.actor
        with CaptureQueriesContext(connection) as single:
            self.assertEqual(photo_ai_panel(request).status_code,200)
        doc=self.doc()
        m.PhotoAIReading.objects.bulk_create([m.PhotoAIReading(capture=doc,lease=uuid.uuid4().hex,model="gpt-6-luna",day=timezone.localdate(),state="completed",input_tokens=100,output_tokens=25) for _ in range(24)])
        with CaptureQueriesContext(connection) as full:
            self.assertEqual(photo_ai_panel(request).status_code,200)
        self.assertEqual(len(single),len(full))
        self.assertLessEqual(len(full),5)

    def test_new_upload_uses_selected_sol_model_and_known_failed_usage_stays_charged(self):
        self.policy(model="gpt-6.1-sol")
        with patch("workshop.capture_vision.provider_status", return_value={"available":True,"message":"ChatGPT"}):
            response=self.client.post("/capture/",{"provider":"codex","photo":photo()})
        self.assertEqual(response.status_code,302)
        doc=m.DocumentCapture.objects.get()
        self.assertEqual(doc.model_name,"gpt-6.1-sol")
        failure=ValidationError("Transcripción inválida")
        failure.extraction_receipt={"usage":{"input_tokens":100,"output_tokens":20}}
        with patch("workshop.capture_vision.extract_photo",side_effect=failure):
            self.assertTrue(process_one())
        doc.refresh_from_db()
        reading=m.PhotoAIReading.objects.get()
        self.assertEqual(reading.state,"failed")
        self.assertEqual(reading.input_tokens,100)
        self.assertEqual(usage_for_day()["known_tokens"],120)
        self.assertEqual(usage_for_day()["unknown"],0)
        self.assertEqual(doc.status,"review")
        self.assertFalse(doc.data["order_number"])

    def test_pause_after_reservation_prevents_cli_and_preserves_admission_count(self):
        self.policy()
        self.doc()
        original=reserve_reading
        def pause(capture,lease):
            reading=original(capture,lease)
            m.PhotoAISettings.objects.filter(pk=1).update(enabled=False)
            return reading
        with patch("workshop.ai_capture.reserve_reading",side_effect=pause), patch("workshop.capture_vision.extract_photo") as extract:
            self.assertTrue(process_one())
        extract.assert_not_called()
        self.assertEqual(usage_for_day()["attempts"],1)
        self.assertEqual(usage_for_day()["known_tokens"],0)
        self.assertEqual(usage_for_day()["unknown"],0)
