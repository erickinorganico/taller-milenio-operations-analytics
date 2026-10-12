"""Private, durable controls. No contact is grandfathered into marketing permission."""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class MailSafety(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    paused = models.BooleanField(default=True)
    reason = models.CharField(max_length=240, default='Revisión del incidente y autorización pendientes')
    revision = models.PositiveIntegerField(default=1)
    provider_status = models.CharField(max_length=24, default='unverified')
    provider_checked_at = models.DateTimeField(null=True)
    sender = models.EmailField(blank=True)
    incident_reference = models.CharField(max_length=500, blank=True)
    reconciliation_reference = models.CharField(max_length=500, blank=True)
    approval_reference = models.CharField(max_length=500, blank=True)


class MailPermission(models.Model):
    contact = models.OneToOneField('commercial.BusinessContact', on_delete=models.PROTECT)
    recipient = models.EmailField()
    status = models.CharField(max_length=24, default='unverified')
    brand = models.CharField(max_length=24, default='Milenio')
    channel = models.CharField(max_length=24, default='email')
    scopes = models.JSONField(default=list)  # presentation, followup; never inferred from publication
    granted_at = models.DateTimeField()
    valid_until = models.DateTimeField()
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reviewed_at = models.DateTimeField(default=timezone.now)
    evidence_file = models.CharField(max_length=240)
    evidence_sha256 = models.CharField(max_length=64)


class MailBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.EmailField()
    safety_revision = models.PositiveIntegerField()
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    approval_reference = models.CharField(max_length=500)
    approved_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    digest = models.CharField(max_length=64)
    revoked = models.BooleanField(default=False)


class MailBatchItem(models.Model):
    batch = models.ForeignKey(MailBatch, on_delete=models.PROTECT, related_name='items')
    message = models.OneToOneField('commercial.MailMessage', on_delete=models.PROTECT)
    payload_digest = models.CharField(max_length=64)
    permission_digest = models.CharField(max_length=64)


class MailAdmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField('commercial.MailMessage', on_delete=models.PROTECT)
    batch_item = models.OneToOneField(MailBatchItem, on_delete=models.PROTECT)
    worker_token = models.CharField(max_length=36)
    reserved_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField()
    state = models.CharField(max_length=24, default='reserved')
