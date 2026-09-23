"""Bounded durable automation for local workshop analytics.

Only analytics snapshots and human-review proposals/tasks are produced here.
Business records are read as evidence and are never changed by the worker.
"""
from __future__ import annotations

import time
import logging
import threading
import uuid
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, transaction
from django.db.models import Max, Q
from django.utils import timezone

from . import models
from .access import can


AUTO_ACTOR_USERNAME = "__milenio_automation__"
LEASE_SECONDS = 15 * 60
HEARTBEAT_INTERVAL_SECONDS = 30
MAX_INTERVAL_MINUTES = 24 * 60 * 30
MAX_DEBOUNCE_SECONDS = 60 * 60
EXCLUDED_EVENT_TYPES = ("AgentRun", "Proposal", "ActionTask", "AutomationJob", "AutomationPolicy")
logger = logging.getLogger(__name__)


def _eligible_events():
    return models.AuditEvent.objects.exclude(entity_type__in=EXCLUDED_EVENT_TYPES)


def initialize_defaults() -> tuple[Any, Any]:
    """Create the policy, state, and non-login attribution actor once."""
    policy, _ = models.AutomationPolicy.objects.get_or_create(pk=1)
    state, created = models.AutomationWorkerState.objects.get_or_create(pk=1)
    if created:
        highwater = _eligible_events().aggregate(value=Max("pk"))["value"] or 0
        models.AutomationWorkerState.objects.filter(pk=1).update(
            event_cursor=highwater, next_periodic_at=timezone.now())
        state.refresh_from_db()
    return policy, state


def _system_actor():
    User = get_user_model()
    actor, created = User.objects.get_or_create(
        username=AUTO_ACTOR_USERNAME,
        defaults={"is_active": False, "is_staff": False, "is_superuser": False},
    )
    fields = []
    for field in ("is_active", "is_staff", "is_superuser"):
        if getattr(actor, field, False):
            setattr(actor, field, False)
            fields.append(field)
    if created or actor.has_usable_password():
        actor.set_unusable_password()
        fields.append("password")
    if fields:
        actor.save(update_fields=fields)
    return actor


def set_policy(actor: Any, *, automatic_enabled: bool | None = None,
               interval_minutes: int | None = None, native_enabled: bool | None = None,
               paused: bool | None = None, debounce_seconds: int | None = None):
    """Update automation policy. Only managers can change worker behavior."""
    if actor is None or not getattr(actor, "is_authenticated", False) or not can(actor, "manage"):
        raise PermissionDenied("Sólo gerencia puede cambiar la política de automatización.")
    policy, _ = models.AutomationPolicy.objects.get_or_create(pk=1)
    updates = {}
    for name, value in (("automatic_enabled", automatic_enabled), ("native_enabled", native_enabled),
                        ("paused", paused)):
        if value is not None:
            if not isinstance(value, bool):
                raise ValidationError({name: "Se requiere un valor booleano."})
            updates[name] = value
    if native_enabled is True and not getattr(settings, "MILENIO_CODEX_ENABLED", False):
        raise ValidationError("No se puede habilitar el modo nativo: Codex local no está habilitado en esta instalación.")
    if interval_minutes is not None:
        if not isinstance(interval_minutes, int) or isinstance(interval_minutes, bool) or not 1 <= interval_minutes <= MAX_INTERVAL_MINUTES:
            raise ValidationError({"interval_minutes": f"Use un intervalo de 1 a {MAX_INTERVAL_MINUTES} minutos."})
        updates["interval_minutes"] = interval_minutes
    if debounce_seconds is not None:
        if not isinstance(debounce_seconds, int) or isinstance(debounce_seconds, bool) or not 0 <= debounce_seconds <= MAX_DEBOUNCE_SECONDS:
            raise ValidationError({"debounce_seconds": f"Use una espera de 0 a {MAX_DEBOUNCE_SECONDS} segundos."})
        updates["debounce_seconds"] = debounce_seconds
    if updates:
        updates.update(updated_by=actor, updated_at=timezone.now())
        with transaction.atomic():
            models.AutomationPolicy.objects.filter(pk=policy.pk).update(**updates)
            if interval_minutes is not None and interval_minutes < policy.interval_minutes:
                state, _ = models.AutomationWorkerState.objects.get_or_create(pk=1)
                state = models.AutomationWorkerState.objects.select_for_update().get(pk=state.pk)
                earlier_due = timezone.now() + timedelta(minutes=interval_minutes)
                if state.next_periodic_at > earlier_due:
                    state.next_periodic_at = earlier_due
                    state.save(update_fields=["next_periodic_at"])
            policy.refresh_from_db()
            models.AuditEvent.objects.create(
                actor=actor, entity_type="AutomationPolicy", entity_id="1", action="updated",
                after={key: getattr(policy, key) for key in updates if key not in {"updated_by", "updated_at"}},
            )
    return policy


