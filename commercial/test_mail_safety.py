"""Regression tests at the actual HTTP gate, with synthetic recipients only."""
import io
import threading
from datetime import timedelta
from unittest.mock import patch
from django.conf import settings
from django.db import connection, close_old_connections, OperationalError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from . import mail_flow as flow, mail_safety as safety
from .gmail import GmailClient
from .models import (MailSafety, MailPermission, MailBatch, MailAdmission, MailMessage,
                     MailWorkerLease, Mailbox, MailEnrollment, Suppression)
from . import test_mail_flow as flow_tests
from .mail_test_support import synthetic_approve


class SafetyFixture:
    company = flow_tests.MailFlowTests.company
    run_tick = flow_tests.MailFlowTests.run_tick
    inbound = flow_tests.MailFlowTests.inbound

    def setUp(self):
        flow_tests.MailFlowTests.setUp(self)
        self.message = MailMessage.objects.get(step=1)
        self.transport = GmailClient('synthetic-token')

    def reserve(self):
        MailWorkerLease.objects.update_or_create(pk=1, defaults={'token': 'synthetic-worker',
                                                       'expires_at': self.clock+timedelta(minutes=3)})
        Mailbox.objects.filter(pk=1).update(last_sync=self.clock)
        with patch('django.utils.timezone.now', return_value=self.clock):
            return safety.reserve(self.message.pk, self.box.email, 'synthetic-worker')

    def denied(self):
        with patch('django.utils.timezone.now', return_value=self.clock), patch('commercial.gmail.urlopen') as network:
            with self.assertRaises(safety.MailBlocked):
                admission = self.reserve()
                self.message.refresh_from_db()
                self.transport.send(self.message, self.box.email, admission=admission.pk)
            network.assert_not_called()


