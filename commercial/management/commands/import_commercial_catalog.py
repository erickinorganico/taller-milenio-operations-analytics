from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from commercial.catalog_import import import_catalog


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--input',required=True)
        parser.add_argument('--owner',required=True)

    def handle(self,*args,**options):
        owner=get_user_model().objects.filter(username=options['owner'],is_active=True,is_superuser=True).first()
        if not owner: raise CommandError('Se requiere usuario activo de Gerencia.')
        result=import_catalog(Path(options['input']),owner)
        self.stdout.write(str(result))
