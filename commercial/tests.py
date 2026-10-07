import csv
import io
import json
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.utils import timezone
from . import services as s
from .models import BusinessContact, Evidence, FleetProfile, SalesAccount, SalesOpportunity, SalesProposal, Suppression
from .rules import domain_for, qualify


class CommercialTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_superuser("commercial-test", password="Only-for-unit-tests-487")
        self.client.force_login(self.actor)
        self.account = s.create_account({"name": "Empresa ficticia", "website": "https://example.test", "city": "Tijuana", "next_action": "Confirmar unidades", "next_action_on": timezone.localdate()}, self.actor)

    def current(self):
        return SalesAccount.objects.select_related("fleet").get(pk=self.account.pk)

    def evidence(self, topic, text="Confirmado directamente", reviewed=True):
        a = self.current()
        return s.add_record(a.pk, a.version, "evidence", {"topic": topic, "source_note": "Conversación ficticia de prueba", "excerpt": text, "reviewed": reviewed}, self.actor)

    def compatible(self, fuel="gasoline", vehicle_type="light", compatible_units=5):
        identity = self.evidence("identity")
        vehicles = self.evidence("vehicles")
        need = self.evidence("need")
        a = self.current()
        s.update_account(a.pk, a.version, {"identity_confirmed": True}, self.actor)
        a = self.current()
        s.add_record(a.pk, a.version, "contact", {"name": "Compras", "email": "compras@example.test", "source_note": "Proporcionado en conversación ficticia", "published_business": True}, self.actor)
        a = self.current()
        s.update_fleet(a.pk, a.version, {"fuel": fuel, "vehicle_type": vehicle_type, "compatible_units": compatible_units, "total_units": 10, "vehicle_evidence": vehicles, "need_confirmed": True, "need_evidence": need}, self.actor)
        return self.current()

    def proposal(self, service="mechanics"):
        a = self.current()
        op = s.add_record(a.pk, a.version, "opportunity", {"title": "Primera atención ficticia", "service": service}, self.actor)
        a = self.current()
        return s.create_proposal(a.pk, a.version, {"opportunity": op, "scope": "Una unidad compatible, alcance ficticio", "terms": "Solo datos de prueba", "amount": Decimal("900.00"), "valid_until": timezone.localdate()+timedelta(days=7)}, self.actor)

    def test_unknown_is_not_qualified(self):
        self.assertFalse(qualify(self.current())["mechanics"])
        self.assertFalse(qualify(self.current())["towing"])

    def test_draft_progression_is_read_only_and_stops_at_three(self):
        from .outreach import prepare
        from .models import Interaction, AuditEvent
        a = self.compatible()
        before = AuditEvent.objects.count()
        self.assertEqual(prepare(a)['draft_label'], 'Primer contacto')
        self.assertEqual(AuditEvent.objects.count(), before)
        self.assertEqual(Interaction.objects.count(), 0)
        for i, label in enumerate(['Primer seguimiento', 'Último seguimiento']):
            Interaction.objects.create(account=a, kind='sent', summary='Contacto ficticio', occurred_at=timezone.now()-timedelta(days=12-i*4), created_by=self.actor)
            self.assertEqual(prepare(a)['draft_label'], label)
            self.assertIsNotNone(prepare(a)['suggested_on'])
        Interaction.objects.create(account=a, kind='sent', summary='Tercer contacto ficticio', created_by=self.actor)
        self.assertFalse(prepare(a)['eligible'])

    def test_reply_meeting_bounce_stop_cold_drafts_even_after_later_send(self):
        from .outreach import prepare
        from .models import Interaction
        a = self.compatible()
        for kind in ['reply', 'meeting', 'bounce']:
            event = Interaction.objects.create(account=a, kind=kind, summary='Resultado ficticio', created_by=self.actor)
            later = Interaction.objects.create(account=a, kind='sent', summary='No reiniciar automáticamente', created_by=self.actor)
            self.assertFalse(prepare(a)['eligible'])
            event.delete()
            later.delete()

    def test_email_draft_requires_email_not_just_phone(self):
        from .outreach import prepare
        a = self.compatible()
        a.contacts.update(email='', phone='6640000000')
        self.assertTrue(qualify(a)['exploratory'])
        self.assertFalse(prepare(a)['eligible'])

    def test_drafts_do_not_restart_closed_or_active_accounts(self):
        from .outreach import prepare
        a = self.compatible()
        for stage in ['lost', 'conversation', 'qualified', 'proposal', 'pilot', 'active']:
            a.stage = stage
            self.assertFalse(prepare(a)['eligible'])

    def test_draft_segment_and_weekday_spacing(self):
        from datetime import date
        from .outreach import opening_for, weekdays_after
        self.assertIn('transportistas externos', opening_for('Mensajería')[1])
        self.assertIn('visitantes', opening_for('Plazas y alianzas')[1])
        self.assertNotIn('mecánica', opening_for('Plazas y alianzas')[1])
        self.assertEqual(weekdays_after(date(2026, 10, 2), 4), date(2026, 10, 8))

    def test_gasoline_confirmed_and_mixed_subset(self):
        a = self.compatible("mixed")
        self.assertTrue(qualify(a)["mechanics"])
        self.assertEqual(a.fleet.compatible_units, 5)
        self.assertFalse(qualify(a)["towing"])

    def test_excluded_fuels_and_trucks(self):
        for fuel, kind in [("diesel", "light"), ("electric", "light"), ("hybrid", "light"), ("gasoline", "truck")]:
            with self.subTest(fuel=fuel, kind=kind):
                f = self.current().fleet
                f.fuel, f.vehicle_type, f.compatible_units = fuel, kind, 0
                f.save()
                self.assertFalse(qualify(self.current())["mechanics"])

    def test_no_fabricated_compatibility_count(self):
        a = self.current()
        with self.assertRaises(ValidationError): s.update_fleet(a.pk, a.version, {"fuel": "diesel", "vehicle_type": "light", "compatible_units": 4}, self.actor)
        with self.assertRaises(ValidationError): s.update_fleet(a.pk, a.version, {"fuel": "gasoline", "vehicle_type": "light", "total_units": 2, "compatible_units": 4}, self.actor)

    def test_unreviewed_and_cross_account_evidence_rejected(self):
        unreviewed = self.evidence("vehicles", reviewed=False)
        a = self.current()
        with self.assertRaises(ValidationError): s.update_fleet(a.pk, a.version, {"vehicle_evidence": unreviewed}, self.actor)
        other = s.create_account({"name": "Otra", "website": "https://other.test"}, self.actor)
        evidence = Evidence.objects.create(account=other, topic="vehicles", source_note="test", excerpt="test", reviewed=True, created_by=self.actor)
        with self.assertRaises(ValidationError): s.update_fleet(a.pk, a.version, {"vehicle_evidence": evidence}, self.actor)

    def test_towing_separate_from_mechanics(self):
        a = self.compatible("diesel", "truck", 0)
        coverage = self.evidence("coverage")
        a = self.current()
        s.update_fleet(a.pk, a.version, {"towing_confirmed": True, "towing_evidence": coverage}, self.actor)
        result = qualify(self.current())
        self.assertTrue(result["towing"])
        self.assertFalse(result["mechanics"])

    def test_identity_checkbox_alone_not_enough(self):
        a = self.current()
        a.identity_confirmed = True
        a.save()
        self.assertFalse(qualify(self.current())["exploratory"])

    def test_stale_version_cannot_overwrite(self):
        a = self.current()
        s.update_account(a.pk, a.version, {"name": "Primero"}, self.actor)
        with self.assertRaises(ValidationError): s.update_account(a.pk, a.version, {"name": "Segundo"}, self.actor)
        self.assertEqual(self.current().name, "Primero")

    def test_optout_cancels_action_and_blocks_drafts_and_proposal(self):
        a = self.compatible()
        proposal = self.proposal()
        a = self.current()
        s.add_interaction(a.pk, a.version, {"kind": "optout", "summary": "No contactar", "occurred_at": timezone.now()}, self.actor)
        a = self.current()
        self.assertEqual(a.stage, "suppressed")
        self.assertIsNone(a.next_action_on)
        self.assertFalse(qualify(a)["exploratory"])
        with self.assertRaises(ValidationError): s.change_stage(a.pk, a.version, "research", self.actor)
        with self.assertRaises(ValidationError): s.accept_proposal(a.pk, a.version, proposal.pk, "test", self.actor)
        self.assertNotContains(self.client.get(f"/commercial/{a.pk}/draft/"), "Asunto:")

    def test_suppressed_email_blocks_another_account(self):
        a = self.compatible()
        s.add_interaction(a.pk, a.version, {"kind": "optout", "summary": "Baja", "occurred_at": timezone.now()}, self.actor)
        other = s.create_account({"name": "Duplicada", "website": "https://alternate.test"}, self.actor)
        BusinessContact.objects.create(account=other, name="Compras", email="compras@example.test", source_note="test")
        self.assertEqual(qualify(other)["label"], "No contactar")

    def test_reply_and_bounce_clear_followup(self):
        a = self.compatible()
        s.add_interaction(a.pk, a.version, {"kind": "reply", "summary": "Respondió", "occurred_at": timezone.now()}, self.actor)
        self.assertIsNone(self.current().next_action_on)
        a = self.current()
        s.add_interaction(a.pk, a.version, {"kind": "bounce", "summary": "Rebote", "occurred_at": timezone.now()}, self.actor)
        self.assertEqual(a.contacts.first().deliverability, "bounced")

    def test_proposal_guard_and_revision(self):
        with self.assertRaises(ValidationError): self.proposal()
        self.compatible()
        proposal = self.proposal()
        a = self.current()
        second = s.create_proposal(a.pk, a.version, {"opportunity": proposal.opportunity, "scope": "Nuevo alcance", "terms": "Nuevas condiciones", "amount": Decimal("1200"), "valid_until": timezone.localdate()}, self.actor)
        self.assertEqual(second.revision, 2)
        a = self.current()
        with self.assertRaises(ValidationError): s.accept_proposal(a.pk, a.version, proposal.pk, "Vieja", self.actor)
        s.accept_proposal(a.pk, a.version, second.pk, "Cliente autorizó por teléfono, prueba", self.actor)

    def test_handoff_idempotent_and_order_same_customer(self):
        from workshop.models import Customer, Vehicle, WorkOrder
        self.compatible()
        proposal = self.proposal()
        a = self.current()
        s.accept_proposal(a.pk, a.version, proposal.pk, "Autorización ficticia", self.actor)
        a = self.current()
        customer = s.handoff(a.pk, a.version, self.actor)
        a = self.current()
        self.assertEqual(s.handoff(a.pk, a.version, self.actor).pk, customer.pk)
        self.assertEqual(Customer.objects.count(), 1)
        other = Customer.objects.create(name="Otra empresa")
        vehicle = Vehicle.objects.create(customer=other, make="Marca", model="Modelo")
        order = WorkOrder.objects.create(vehicle=vehicle, number="TEST-1", complaint="Prueba")
        with self.assertRaises(ValidationError): s.link_service(a.pk, a.version, proposal.opportunity, order, None, self.actor)
        vehicle.customer = customer
        vehicle.save()
        s.link_service(a.pk, a.version, proposal.opportunity, order, None, self.actor)
        proposal.opportunity.refresh_from_db()
        self.assertEqual(proposal.opportunity.status, "won")

    def csv_bytes(self, rows):
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(s.CSV_FIELDS)
        writer.writerows(rows)
        return out.getvalue().encode()

    def test_import_idempotent_and_atomic(self):
        raw = self.csv_bytes([["", "Nueva", "https://new.test", "Tijuana", "Técnicos", "manual", "", ""]])
        self.assertEqual(s.import_candidates(raw, self.actor)["created"], 1)
        self.assertTrue(s.import_candidates(raw, self.actor)["repeated"])
        count = SalesAccount.objects.count()
        bad = self.csv_bytes([["", "Otra nueva", "https://more.test", "Tijuana", "Técnicos", "manual", "", ""], ["", "Error", "invalid", "", "", "", "", ""]])
        with self.assertRaises(ValidationError): s.import_candidates(bad, self.actor)
        self.assertEqual(SalesAccount.objects.count(), count)

    def test_shared_domain_preserves_accounts_and_platform_not_identity(self):
        self.assertEqual(domain_for("HTTPS://WWW.Example.Test/contact"), "example.test")
        other = s.create_account({"name": "Otra sucursal", "website": "https://www.example.test/contact"}, self.actor)
        self.assertNotEqual(other.pk, self.account.pk)
        self.assertEqual(other.domain, self.account.domain)
        with self.assertRaises(ValidationError): domain_for("https://facebook.com/empresa")

    def test_export_formula_escape(self):
        self.assertEqual(s.safe_cell("=HYPERLINK()"), "'=HYPERLINK()")
        self.assertEqual(s.safe_cell("  +1"), "'  +1")

    def test_pages_and_permissions(self):
        self.assertEqual(self.client.get("/static/workshop/commercial.css").status_code, 200)
        for path in ["/commercial/", "/commercial/new/", "/commercial/import/", "/commercial/research/", f"/commercial/{self.account.pk}/", f"/commercial/{self.account.pk}/draft/", "/commercial/export/"]:
            with self.subTest(path=path): self.assertEqual(self.client.get(path).status_code, 200)
        viewer = User.objects.create_user("restricted")
        viewer.groups.add(Group.objects.create(name="technician"))
        self.client.force_login(viewer)
        self.assertEqual(self.client.get("/commercial/").status_code, 403)
        self.assertEqual(self.client.get("/commercial/export/").status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get("/commercial/").status_code, 302)

    def test_csrf_required_and_get_no_mutation(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.actor)
        self.assertEqual(csrf.post(f"/commercial/{self.account.pk}/", {"action": "stage", "stage": "lost", "version": 1}).status_code, 403)
        before = self.current().version
        self.client.get(f"/commercial/{self.account.pk}/")
        self.assertEqual(self.current().version, before)

    def test_extract_replay_no_duplicate_and_no_inference(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        report = {"schema": "milenio-research-v1", "pages": [{"url": "https://example.test/", "status": "ok", "text": "Servicios de reparto", "captured_at": timezone.now().isoformat()}]}
        for _ in range(2):
            a = self.current()
            response = self.client.post(f"/commercial/{a.pk}/extract/", {"version": a.version, "file": SimpleUploadedFile("report.json", json.dumps(report).encode())})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(Evidence.objects.filter(topic="website").count(), 1)
        self.assertFalse(Evidence.objects.get(topic="website").reviewed)
        self.assertEqual(self.current().fleet.fuel, "unknown")

    def test_post_bad_data_does_not_mutate(self):
        response = self.client.post(f"/commercial/{self.account.pk}/", {"action": "contact", "version": 1, "contact-name": "Sin procedencia", "contact-email": "valid@example.test", "contact-deliverability": "unknown"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(BusinessContact.objects.count(), 0)

    def test_contact_correction_and_view_binding(self):
        response = self.client.post(f"/commercial/{self.account.pk}/", {"action": "contact", "version": 1, "contact-name": "Compras", "contact-email": "old@example.test", "contact-source_note": "Contacto proporcionado por empresa", "contact-published_business": "on", "contact-deliverability": "unknown"})
        self.assertEqual(response.status_code, 302)
        contact = self.account.contacts.get()
        a = self.current()
        s.add_record(a.pk, a.version, "contact", {"existing_contact": contact, "name": "Compras", "email": "new@example.test", "source_note": "Corrección confirmada por teléfono", "published_business": True, "deliverability": "confirmed"}, self.actor)
        self.assertEqual(self.account.contacts.count(), 1)
        self.assertEqual(self.account.contacts.get().email, "new@example.test")

    def test_seed_never_writes_live(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from django.test import override_settings
        with override_settings(MILENIO_MODE="live"), self.assertRaises(CommandError): call_command("seed_commercial_demo")

    def test_stale_browser_write_returns_error(self):
        a = self.current()
        s.update_account(a.pk, a.version, {"notes": "Primera edición"}, self.actor)
        response = self.client.post(f"/commercial/{a.pk}/", {"action": "stage", "version": a.version, "stage-stage": "lost"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.current().stage, "research")

    def test_extract_wrong_domain_does_not_add_partial_evidence(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        pages = [{"url": "https://example.test/", "status": "ok", "text": "Primer texto", "captured_at": timezone.now().isoformat()}, {"url": "https://other.test/", "status": "ok", "text": "Texto ajeno", "captured_at": timezone.now().isoformat()}]
        self.client.post(f"/commercial/{self.account.pk}/extract/", {"version": 1, "file": SimpleUploadedFile("report.json", json.dumps({"schema": "milenio-research-v1", "pages": pages}).encode())})
        self.assertEqual(self.account.evidence.count(), 0)
