"""Issue/revoke an agent credential locally. Never print the secret."""
import hashlib
import json
import secrets
from datetime import timedelta
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from commercial.agent_models import AgentCredential
from workshop.access import can


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--owner')
        parser.add_argument('--label')
        parser.add_argument('--output')
        parser.add_argument('--allow-send',action='store_true')
        parser.add_argument('--read-only',action='store_true')
        parser.add_argument('--revoke')

    def handle(self,*args,**options):
        if options['revoke']:
            count=AgentCredential.objects.filter(pk=options['revoke']).update(revoked=True)
            self.stdout.write(f'Revocadas: {count}')
            return
        if not all(options[k] for k in ('owner','label','output')): raise CommandError('Faltan owner, label u output.')
        user=get_user_model().objects.get(username=options['owner'],is_active=True)
        if not can(user,'manage'): raise CommandError('Se requiere Gerencia.')
        output=Path(options['output']).resolve()
        if output.exists(): raise CommandError('El destino ya existe; no se reemplaza una credencial.')
        if 'private' not in output.parts: raise CommandError('Guarda el token en una carpeta private protegida.')
        scopes=['read'] if options['read_only'] else ['read','prepare']
        if options['allow_send'] and not options['read_only']: scopes.append('send')
        token=secrets.token_urlsafe(48)
        credential=AgentCredential.objects.create(owner=user,label=options['label'],token_hash=hashlib.sha256(token.encode()).hexdigest(),scopes=scopes,expires_at=timezone.now()+timedelta(days=90))
        try:
            output.parent.mkdir(parents=True,exist_ok=True)
            with output.open('x',encoding='utf-8') as handle:
                json.dump({'credential_id':str(credential.pk),'token':token,'scopes':scopes},handle)
            output.chmod(0o600)
        except Exception:
            credential.revoked=True; credential.save(update_fields=['revoked'])
            raise
        self.stdout.write(f'Credencial {credential.pk} creada. Vence en 90 días. Secreto guardado sin mostrar.')
