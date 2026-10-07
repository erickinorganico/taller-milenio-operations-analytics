"""Explicit local mail gate after deployment/controlled QA, separate from campaigns."""
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from milenio_web.deployment import config_path,guard_server,write_json
from commercial.models import Mailbox
from commercial.services import audit


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--enable',action='store_true')
        parser.add_argument('--authorization',required=True)
        parser.add_argument('--reconciliation-reference')

    def handle(self,*args,**options):
        config=guard_server()
        box=Mailbox.objects.filter(pk=1).first()
        if not options['authorization'].strip(): raise CommandError('Referencia de autorización obligatoria.')
        if not box or not box.owner_id: raise CommandError('Conecta Gmail con un responsable antes de habilitar transporte.')
        hold=settings.DATA_DIR/'.mail-recovery-hold'
        if options['enable']:
            if not box.connected: raise CommandError('Gmail desconectado.')
            if hold.exists() and not options['reconciliation_reference']:
                raise CommandError('Recuperación: concilia Gmail desde el respaldo y registra la referencia antes de desbloquear.')
            from commercial.gmail import GmailClient
            GmailClient().request('profile')  # Verify DPAPI + OAuth under this identity; sends nothing.
            hold.unlink(missing_ok=True)
        else:
            Mailbox.objects.filter(pk=1).update(enabled=False)
        config['mail_worker_allowed']=options['enable']
        write_json(config_path(),config)
        audit(None,box.owner,'deployment_mail_gate',enabled=options['enable'],authorization=options['authorization'][:500],reconciliation=options['reconciliation_reference'])
        self.stdout.write('Permiso de transporte actualizado. La campaña se activa por separado en el panel.')
