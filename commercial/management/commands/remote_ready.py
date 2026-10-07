from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError


class Command(BaseCommand):
    def handle(self,*args,**options):
        if not get_user_model().objects.filter(is_superuser=True,is_active=True).exists():
            raise CommandError('Gerencia no está configurada.')
        self.stdout.write('Gerencia configurada; acceso remoto puede prepararse.')