def enqueue_manual(actor: Any, mode: str = "rules"):
    """Queue an explicit run under the review capability."""
    if actor is None or not getattr(actor, "is_authenticated", False) or not can(actor, "review"):
        raise PermissionDenied("Tu rol no permite ejecutar revisiones de inteligencia.")
    if mode not in {"rules", "native"}:
        raise ValidationError("mode debe ser rules o native")
    if mode == "native" and not getattr(settings, "MILENIO_CODEX_ENABLED", False):
        raise ValidationError("La ejecución nativa no está habilitada en esta instalación de Codex local.")
    job, _ = models.AutomationJob.objects.get_or_create(
        dedup_key=f"manual:{uuid.uuid4()}",
        defaults={"trigger": "manual", "mode": mode, "actor": actor, "max_attempts": 1 if mode == "native" else 3},
    )
    return job


def _enqueue_automatic(now):
    policy, _ = models.AutomationPolicy.objects.get_or_create(pk=1)
    state, _ = models.AutomationWorkerState.objects.get_or_create(pk=1)
    if policy.paused or not policy.automatic_enabled:
        return None

    cutoff = now - timedelta(seconds=policy.debounce_seconds)
    event = _eligible_events().filter(pk__gt=state.event_cursor, created_at__lte=cutoff).order_by("-pk").only("pk").first()
    if event:
        highwater = event.pk
        with transaction.atomic():
            state = models.AutomationWorkerState.objects.select_for_update().get(pk=1)
            if highwater <= state.event_cursor:
                return None
            job, _ = models.AutomationJob.objects.get_or_create(
                dedup_key=f"events:{state.event_cursor}:{highwater}",
                defaults={"trigger": "events", "mode": "native" if policy.native_enabled else "rules",
                          "source_highwater": highwater},
            )
            # Cursor advances only after the corresponding durable job exists.
            state.event_cursor = highwater
            state.save(update_fields=["event_cursor"])
        return job

    if state.next_periodic_at <= now:
        with transaction.atomic():
            state = models.AutomationWorkerState.objects.select_for_update().get(pk=1)
            if state.next_periodic_at > now:
                return None
            highwater = _eligible_events().filter(created_at__lte=now).aggregate(value=Max("pk"))["value"] or state.event_cursor
            due_at = state.next_periodic_at
            job, _ = models.AutomationJob.objects.get_or_create(
                dedup_key=f"interval:{due_at.isoformat()}",
                defaults={"trigger": "interval", "mode": "native" if policy.native_enabled else "rules",
                          "source_highwater": highwater},
            )
            # The periodic run also captures the cursor before processing.
            state.event_cursor = max(state.event_cursor, highwater)
            state.next_periodic_at = now + timedelta(minutes=policy.interval_minutes)
            state.save(update_fields=["event_cursor", "next_periodic_at"])
        return job
    return None


def _recover_expired_jobs(now):
    """Recover only safely replayable jobs after an expired worker lease."""
    for job in models.AutomationJob.objects.filter(status="running"):
        if job.mode == "native":
            job.status = "failed"
            job.errors = [*job.errors, "Worker lease expired during native execution; outcome is ambiguous and will not be invoked again."]
            job.finished_at = now
            job.save(update_fields=["status", "errors", "finished_at"])
        elif job.attempts >= job.max_attempts:
            job.status = "failed"
            job.errors = [*job.errors, "Worker lease expired; retry limit reached."]
            job.finished_at = now
            job.save(update_fields=["status", "errors", "finished_at"])
        else:
            job.status = "pending"
            job.available_at = now
            job.errors = [*job.errors, "Worker lease expired; safe rules job returned to queue."]
            job.save(update_fields=["status", "available_at", "errors"])


