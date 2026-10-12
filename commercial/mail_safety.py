"""Fail-closed admission at the sender, shared by UI, agents and worker.

Supported routes cannot send without a reviewed finite batch. Local administrators
remain trusted; this is not a sandbox for arbitrary Python or third-party connectors.
"""
import hashlib
import json
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from .models import (Mailbox, MailSafety, MailPermission, MailBatch, MailBatchItem,
                     MailAdmission, MailMessage, MailEnrollment, MailInbound, MailWorkerLease)
from .rules import qualify, suppressed
from .services import audit

TZ = ZoneInfo('America/Tijuana')
UTC = ZoneInfo('UTC')
MAX_BATCH = MAX_DAILY = 5  # Internal pilot limits, NOT provider anti-spam thresholds.
MIN_INTERVAL = timedelta(minutes=10)
MAX_TOUCHES = 3
MIN_BUSINESS_DAYS = 4


class MailBlocked(ValidationError):
    def __init__(self, code):
        self.code_name = code
        super().__init__('Envío bloqueado: ' + code)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def manager(actor):
    from workshop.access import can
    if not actor or not actor.is_active or not can(actor, 'manage'):
        raise MailBlocked('human_review_required')


def evidence_hash(relative):
    data_root = settings.DATA_DIR.resolve()
    base = (data_root / 'mail-evidence').resolve()
    if not base.is_relative_to(data_root):
        raise MailBlocked('private_evidence_directory_invalid')
    path = (base / relative).resolve()
    if not relative or path == base or not path.is_relative_to(base) or not path.is_file():
        raise MailBlocked('private_evidence_missing')
    if path.stat().st_size > 5 * 1024 * 1024:
        raise MailBlocked('evidence_too_large')
    return hashlib.sha256(path.read_bytes()).hexdigest()


@transaction.atomic
def record_permission(contact, actor, *, scopes, granted_at, valid_until, evidence_file, evidence_sha256):
    manager(actor)
    now = timezone.now()
    validate_email(contact.email)
    if (not isinstance(scopes, list) or not scopes or set(scopes) - {'presentation', 'followup'}
            or not timezone.is_aware(granted_at) or not timezone.is_aware(valid_until)
            or not granted_at <= now < valid_until or evidence_hash(evidence_file) != evidence_sha256):
        raise MailBlocked('invalid_permission_evidence')
    grant, _ = MailPermission.objects.update_or_create(contact=contact, defaults={
        'recipient': contact.email.strip().lower(), 'status': 'granted', 'brand': 'Milenio',
        'channel': 'email', 'scopes': sorted(set(scopes)), 'granted_at': granted_at,
        'valid_until': valid_until, 'reviewer': actor, 'reviewed_at': now,
        'evidence_file': evidence_file, 'evidence_sha256': evidence_sha256})
    audit(contact.account, actor, 'mail_permission_reviewed', permission=grant.pk, scopes=grant.scopes)
    return grant


def permission_for(contact, scope, now=None):
    now = now or timezone.now()
    p = MailPermission.objects.filter(contact=contact).select_related('reviewer').first()
    if (not p or p.status != 'granted' or p.recipient != contact.email.strip().lower()
            or p.channel != 'email' or p.brand != 'Milenio' or not isinstance(p.scopes, list)
            or scope not in p.scopes or not p.granted_at <= p.reviewed_at <= now < p.valid_until
            or not p.reviewer.is_active or evidence_hash(p.evidence_file) != p.evidence_sha256):
        raise MailBlocked('recipient_permission_missing_or_expired')
    manager(p.reviewer)
    if not p.granted_at <= timezone.now() < p.valid_until:
        raise MailBlocked('recipient_permission_missing_or_expired')
    return digest({'id': p.pk, 'recipient': p.recipient, 'scopes': p.scopes,
                   'granted_at': p.granted_at.isoformat(), 'reviewed_at': p.reviewed_at.isoformat(),
                   'expires': p.valid_until.isoformat(), 'reviewer': p.reviewer_id,
                   'evidence': p.evidence_sha256})


