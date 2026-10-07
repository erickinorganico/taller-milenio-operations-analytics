"""Explainable eligibility, never a prediction of willingness to buy."""
from urllib.parse import urlsplit
from django.core.exceptions import ValidationError
from .models import Suppression

PLATFORMS = {"facebook.com", "instagram.com", "linkedin.com", "google.com", "google.com.mx", "maps.app.goo.gl", "goo.gl", "youtube.com", "tiktok.com", "x.com"}


def domain_for(value):
    value = (value or "").strip().lower()
    if not value:
        return None
    parsed = urlsplit(value if "://" in value else "https://" + value)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise ValidationError("Usa un sitio HTTP(S) empresarial sin credenciales.")
    host = (parsed.hostname or "").removeprefix("www.").rstrip(".")
    if not host or "." not in host:
        raise ValidationError("Dominio empresarial no válido.")
    if any(host == p or host.endswith("." + p) for p in PLATFORMS):
        raise ValidationError("Las redes se guardan como fuente, no como dominio único de una empresa.")
    return host.encode("idna").decode("ascii")


def suppressed(account):
    if account.stage == "suppressed" or Suppression.objects.filter(account=account).exists():
        return True
    if account.domain and Suppression.objects.filter(domain=account.domain).exists():
        return True
    emails = {x.lower() for x in account.contacts.exclude(email="").values_list("email", flat=True)}
    return any(emails.intersection(s.emails) for s in Suppression.objects.exclude(emails=[])) if emails else False


def reviewed(evidence, account, topic):
    return bool(evidence and evidence.account_id == account.pk and evidence.reviewed and evidence.topic == topic)


def qualify(account):
    reasons = []
    if suppressed(account):
        return {"mechanics": False, "towing": False, "exploratory": False, "label": "No contactar", "reasons": ["Baja de empresa, dominio o correo."], "engine": "rules-v1"}
    fleet = account.fleet
    identity = account.identity_confirmed and account.evidence.filter(topic="identity", reviewed=True).exists()
    locality = account.city.strip().casefold() == "tijuana"
    contact = account.contacts.filter(published_business=True).exclude(deliverability="bounced").exclude(email="", phone="").exists()
    vehicle = reviewed(fleet.vehicle_evidence, account, "vehicles")
    need = fleet.need_confirmed and reviewed(fleet.need_evidence, account, "need")
    fuel = fleet.fuel in {"gasoline", "mixed"} and (fleet.compatible_units or 0) > 0
    mechanics = identity and locality and vehicle and need and fuel and fleet.vehicle_type == "light"
    towing = identity and need and fleet.towing_confirmed and reviewed(fleet.towing_evidence, account, "coverage")
    if not identity: reasons.append("Revisar identidad empresarial y su evidencia.")
    if not locality: reasons.append("La mecánica del piloto se limita a Tijuana.")
    if not contact: reasons.append("Falta un canal empresarial utilizable con procedencia.")
    if not vehicle: reasons.append("Falta evidencia revisada de unidades y combustible.")
    if not fuel or fleet.vehicle_type != "light": reasons.append("Mecánica: confirmar unidades ligeras a gasolina; excluir diésel, camiones, eléctricos e híbridos.")
    if not need: reasons.append("Falta una necesidad confirmada y documentada.")
    if not towing: reasons.append("Grúa: despacho debe confirmar capacidad y cobertura por separado.")
    return {"mechanics": bool(mechanics), "towing": bool(towing), "exploratory": bool(identity and contact), "label": "Compatible confirmado" if mechanics or towing else "Por investigar", "reasons": reasons, "engine": "rules-v1"}
