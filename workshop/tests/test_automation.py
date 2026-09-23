from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
import threading
import time

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from workshop import automation, models
from workshop.management.commands import run_automations


class AutomationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user("automation-manager", password="test-only")
        cls.manager.groups.add(Group.objects.create(name="manager"))

    def setUp(self):
        self.policy, self.state = automation.initialize_defaults()
        self.state.next_periodic_at = timezone.now() + timedelta(days=1)
        self.state.save(update_fields=["next_periodic_at"])

    def event(self, *, entity_type="WorkOrder", action="updated", created_at=None):
        return models.AuditEvent.objects.create(
            actor=self.manager, entity_type=entity_type, entity_id="42", action=action,
            created_at=created_at or timezone.now() - timedelta(minutes=2),
        )

    def test_business_event_generation_is_deduplicated_and_excludes_agent_events(self):
        self.event(entity_type="AgentRun")
        business_event = self.event()
        with patch("workshop.automation._execute"):
            result = automation.run_once("events-test")
            automation.run_once("events-test")
        jobs = models.AutomationJob.objects.filter(trigger="events")
        self.assertEqual(jobs.count(), 1)
        self.assertEqual(jobs.get().source_highwater, business_event.pk)
        self.assertEqual(result["status"], "completed", f"result={result!r}; jobs={list(jobs.values('status', 'available_at', 'attempts'))!r}")

    def test_interval_enqueues_without_audit_events(self):
        self.state.next_periodic_at = timezone.now() - timedelta(minutes=1)
        self.state.save(update_fields=["next_periodic_at"])
        with patch("workshop.automation._execute"):
            result = automation.run_once("interval-test")
        job = models.AutomationJob.objects.get()
        self.assertEqual((job.trigger, result["status"]), ("interval", "completed"), f"job={job.status}/{job.available_at}; result={result!r}")

    def test_pause_suppresses_automatic_event_and_interval_jobs(self):
        job = automation.enqueue_manual(self.manager)
        self.policy.paused = True
        self.policy.save(update_fields=["paused"])
        self.state.next_periodic_at = timezone.now() - timedelta(minutes=1)
        self.state.save(update_fields=["next_periodic_at"])
        self.event()
        result = automation.run_once("paused-test")
        job.refresh_from_db()
        self.assertEqual(result["status"], "paused")
        self.assertEqual(job.status, "pending")
        self.assertFalse(models.AutomationJob.objects.filter(trigger__in=("events", "interval")).exists())

    @override_settings(MILENIO_CODEX_ENABLED=True)
    def test_automatic_jobs_use_native_only_when_explicitly_enabled(self):
        automation.set_policy(self.manager, native_enabled=True)
        self.event()
        with patch("workshop.automation._execute") as execute:
            result = automation.run_once("native-auto")
        job = models.AutomationJob.objects.get(trigger="events")
        self.assertEqual(job.mode, "native")
        self.assertEqual(result["status"], "completed")
        execute.assert_called_once()

    @override_settings(MILENIO_CODEX_ENABLED=False)
    def test_native_policy_cannot_be_enabled_without_local_codex(self):
        with self.assertRaises(ValidationError):
            automation.set_policy(self.manager, native_enabled=True)
        self.policy.refresh_from_db()
        self.assertFalse(self.policy.native_enabled)

    @override_settings(MILENIO_CODEX_ENABLED=True)
    def test_disabling_automatic_native_blocks_queued_auto_job_before_model_call(self):
        automation.set_policy(self.manager, native_enabled=True)
        self.event()
        queued = automation._enqueue_automatic(timezone.now())
        self.assertEqual(queued.mode, "native")
        automation.set_policy(self.manager, native_enabled=False)
        with patch("workshop.analytics.refresh_analytics") as refresh:
            result = automation.run_once("disabled-native")
        queued.refresh_from_db()
        self.assertEqual(queued.status, "failed")
        self.assertEqual(result["status"], "failed")
        refresh.assert_not_called()

    @override_settings(MILENIO_CODEX_ENABLED=True)
    def test_explicit_manual_native_run_does_not_depend_on_automatic_native_toggle(self):
        job = automation.enqueue_manual(self.manager, mode="native")
        runs = [SimpleNamespace(pk=301 + i, agent=agent, status="completed", error="", model_invoked=True)
                for i, agent in enumerate(("operations", "collections", "data_quality"))]
        with patch("workshop.analytics.refresh_analytics", return_value=SimpleNamespace(pk=77)), \
             patch("workshop.intelligence.run_agents", return_value=runs):
            result = automation.run_once("manual-native")
        job.refresh_from_db()
        self.assertEqual((job.mode, job.status, result["status"]), ("native", "completed", "completed"))

    def test_stale_worker_cannot_persist_after_lease_changes_owner(self):
        job = automation.enqueue_manual(self.manager)

        def replace_owner(_job):
            models.AutomationWorkerState.objects.filter(pk=1).update(
                lease_owner="successor:lease", lease_expires_at=timezone.now() + timedelta(minutes=2))

        with patch("workshop.automation._execute", side_effect=replace_owner):
            result = automation.run_once("old-worker")
        job.refresh_from_db()
        state = models.AutomationWorkerState.objects.get(pk=1)
        self.assertEqual(result["status"], "lease_lost")
        self.assertEqual(job.status, "running")
        self.assertEqual(state.lease_owner, "successor:lease")

    def test_shorter_interval_moves_next_schedule_forward(self):
        self.state.next_periodic_at = timezone.now() + timedelta(days=1)
        self.state.save(update_fields=["next_periodic_at"])
        automation.set_policy(self.manager, interval_minutes=10)
        self.state.refresh_from_db()
        self.assertLessEqual(self.state.next_periodic_at, timezone.now() + timedelta(minutes=10))

    def test_two_ticks_execute_one_queued_job_once(self):
        job = automation.enqueue_manual(self.manager)
        with patch("workshop.automation._execute") as execute:
            first = automation.run_once("same-worker")
            second = automation.run_once("same-worker")
        job.refresh_from_db()
        self.assertEqual((first["job_id"], first["status"]), (job.pk, "completed"))
        self.assertEqual(second["status"], "idle")
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(models.AutomationJob.objects.count(), 1)

    def test_expired_rules_lease_recovers_and_claims_job(self):
        job = models.AutomationJob.objects.create(
            dedup_key="stale-rules", trigger="manual", actor=self.manager, status="running", attempts=1,
        )
        self.state.lease_owner = "dead-worker"
        self.state.lease_expires_at = timezone.now() - timedelta(seconds=1)
        self.state.save(update_fields=["lease_owner", "lease_expires_at"])
        with patch("workshop.automation._execute"):
            result = automation.run_once("recovery-worker")
        job.refresh_from_db()
        self.assertEqual((job.status, job.attempts, result["status"]), ("completed", 2, "completed"))

    def test_expired_native_lease_fails_without_reinvoking_ambiguous_work(self):
        job = models.AutomationJob.objects.create(
            dedup_key="stale-native", trigger="manual", actor=self.manager,
            mode="native", status="running", attempts=1, max_attempts=1,
        )
        self.state.lease_owner = "dead-native-worker"
        self.state.lease_expires_at = timezone.now() - timedelta(seconds=1)
        self.state.save(update_fields=["lease_owner", "lease_expires_at"])
        with patch("workshop.automation._execute") as execute:
            result = automation.run_once("native-recovery-worker")
        job.refresh_from_db()
        execute.assert_not_called()
        self.assertEqual((job.status, result["status"]), ("failed", "idle"))
        self.assertIn("outcome is ambiguous", job.errors[-1])

    def test_retry_limit_is_bounded(self):
        job = models.AutomationJob.objects.create(
            dedup_key="last-attempt", trigger="manual", actor=self.manager,
            attempts=2, max_attempts=3,
        )
        with patch("workshop.automation._execute", side_effect=RuntimeError("refresh unavailable")):
            result = automation.run_once("retry-worker")
        job.refresh_from_db()
        self.assertEqual((result["status"], job.attempts, job.status), ("failed", 3, "failed"))
        self.assertIsNotNone(job.finished_at)

    def test_partial_agent_failure_persists_snapshot_ids_and_errors(self):
        job = models.AutomationJob.objects.create(
            dedup_key="partial-agents", trigger="manual", actor=self.manager,
            attempts=2, max_attempts=3,
        )
        runs = [SimpleNamespace(pk=101, agent="operations", status="completed", error="", model_invoked=False),
                SimpleNamespace(pk=102, agent="collections", status="failed", error="evidence unavailable", model_invoked=False),
                SimpleNamespace(pk=103, agent="data_quality", status="completed", error="", model_invoked=False)]
        with patch("workshop.analytics.refresh_analytics", return_value=SimpleNamespace(pk=55)), \
             patch("workshop.intelligence.run_agents", return_value=runs):
            result = automation.run_once("partial-worker")
        job.refresh_from_db()
        self.assertEqual(job.snapshot_id, "55")
        self.assertEqual(job.agent_run_ids, ["101", "102", "103"])
        self.assertEqual(job.status, "failed")
        self.assertTrue(any("evidence unavailable" in message for message in job.errors))
        self.assertEqual(result["status"], "failed")

    def test_worker_orchestration_does_not_mutate_business_records(self):
        before = {name: getattr(models, name).objects.count() for name in
                  ("Customer", "Vehicle", "WorkOrder", "Invoice", "Payment", "Part", "TowService")}
        automation.enqueue_manual(self.manager)
        runs = [SimpleNamespace(pk=201 + i, agent=agent, status="completed", error="", model_invoked=False)
                for i, agent in enumerate(("operations", "collections", "data_quality"))]
        with patch("workshop.analytics.refresh_analytics", return_value=SimpleNamespace(pk=66)), \
             patch("workshop.intelligence.run_agents", return_value=runs):
            result = automation.run_once("readonly-worker")
        after = {name: getattr(models, name).objects.count() for name in before}
        self.assertEqual(result["status"], "completed")
        self.assertEqual(after, before)

    def test_job_result_marks_audit_activity_after_snapshot_cut(self):
        job = automation.enqueue_manual(self.manager)
        runs = [SimpleNamespace(pk=401 + i, agent=agent, status="completed", error="", model_invoked=False)
                for i, agent in enumerate(("operations", "collections", "data_quality"))]

        def runs_with_new_event(actor, **kwargs):
            models.AuditEvent.objects.create(actor=actor, entity_type="WorkOrder", entity_id="77",
                                             action="status_changed")
            return runs

        with patch("workshop.analytics.refresh_analytics",
                   return_value=SimpleNamespace(pk=88, audit_cursor=0)), \
             patch("workshop.intelligence.run_agents", side_effect=runs_with_new_event):
            result = automation.run_once("cut-context")
        job.refresh_from_db()
        context = job.result["evidence_context"]
        self.assertEqual(result["status"], "completed")
        self.assertEqual(context["snapshot_audit_cursor"], 0)
        self.assertTrue(context["audit_cursor_advanced_after_snapshot"])
        self.assertGreater(context["post_agent_audit_cursor"], 0)
        self.assertIn("Recomprueba", context["interpretation"])

    def test_policy_changes_require_manager_capability_and_validate_bounds(self):
        viewer = User.objects.create_user("automation-viewer", password="test-only")
        viewer.groups.add(Group.objects.create(name="viewer"))
        with self.assertRaises(PermissionDenied):
            automation.set_policy(viewer, paused=True)
        with self.assertRaises(ValidationError):
            automation.set_policy(self.manager, interval_minutes=0)


