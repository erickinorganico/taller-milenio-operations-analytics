"""Bounded, deterministic Gmail workflow. Network runs only through an injected client."""
import html
import re
import uuid
import unicodedata
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import (Mailbox, MailEnrollment, MailMessage, MailInbound, MailWorkerLease,
                     Interaction, Suppression, SalesAccount, BusinessContact)
from .rules import qualify, suppressed
from .outreach import opening_for
from .services import audit

TZ = ZoneInfo('America/Tijuana')
SIGNATURE = ('\n\nEquipo Milenio\nWhatsApp / teléfono: 664 820 1966\n'
             'Héctor Terán Terán 2740, Jardín Dorado, Tijuana.\n'
             'Si prefieren no recibir más correos, respondan «baja».')


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower()) if not unicodedata.combining(c))


def latest_text(body):
    """Conservative quote trimming: quoted opt-outs and prior marketing are not new requests."""
    lines = []
    for line in body.splitlines():
        n = normalize(line.strip())
        if line.lstrip().startswith('>') or re.match(r'^(on .+wrote:|el .+escribio:|de:|from:|--\s*$|-{2,}\s*(original|mensaje))', n):
            break
        lines.append(line)
    return '\n'.join(lines).strip()[:12000]


def classify(body, headers):
    text = normalize(latest_text(body))
    # Explicit suppression takes precedence; never send an automated opt-out confirmation.
    if re.search(r'\b(baja|unsubscribe|stop|no (me |nos )?(contacten|escriban|envien)|elimin[ae]n? (mi|mis|nuestros) datos)\b', text):
        return 'optout', ''
    automatic = headers.get('auto-submitted', '').lower() not in ('', 'no')
    bulk = headers.get('precedence', '').lower() in ('bulk', 'list', 'junk') or 'list-id' in headers
    if automatic or bulk or re.search(r'fuera de (la )?oficina|out of (the )?office|respuesta automatica|vacaciones', text):
        return 'automatic', ''
    if re.search(r'no (nos |me )?interesa|no gracias|not interested|no tenemos (flotilla|vehiculos)', text):
        return 'negative', ''
    if re.search(r'urgente|accidente|varad[oa]|emergencia|emergency', text):
        return 'urgent', ''
    if re.search(r'precio|cuanto|cotiz|costo|tarifa|credito|factura|descuento|cita|agend|disponib|garantia|reclamo|queja|diesel|electric|hibrid|camion', text):
        return 'review', ''
    # Full-message allowlist, not keyword-based guesses. Anything else needs a person.
    text = re.sub(r'^(hola|buenos dias|buenas tardes)[,.!\s]*', '', text)
    text = re.sub(r'[¿?¡!.,;:]+', '', text).strip()
    if re.fullmatch(r'(donde (estan|se ubican)|cual es (su |la )?(direccion|ubicacion)|me (pueden |puedes )?pasar (su |la )?(direccion|ubicacion))', text):
        return 'location', 'Estamos en Héctor Terán Terán 2740, Jardín Dorado, 22200 Tijuana, B.C.'
    if re.fullmatch(r'(cual es (su |el )?horario|que horario (tienen|manejan)|a que hora (abren|cierran))', text):
        return 'hours', ('El horario del taller es de 8:00 a. m. a 6:00 p. m.; confirma por WhatsApp el día que deseas visitarnos. '
                         'Grúas atiende 24/7 en Tijuana; servicio federal sujeto a confirmación de despacho.')
    if re.fullmatch(r'(si( nos interesa| me interesa)?|me interesa|nos interesa|mas informacion|mand(a|en|ame|enos) (mas )?informacion|envien (mas )?informacion)', text):
        return 'interest', ('Gracias por su interés. Para orientarles: ¿sus unidades son autos, pickups o vans a gasolina? '
                            '¿Cuántas unidades tienen y qué necesitan: mantenimiento o grúa? '
                            'La atención mecánica no incluye diésel, camiones ni eléctricos. '
                            'Un integrante del equipo revisará sus datos antes de proponer un servicio.')
    return 'review', ''


