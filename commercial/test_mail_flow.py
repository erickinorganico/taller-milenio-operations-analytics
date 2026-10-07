from datetime import datetime, timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from .models import (SalesAccount, FleetProfile, BusinessContact, Evidence, Interaction,
                     Mailbox, MailEnrollment, MailMessage, MailInbound, MailWorkerLease, Suppression)
from . import mail_flow as flow
from .gmail import parse_message, GmailClient, b64decode, protect


class FakeGmail:
    def __init__(self): self.sent = []; self.items = []; self.found = None; self.failure = False
    def thread(self, thread): return self.items
    def discover(self, email, since): return [m for m in self.items if m['date'] >= since]
    def find_sent(self, rfc): return self.found
    def send(self, message, sender):
        self.sent.append(message.pk)
        if self.failure: raise TimeoutError()
        return {'id': 'provider' + str(len(self.sent)), 'threadId': 'thread1'}


class MailFlowTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser('manager', password='test-only-4477')
        self.box = Mailbox.objects.create(owner=self.actor, email='milenio@example.test', connected=True, enabled=True)
        self.clock = datetime(2026, 10, 6, 10, 0, tzinfo=flow.TZ)
        self.fake = FakeGmail()
        self.account, self.contact = self.company()
        self.e = flow.enroll(self.contact, self.actor)
        MailEnrollment.objects.filter(pk=self.e.pk).update(created_at=self.clock-timedelta(days=1))
        MailMessage.objects.update(due_at=self.clock-timedelta(minutes=1))

    def company(self, suffix=''):
        a = SalesAccount.objects.create(name='Ficticia ' + suffix, owner=self.actor, identity_confirmed=True)
        FleetProfile.objects.create(account=a)
        Evidence.objects.create(account=a, topic='identity', reviewed=True, excerpt='Synthetic', source_note='Test', created_by=self.actor)
        c = BusinessContact.objects.create(account=a, name='Compras', email='compras'+suffix+'@example.test', published_business=True, source_note='Synthetic')
        return a, c

    def run_tick(self, advance=0):
        self.clock += timedelta(minutes=advance)
        with patch('django.utils.timezone.now', return_value=self.clock):
            return flow.tick(self.fake, self.clock)

    def inbound(self, body='Sí, nos interesa', **changes):
        item = dict(id='in1', thread_id='thread1', sender=self.e.email, subject='Vehículos de servicio',
                    body=body, headers={}, date=self.clock, rfc_id='<incoming@example.test>', sent=False)
        item.update(changes)
        return item

    def test_sync_crossing_end_of_window_does_not_send(self):
        self.clock = self.clock.replace(hour=15, minute=59)
        def discovery(*args):
            self.clock = self.clock.replace(hour=16, minute=1)
            return []
        self.fake.discover = discovery
        with patch('django.utils.timezone.now', side_effect=lambda: self.clock):
            self.assertEqual(flow.tick(self.fake), 'outside_window')
        self.assertFalse(self.fake.sent)
        self.assertIsNone(MailMessage.objects.get().attempted_at)

    def test_sent_once_and_followup_four_business_days(self):
        self.assertEqual(self.run_tick(), 'sent')
        self.assertEqual(self.run_tick(), 'idle')
        self.run_tick(2)
        self.assertEqual(len(self.fake.sent), 1)
        next_message = MailMessage.objects.get(step=2)
        self.assertEqual(next_message.due_at.astimezone(flow.TZ).date().isoformat(), '2026-10-12')
        self.assertTrue(Interaction.objects.filter(kind='sent').exists())

    def test_reply_stops_followup_and_queues_only_one_auto(self):
        self.run_tick(); self.fake.items = [self.inbound()]
        self.run_tick(2); self.run_tick(2)
        self.e.refresh_from_db()
        self.assertEqual(self.e.state, 'paused')
        self.assertEqual(MailInbound.objects.count(), 1)
        self.assertEqual(MailMessage.objects.filter(kind='auto').count(), 1)
        self.assertFalse(MailMessage.objects.filter(kind='cold', step=2).exists())

    def test_optout_global_suppression_no_auto(self):
        self.run_tick(); self.fake.items = [self.inbound('Por favor denme de baja')]
        self.run_tick(2)
        self.assertTrue(Suppression.objects.filter(account=self.account).exists())
        self.assertFalse(MailMessage.objects.filter(kind='auto').exists())
        self.assertEqual(len(self.fake.sent), 1)

    def test_unknown_send_never_retried_then_reconciled(self):
        self.fake.failure = True
        self.assertEqual(self.run_tick(), 'unknown_send')
        self.fake.failure = False
        self.run_tick(2)
        self.assertEqual(len(self.fake.sent), 1)
        self.fake.found = {'id':'recovered', 'threadId':'thread1'}
        self.run_tick(2)
        self.assertEqual(MailMessage.objects.get(step=1).status, 'sent')
        self.assertEqual(len(self.fake.sent), 1)

    def test_expired_sending_is_reconciled_not_retried(self):
        MailMessage.objects.update(status='sending', attempted_at=self.clock-timedelta(minutes=5))
        self.run_tick()
        self.assertEqual(MailMessage.objects.get().status, 'unknown')
        self.assertFalse(self.fake.sent)

    def test_worker_lease_blocks_second_worker(self):
        MailWorkerLease.objects.create(expires_at=self.clock+timedelta(minutes=3), token='other')
        self.assertEqual(self.run_tick(), 'busy')
        self.assertFalse(self.fake.sent)

    def test_sync_failure_prevents_send(self):
        self.fake.discover = lambda *args: (_ for _ in ()).throw(OSError())
        self.assertEqual(self.run_tick(), 'error')
        self.assertFalse(self.fake.sent)

    def test_paused_disconnected_no_network(self):
        self.box.connected = False; self.box.save()
        self.assertEqual(self.run_tick(), 'paused')
        self.assertFalse(self.fake.sent)

    def test_outside_window_syncs_but_does_not_send(self):
        self.clock = self.clock.replace(hour=20)
        self.fake.items = [self.inbound('Hola')]
        self.assertEqual(self.run_tick(), 'outside_window')
        self.assertTrue(MailInbound.objects.exists())
        self.assertFalse(self.fake.sent)

    def test_automatic_no_bot_loop(self):
        flow.accept_inbound(self.e, self.inbound('¿Dónde están?', headers={'auto-submitted':'auto-replied'}), self.box)
        self.assertFalse(MailMessage.objects.filter(kind='auto').exists())
        self.assertFalse(MailInbound.objects.get().human_reply)

    def test_urgent_price_ambiguous_negative_do_not_auto_reply(self):
        for index, body in enumerate(['Urgente estoy varado','¿Cuánto cobran?', '¿Dónde están y cuánto cuesta?', 'No gracias']):
            flow.accept_inbound(self.e, self.inbound(body, id='q'+str(index)), self.box)
        self.assertFalse(MailMessage.objects.filter(kind='auto').exists())

    def test_allowed_location_and_hours(self):
        self.assertEqual(flow.classify('¿Dónde están?', {})[0], 'location')
        self.assertEqual(flow.classify('Hola, ¿cuál es su horario?', {})[0], 'hours')

    def test_quote_does_not_cause_optout(self):
        self.assertEqual(flow.classify('Sí nos interesa\nEl martes escribió:\nResponde baja', {})[0], 'interest')

    def test_unknown_sender_never_receives_response(self):
        flow.accept_inbound(self.e, self.inbound('¿Dónde están?', sender='other@example.test'), self.box)
        self.assertEqual(MailInbound.objects.get().category, 'unknown_sender')
        self.assertFalse(MailMessage.objects.filter(kind='auto').exists())

    def test_bounce_marks_only_matched_email(self):
        flow.accept_inbound(self.e, self.inbound('Delivery failure', sender='mailer-daemon@googlemail.com'), self.box)
        self.contact.refresh_from_db(); self.assertEqual(self.contact.deliverability, 'bounced')
        self.assertFalse(MailMessage.objects.filter(kind='auto').exists())

    def test_manual_sent_in_gmail_pauses_even_new_thread(self):
        self.fake.items = [self.inbound('Manual reply', sender=self.box.email, sent=True, thread_id='another')]
        self.run_tick()
        self.assertFalse(self.fake.sent)
        self.e.refresh_from_db(); self.assertEqual(self.e.state, 'paused')

    def test_recent_prior_conversation_blocks_first_send(self):
        self.fake.items = [self.inbound('¿Dónde están?', date=self.clock-timedelta(days=2))]
        self.run_tick(); self.assertFalse(self.fake.sent)
        self.assertFalse(MailMessage.objects.filter(kind='auto').exists())

    def test_duplicate_enrollment_and_shared_email_blocked(self):
        with self.assertRaises(ValidationError): flow.enroll(self.contact, self.actor)
        a, contact = self.company('2'); contact.email = self.contact.email; contact.save()
        with self.assertRaises(ValidationError): flow.enroll(contact, self.actor)

    def test_identity_unreviewed_cannot_enroll(self):
        a, contact = self.company('2'); a.evidence.update(reviewed=False)
        with self.assertRaises(ValidationError): flow.enroll(contact, self.actor)

    def test_current_optout_checked_immediately_before_send(self):
        Suppression.objects.create(account=self.account, emails=[self.e.email], reason='Baja', created_by=self.actor)
        self.run_tick(); self.assertFalse(self.fake.sent)

    def test_manual_crm_interaction_cancels_queue(self):
        from .services import add_interaction
        add_interaction(self.account.pk, self.account.version, dict(kind='meeting',summary='Llamada', occurred_at=timezone.now()), self.actor)
        self.assertEqual(MailMessage.objects.get().status, 'cancelled')

    def test_daily_cap_includes_unknown_attempts(self):
        for step in range(10):
            MailMessage.objects.create(enrollment=self.e, kind='manual', recipient=self.e.email, subject='test',body='x', status='sent', attempted_at=self.clock)
        self.assertEqual(self.run_tick(), 'daily_limit'); self.assertFalse(self.fake.sent)

    def test_auto_reply_cap(self):
        self.run_tick()
        for i in range(3):
            flow.accept_inbound(self.e, self.inbound('¿Dónde están?', id='auto'+str(i)), self.box)
            MailMessage.objects.filter(kind='auto', status='queued').update(status='sent')
        self.assertEqual(MailMessage.objects.filter(kind='auto').count(), 2)

    def test_private_assets_not_linked_and_html_escaped(self):
        self.box.site_url = 'https://private.example.test'
        rendered = flow.render_html('<script>bad</script>', self.box)
        self.assertNotIn(self.box.site_url, rendered); self.assertNotIn('<script>', rendered)

    def test_business_calendar_skips_holiday(self):
        self.assertEqual(flow.business_due(self.clock, ['2026-10-12']).date().isoformat(),'2026-10-13')

    def test_dashboard_and_inbound_escape_html(self):
        self.client.force_login(self.actor)
        self.assertEqual(self.client.get('/commercial/mail/').status_code, 200)
        flow.accept_inbound(self.e, self.inbound('<script>alert(1)</script>'), self.box)
        page = self.client.get('/commercial/mail/incoming/1/')
        self.assertNotContains(page, '<script>alert(1)</script>')
        self.assertContains(page, '&lt;script&gt;')

    def test_csrf_and_role_required(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True); client.force_login(self.actor)
        self.assertEqual(client.post('/commercial/mail/', {'action':'toggle'}).status_code, 403)
        user = get_user_model().objects.create_user('ordinary', password='test-only')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/commercial/mail/').status_code, 403)

    def test_mime_contains_thread_and_auto_headers(self):
        from email import message_from_bytes
        self.run_tick()
        flow.accept_inbound(self.e, self.inbound(), self.box)
        auto = MailMessage.objects.get(kind='auto')
        client = GmailClient('test-token')
        with patch.object(client, 'request', return_value={}) as call:
            client.send(auto, self.box.email)
        data = call.call_args.args[1]
        mime = message_from_bytes(b64decode(data['raw']))
        self.assertEqual(mime['Auto-Submitted'], 'auto-replied')
        self.assertEqual(mime['In-Reply-To'], auto.reply_to_id)
        self.assertEqual(data['threadId'], 'thread1')

    def test_dpapi_roundtrip(self):
        import os
        if os.name != 'nt': self.skipTest('Windows only')
        self.assertEqual(protect(protect(b'synthetic-test-value'), decrypt=True), b'synthetic-test-value')

    def test_manual_takeover_remains_after_later_inbound(self):
        flow.pause_account(self.account.pk, 'Llamada humana', manual=True)
        flow.accept_inbound(self.e, self.inbound('¿Dónde están?'), self.box)
        self.assertFalse(MailMessage.objects.filter(kind='auto').exists())

    def test_first_contact_limit_five_per_day(self):
        for i in range(5):
            a, contact = self.company(str(i))
            e = flow.enroll(contact, self.actor)
            e.messages.update(status='sent', attempted_at=self.clock, sent_at=self.clock)
        self.run_tick(); self.assertFalse(self.fake.sent)

    def test_three_touches_end_sequence(self):
        self.run_tick()
        self.run_tick(6*24*60)
        self.run_tick(4*24*60)
        self.e.refresh_from_db()
        self.assertEqual(self.e.state, 'completed')
        self.assertEqual(len(self.fake.sent), 3)
        self.run_tick(7*24*60)
        self.assertEqual(len(self.fake.sent), 3)

    def test_settings_validate_dates_and_https(self):
        from .mail_views import MailSettingsForm
        invalid = MailSettingsForm({'site_url':'http://example.test', 'holidays':'2026-02-31'})
        self.assertFalse(invalid.is_valid())
        valid = MailSettingsForm({'site_url':'https://example.test', 'holidays':'2026-12-25'})
        self.assertTrue(valid.is_valid())

    def test_current_catalog_import_idempotent_preserves_unknown(self):
        from django.conf import settings
        from .catalog_import import import_catalog
        path = settings.BASE_DIR.parent/'outputs/ampliacion-prospeccion-20261003T220600Z/datos-revisados.json'
        if not path.exists(): self.skipTest('External research catalog not bundled in isolated package')
        first = import_catalog(path, self.actor)
        self.assertEqual(first['created'], 485)
        self.assertTrue(import_catalog(path, self.actor)['already_imported'])
        imported = SalesAccount.objects.filter(batch__key='catalog-20261003-485')
        self.assertEqual(imported.count(), 485)
        self.assertFalse(imported.filter(identity_confirmed=True).exists())
        self.assertFalse(FleetProfile.objects.filter(account__in=imported).exclude(fuel='unknown').exists())
