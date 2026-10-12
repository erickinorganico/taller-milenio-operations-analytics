"""Explicit synthetic permissions/approvals; no production test-mode bypass."""
from datetime import timedelta
from unittest.mock import patch
from django.conf import settings
from . import mail_safety as safety


def synthetic_permission(contact, actor, clock):
    directory = settings.DATA_DIR / 'mail-evidence'
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'synthetic-permission.txt').write_text('Synthetic recipient explicitly invited Milenio email presentation and followups.', encoding='utf-8')
    with patch('django.utils.timezone.now', return_value=clock):
        return safety.record_permission(contact, actor, scopes=['presentation', 'followup'],
            granted_at=clock-timedelta(days=1), valid_until=clock+timedelta(days=365),
            evidence_file='synthetic-permission.txt', evidence_sha256=safety.evidence_hash('synthetic-permission.txt'))


def synthetic_release(box, actor, clock):
    with patch('django.utils.timezone.now', return_value=clock):
        safety.release_hold(actor, sender=box.email, incident_reference='Synthetic incident review',
            reconciliation_reference='Synthetic receipt review', approval_reference='Synthetic exact user approval',
            evidence_file='synthetic-permission.txt', evidence_sha256=safety.evidence_hash('synthetic-permission.txt'),
            verified_profile={'emailAddress': box.email})
        box.enabled = True; box.save(update_fields=['enabled'])


def synthetic_approve(messages, actor, clock):
    with patch('django.utils.timezone.now', return_value=clock):
        return safety.approve_batch(safety.preview([m.pk for m in messages]), actor,
                                    'Synthetic review of these exact messages', clock+timedelta(hours=4))