def _snapshot_id(snapshot):
    if snapshot is None:
        return ""
    if isinstance(snapshot, (str, int)):
        return str(snapshot)
    return str(getattr(snapshot, "pk", None) or getattr(snapshot, "id", ""))


def _execute(job):
    from . import analytics, intelligence

    if job.mode == "native":
        policy = models.AutomationPolicy.objects.get(pk=1)
        policy_disabled = job.trigger in {"events", "interval"} and not policy.native_enabled
        if policy_disabled or not getattr(settings, "MILENIO_CODEX_ENABLED", False):
            raise RuntimeError("La ejecución Codex nativa se deshabilitó antes de iniciar este trabajo.")
    actor = job.actor or _system_actor()
    snapshot = analytics.refresh_analytics(actor, trigger=job.trigger)
    job.snapshot_id = _snapshot_id(snapshot)
    if not job.snapshot_id:
        raise RuntimeError("analytics.refresh_analytics no devolvió una identidad de snapshot verificable")
    runs = intelligence.run_agents(actor, mode=job.mode, agent="all")
    job.agent_run_ids = list(dict.fromkeys([*job.agent_run_ids, *[str(run.pk) for run in runs]]))
    snapshot_cursor = getattr(snapshot, "audit_cursor", None)
    post_agent_cursor = models.AuditEvent.objects.aggregate(value=Max("pk"))["value"] or 0
    errors = [f"{run.agent} run {run.pk}: {run.error or run.status}" for run in runs if run.status != "completed"]
    job.result = {"snapshot_id": job.snapshot_id,
                  "agent_runs": [{"id": str(run.pk), "agent": run.agent, "status": run.status,
                                  "model_invoked": run.model_invoked} for run in runs],
                  "evidence_context": {
                      "snapshot_audit_cursor": snapshot_cursor,
                      "post_agent_audit_cursor": post_agent_cursor,
                      "audit_cursor_advanced_after_snapshot": (
                          post_agent_cursor > snapshot_cursor if snapshot_cursor is not None else None),
                      "cursor_scope": "AuditEvent high-water; records audited activity only and cannot rule out unaudited table changes.",
                      "interpretation": "El corte analítico se guarda antes de los revisores; éstos evalúan registros operativos vigentes. Recomprueba la evidencia antes de aceptar una propuesta.",
                  }}
    job.errors = [*job.errors, *errors]
    if errors:
        raise RuntimeError("Uno o más agentes no terminaron correctamente")


def _heartbeat_lease(stop_event, lost_event, *, job_id: int, lease_owner: str) -> None:
    """Renew only the lease still owned by this running job, with thread-local DB hygiene."""
    while not stop_event.wait(HEARTBEAT_INTERVAL_SECONDS):
        close_old_connections()
        try:
            if not models.AutomationJob.objects.filter(pk=job_id, status="running").exists():
                lost_event.set()
                return
            now = timezone.now()
            renewed = models.AutomationWorkerState.objects.filter(
                pk=1, lease_owner=lease_owner, status="running").update(
                    lease_expires_at=now + timedelta(seconds=LEASE_SECONDS), heartbeat_at=now)
            if renewed != 1:
                lost_event.set()
                return
        except Exception as error:
            logger.warning("Automation lease heartbeat failed: %s: %s", type(error).__name__, str(error)[:300])
        finally:
            close_old_connections()


def _execute_with_heartbeat(job, lease_owner: str) -> bool:
    stop_event = threading.Event()
    lost_event = threading.Event()
    heartbeat = threading.Thread(
        target=_heartbeat_lease, args=(stop_event, lost_event),
        kwargs={"job_id": job.pk, "lease_owner": lease_owner},
        name=f"automation-heartbeat-{job.pk}", daemon=True,
    )
    heartbeat.start()
    try:
        _execute(job)
    finally:
        stop_event.set()
        heartbeat.join(timeout=max(5.0, HEARTBEAT_INTERVAL_SECONDS + 2.0))
    return lost_event.is_set()


