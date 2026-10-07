"""Idempotent research import. Preserves canonical IDs; never upgrades research to qualification."""
import hashlib
import json
import re
import uuid
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .models import SalesAccount, FleetProfile, BusinessContact, Evidence, ResearchBatch, ImportReceipt
from .rules import domain_for
from .services import audit

NAMESPACE = uuid.UUID('8e05c8ea-859e-4e56-9056-a2415f58a54d')


@transaction.atomic
def import_catalog(path, actor):
    raw = path.read_bytes()
    fingerprint = hashlib.sha256(raw).hexdigest()
    previous = ImportReceipt.objects.filter(fingerprint=fingerprint).first()
    if previous: return {**previous.summary, 'already_imported': True}
    records = json.loads(raw.decode('utf-8-sig'))['records']
    keys = [r.get('canonical_id') or r.get('record_id') for r in records]
    if not all(keys) or len(keys) != len(set(keys)):
        raise ValidationError('El catálogo contiene identidades vacías o repetidas.')
    batch, _ = ResearchBatch.objects.get_or_create(key='catalog-20261003-485', defaults={
        'title':'Catálogo investigado · 485 candidatos · 3 octubre 2026', 'source':'research', 'created_by':actor,
        'notes':'Identidad, unidades y necesidad pendientes de revisión comercial. No autoriza contacto.'})
    count, contacts, skipped = 0, 0, 0
    for record, key in zip(records, keys):
        pk = uuid.uuid5(NAMESPACE, key)
        if SalesAccount.objects.filter(pk=pk).exists():
            skipped += 1; continue
        urls = record.get('source_urls') or []
        source = next((u for u in urls if isinstance(u, str) and len(u) <= 200 and u.startswith(('https://','http://'))), '')
        website = record.get('website') or ''
        if len(website) > 200: website = ''
        try: domain = domain_for(website)
        except ValidationError: domain = None
        a = SalesAccount.objects.create(id=pk, name=record['company'][:200], branch=record.get('branch', '')[:120],
            owner=actor, batch=batch, city=(record.get('city') or 'Por confirmar')[:100], website=website,
            domain=domain, segment=(record.get('sector') or record.get('research_segment') or '')[:120],
            source='website' if domain else 'manual', source_url=source,
            notes=f'ID canónico: {key}\nInvestigación del catálogo; no es flotilla calificada.\n' + record.get('notes',''),
            next_action='Revisar identidad, canal y unidades antes de incorporar al piloto')
        FleetProfile.objects.create(account=a)
        # Entire source snapshot keeps WhatsApp, social networks, branches, dates and identity warnings.
        Evidence.objects.create(account=a, topic='identity', source_url=source,
            source_note=f'Catálogo 20261003; ID {key}'[:240], reviewed=False, created_by=actor,
            excerpt=json.dumps(record, ensure_ascii=False, indent=2))
        emails = sorted(set(re.findall(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+', record.get('public_email') or '')))
        for email in emails:
            try: validate_email(email)
            except ValidationError: continue
            if len(email) > 254: continue
            BusinessContact.objects.create(account=a, name='Correo empresarial publicado · destinatario por confirmar',
                email=email.lower(), source_url=source, source_note=f'Importado del catálogo; ID {key}'[:240],
                published_business=True)
            contacts += 1
        phone = record.get('public_phone') or ''
        if phone:
            BusinessContact.objects.create(account=a, name='Teléfono publicado · ver ficha fuente', phone=phone[:40],
                source_url=source, source_note=f'Catálogo; texto completo y canales en evidencia {key}'[:240], published_business=True)
        count += 1
    summary = {'created':count, 'email_contacts':contacts, 'skipped':skipped, 'source_records':len(records)}
    ImportReceipt.objects.create(fingerprint=fingerprint, summary=summary, created_by=actor)
    audit(None, actor, 'mail_catalog_imported', **summary)
    return summary