def policy(now=None):
    now = now or timezone.now()
    p, _ = MailSafety.objects.get_or_create(pk=1)
    if p.paused:
        raise MailBlocked('safety_hold')
    if (p.provider_status != 'available' or not p.provider_checked_at
            or not timedelta(0) <= now - p.provider_checked_at <= timedelta(days=1)
            or not p.sender or not all([p.incident_reference, p.reconciliation_reference, p.approval_reference])):
        raise MailBlocked('provider_unverified')
    if (settings.DATA_DIR / '.mail-recovery-hold').exists():
        raise MailBlocked('recovery_hold')
    return p


@transaction.atomic
def hold(reason, actor=None):
    p, _ = MailSafety.objects.get_or_create(pk=1)
    p = MailSafety.objects.select_for_update().get(pk=1)
    p.paused = True
    p.reason = reason[:240]
    p.revision += 1
    p.save()
    Mailbox.objects.filter(pk=1).update(enabled=False)
    MailBatch.objects.filter(revoked=False).update(revoked=True)
    MailMessage.objects.filter(status='queued').update(error='Bloqueo de seguridad; requiere nueva revisión')
    audit(None, actor, 'mail_safety_hold', reason=reason[:240], revision=p.revision)


@transaction.atomic
def release_hold(actor, *, sender, incident_reference, reconciliation_reference, approval_reference,
                 evidence_file, evidence_sha256, verified_profile):
    """Explicit human review + fresh provider profile; connecting OAuth never calls this."""
    manager(actor)
    if (not all([incident_reference.strip(), reconciliation_reference.strip(), approval_reference.strip()])
            or evidence_hash(evidence_file) != evidence_sha256):
        raise MailBlocked('incident_review_missing')
    box = Mailbox.objects.select_for_update().get(pk=1)
    sender = sender.strip().lower()
    if not box.connected or not box.owner_id or sender != box.email.lower() or verified_profile.get('emailAddress', '').lower() != sender:
        raise MailBlocked('sender_identity_mismatch')
    if MailMessage.objects.filter(status__in=['sending', 'unknown']).exists():
        raise MailBlocked('unreconciled_attempt')
    if (settings.DATA_DIR / '.mail-recovery-hold').exists():
        raise MailBlocked('recovery_hold')
    p, _ = MailSafety.objects.get_or_create(pk=1)
    p = MailSafety.objects.select_for_update().get(pk=1)
    p.paused, p.reason, p.sender, p.provider_status = False, '', sender, 'available'
    p.provider_checked_at = timezone.now()
    p.revision += 1
    p.incident_reference, p.reconciliation_reference = incident_reference[:500], reconciliation_reference[:500]
    p.approval_reference = approval_reference[:500]
    p.save()
    # New approval never revives an old lot or starts a mailbox.
    MailBatch.objects.filter(revoked=False).update(revoked=True)
    box.enabled = False
    box.save(update_fields=['enabled'])
    audit(None, actor, 'mail_safety_reviewed', revision=p.revision, evidence=evidence_sha256,
          authorization=approval_reference[:500])


def payload_digest(message, sender):
    e = message.enrollment
    return digest({'message': str(message.pk), 'from': sender.lower(), 'to': message.recipient,
        'account': str(e.account_id), 'version': e.account.version, 'contact': e.contact_id,
        'kind': message.kind, 'step': message.step, 'subject': message.subject, 'body': message.body,
        'html': message.html, 'rfc': message.rfc_id, 'reply_to': message.reply_to_id,
        'thread': message.thread_id, 'inbound': message.inbound_id, 'due': message.due_at.isoformat()})