class MailSafetyTests(SafetyFixture, TestCase):
    def test_default_policy_blocks_even_connected_mailbox_before_any_network(self):
        MailSafety.objects.all().delete()
        with patch.object(self.fake, 'profile') as profile:
            self.assertEqual(self.run_tick(), 'safety_hold')
            profile.assert_not_called()
        self.assertFalse(self.fake.sent)

    def test_direct_send_without_admission_cannot_call_http(self):
        with patch('commercial.gmail.urlopen') as network:
            with self.assertRaises(safety.MailBlocked): self.transport.send(self.message, self.box.email)
            network.assert_not_called()

    def test_raw_and_private_adapter_mutations_cannot_bypass_gate(self):
        with patch('commercial.gmail.urlopen') as network:
            for method in (self.transport.request, self.transport._request):
                for path in ('messages/send', 'drafts/send'):
                    with self.assertRaises(safety.MailBlocked): method(path, {'raw': 'fake'})
                    with self.assertRaises(safety.MailBlocked): method(path)
            network.assert_not_called()

    def test_approved_exact_message_consumes_admission_once_at_http(self):
        admission = self.reserve()
        self.message.refresh_from_db()
        with patch('django.utils.timezone.now', return_value=self.clock), patch('commercial.gmail.urlopen') as network:
            network.return_value.__enter__.return_value = io.StringIO('{"id":"synthetic-id","threadId":"synthetic-thread"}')
            result = self.transport.send(self.message, self.box.email, admission=admission.pk)
            self.assertEqual(result['id'], 'synthetic-id')
            self.assertEqual(network.call_count, 1)
            admission.refresh_from_db(); self.assertEqual(admission.state, 'submitted')
            with self.assertRaises(safety.MailBlocked):
                self.transport.send(self.message, self.box.email, admission=admission.pk)
            self.assertEqual(network.call_count, 1)

    def test_public_email_without_permission_cannot_enroll(self):
        a, contact = self.company('nopermission')
        MailPermission.objects.filter(contact=contact).delete()
        with self.assertRaises(safety.MailBlocked): flow.enroll(contact, self.actor)
        self.assertFalse(MailEnrollment.objects.filter(account=a).exists())

    def test_unknown_permission_and_wrong_channel_block_http(self):
        MailPermission.objects.update(channel='whatsapp')
        self.denied()
        MailPermission.objects.update(channel='email', status='unverified')
        self.denied()

    def test_expired_permission_blocks_http(self):
        MailPermission.objects.update(valid_until=self.clock)
        self.denied()

    def test_permission_expiring_during_evidence_read_blocks_http(self):
        started = self.clock
        MailPermission.objects.update(valid_until=started+timedelta(seconds=1))
        original = safety.evidence_hash
        def delayed_read(relative):
            result = original(relative)
            self.clock = started+timedelta(seconds=2)
            return result
        with patch('django.utils.timezone.now', side_effect=lambda: self.clock), patch.object(safety, 'evidence_hash', side_effect=delayed_read):
            with self.assertRaises(safety.MailBlocked): safety.permission_for(self.contact, 'presentation', started)

    def test_recorded_contacts_by_other_channels_do_not_reset_touch_count(self):
        from .models import Interaction
        for i in range(3):
            Interaction.objects.create(account=self.account, kind='sent', summary='Synthetic contact by another channel', created_by=self.actor)
        self.denied()

    def test_changed_proof_file_blocks_http(self):
        (settings.DATA_DIR/'mail-evidence/synthetic-permission.txt').write_text('Changed evidence', encoding='utf-8')
        self.denied()

    def test_evidence_cannot_escape_private_directory(self):
        MailPermission.objects.update(evidence_file='../outside.txt')
        self.denied()

    def test_scope_is_not_inferred_from_interest_reply(self):
        flow.accept_inbound(self.e, self.inbound('Más información'), self.box)
        MailPermission.objects.update(scopes=['presentation'])
        with self.assertRaises(safety.MailBlocked): safety.permission_for(self.contact, 'followup', self.clock)

    def test_unknown_provider_and_stale_provider_verification_block_http(self):
        MailSafety.objects.update(provider_status='restricted')
        self.denied()
        MailSafety.objects.update(provider_status='available', provider_checked_at=self.clock-timedelta(days=2))
        self.denied()

    def test_approved_lot_is_not_transferable_to_another_sender(self):
        Mailbox.objects.update(email='other@example.test')
        self.denied()

    def test_worker_checks_google_profile_matches_selected_mailbox(self):
        self.fake.profile = lambda: {'emailAddress': 'other@example.test'}
        self.assertEqual(self.run_tick(), 'sender_identity_mismatch')
        self.assertFalse(self.fake.sent)
        self.assertTrue(MailSafety.objects.get().paused)

    def test_missing_or_expired_batch_blocks_http(self):
        MailBatch.objects.update(expires_at=self.clock)
        self.denied()

    def test_mutated_subject_body_and_account_version_invalidate_approval(self):
        for field, value in [('subject', 'Changed subject'), ('body', 'Changed body')]:
            original = getattr(self.message, field)
            MailMessage.objects.filter(pk=self.message.pk).update(**{field: value})
            self.denied()
            MailMessage.objects.filter(pk=self.message.pk).update(**{field: original})
        self.account.version += 1; self.account.save()
        self.denied()

    def test_batch_cannot_be_extended_or_modified_after_review(self):
        MailBatch.objects.update(approval_reference='Changed reference')
        self.denied()

    def test_replay_manifest_cannot_approve_message_twice(self):
        with patch('django.utils.timezone.now', return_value=self.clock):
            with self.assertRaises(safety.MailBlocked): safety.preview([self.message.pk])

    def test_six_recipients_cannot_be_approved_as_one_lot(self):
        with self.assertRaises(safety.MailBlocked): safety.preview([str(i) for i in range(6)])

    def test_broad_campaign_request_is_not_a_finite_manifest(self):
        with patch('django.utils.timezone.now', return_value=self.clock):
            with self.assertRaises(safety.MailBlocked):
                safety.approve_batch({'all_companies': True}, self.actor, 'send all', self.clock+timedelta(hours=1))

    def test_stale_mailbox_snapshot_cannot_transmit(self):
        MailWorkerLease.objects.create(token='worker', expires_at=self.clock+timedelta(minutes=3))
        Mailbox.objects.update(last_sync=self.clock-timedelta(minutes=6))
        with patch('django.utils.timezone.now', return_value=self.clock), patch('commercial.gmail.urlopen') as network:
            with self.assertRaises(safety.MailBlocked): safety.reserve(self.message.pk, self.box.email, 'worker')
            network.assert_not_called()

    def test_pause_between_reservation_and_http_stops_submission(self):
        admission = self.reserve()
        safety.hold('Synthetic pause', self.actor)
        self.message.refresh_from_db()
        with patch('django.utils.timezone.now', return_value=self.clock), patch('commercial.gmail.urlopen') as network:
            with self.assertRaises(safety.MailBlocked): self.transport.send(self.message, self.box.email, admission=admission.pk)
            network.assert_not_called()

    def test_permission_revoked_after_reservation_stops_submission(self):
        admission = self.reserve()
        MailPermission.objects.update(status='revoked')
        self.message.refresh_from_db()
        with patch('django.utils.timezone.now', return_value=self.clock), patch('commercial.gmail.urlopen') as network:
            with self.assertRaises(safety.MailBlocked): self.transport.send(self.message, self.box.email, admission=admission.pk)
            network.assert_not_called()

    def test_changed_in_memory_payload_cannot_transmit(self):
        admission = self.reserve()
        self.message.refresh_from_db(); self.message.body = 'Not reviewed'
        with patch('django.utils.timezone.now', return_value=self.clock), patch('commercial.gmail.urlopen') as network:
            with self.assertRaises(safety.MailBlocked): self.transport.send(self.message, self.box.email, admission=admission.pk)
            network.assert_not_called()

    def test_lost_worker_lease_after_reservation_stops_http(self):
        admission = self.reserve()
        MailWorkerLease.objects.update(token='other')
        self.message.refresh_from_db()
        with patch('django.utils.timezone.now', return_value=self.clock), patch('commercial.gmail.urlopen') as network:
            with self.assertRaises(safety.MailBlocked): self.transport.send(self.message, self.box.email, admission=admission.pk)
            network.assert_not_called()

    def test_crash_reservation_counts_and_is_not_reused(self):
        self.reserve()
        self.assertEqual(MailAdmission.objects.count(), 1)
        self.denied()
        self.assertEqual(MailAdmission.objects.count(), 1)

    def test_ten_minute_minimum_is_durable_across_worker_restart(self):
        MailMessage.objects.create(enrollment=self.e, recipient=self.e.email, kind='manual', body='Synthetic prior attempt',
            subject='Synthetic', status='sent', attempted_at=self.clock-timedelta(minutes=9))
        self.denied()

    def test_five_total_daily_includes_manual_cancelled_and_unknown_attempts(self):
        for i in range(5):
            MailMessage.objects.create(enrollment=self.e, recipient=self.e.email, kind='manual', body='Fixture',
                subject='Fixture', status='cancelled', attempted_at=self.clock-timedelta(hours=1))
        self.denied()

    def test_followup_preserves_four_whole_business_days(self):
        due = safety.next_touch(self.clock.replace(hour=15), ['2026-10-12'])
        self.assertEqual(due.isoformat(), '2026-10-13T15:00:00-07:00')

    def test_no_send_at_weekend_holiday_or_close(self):
        for clock in (self.clock.replace(hour=16), self.clock+timedelta(days=5)):
            self.clock = clock
            self.denied()

    def test_bounce_optout_and_spam_pause_all_not_only_one_company(self):
        for i, changes in enumerate([{'sender': 'mailer-daemon@example.test'}, {'body': 'baja'}, {'spam': True}]):
            flow.accept_inbound(self.e, self.inbound(id='signal'+str(i), **changes), self.box)
            self.assertTrue(MailSafety.objects.get().paused)
            self.assertFalse(Mailbox.objects.get().enabled)
            self.assertFalse(MailBatch.objects.filter(revoked=False).exists())

    def test_timeout_consumes_budget_and_holds_no_automatic_retry(self):
        self.fake.failure = True
        self.assertEqual(self.run_tick(), 'unknown_send')
        self.assertTrue(MailSafety.objects.get().paused)
        self.assertEqual(MailAdmission.objects.get().state, 'unknown')
        self.fake.failure = False
        self.assertEqual(self.run_tick(11), 'safety_hold')
        self.assertEqual(len(self.fake.sent), 1)

    def test_reply_proposal_requires_another_batch_and_grants_no_campaign_permission(self):
        self.assertEqual(self.run_tick(), 'sent')
        flow.accept_inbound(self.e, self.inbound('¿Dónde están?'), self.box)
        proposal = MailMessage.objects.get(kind='auto')
        self.assertFalse(hasattr(proposal, 'mailbatchitem'))
        self.run_tick(11)
        self.assertEqual(len(self.fake.sent), 1)

    def test_human_reply_can_be_approved_only_for_its_exact_context(self):
        self.assertEqual(self.run_tick(), 'sent')
        with patch('django.utils.timezone.now', return_value=self.clock):
            flow.accept_inbound(self.e, self.inbound('¿Dónde están?'), self.box)
        self.clock += timedelta(minutes=11)
        reply = MailMessage.objects.get(kind='auto')
        synthetic_approve([reply], self.actor, self.clock)
        self.assertEqual(self.run_tick(), 'sent')
        self.assertEqual(len(self.fake.sent), 2)

    def test_toggle_ui_cannot_release_safety_hold(self):
        safety.hold('Synthetic incident', self.actor)
        self.client.force_login(self.actor)
        self.client.post('/commercial/mail/', {'action': 'toggle'})
        self.assertFalse(Mailbox.objects.get().enabled)
        self.assertTrue(MailSafety.objects.get().paused)

    def test_reconciliation_clears_restore_latch_without_releasing_incident(self):
        from django.core.management import call_command
        latch = settings.DATA_DIR/'.mail-recovery-hold'
        latch.touch()
        self.addCleanup(lambda: latch.unlink(missing_ok=True))
        with patch('commercial.gmail.GmailClient', return_value=self.fake):
            call_command('mail_safety', 'reconcile', actor=self.actor.username, reference='Synthetic restore review', stdout=io.StringIO())
        self.assertFalse(latch.exists())
        self.assertTrue(MailSafety.objects.get().paused)
        self.assertFalse(Mailbox.objects.get().enabled)
        self.assertFalse(self.fake.sent)

    def test_external_outbound_prevents_clearing_restore_latch(self):
        from django.core.management import call_command, CommandError
        latch = settings.DATA_DIR/'.mail-recovery-hold'
        latch.touch()
        self.addCleanup(lambda: latch.unlink(missing_ok=True))
        self.fake.outbound_ids = lambda since: ['external-synthetic']
        with patch('commercial.gmail.GmailClient', return_value=self.fake):
            with self.assertRaises(CommandError):
                call_command('mail_safety', 'reconcile', actor=self.actor.username, reference='Synthetic review', stdout=io.StringIO())
        self.assertTrue(latch.exists())
        self.assertTrue(MailSafety.objects.get().paused)

    def test_non_manager_cannot_approve_even_with_reference(self):
        from django.contrib.auth import get_user_model
        actor = get_user_model().objects.create_user('ordinary', password='synthetic-password')
        with self.assertRaises(safety.MailBlocked):
            safety.approve_batch({}, actor, 'reference', self.clock+timedelta(hours=1))

    def test_external_connector_or_manual_account_send_stops_worker(self):
        self.fake.outbound_ids = lambda since: ['unmanaged-synthetic']
        self.assertEqual(self.run_tick(), 'unmanaged_outbound')
        self.assertTrue(MailSafety.objects.get().paused)
        self.assertFalse(self.fake.sent)

    def test_explicit_spam_complaint_holds_future_growth(self):
        flow.accept_inbound(self.e, self.inbound('Esto es spam, correo no deseado'), self.box)
        self.assertTrue(MailSafety.objects.get().paused)
        self.assertFalse(self.fake.sent)


