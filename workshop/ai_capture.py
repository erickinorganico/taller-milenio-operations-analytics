"""Durable image-reading admission. Never authenticates or stores credentials."""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import AuditEvent, PhotoAIReading, PhotoAISettings
from .access import can


def photo_ai_settings():
    return PhotoAISettings.objects.filter(pk=1).first() or PhotoAISettings(pk=1)


def usage_for_day(day=None):
    readings = PhotoAIReading.objects.filter(day=day or timezone.localdate())
    values = readings.aggregate(attempts=Count("pk"), reported_input=Sum("input_tokens"), reported_output=Sum("output_tokens"),
        unknown=Count("pk", filter=Q(input_tokens__isnull=True) | Q(output_tokens__isnull=True)))
    values["input_tokens"] = values.pop("reported_input")
    values["output_tokens"] = values.pop("reported_output")
    values["known_tokens"] = (values["input_tokens"] or 0) + (values["output_tokens"] or 0)
    return values


def admission_problem(policy, usage, capture=None):
    if not policy.enabled:
        return "La lectura con ChatGPT está pausada en Milenio. Usa el lector local o continúa manualmente."
    if usage["unknown"]:
        return "Hay una lectura de hoy con consumo pendiente o desconocido. Se bloquean nuevas lecturas con IA; no se asume consumo cero."
    if usage["attempts"] >= policy.daily_attempt_limit:
        return "Se alcanzó el límite diario de intentos de lectura con IA. Puedes continuar con el lector local o manualmente."
    if usage["known_tokens"] >= policy.daily_token_budget:
        return "Se alcanzó el presupuesto de tokens observado de hoy. No se iniciarán más lecturas con IA."
    if capture and PhotoAIReading.objects.filter(capture=capture).count() >= policy.per_document_limit:
        return "Esta foto alcanzó su límite de intentos con IA. Compara y completa los campos manualmente."
    return ""


@transaction.atomic
def reserve_reading(capture, lease):
    """Called inside the worker's claim transaction, serializing the singleton."""
    policy, _ = PhotoAISettings.objects.select_for_update().get_or_create(pk=1)
    if capture.model_name not in {"gpt-6-luna", "gpt-6.1-sol", "gpt-5.6-luna"}:
        raise ValidationError("El modelo solicitado no está permitido para leer imágenes.")
    problem = admission_problem(policy, usage_for_day(), capture)
    if problem:
        raise ValidationError(problem)
    if PhotoAIReading.objects.filter(state="started").exists():
        raise ValidationError("Ya hay una lectura con IA en curso. Revisa su resultado antes de iniciar otra.")
    return PhotoAIReading.objects.create(capture=capture, lease=lease, model=capture.model_name, day=timezone.localdate())


def finish_reading(reading, receipt=None, error_code=""):
    if reading is None:
        return
    usage = (receipt or {}).get("usage", {})
    usage = usage if isinstance(usage, dict) else {}
    observed = {key: value if type(value := usage.get(key)) is int and 0 <= value <= 1000000000 else None
                for key in ("input_tokens", "output_tokens")}
    PhotoAIReading.objects.filter(pk=reading.pk).update(
        state="failed" if error_code else "completed", finished_at=timezone.now(),
        input_tokens=observed["input_tokens"], output_tokens=observed["output_tokens"],
        outcome_code=(error_code or "completed")[:60])


def recover_readings():
    PhotoAIReading.objects.filter(state="started", started_at__lt=timezone.now()-timedelta(minutes=3)).update(
        state="failed", finished_at=timezone.now(), outcome_code="interrupted")


def configure_photo_ai(*, actor, version, values):
    if not can(actor, "manage"):
        raise PermissionDenied("Solo Gerencia configura el uso de IA.")
    expected = {"enabled", "model", "daily_attempt_limit", "per_document_limit", "daily_token_budget"}
    if set(values) != expected or type(values["enabled"]) is not bool or values["model"] not in {"gpt-6-luna", "gpt-6.1-sol"}:
        raise ValidationError("Configuración de IA inválida.")
    for key, maximum in (("daily_attempt_limit", 200), ("per_document_limit", 5), ("daily_token_budget", 1000000)):
        if type(values[key]) is not int or not 1 <= values[key] <= maximum:
            raise ValidationError("Los límites de lectura deben estar dentro de los valores permitidos.")
    with transaction.atomic():
        policy, _ = PhotoAISettings.objects.select_for_update().get_or_create(pk=1)
        if policy.version != version:
            raise ValidationError("La configuración cambió. Actualiza la página antes de guardar.")
        before = {key: getattr(policy, key) for key in values}
        for key, value in values.items():
            setattr(policy, key, value)
        policy.version += 1
        policy.updated_by, policy.updated_at = actor, timezone.now()
        policy.save()
        AuditEvent.objects.create(actor=actor, entity_type="PhotoAISettings", entity_id="1", action="configure",
            before=before, after={**values, "version": policy.version})
        return policy
