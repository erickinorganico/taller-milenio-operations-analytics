"""Connection guidance and Gerencia controls; no passwords or OAuth tokens."""
from django import forms
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .access import can, require
from .ai_capture import admission_problem, configure_photo_ai, photo_ai_settings, usage_for_day
from .ai_capture_models import PHOTO_MODELS
from .models import PhotoAIReading


class PhotoAISettingsForm(forms.Form):
    version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    enabled = forms.BooleanField(label="Permitir lectura de fotos con ChatGPT", required=False,
        help_text="Envía la foto al modelo mediante la sesión de Codex del equipo lector. Desmarcar pausa nuevas lecturas solo en Milenio.")
    model = forms.ChoiceField(label="Modelo de nuevas fotos", choices=PHOTO_MODELS)
    daily_attempt_limit = forms.IntegerField(label="Máximo de intentos al día", min_value=1, max_value=200)
    per_document_limit = forms.IntegerField(label="Máximo de intentos por foto", min_value=1, max_value=5)
    daily_token_budget = forms.IntegerField(label="Presupuesto diario de tokens observados", min_value=1, max_value=1000000,
        help_text="Bloquea la próxima lectura cuando se alcanza. No puede limitar los tokens de una lectura ya iniciada ni el consumo de otras apps.")


def panel_context(request, form=None):
    policy = photo_ai_settings()
    usage = usage_for_day()
    usage["remaining_attempts"] = max(0, policy.daily_attempt_limit-usage["attempts"])
    page = Paginator(PhotoAIReading.objects.select_related("capture", "capture__uploaded_by"), 25).get_page(request.GET.get("page"))
    connection = cache.get("capture:codex-availability") or {"available": False, "auth_method": "unknown",
        "message": "Sesión sin comprobar. Gerencia puede verificarla sin enviar una imagen ni ejecutar un modelo."}
    if form is None:
        form = PhotoAISettingsForm(initial={key: getattr(policy, key) for key in PhotoAISettingsForm.base_fields})
    return {"title": "Conexión y uso de IA", "section": "IA para documentos", "policy": policy,
        "usage": usage, "problem": admission_problem(policy, usage), "page": page, "connection": connection,
        "form": form, "can_configure": can(request.user, "manage"), "today": timezone.localdate(),
        "model_label": dict(PHOTO_MODELS).get(policy.model, policy.model)}


@require("reception")
@require_GET
def photo_ai_panel(request):
    return render(request, "workshop/photo_ai.html", panel_context(request))


@require("manage")
@require_POST
def configure(request):
    form = PhotoAISettingsForm(request.POST)
    if form.is_valid():
        values = {key: value for key, value in form.cleaned_data.items() if key != "version"}
        try:
            configure_photo_ai(actor=request.user, version=form.cleaned_data["version"], values=values)
        except ValidationError as error:
            form.add_error(None, " · ".join(error.messages))
            return render(request, "workshop/photo_ai.html", panel_context(request, form), status=409)
        messages.success(request, "Configuración de IA guardada. No se inició ninguna lectura ni se cambió la sesión de Codex.")
        return redirect("/capture/ai/")
    return render(request, "workshop/photo_ai.html", panel_context(request, form), status=400)


@require("manage")
@require_POST
def check_connection(request):
    from .capture_vision import provider_status
    connection = provider_status("codex")
    connection["checked_at"] = timezone.localtime().isoformat(timespec="seconds")
    cache.set("capture:codex-availability", connection, 30)
    messages.info(request, connection["message"])
    return redirect("/capture/ai/")