class ConcurrentMailBudgetTests(SafetyFixture, TransactionTestCase):
    def test_send_inside_outer_transaction_cannot_rollback_used_admission(self):
        from django.db import transaction
        admission = self.reserve()
        self.message.refresh_from_db()
        with patch('django.utils.timezone.now', return_value=self.clock), patch('commercial.gmail.urlopen') as network:
            with transaction.atomic():
                with self.assertRaises(RuntimeError):
                    self.transport.send(self.message, self.box.email, admission=admission.pk)
            network.assert_not_called()

    def test_two_processes_share_one_daily_budget(self):
        a, contact = self.company('second')
        with patch('django.utils.timezone.now', return_value=self.clock):
            e = flow.enroll(contact, self.actor)
        m2 = e.messages.get()
        synthetic_approve([m2], self.actor, self.clock)
        for i in range(4):
            MailMessage.objects.create(enrollment=self.e, recipient=self.e.email, kind='manual', subject='Fixture',
                body='Fixture', status='sent', attempted_at=self.clock-timedelta(hours=1))
        MailWorkerLease.objects.create(token='synthetic-worker', expires_at=self.clock+timedelta(minutes=3))
        Mailbox.objects.update(last_sync=self.clock)
        barrier = threading.Barrier(2)
        results = []
        def reserve(pk):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                safety.reserve(pk, self.box.email, 'synthetic-worker')
                results.append('reserved')
            except (safety.MailBlocked, OperationalError):
                results.append('blocked')
            finally:
                close_old_connections()
        with patch('django.utils.timezone.now', return_value=self.clock):
            threads = [threading.Thread(target=reserve, args=(pk,)) for pk in (self.message.pk, m2.pk)]
            for thread in threads: thread.start()
            for thread in threads: thread.join(timeout=10)
            self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(sorted(results), ['blocked', 'reserved'])
        self.assertEqual(MailAdmission.objects.count(), 1)
        self.assertEqual(MailMessage.objects.filter(attempted_at__isnull=False).count(), 5)


