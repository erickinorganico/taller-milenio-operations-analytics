"""Durable mail outbox, separate from commercial qualification and operational work."""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Mailbox(models.Model):
    # One connected Gmail account per installation; no secrets in this table.
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    email = models.EmailField(blank=True)
    connected = models.BooleanField(default=False)
    enabled = models.BooleanField(default=False)
    auto_reply = models.BooleanField(default=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    last_sync = models.DateTimeField(null=True)
    last_tick = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=240, blank=True)
    holidays = models.JSONField(default=list)
    site_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)
    public_assets_confirmed = models.BooleanField(default=False)


class MailEnrollment(models.Model):
    account = models.OneToOneField('commercial.SalesAccount', on_delete=models.PROTECT, related_name='mail_enrollment')
    contact = models.ForeignKey('commercial.BusinessContact', on_delete=models.PROTECT)
    # Globally unique in this installation, including finished/paused enrollments.
    email = models.EmailField(unique=True)
    state = models.CharField(max_length=24, default='active')
    reason = models.CharField(max_length=240, blank=True)
    manual_control = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)


class MailMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(MailEnrollment, on_delete=models.PROTECT, related_name='messages')
    kind = models.CharField(max_length=16)  # cold / auto / manual
    step = models.PositiveSmallIntegerField(default=0)
    recipient = models.EmailField()
    subject = models.CharField(max_length=240)
    body = models.TextField()
    html = models.TextField(blank=True)
    status = models.CharField(max_length=16, default='queued', db_index=True)
    due_at = models.DateTimeField(default=timezone.now)
    attempted_at = models.DateTimeField(null=True)
    sent_at = models.DateTimeField(null=True)
    provider_id = models.CharField(max_length=128, blank=True)
    thread_id = models.CharField(max_length=128, blank=True)
    reply_to_id = models.CharField(max_length=500, blank=True)
    inbound = models.OneToOneField('MailInbound', on_delete=models.PROTECT, null=True, related_name='response')
    error = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    @property
    def rfc_id(self):
        return f'<{self.pk}@mail.milenio.local>'

    class Meta:
        constraints = [models.UniqueConstraint(fields=['enrollment', 'step'], condition=models.Q(kind='cold'), name='mail_unique_cold_step')]


class MailInbound(models.Model):
    enrollment = models.ForeignKey(MailEnrollment, on_delete=models.PROTECT, related_name='incoming')
    provider_id = models.CharField(max_length=128, unique=True)
    thread_id = models.CharField(max_length=128)
    rfc_id = models.CharField(max_length=500, blank=True)
    sender = models.EmailField(blank=True)
    subject = models.CharField(max_length=240, blank=True)
    body = models.TextField(blank=True)
    category = models.CharField(max_length=24)
    human_reply = models.BooleanField(default=False)
    needs_review = models.BooleanField(default=True)
    received_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)


class MailWorkerLease(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    token = models.CharField(max_length=36, blank=True)
    expires_at = models.DateTimeField(default=timezone.now)