def eligibility(message, now=None):
    now = now or timezone.now()
    e = MailEnrollment.objects.select_related('account', 'contact').get(pk=message.enrollment_id)
    message.enrollment = e
    if (e.account.is_demo or suppressed(e.account) or e.contact.deliverability == 'bounced'
            or e.email != message.recipient or e.contact.email.strip().lower() != message.recipient
            or re.search(r'[\r\n,;<>]', message.recipient)):
        raise MailBlocked('recipient_or_suppression_changed')
    validate_email(message.recipient)
    if message.kind == 'cold':
        if (e.state != 'active' or not qualify(e.account)['exploratory']
                or e.account.stage not in ('research', 'ready')
                or e.account.interactions.filter(kind__in=['reply', 'meeting', 'bounce', 'optout']).exists()
                or e.account.interactions.filter(kind='sent').count() >= MAX_TOUCHES
                or e.incoming.exists() or not 1 <= message.step <= MAX_TOUCHES):
            raise MailBlocked('sequence_stopped')
        previous = e.messages.filter(kind='cold').exclude(pk=message.pk)
        if message.step == 1:
            if previous.filter(status__in=['sent', 'sending', 'unknown']).exists() or e.account.interactions.filter(kind='sent').exists():
                raise MailBlocked('duplicate_initial')
        else:
            last = previous.filter(step=message.step-1, status='sent').first()
            if not last or not last.sent_at:
                raise MailBlocked('previous_touch_missing')
            box = Mailbox.objects.get(pk=1)
            due = next_touch(last.sent_at, box.holidays)
            if message.due_at < due:
                raise MailBlocked('followup_too_early')
        return permission_for(e.contact, 'presentation' if message.step == 1 else 'followup', now)
    if message.kind not in ('auto', 'manual') or not message.inbound_id:
        raise MailBlocked('reply_without_request')
    inbound = MailInbound.objects.get(pk=message.inbound_id)
    if (inbound.enrollment_id != e.pk or not inbound.human_reply or inbound.sender != e.email
            or not inbound.rfc_id or message.reply_to_id != inbound.rfc_id or message.thread_id != inbound.thread_id
            or inbound.received_at > now or inbound.category in ('optout', 'negative', 'spam', 'spam_report', 'automatic', 'bounce', 'manual_sent', 'unknown_sender')):
        raise MailBlocked('reply_context_invalid')
    box = Mailbox.objects.get(pk=1)
    if message.kind == 'auto' and (not box.auto_reply or e.manual_control
            or inbound.category not in ('location', 'hours', 'interest') or e.incoming.filter(category='manual_sent').exists()):
        raise MailBlocked('automatic_reply_not_allowed')
    # Wanted reply in this specific conversation; never a grant for another campaign.
    return digest({'request': inbound.pk, 'rfc': inbound.rfc_id, 'sender': inbound.sender,
                   'body': inbound.body, 'category': inbound.category, 'received': inbound.received_at.isoformat()})


def next_touch(sent_at, holidays):
    validate_calendar(holidays)
    local = sent_at.astimezone(TZ)
    day, count = local.date(), 0
    while count < MIN_BUSINESS_DAYS:
        day += timedelta(days=1)
        if day.weekday() < 5 and day.isoformat() not in holidays:
            count += 1
    # At least four whole business days, preserving the send's wall time.
    return datetime.combine(day, local.timetz().replace(tzinfo=None), TZ)


def validate_calendar(holidays):
    if not isinstance(holidays, list) or len(holidays) > 366:
        raise MailBlocked('invalid_calendar')
    try:
        for value in holidays:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError()
    except (ValueError, TypeError):
        raise MailBlocked('invalid_calendar')