def render_html(body, box):
    # No remote images, tracking pixels, attachments or private Site links.
    paragraphs = ''.join('<p style="margin:0 0 16px">' + html.escape(p).replace('\n', '<br>') + '</p>' for p in body.split('\n\n'))
    links = ''
    if box.public_assets_confirmed:
        for label, url in [('Conoce Milenio', box.site_url), ('Ver presentación en video', box.video_url)]:
            if url.startswith('https://'):
                links += '<p><a style="color:#10265c" href="' + html.escape(url, quote=True) + '">' + label + '</a></p>'
    return ('<!doctype html><html lang="es"><body style="margin:0;background:#fff">'
            '<table role="presentation" width="100%"><tr><td style="padding:28px;font:16px Arial,sans-serif;color:#17243d">'
            '<div style="border-top:4px solid #ff791f;max-width:600px;padding-top:20px">'
            '<p style="font-size:22px;font-weight:bold;color:#10265c">MILENIO</p>' + paragraphs + links + '</div></td></tr></table></body></html>')


def queue_message(enrollment, kind, subject, body, **extra):
    extra.setdefault('due_at', timezone.now())
    box, _ = Mailbox.objects.get_or_create(pk=1)
    rich_body = render_html(body, box)
    if box.public_assets_confirmed:
        for label, url in [('Sitio', box.site_url), ('Video', box.video_url)]:
            if url.startswith('https://'):
                body += f'\n\n{label}: {url}'
    return MailMessage.objects.create(enrollment=enrollment, recipient=enrollment.email, kind=kind,
        subject=subject[:240], body=body, html=rich_body, **extra)


@transaction.atomic
def enroll(contact, actor):
    account = SalesAccount.objects.select_for_update().get(pk=contact.account_id)
    if not qualify(account)['exploratory'] or account.is_demo or account.stage not in ('research', 'ready'):
        raise ValidationError('Revisa identidad, evidencia y etapa antes de incorporar esta empresa.')
    if not contact.email or not contact.published_business or contact.deliverability == 'bounced':
        raise ValidationError('Falta un correo empresarial utilizable y su procedencia.')
    email = contact.email.strip().lower()
    if MailEnrollment.objects.filter(Q(account=account) | Q(email=email)).exists():
        raise ValidationError('Empresa o buzón ya incorporado; no se duplica la secuencia.')
    if BusinessContact.objects.filter(email__iexact=email).exclude(account=account).exists():
        raise ValidationError('Buzón compartido entre fichas: concilia la identidad primero.')
    if account.interactions.filter(kind__in=['sent', 'reply', 'meeting', 'bounce', 'optout']).exists():
        raise ValidationError('Ya existe contacto previo: requiere seguimiento humano, no una nueva secuencia.')
    if MailEnrollment.objects.count() >= 20:
        raise ValidationError('Piloto limitado a 20 empresas. Evalúa resultados antes de ampliar.')
    e = MailEnrollment.objects.create(account=account, contact=contact, email=email)
    subject, question = opening_for(account.segment)
    body = (f'Hola, equipo de {account.name}:\n\nSoy del equipo de Milenio, en Jardín Dorado, Tijuana. '
            'Atendemos mecánica de autos, pickups y vans a gasolina, y contamos con grúas 24/7 en Tijuana y servicio federal sujeto a evaluación.\n\n'
            + question + SIGNATURE)
    queue_message(e, 'cold', subject, body, step=1)
    audit(account, actor, 'mail_enrolled', enrollment=e.pk, email=email)
    return e


def pause_account(account_id, reason, manual=False):
    MailEnrollment.objects.filter(account_id=account_id).exclude(state='suppressed').update(state='paused', reason=reason[:240])
    MailMessage.objects.filter(enrollment__account_id=account_id, status='queued').update(status='cancelled', error=reason[:240])
    if manual:
        MailEnrollment.objects.filter(account_id=account_id).update(manual_control=True)


