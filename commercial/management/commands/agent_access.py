"""Issue/revoke an agent credential locally. Never print the secret."""
import hashlib
import json
import os
import secrets
from datetime import timedelta
from pathlib import Path
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from commercial.agent_models import AgentCredential
from workshop.access import can
from workshop.agent_api import ORDER_PREFIX, SUMMARY_SCOPE
from workshop.models import WorkOrder


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--owner')
        parser.add_argument('--label')
        parser.add_argument('--output')
        parser.add_argument('--allow-send',action='store_true')
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--read-only',action='store_true')
        mode.add_argument('--workshop-summary', action='store_true', help='Sólo conteos del taller.')
        mode.add_argument('--workshop-order', metavar='FOLIO', help='Sólo estado y notas de una orden abierta.')
        parser.add_argument('--revoke')

    def handle(self,*args,**options):
        if options['revoke']:
            count=AgentCredential.objects.filter(pk=options['revoke']).update(revoked=True)
            self.stdout.write(f'Revocadas: {count}')
            return
        if not all(options[k] for k in ('owner','label','output')): raise CommandError('Faltan owner, label u output.')
        if len(options['label']) > 100 or not options['label'].strip():
            raise CommandError('Usa una etiqueta de una a 100 letras para identificar al agente.')
        user=get_user_model().objects.get(username=options['owner'],is_active=True)
        if not can(user,'manage'): raise CommandError('Se requiere Gerencia.')
        output=Path(options['output']).resolve()
        if output.exists(): raise CommandError('El destino ya existe; no se reemplaza una credencial.')
        if 'private' not in output.parts: raise CommandError('Guarda el token en una carpeta private protegida.')
        scopes=['read'] if options['read_only'] else ['read','prepare']
        if options['allow_send'] and not options['read_only']: scopes.append('send')
        days = 90
        metadata = {}
        if options['workshop_summary'] or options['workshop_order'] is not None:
            if options['allow_send'] or not getattr(settings, 'MILENIO_CLOUD', False):
                raise CommandError('El permiso del taller requiere el perfil de nube y es exclusivo de la operación elegida.')
            metadata['workshop_url'] = 'https://' + settings.CLOUD_HOST
            scopes = [SUMMARY_SCOPE]
            days = 30
            if options['workshop_order'] is not None:
                order = WorkOrder.objects.filter(number=options['workshop_order']).first()
                if not order or order.status in (WorkOrder.Status.DELIVERED, WorkOrder.Status.CANCELLED):
                    raise CommandError('Se requiere el folio exacto de una orden abierta.')
                scopes = [f'{ORDER_PREFIX}{order.pk}']
                days = 7
        elif getattr(settings, 'MILENIO_CLOUD', False):
            raise CommandError('Elige --workshop-summary o --workshop-order FOLIO en la nube.')
        token=secrets.token_urlsafe(48)
        credential=AgentCredential.objects.create(owner=user,label=options['label'].strip(),token_hash=hashlib.sha256(token.encode()).hexdigest(),scopes=scopes,expires_at=timezone.now()+timedelta(days=days))
        try:
            output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as handle:
                json.dump({'credential_id':str(credential.pk),'token':token,'scopes':scopes,**metadata},handle)
        except Exception:
            credential.revoked=True; credential.save(update_fields=['revoked'])
            raise
        self.stdout.write(f'Credencial {credential.pk} creada. Vence en {days} días. Secreto guardado sin mostrar.')