class WorkerLoopTests(TestCase):
    class StopEvent:
        def __init__(self):
            self.waits = []

        def is_set(self):
            return False

        def wait(self, timeout):
            self.waits.append(timeout)

    def setUp(self):
        automation.initialize_defaults()
        self.stop_event = self.StopEvent()
        self.stderr = StringIO()
        self.command = run_automations.Command(stdout=StringIO(), stderr=self.stderr)

    def run_command(self, max_idle=1):
        options = {"idle_sleep": 0.25, "max_idle": max_idle, "watch_parent": False,
                   "once": False, "worker_id": "loop-test"}
        with patch("workshop.management.commands.run_automations.threading.Event",
                   return_value=self.stop_event):
            self.command.handle(**options)

    def test_worker_waits_after_successful_and_idle_ticks(self):
        with patch("workshop.management.commands.run_automations.run_once",
                   side_effect=[{"status": "completed"}, {"status": "idle"}, {"status": "idle"}]):
            self.run_command(max_idle=2)
        self.assertEqual(self.stop_event.waits, [0.1, 0.25])

    def test_transient_database_error_is_logged_and_retried_after_backoff(self):
        with patch("workshop.management.commands.run_automations.run_once",
                   side_effect=[OperationalError("database is locked"), {"status": "idle"}]), \
             patch("workshop.management.commands.run_automations.logger.warning") as log_warning:
            self.run_command()
        state = models.AutomationWorkerState.objects.get(pk=1)
        self.assertEqual(self.stop_event.waits, [2.0])
        self.assertIn("database error; retrying", self.stderr.getvalue())
        self.assertEqual(state.status, "error")
        log_warning.assert_called_once()

    def test_unexpected_tick_error_is_visible_and_not_marked_healthy(self):
        with patch("workshop.management.commands.run_automations.run_once",
                   side_effect=[RuntimeError("unexpected"), {"status": "idle"}]), \
             patch("workshop.management.commands.run_automations.logger.exception") as log_exception:
            self.run_command()
        state = models.AutomationWorkerState.objects.get(pk=1)
        self.assertEqual(self.stop_event.waits, [5.0])
        self.assertIn("tick failed; retrying", self.stderr.getvalue())
        self.assertEqual(state.status, "error")
        self.assertIsNone(state.heartbeat_at)
        log_exception.assert_called_once()


class LeaseHeartbeatTests(TransactionTestCase):
    reset_sequences = True

    def test_long_job_renews_lease_from_separate_database_connection(self):
        automation.initialize_defaults()
        policy = models.AutomationPolicy.objects.get(pk=1)
        policy.automatic_enabled = False
        policy.save(update_fields=["automatic_enabled"])
        job = models.AutomationJob.objects.create(dedup_key="heartbeat-test", trigger="manual")
        observed_renewal = threading.Event()

        def wait_for_renewal(_job):
            initial = models.AutomationWorkerState.objects.get(pk=1).lease_expires_at
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                models.AutomationWorkerState.objects.get(pk=1)
                current = models.AutomationWorkerState.objects.get(pk=1).lease_expires_at
                if current > initial:
                    observed_renewal.set()
                    return
                time.sleep(0.005)

        with patch("workshop.automation.HEARTBEAT_INTERVAL_SECONDS", 0.02), \
             patch("workshop.automation.LEASE_SECONDS", 2), \
             patch("workshop.automation._execute", side_effect=wait_for_renewal):
            result = automation.run_once("heartbeat-worker")
        self.assertTrue(observed_renewal.is_set())
        self.assertEqual(result["status"], "completed")