def preview(message_ids):
    """Private review manifest; a draft/preview never authorizes the sender."""
    ids = [str(x) for x in message_ids]
    if not 1 <= len(ids) <= MAX_BATCH or len(set(ids)) != len(ids):
        raise MailBlocked('finite_batch_required')
    box, _ = Mailbox.objects.get_or_create(pk=1)
    p, _ = MailSafety.objects.get_or_create(pk=1)
    items = []
    recipients, accounts = set(), set()
    for pk in ids:
        m = MailMessage.objects.select_related('enrollment__account').get(pk=pk)
        if m.status != 'queued' or hasattr(m, 'mailbatchitem'):
            raise MailBlocked('message_already_approved_or_attempted')
        permission = eligibility(m)
        if m.recipient in recipients or m.enrollment.account_id in accounts:
            raise MailBlocked('duplicate_company_or_recipient')
        recipients.add(m.recipient); accounts.add(m.enrollment.account_id)
        items.append({'message': str(m.pk), 'recipient': m.recipient, 'subject': m.subject,
                      'body': m.body, 'html': m.html, 'payload_digest': payload_digest(m, box.email),
                      'permission_digest': permission})
    return {'schema': 'milenio-reviewed-batch-v1', 'sender': box.email,
            'safety_revision': p.revision, 'items': items}


def batch_digest(batch):
    return digest({'sender': batch.sender, 'revision': batch.safety_revision, 'actor': batch.approved_by_id,
        'reference': batch.approval_reference, 'approved': batch.approved_at.astimezone(UTC).isoformat(),
        'expires': batch.expires_at.astimezone(UTC).isoformat(),
        'items': sorted((str(i.message_id), i.payload_digest, i.permission_digest) for i in batch.items.all())})


@transaction.atomic
def approve_batch(manifest, actor, reference, expires_at):
    manager(actor)
    p = policy()
    now = timezone.now()
    if not reference.strip() or not now < expires_at <= now + timedelta(hours=4):
        raise MailBlocked('finite_approval_required')
    if not isinstance(manifest, dict) or manifest.get('schema') != 'milenio-reviewed-batch-v1':
        raise MailBlocked('invalid_manifest')
    expected = preview([item['message'] for item in manifest.get('items', [])])
    if manifest != expected or manifest['sender'].lower() != p.sender:
        raise MailBlocked('reviewed_content_changed')
    batch = MailBatch.objects.create(sender=p.sender, safety_revision=p.revision, approved_by=actor,
        approval_reference=reference[:500], approved_at=now, expires_at=expires_at)
    for item in manifest['items']:
        MailBatchItem.objects.create(batch=batch, message_id=item['message'],
            payload_digest=item['payload_digest'], permission_digest=item['permission_digest'])
    batch.digest = batch_digest(batch)
    batch.save(update_fields=['digest'])
    audit(None, actor, 'mail_finite_batch_approved', batch=str(batch.pk), count=len(manifest['items']),
          digest=batch.digest, authorization=reference[:500])
    return batch


def current_checks(message, sender, worker_token, now):
    if settings.MILENIO_MODE == 'live':
        from milenio_web.deployment import guard_server
        deployment = guard_server()
        if not deployment.get('mail_worker_allowed'):
            raise MailBlocked('deployment_paused')
    p = policy(now)
    box = Mailbox.objects.get(pk=1)
    if not box.enabled or not box.connected or not box.owner_id or box.email.lower() != p.sender or sender.lower() != p.sender:
        raise MailBlocked('sender_identity_mismatch')
    lease = MailWorkerLease.objects.filter(pk=1, token=worker_token, expires_at__gt=now).first()
    if not worker_token or not lease:
        raise MailBlocked('worker_lease_missing')
    if not box.last_sync or not timedelta(0) <= now - box.last_sync <= timedelta(minutes=5):
        raise MailBlocked('mailbox_snapshot_stale')
    if MailMessage.objects.filter(status__in=['unknown', 'sending']).exclude(pk=message.pk).exists():
        raise MailBlocked('unreconciled_attempt')
    local = now.astimezone(TZ)
    validate_calendar(box.holidays)
    if local.weekday() >= 5 or local.date().isoformat() in box.holidays or not 9 <= local.hour < 16:
        raise MailBlocked('outside_window')
    if message.due_at > now:
        raise MailBlocked('not_due')
    item = MailBatchItem.objects.filter(message=message).select_related('batch__approved_by').first()
    if not item:
        raise MailBlocked('batch_approval_missing')
    b = item.batch
    manager(b.approved_by)
    if (b.revoked or b.safety_revision != p.revision or b.sender != p.sender
            or not b.approved_at <= now < b.expires_at or not b.approved_by.is_active
            or not 1 <= b.items.count() <= MAX_BATCH or b.digest != batch_digest(b)
            or item.payload_digest != payload_digest(message, sender)
            or item.permission_digest != eligibility(message, now)):
        raise MailBlocked('approval_stale_or_changed')
    # File/identity review can be slow. Recheck real time at the last DB admission point.
    actual = timezone.now()
    actual_local = actual.astimezone(TZ)
    if (actual_local.weekday() >= 5 or actual_local.date().isoformat() in box.holidays
            or not 9 <= actual_local.hour < 16 or not b.approved_at <= actual < b.expires_at
            or not lease.expires_at > actual or actual - box.last_sync > timedelta(minutes=5)):
        raise MailBlocked('outside_window' if not 9 <= actual_local.hour < 16 else 'admission_time_changed')
    return item