def _persist_outcome(job, *, lease_owner: str, completed_at) -> bool:
    """Fence job and worker finalization so a stale worker cannot overwrite a successor."""
    with transaction.atomic():
        state = models.AutomationWorkerState.objects.select_for_update().get(pk=1)
        if state.lease_owner != lease_owner:
            return False
        updates = {
            "snapshot_id": job.snapshot_id,
            "agent_run_ids": job.agent_run_ids,
            "result": job.result,
            "errors": job.errors,
            "status": job.status,
            "available_at": job.available_at,
            "finished_at": job.finished_at,
        }
        if models.AutomationJob.objects.filter(pk=job.pk, status="running").update(**updates) != 1:
            return False
        state.lease_owner = ""
        state.lease_expires_at = None
        state.status = "idle" if job.status == "completed" else "error"
        state.heartbeat_at = completed_at
        state.completed_at = completed_at
        state.last_error = "" if job.status == "completed" else "; ".join(job.errors[-2:])[:1000]
        state.save(update_fields=["lease_owner", "lease_expires_at", "status", "heartbeat_at",
                                  "completed_at", "last_error"])
    return True


def run_once(worker_id: str | None = None) -> dict[str, Any]:
    """Generate due work and execute at most one durable job."""
    worker_id = worker_id or str(uuid.uuid4())
    if len(worker_id) > 120:
        raise ValidationError("worker_id excede 120 caracteres")
    now = timezone.now()
    initialize_defaults()
    policy = models.AutomationPolicy.objects.get(pk=1)
    if policy.paused:
        models.AutomationWorkerState.objects.filter(pk=1).update(
            status="paused", heartbeat_at=now)
        return {"status": "paused", "job_id": None}
    _enqueue_automatic(now)
    # Queue defaults use their own timezone.now call; sample after enqueue so
    # a just-created job is immediately eligible on the same worker tick.
    now = timezone.now()

    with transaction.atomic():
        state = models.AutomationWorkerState.objects.select_for_update().get(pk=1)
        if state.lease_expires_at and state.lease_expires_at > now:
            return {"status": "busy", "job_id": None}
        if state.lease_expires_at and state.lease_expires_at <= now:
            _recover_expired_jobs(now)
        job = models.AutomationJob.objects.select_for_update().filter(
            status="pending", available_at__lte=now).order_by("available_at", "created_at", "pk").first()
        if job is None:
            state.lease_owner = ""
            state.lease_expires_at = None
            state.status = "idle"
            state.heartbeat_at = now
            state.save(update_fields=["lease_owner", "lease_expires_at", "status", "heartbeat_at"])
            return {"status": "idle", "job_id": None}
        job.status = "running"
        job.attempts += 1
        job.started_at = now
        job.save(update_fields=["status", "attempts", "started_at"])
        lease_owner = f"{worker_id[:80]}:{uuid.uuid4().hex}"
        state.lease_owner = lease_owner
        state.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
        state.status = "running"
        state.heartbeat_at = now
        state.started_at = now
        state.last_error = ""
        state.save(update_fields=["lease_owner", "lease_expires_at", "status", "heartbeat_at", "started_at", "last_error"])

    try:
        lease_lost = _execute_with_heartbeat(job, lease_owner)
        if lease_lost:
            return {"status": "lease_lost", "job_id": job.pk, "attempts": job.attempts}
        job.status = "completed"
        job.finished_at = timezone.now()
    except Exception as error:
        message = f"{type(error).__name__}: {str(error)[:500]}"
        job.errors = [*job.errors, message]
        retry = job.mode == "rules" and job.attempts < job.max_attempts
        if retry:
            job.status = "pending"
            job.available_at = timezone.now() + timedelta(seconds=min(300, 15 * (2 ** (job.attempts - 1))))
        else:
            job.status = "failed"
            job.finished_at = timezone.now()

    completed = timezone.now()
    if not _persist_outcome(job, lease_owner=lease_owner, completed_at=completed):
        return {"status": "lease_lost", "job_id": job.pk, "attempts": job.attempts}
    return {"status": job.status, "job_id": job.pk, "attempts": job.attempts,
            "snapshot_id": job.snapshot_id, "agent_run_ids": job.agent_run_ids,
            "errors": job.errors}


def serve(*, idle_sleep: float = 2.0, max_idle: int = 0, stop_event=None) -> None:
    """Run ticks continuously; stop_event makes idle waits interruptible."""
    idle_count = 0
    while stop_event is None or not stop_event.is_set():
        result = run_once()
        if result["status"] in {"idle", "busy", "paused"}:
            idle_count += 1
            if max_idle and idle_count >= max_idle:
                break
            if stop_event is not None:
                stop_event.wait(idle_sleep)
            else:
                time.sleep(idle_sleep)
        else:
            idle_count = 0
