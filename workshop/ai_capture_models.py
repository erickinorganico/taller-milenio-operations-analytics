"""Image-reading controls and usage in the existing workshop database."""
from django.conf import settings
from django.db import models
from django.utils import timezone


PHOTO_MODELS = [("gpt-6-luna", "GPT-6 Luna · low"), ("gpt-6.1-sol", "GPT-6.1 Sol · low")]


class PhotoAISettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    enabled = models.BooleanField(default=False)
    model = models.CharField(max_length=32, choices=PHOTO_MODELS, default="gpt-6-luna")
    daily_attempt_limit = models.PositiveIntegerField(default=10)
    per_document_limit = models.PositiveIntegerField(default=2)
    daily_token_budget = models.PositiveIntegerField(default=25000)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(default=timezone.now)


class PhotoAIReading(models.Model):
    class State(models.TextChoices):
        STARTED = "started", "En curso / consumo pendiente"
        COMPLETED = "completed", "Lectura terminada"
        FAILED = "failed", "Lectura fallida"

    capture = models.ForeignKey("workshop.DocumentCapture", on_delete=models.PROTECT, related_name="ai_readings")
    lease = models.CharField(max_length=32, unique=True)
    model = models.CharField(max_length=100)
    reasoning_effort = models.CharField(max_length=8, default="low")
    day = models.DateField(db_index=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.STARTED)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    input_tokens = models.PositiveBigIntegerField(null=True, blank=True)
    output_tokens = models.PositiveBigIntegerField(null=True, blank=True)
    outcome_code = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["-started_at", "-pk"]
