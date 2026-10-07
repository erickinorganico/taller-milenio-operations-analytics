from django.core.management.base import BaseCommand
from commercial.models import Mailbox, MailMessage, MailEnrollment, MailInbound


class Command(BaseCommand):
    help = 'Estado de correo sin leer credenciales ni contactar Google.'

    def handle(self, *args, **options):
        box = Mailbox.objects.filter(pk=1).first()
        self.stdout.write(str({
            'gmail_connected': bool(box and box.connected), 'sending_enabled': bool(box and box.enabled),
            'companies': MailEnrollment.objects.count(), 'queued': MailMessage.objects.filter(status='queued').count(),
            'accepted_by_gmail': MailMessage.objects.filter(status='sent').count(),
            'unknown_send': MailMessage.objects.filter(status='unknown').count(),
            'pending_review': MailInbound.objects.filter(needs_review=True).count(),
            'last_sync': str(box.last_sync) if box else None,
        }))