class SafetyMigrationTests(TransactionTestCase):
    def test_upgrade_quarantines_old_queue_without_granting_permission(self):
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        old_target = [('commercial', '0005_agentcredential_agentdraft_conversationclaim_and_more')]
        latest = executor.loader.graph.leaf_nodes()
        executor.migrate(old_target)
        try:
            old = executor.loader.project_state(old_target).apps
            actor = old.get_model('auth', 'User').objects.create(username='synthetic-upgrade')
            account = old.get_model('commercial', 'SalesAccount').objects.create(name='Synthetic', owner_id=actor.pk)
            contact = old.get_model('commercial', 'BusinessContact').objects.create(account_id=account.pk, email='synthetic@example.test', published_business=True)
            box = old.get_model('commercial', 'Mailbox').objects.create(owner_id=actor.pk, connected=True, enabled=True, auto_reply=True)
            e = old.get_model('commercial', 'MailEnrollment').objects.create(account_id=account.pk, contact_id=contact.pk, email=contact.email)
            m = old.get_model('commercial', 'MailMessage').objects.create(enrollment_id=e.pk, kind='cold', step=1, recipient=e.email, subject='Fixture', body='Fixture')
            MigrationExecutor(connection).migrate(latest)
            self.assertTrue(MailSafety.objects.get().paused)
            self.assertFalse(Mailbox.objects.get(pk=box.pk).enabled)
            self.assertFalse(Mailbox.objects.get(pk=box.pk).auto_reply)
            self.assertEqual(MailMessage.objects.get(pk=m.pk).status, 'cancelled')
            self.assertEqual(MailPermission.objects.count(), 0)
            self.assertEqual(MailBatch.objects.count(), 0)
        finally:
            MigrationExecutor(connection).migrate(latest)
