import hashlib
import json
import tempfile
import uuid
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from commercial.agent_models import AgentCredential, AgentRequest
from scripts import agent_client
from workshop.access import WORKSHOP_AGENT_PATH
from workshop.models import AuditEvent, Customer, Vehicle, WorkOrder


@override_settings(MILENIO_CLOUD=True, CLOUD_HOST="taller.example.test", ROOT_URLCONF="milenio_web.cloud_urls")
class WorkshopAgentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("gerencia")
        self.private = Path(self.enterContext(tempfile.TemporaryDirectory())) / "private"
        customer = Customer.objects.create(name="Persona reservada", phone="555-ficticio")
        vehicle = Vehicle.objects.create(customer=customer, plate="PRIV-123")
        self.order = WorkOrder.objects.create(vehicle=vehicle, number="PRUEBA-1", complaint="Texto privado",
                                             promised_at=timezone.now() - timedelta(hours=1))
        self.other = WorkOrder.objects.create(vehicle=vehicle, number="PRUEBA-2", complaint="Privado",
                                             status=WorkOrder.Status.DELIVERED, promised_at=self.order.promised_at)

    def issue(self, *options):
        dest = self.private / (str(uuid.uuid4()) + ".json")
        output = StringIO()
        call_command("agent_access", "--owner", "gerencia", "--output", str(dest), "--label", "Pruebas",
                     *options, stdout=output)
        grant = json.loads(dest.read_text(encoding="utf-8"))
        self.assertNotIn(grant["token"], output.getvalue())
        self.assertEqual(grant["workshop_url"], "https://taller.example.test")
        credential = AgentCredential.objects.get(pk=grant["credential_id"])
        self.assertEqual(credential.token_hash, hashlib.sha256(grant["token"].encode()).hexdigest())
        return grant

    def post(self, grant, data):
        headers = {"HTTP_AUTHORIZATION": "Bearer " + grant["token"]} if grant else {}
        return self.client.post(WORKSHOP_AGENT_PATH, data, content_type="application/json", **headers)

    def test_aggregate_has_only_counts_and_no_order_metadata(self):
        grant = self.issue("--workshop-summary")
        response = self.post(grant, {"action": "workshop.summary"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        payload = response.json()
        self.assertEqual(set(payload), {"as_of", "by_status", "open_overdue", "open_unassigned"})
        self.assertEqual(payload["open_overdue"], 1)
        self.assertEqual(payload["open_unassigned"], 1)
        self.assertEqual(payload["by_status"]["delivered"], 1)
        self.assertEqual(sum(payload["by_status"].values()), 2)
        self.assertEqual(set(payload["by_status"]), set(WorkOrder.Status.values))
        self.assertEqual(self.post(grant, {"action": "order.status"}).status_code, 403)
        self.assertEqual(self.post(grant, {"action": "order.note"}).status_code, 403)
        self.assertEqual(self.post(grant, {"action": "workshop.summary", "fields": ["name"]}).status_code, 400)

    def test_restricted_note_visible_to_human_retry_and_conflicts(self):
        grant = self.issue("--workshop-order", self.order.number)
        status = self.post(grant, {"action": "order.status"}).json()
        self.assertEqual(status, {"order_id": self.order.pk, "version": 1, "status": "intake"})
        request_id = str(uuid.uuid4())
        note = {"action": "order.note", "expected_version": 1, "request_id": request_id,
                "note": "Confirmar disponibilidad de refacción <prueba>."}
        self.assertEqual(self.post(grant, {**note, "order_id": self.other.pk}).status_code, 400)
        response = self.post(grant, note)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["version"], 2)
        self.assertEqual(self.post(grant, note).json(), response.json())
        self.assertEqual(self.post(grant, {**note, "note": "Otro texto"}).json()["error"], "request_id_conflict")
        self.assertEqual(self.post(grant, {**note, "request_id": str(uuid.uuid4())}).json()["error"], "stale_version")
        event = AuditEvent.objects.get(action="agent_note")
        self.assertEqual(event.pk, response.json()["event_id"])
        self.assertEqual(event.actor, self.owner)
        self.assertEqual(event.after["credential_id"], grant["credential_id"])
        self.assertEqual(event.after["request_id"], request_id)
        self.assertEqual(AgentRequest.objects.count(), 1)
        self.other.refresh_from_db()
        self.assertEqual(self.other.version, 1)
        self.client.force_login(self.owner)
        page = self.client.get(f"/orders/{self.order.pk}/")
        self.assertContains(page, "Nota interna del agente")
        self.assertContains(page, "Agente Pruebas")
        self.assertContains(page, "Confirmar disponibilidad de refacción &lt;prueba&gt;.")
        self.assertNotContains(page, grant["token"])

    def test_different_agent_same_order_cannot_overwrite_stale_or_closed_order(self):
        first = self.issue("--workshop-order", self.order.number)
        second = self.issue("--workshop-order", self.order.number)
        note = {"action": "order.note", "expected_version": 1, "request_id": str(uuid.uuid4()), "note": "Revisar."}
        self.assertEqual(self.post(first, note).status_code, 200)
        self.assertEqual(self.post(second, note).json()["error"], "stale_version")
        WorkOrder.objects.filter(pk=self.order.pk).update(status=WorkOrder.Status.CANCELLED, version=3)
        self.assertEqual(self.post(second, {**note, "expected_version": 3}).json()["error"], "order_closed")
        self.assertEqual(self.post(first, note).status_code, 200)

    def test_credentials_are_isolated_and_rechecked(self):
        grant = self.issue("--workshop-summary")
        summary = {"action": "workshop.summary"}
        self.client.force_login(self.owner)
        self.assertEqual(self.post(None, summary).status_code, 401)
        self.assertEqual(self.post(grant, {"action": "accounts.search"}).status_code, 403)
        self.assertEqual(self.client.post("/agent/v1/action", summary, content_type="application/json",
                                          HTTP_AUTHORIZATION="Bearer " + grant["token"]).status_code, 404)
        row = AgentCredential.objects.filter(pk=grant["credential_id"])
        row.update(scopes=["read", "prepare", "send"])
        self.assertEqual(self.post(grant, summary).status_code, 403)
        row.update(scopes=["workshop.summary"])
        self.owner.is_superuser = False
        self.owner.save()
        self.assertEqual(self.post(grant, summary).status_code, 401)
        self.owner.groups.add(Group.objects.create(name="manager"))
        self.assertEqual(self.post(grant, summary).status_code, 200)
        row.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.post(grant, summary).status_code, 401)
        row.update(expires_at=timezone.now() + timedelta(minutes=1))
        call_command("agent_access", "--revoke", grant["credential_id"], stdout=StringIO())
        self.assertEqual(self.post(grant, summary).status_code, 401)

    def test_bad_inputs_create_no_receipt_or_event(self):
        grant = self.issue("--workshop-order", self.order.number)
        base = {"action": "order.note", "request_id": str(uuid.uuid4()), "expected_version": 1, "note": "Válida"}
        for invalid in ({"request_id": "abc"}, {"expected_version": True}, {"note": "   "}, {"note": "a" * 501},
                        {"note": ""}, {"note": "char\x00"}, {"note": "\ud800"}, {"version": 1}):
            self.assertEqual(self.post(grant, {**base, **invalid}).status_code, 400)
        self.assertEqual(self.post(grant, {**base, "note": "a" * 8200}).status_code, 413)
        self.assertFalse(AgentRequest.objects.exists())
        self.assertFalse(AuditEvent.objects.exists())
        with self.assertRaises(CommandError):
            self.issue("--workshop-order", self.other.number)
        with self.assertRaises(CommandError):
            self.issue("--workshop-summary", "--allow-send")
        with self.assertRaises(CommandError):
            self.issue("--allow-send")

    def test_client_uses_only_credential_origin_and_refuses_insecure_transport(self):
        grant = self.issue("--workshop-summary")
        credentials = self.private / "client.json"
        payload = self.private / "consultar.json"
        request = {"action": "workshop.summary"}
        credentials.write_text(json.dumps(grant), encoding="utf-8")
        payload.write_text(json.dumps(request), encoding="utf-8")
        argv = ["agent_client", "--workshop", "--credential", str(credentials), "--request", str(payload)]
        with patch("sys.argv", argv), patch("scripts.agent_client.urllib.request.build_opener") as build:
            build.return_value.open.return_value = BytesIO(b'{"by_status": {}}')
            with patch("sys.stdout", new_callable=StringIO) as output:
                self.assertIsNone(agent_client.main())
                self.assertNotIn(grant["token"], output.getvalue())
            sent = build.return_value.open.call_args.args[0]
            self.assertEqual(sent.full_url, grant["workshop_url"] + WORKSHOP_AGENT_PATH)
            self.assertEqual(json.loads(sent.data), request)
            self.assertEqual(sent.get_header("Authorization"), "Bearer " + grant["token"])
            build.reset_mock()
            credentials.write_text(json.dumps({**grant, "workshop_url": "http://127.0.0.1"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                agent_client.main()
            build.assert_not_called()
