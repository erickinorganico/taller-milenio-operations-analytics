"""Human controls on the central host; agent tokens cannot grant permission or approve lots."""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from commercial import mail_safety as safety
from commercial.models import BusinessContact, Mailbox, MailMessage


class Command(BaseCommand):
    help = 'Revisión humana: status, preview, permission, hold, release, approve, reconcile. Nunca envía.'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['status', 'preview', 'permission', 'hold', 'release', 'approve', 'reconcile'])
        parser.add_argument('--actor')
        parser.add_argument('--messages', nargs='+')
        parser.add_argument('--file')
        parser.add_argument('--sha256')
        parser.add_argument('--reference')
        parser.add_argument('--incident-reference')
        parser.add_argument('--reconciliation-reference')
        parser.add_argument('--contact', type=int)
        parser.add_argument('--scopes', nargs='+', choices=['presentation', 'followup'])
        parser.add_argument('--granted-at')
        parser.add_argument('--valid-until')
        parser.add_argument('--expires-minutes', type=int, default=60)

    def private_file(self, name):
        base = (settings.DATA_DIR / 'mail-evidence').resolve()
        path = (base / str(name or '')).resolve()
        if path == base or not path.is_relative_to(base):
            raise CommandError('Usa un archivo relativo dentro de DATA_DIR/mail-evidence.')
        return path

    def handle(self, *args, **o):
        try:
            action = o['action']
            if action == 'status':
                self.stdout.write(json.dumps(safety.status(), ensure_ascii=False))
                return
            # Every live operation requires the assigned central host, not a clone/client.
            if settings.MILENIO_MODE == 'live':
                from milenio_web.deployment import guard_server
                guard_server()
            if action == 'preview':
                result = safety.preview(o['messages'] or [])
                path = self.private_file(o['file'])
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('x', encoding='utf-8') as handle:
                    json.dump(result, handle, ensure_ascii=False, indent=2)
                self.stdout.write('Preparado, sin aprobación ni envío. SHA256: '+hashlib.sha256(path.read_bytes()).hexdigest())
                return
            actor = get_user_model().objects.get(username=o['actor'])
            safety.manager(actor)
            if action == 'hold':
                if not o['reference']: raise CommandError('Motivo obligatorio.')
                safety.hold(o['reference'], actor)
            elif action == 'permission':
                safety.record_permission(BusinessContact.objects.get(pk=o['contact']), actor,
                    scopes=o['scopes'], granted_at=datetime.fromisoformat(o['granted_at']),
                    valid_until=datetime.fromisoformat(o['valid_until']),
                    evidence_file=o['file'], evidence_sha256=o['sha256'])
            elif action == 'approve':
                if safety.evidence_hash(o['file']) != o['sha256']:
                    raise CommandError('El archivo no coincide con el SHA256 revisado.')
                manifest = json.loads(self.private_file(o['file']).read_text(encoding='utf-8'))
                result = safety.approve_batch(manifest, actor, o['reference'] or '',
                                               timezone.now()+timedelta(minutes=o['expires_minutes']))
                self.stdout.write('Lote aprobado: '+str(result.pk)+'. La cola aún depende de los demás controles.')
                return
            elif action == 'release':
                # Verify evidence and unresolved attempts BEFORE reading credentials/OAuth.
                if safety.evidence_hash(o['file']) != o['sha256'] or not all([o['reference'], o['incident_reference'], o['reconciliation_reference']]):
                    raise CommandError('Revisión y referencias incompletas.')
                if MailMessage.objects.filter(status__in=['unknown', 'sending']).exists():
                    raise CommandError('Primero concilia todos los resultados desconocidos.')
                box = Mailbox.objects.get(pk=1)
                if not box.connected or (settings.DATA_DIR/'.mail-recovery-hold').exists():
                    raise CommandError('Conecta el buzón y completa la conciliación de recuperación antes de revisar reapertura.')
                from commercial.gmail import GmailClient
                safety.release_hold(actor, sender=box.email, verified_profile=GmailClient().profile(),
                    incident_reference=o['incident_reference'], reconciliation_reference=o['reconciliation_reference'],
                    approval_reference=o['reference'], evidence_file=o['file'], evidence_sha256=o['sha256'])
            elif action == 'reconcile':
                # Read-only Google operation. Failure/not-found stays unknown; never retry.
                if not o['reference']: raise CommandError('Referencia de revisión obligatoria.')
                safety.hold('Conciliación manual; mantener pausa hasta revisión posterior', actor)
                from commercial.gmail import GmailClient
                from commercial.mail_flow import mark_sent
                box = Mailbox.objects.get(pk=1)
                client = GmailClient()
                if client.profile().get('emailAddress', '').lower() != box.email.lower():
                    raise CommandError('Identidad del buzón no coincide.')
                MailMessage.objects.filter(status='sending').update(status='unknown')
                for message in MailMessage.objects.filter(status='unknown'):
                    found = client.find_sent(message.rfc_id)
                    if found:
                        mark_sent(message, found, box, message.attempted_at or timezone.now())
                from commercial.services import audit
                from datetime import datetime, time
                start = datetime.combine(timezone.now().astimezone(safety.TZ).date(), time.min, safety.TZ)
                external = set(client.outbound_ids(start)) - set(MailMessage.objects.exclude(provider_id='').values_list('provider_id', flat=True))
                if external or MailMessage.objects.filter(status='unknown').exists():
                    raise CommandError('Conciliación incompleta: enviados externos o resultados desconocidos. No reintentar.')
                # Clear only the restore latch. Incident policy and mailbox remain paused.
                (settings.DATA_DIR/'.mail-recovery-hold').unlink(missing_ok=True)
                audit(None, actor, 'mail_reconciled_read_only', reference=o['reference'][:500],
                      remaining=MailMessage.objects.filter(status='unknown').count())
                self.stdout.write('Conciliado sin envíos. No encontrar un mensaje no demuestra que no se haya enviado.')
                return
            self.stdout.write('Control registrado. Ningún correo enviado; ningún lote histórico reactivado.')
        except (ValidationError, ValueError, TypeError, KeyError, OSError,
                get_user_model().DoesNotExist, BusinessContact.DoesNotExist, Mailbox.DoesNotExist) as exc:
            raise CommandError('; '.join(exc.messages) if isinstance(exc, ValidationError) else 'Entrada inválida o archivo no disponible: '+type(exc).__name__)