def business_due(sent_at, holidays):
    day = sent_at.astimezone(TZ).date()
    count = 0
    while count < 4:
        day += timedelta(days=1)
        if day.weekday() < 5 and day.isoformat() not in holidays:
            count += 1
    return datetime.combine(day, time(9), TZ)


@transaction.atomic
def accept_inbound(e, item, box):
    """Only items from a known Gmail thread are supplied by the adapter."""
    if MailInbound.objects.filter(provider_id=item['id']).exists():
        return
    if item.get('draft'):
        return
    e = MailEnrollment.objects.select_for_update().select_related('account', 'contact').get(pk=e.pk)
    own_sent = item.get('sent', False)
    if own_sent and MailMessage.objects.filter(provider_id=item['id']).exists():
        return
    sender = item['sender'].lower()
    if own_sent:
        category, response = 'manual_sent', ''
    elif item.get('spam'):
        category, response = 'spam', ''
    elif sender != e.email:
        # A third party or delivery robot in a thread is never addressed automatically.
        is_bounce = ('delivery-status' in item['headers'].get('content-type', '').lower()
                     or re.search(r'mailer-daemon|postmaster', sender))
        category, response = ('bounce' if is_bounce else 'unknown_sender'), ''
    else:
        category, response = classify(item['body'], item['headers'])
    human = not own_sent and sender == e.email and category not in ('automatic', 'spam')
    event = MailInbound.objects.create(enrollment=e, provider_id=item['id'], thread_id=item['thread_id'],
        rfc_id=item.get('rfc_id', '')[:500], sender=sender, subject=item['subject'][:240],
        body=latest_text(item['body']), category=category, human_reply=human,
        needs_review=category not in ('optout', 'negative'), received_at=item['date'])
    pause_account(e.account_id, 'Respuesta: ' + category, manual=category == 'manual_sent')
    actor = box.owner or e.account.owner
    if category == 'bounce':
        BusinessContact.objects.filter(email__iexact=e.email).update(deliverability='bounced')
        Interaction.objects.create(account=e.account, kind='bounce', summary='Rebote recibido en hilo Gmail; revisar canal.', occurred_at=event.received_at, created_by=actor)
    if category == 'optout':
        current, _ = Suppression.objects.get_or_create(account=e.account, defaults={'created_by': actor, 'reason': 'Baja recibida por Gmail', 'emails': [e.email], 'domain': ''})
        current.emails = sorted(set(current.emails + [e.email]))
        current.save()
        SalesAccount.objects.filter(pk=e.account_id).update(stage='suppressed')
        MailEnrollment.objects.filter(pk=e.pk).update(state='suppressed')
    if human:
        Interaction.objects.create(account=e.account, kind='optout' if category == 'optout' else 'reply',
            summary='Gmail: ' + category + '\n' + event.body, occurred_at=event.received_at, created_by=actor)
        if category not in ('optout', 'negative'):
            SalesAccount.objects.filter(pk=e.account_id, stage__in=['research', 'ready']).update(stage='conversation')
        elif category == 'negative':
            SalesAccount.objects.filter(pk=e.account_id, stage__in=['research', 'ready', 'conversation']).update(stage='lost')
    audit(e.account, actor, 'mail_received', message=item['id'], category=category)
    # At most two automatic replies per conversation, one per incoming message.
    # Further questions are handled by the team; no bot-to-bot loops.
    auto_count = e.messages.filter(kind='auto', status__in=['queued', 'sending', 'sent', 'unknown']).count()
    if (response and box.auto_reply and not e.manual_control and not suppressed(e.account) and auto_count < 2
            and e.messages.filter(status='sent', sent_at__lte=event.received_at).exists()
            and event.rfc_id and not e.incoming.filter(category='manual_sent').exists()):
        queue_message(e, 'auto', 'Re: ' + item['subject'].removeprefix('Re: '),
                      'Respuesta automática de Milenio:\n\n' + response + SIGNATURE,
                      inbound=event, thread_id=item['thread_id'], reply_to_id=event.rfc_id)


