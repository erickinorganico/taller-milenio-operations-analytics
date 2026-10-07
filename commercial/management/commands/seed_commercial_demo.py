from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from commercial.models import SalesAccount
from commercial import services as s


class Command(BaseCommand):
    help = "Create clearly fictional commercial examples, demo/test mode only. Never creates users."

    @transaction.atomic
    def handle(self, **options):
        if settings.MILENIO_MODE not in {"demo", "test"}: raise CommandError("Los ejemplos solo se cargan en demo/test.")
        actor = get_user_model().objects.filter(is_superuser=True, is_active=True).first()
        if not actor: raise CommandError("Primero crea el acceso de gerencia en /setup/.")
        examples = [("Cuadrillas Ejemplo", "unknown", None, "Servicios técnicos"), ("Reparto Ejemplo", "gasoline", 7, "Distribuidor"), ("Mensajería Ejemplo", "diesel", 0, "Mensajería"), ("Operación Eléctrica Ejemplo", "electric", 0, "Reparto"), ("Flotilla Mixta Ejemplo", "mixed", 3, "Mantenimiento")]
        count = 0
        for i, (name, fuel, units, segment) in enumerate(examples, 1):
            domain = f"demo-{i}.example.test"
            if SalesAccount.objects.filter(domain=domain).exists(): continue
            a = s.create_account({"name": "[FICTICIA] " + name, "website": "https://"+domain, "city": "Tijuana", "segment": segment, "source": "manual", "identity_confirmed": True, "next_action": "Revisar ejemplo y ensayar conversación", "next_action_on": timezone.localdate(), "is_demo": True}, actor)
            for topic in ["identity", "vehicles", "need"]:
                a.refresh_from_db()
                e = s.add_record(a.pk, a.version, "evidence", {"topic": topic, "source_note": "Escenario ficticio para capacitación", "excerpt": f"Datos sintéticos: {topic}; combustible {fuel}; unidades compatibles {units}.", "reviewed": True}, actor)
                if topic == "vehicles": vehicle_evidence = e
                if topic == "need": need_evidence = e
            a.refresh_from_db()
            s.add_record(a.pk, a.version, "contact", {"name": "Área ficticia de operaciones", "email": "contacto@"+domain, "source_note": "Contacto ficticio, no enviar", "published_business": True}, actor)
            a.refresh_from_db()
            s.update_fleet(a.pk, a.version, {"fuel": fuel, "vehicle_type": "light", "total_units": 10, "compatible_units": units, "vehicle_evidence": vehicle_evidence, "need_confirmed": fuel != "unknown", "need_evidence": need_evidence}, actor)
            count += 1
        self.stdout.write(f"Empresas ficticias creadas: {count}. Ningún contacto fue enviado.")