@transaction.atomic(durable=True)
def reserve(message_id, sender, worker_token):
    """SQLite IMMEDIATE serializes the mailbox/budget; durable attempts survive failures."""
    now = timezone.now()
    MailSafety.objects.get_or_create(pk=1)
    MailSafety.objects.select_for_update().get(pk=1)
    m = MailMessage.objects.select_for_update().select_related('enrollment__account').get(pk=message_id)
    if m.status != 'queued' or MailAdmission.objects.filter(message=m).exists():
        raise MailBlocked('already_attempted')
    item = current_checks(m, sender, worker_token, now)
    now = timezone.now()
    start = datetime.combine(now.astimezone(TZ).date(), time.min, TZ)
    # Include legacy attempts, timeout/unknown, cancelled admissions and all response kinds.
    attempts = MailMessage.objects.filter(attempted_at__gte=start)
    if attempts.count() >= MAX_DAILY or MailAdmission.objects.filter(reserved_at__gte=start).count() >= MAX_DAILY:
        raise MailBlocked('daily_limit')
    if MailMessage.objects.filter(attempted_at__gt=now-MIN_INTERVAL).exists() or MailAdmission.objects.filter(reserved_at__gt=now-MIN_INTERVAL).exists():
        raise MailBlocked('minimum_interval')
    admission = MailAdmission.objects.create(message=m, batch_item=item, worker_token=worker_token,
        reserved_at=now, expires_at=now+timedelta(seconds=30))
    m.status, m.attempted_at, m.error = 'sending', now, ''
    m.save(update_fields=['status', 'attempted_at', 'error'])
    return admission


@transaction.atomic(durable=True)
def consume(admission_id, message, sender):
    """Check immediately before HTTP; consume once, commit BEFORE transmitting bytes."""
    now = timezone.now()
    a = MailAdmission.objects.select_for_update().filter(pk=admission_id, message_id=message.pk).first()
    if not a or a.state != 'reserved' or not a.reserved_at <= now < a.expires_at:
        raise MailBlocked('admission_missing_expired_or_consumed')
    persisted = MailMessage.objects.select_related('enrollment__account').get(pk=message.pk)
    if persisted.status != 'sending' or payload_digest(message, sender) != payload_digest(persisted, sender):
        raise MailBlocked('payload_changed_after_reservation')
    current_checks(persisted, sender, a.worker_token, now)
    if timezone.now() >= a.expires_at:
        raise MailBlocked('admission_missing_expired_or_consumed')
    a.state = 'submitted'
    a.save(update_fields=['state'])
    return a


def status():
    p, _ = MailSafety.objects.get_or_create(pk=1)
    return {'paused': p.paused, 'reason': p.reason, 'revision': p.revision,
            'provider_status': p.provider_status, 'permission_records': MailPermission.objects.filter(status='granted').count(),
            'max_batch': MAX_BATCH, 'max_total_daily': MAX_DAILY, 'minimum_interval_seconds': 600,
            'direct_connector_sending_supported': False}
