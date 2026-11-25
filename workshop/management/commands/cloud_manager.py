"""Create the initial cloud manager privately from the server terminal."""
import getpass
import sys

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from workshop.access import ROLES
from workshop.webforms import SetupForm


class Command(BaseCommand):
    help = "Crear la primera cuenta de Gerencia en la consola privada del servidor."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        if not getattr(settings, "MILENIO_CLOUD", False) or not sys.stdin.isatty():
            raise CommandError("Usa una terminal privada interactiva de la instalación en la nube.")
        if User.objects.filter(is_superuser=True).exists():
            raise CommandError("Ya existe una cuenta inicial. Usa Equipo y acceso o changepassword.")
        form = SetupForm({"username": options["username"], "first_name": input("Nombre de Gerencia: "),
                          "password1": getpass.getpass("Contraseña: "),
                          "password2": getpass.getpass("Repite la contraseña: ")})
        if not form.is_valid():
            raise CommandError(" ".join(str(error) for errors in form.errors.values() for error in errors))
        with transaction.atomic():
            if User.objects.filter(is_superuser=True).exists():
                raise CommandError("Otra sesión completó el alta de Gerencia.")
            user = form.save(commit=False)
            user.is_staff = user.is_superuser = True
            user.save()
            for name in ROLES:
                group, _ = Group.objects.get_or_create(name=name)
                if name == "manager":
                    user.groups.add(group)
        self.stdout.write("Gerencia puede iniciar sesión. Agrega al equipo desde Equipo y acceso.")
