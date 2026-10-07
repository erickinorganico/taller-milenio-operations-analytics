"""Document drafts stay separate from operational orders until reviewed."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class DocumentCapture(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En cola de lectura"
        READING = "reading", "Leyendo fotografía"
        REVIEW = "review", "Por revisar"
        CONFIRMED = "confirmed", "Revisado para exportar"
        APPLIED = "applied", "Aplicado al taller"

    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=12, choices=[("order", "Orden de trabajo"), ("service", "Hoja de servicio")])
    photo = models.ImageField(upload_to="document-captures/%Y/%m/")
    fingerprint = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    raw_text = models.TextField(blank=True)
    data = models.JSONField(default=dict)
    reading_note = models.CharField(max_length=350, blank=True)
    reading_token = models.CharField(max_length=32, blank=True)
    reading_started_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_documents")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_documents")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    provider = models.CharField(max_length=16, default="local")
    model_name = models.CharField(max_length=100, blank=True)
    extraction = models.JSONField(default=dict)
    service_items = models.JSONField(default=list)
    work_order = models.ForeignKey("workshop.WorkOrder", null=True, blank=True, on_delete=models.PROTECT, related_name="document_captures")
    applied_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="applied_documents")
    applied_at = models.DateTimeField(null=True, blank=True)
    application_result = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at", "-pk"]


class CapturedService(models.Model):
    """Requested concepts from documents, distinct from authorized quote lines."""
    work_order = models.ForeignKey("workshop.WorkOrder", on_delete=models.PROTECT, related_name="captured_services")
    fingerprint = models.CharField(max_length=64)
    description = models.CharField(max_length=250)
    kind = models.CharField(max_length=12, default="unknown", choices=[("unknown", "Por clasificar"), ("labor", "Mano de obra"), ("service", "Servicio"), ("part", "Refacción")])
    quantity = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    part_sku = models.CharField(max_length=80, blank=True)
    documents = models.ManyToManyField(DocumentCapture, related_name="captured_services")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["work_order", "fingerprint"], name="uniq_order_captured_service")]


class PhotoQuoteBatch(models.Model):
    """A confirmed photo-to-quote request may be repeated without adding lines."""
    key = models.CharField(max_length=64, unique=True)
    request_fingerprint = models.CharField(max_length=64)
    quote = models.ForeignKey("workshop.Quote", on_delete=models.PROTECT, related_name="photo_batches")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