def mark_sent(message, result, box, now):
    if not result.get('id') or not result.get('threadId'):
        raise ValueError('Respuesta de envío incompleta')
    with transaction.atomic():
        message.status = 'sent'
        message.provider_id = result['id']
        message.thread_id = result['threadId']
        message.sent_at = now
        message.error = ''
        message.save()
        Interaction.objects.create(account=message.enrollment.account, kind='sent', summary=f'Gmail {message.kind}, paso {message.step}; id={message.provider_id}', occurred_at=now, created_by=box.owner)
        audit(message.enrollment.account, box.owner, 'mail_sent', message=str(message.pk), provider_id=message.provider_id)
        if message.kind == 'cold' and message.step == 3:
            MailEnrollment.objects.filter(pk=message.enrollment_id, state='active').update(state='completed', reason='Tres contactos realizados')


def schedule_followups(box):
    for e in MailEnrollment.objects.filter(state='active').select_related('account'):
        if suppressed(e.account) or e.account.stage not in ('research', 'ready') or e.account.interactions.filter(kind__in=['reply','meeting','bounce','optout']).exists():
            pause_account(e.account_id, 'Conversación, etapa o baja registrada')
            continue
        last = e.messages.filter(kind='cold').order_by('-step').first()
        if not last or last.status != 'sent' or last.step >= 3:
            continue
        due = business_due(last.sent_at, box.holidays)
        body = ('Retomo mi correo sobre sus vehículos. ¿Quién coordina mantenimiento o apoyo de grúa en su empresa?' if last.step == 1 else
                'Cierro este seguimiento. Si más adelante necesitan apoyo para sus unidades, pueden contactar a Milenio por este correo o WhatsApp.')
        with transaction.atomic():
            if not e.messages.filter(kind='cold', step=last.step+1).exists():
                queue_message(e, 'cold', last.subject, body + SIGNATURE, step=last.step+1,
                              due_at=due, thread_id=last.thread_id, reply_to_id=last.rfc_id)


