"""Durable local automation state; imported by ``workshop.models``."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class AutomationPolicy(models.Model):
    """Singleton configuration for local analytics automation."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    automatic_enabled = models.BooleanField(default=True)
    interval_minutes = models.PositiveIntegerField(default=60)
    debounce_seconds = models.PositiveIntegerField(default=30)
    native_enabled = models.BooleanField(default=False)
    paused = models.BooleanField(default=False)
    updated_at = models.DateTimeField(default=timezone.now)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")


class AutomationWorkerState(models.Model):
    """Singleton worker lease and high-water cursor."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    event_cursor = models.PositiveBigIntegerField(default=0)
    next_periodic_at = models.DateTimeField(default=timezone.now)
    lease_owner = models.CharField(max_length=120, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, default="idle")
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)


class AutomationJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        RUNNING = "running", "En curso"
        COMPLETED = "completed", "Completado"
        FAILED = "failed", "Falló"

    dedup_key = models.CharField(max_length=180, unique=True)
    trigger = models.CharField(max_length=20)
    mode = models.CharField(max_length=12, default="rules")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="automation_jobs")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    source_highwater = models.PositiveBigIntegerField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    available_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    snapshot_id = models.CharField(max_length=100, blank=True)
    agent_run_ids = models.JSONField(default=list)
    result = models.JSONField(default=dict)
    errors = models.JSONField(default=list)

    class Meta:
        indexes = [models.Index(fields=["status", "available_at", "created_at"])]