def tick(client=None, now=None):
    """One bounded cycle. Entire mailbox has one renewable DB lease; unknown sends never retry."""
    from django.conf import settings
    from milenio_web.deployment import read_config, guard_server
    if (settings.DATA_DIR / '.mail-recovery-hold').exists():
        return 'recovery_hold'
    if settings.MILENIO_MODE == 'live':
        deployment = read_config()
        if deployment:
            guard_server(deployment)
            if not deployment.get('mail_worker_allowed'):
                return 'deployment_paused'
    now = now or timezone.now()
    box, _ = Mailbox.objects.get_or_create(pk=1)
    if not box.connected or not box.enabled or not box.owner_id:
        return 'paused'
    if box.last_tick and now - box.last_tick < timedelta(seconds=60):
        return 'idle'
    token = str(uuid.uuid4())
    with transaction.atomic():
        lease, _ = MailWorkerLease.objects.get_or_create(pk=1, defaults={'expires_at': now})
        if lease.expires_at > now:
            return 'busy'
        lease.token, lease.expires_at = token, now + timedelta(minutes=3)
        lease.save()
        Mailbox.objects.filter(pk=1).update(last_tick=now)
    def renew():
        if not MailWorkerLease.objects.filter(pk=1, token=token, expires_at__gt=timezone.now()).update(expires_at=timezone.now()+timedelta(minutes=3)):
            raise RuntimeError('Se perdió el bloqueo del worker')
    try:
        if client is None:
            from .gmail import GmailClient
            client = GmailClient()
        # A previous crashed worker may have submitted this mail: never repeat blindly.
        MailMessage.objects.filter(status='sending').update(status='unknown', error='Resultado interrumpido; reconciliación requerida')
        for m in MailMessage.objects.filter(status='unknown').select_related('enrollment__account'):
            renew()
            found = client.find_sent(m.rfc_id)
            if found:
                mark_sent(m, found, box, m.attempted_at or now)
        # Sync every monitored conversation before considering any new outbound action.
        threads = list(MailMessage.objects.exclude(thread_id='').values_list('enrollment_id', 'thread_id').distinct())
        for eid, thread in threads:
            renew()
            e = MailEnrollment.objects.get(pk=eid)
            for item in client.thread(thread):
                if item['date'] >= e.created_at:
                    accept_inbound(e, item, box)
        for e in MailEnrollment.objects.all():
            renew()
            # Before the first send, inspect recent contact in Gmail too; CRM may have no history.
            since = max(e.created_at - timedelta(days=30), (box.last_sync - timedelta(minutes=10)) if box.last_sync else e.created_at - timedelta(days=30))
            for item in client.discover(e.email, since):
                accept_inbound(e, item, box)
        Mailbox.objects.filter(pk=1).update(last_sync=now, last_error='')
        schedule_followups(box)
        # Includes autoresponses: 10 total/day; urgent queries are shown for human action.
        now = timezone.now()  # Synchronization can cross the sending window.
        local = now.astimezone(TZ)
        if local.weekday() >= 5 or local.date().isoformat() in box.holidays or not (9 <= local.hour < 16):
            return 'outside_window'
        candidates = MailMessage.objects.filter(status='queued', due_at__lte=now).select_related('enrollment__account', 'enrollment__contact').order_by('due_at', 'created_at')
        for m in candidates:
            renew()
            with transaction.atomic():
                current_box = Mailbox.objects.get(pk=1)
                if not current_box.enabled or not current_box.connected:
                    return 'paused'
                if MailMessage.objects.filter(status='unknown').exists():
                    return 'unknown_send'
                e = MailEnrollment.objects.select_related('account', 'contact').get(pk=m.enrollment_id)
                blocked = suppressed(e.account) or e.contact.deliverability == 'bounced' or not e.contact.published_business or e.contact.email.lower() != m.recipient
                blocked |= m.kind == 'cold' and (e.state != 'active' or not qualify(e.account)['exploratory'] or e.account.stage not in ('research','ready'))
                blocked |= m.kind == 'auto' and (not current_box.auto_reply or e.manual_control or e.incoming.filter(category='manual_sent').exists())
                if blocked:
                    MailMessage.objects.filter(pk=m.pk, status='queued').update(status='cancelled', error='Reglas actuales impiden el envío')
                    continue
                # A long sync can cross the window or midnight. Admit using the real time.
                attempted_at = timezone.now()
                local = attempted_at.astimezone(TZ)
                if local.weekday() >= 5 or local.date().isoformat() in current_box.holidays or not (9 <= local.hour < 16):
                    return 'outside_window'
                day_start = datetime.combine(local.date(), time.min, TZ)
                attempts = MailMessage.objects.filter(attempted_at__gte=day_start)
                if attempts.count() >= 10:
                    return 'daily_limit'
                if m.kind == 'cold' and m.step == 1 and attempts.filter(kind='cold', step=1).count() >= 5:
                    continue
                if MailMessage.objects.filter(attempted_at__gt=attempted_at-timedelta(seconds=60)).exists():
                    return 'idle'
                if not MailMessage.objects.filter(pk=m.pk, status='queued').update(status='sending', attempted_at=attempted_at):
                    continue
                m.attempted_at = attempted_at
            try:
                result = client.send(m, box.email)
                mark_sent(m, result, box, attempted_at)
            except Exception:
                MailMessage.objects.filter(pk=m.pk).update(status='unknown', error='Gmail no confirmó el resultado. No se reintenta automáticamente.')
                return 'unknown_send'
            return 'sent'  # One send per minute, even across restarts.
        return 'idle'
    except Exception as exc:
        # Never store provider response bodies, token strings or incoming HTML in logs.
        Mailbox.objects.filter(pk=1).update(last_error='No se completó la sincronización: ' + type(exc).__name__)
        return 'error'
    finally:
        MailWorkerLease.objects.filter(pk=1, token=token).update(expires_at=timezone.now(), token='')
