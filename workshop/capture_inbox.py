"""Read-only exception inbox over the existing durable capture queue."""
from datetime import timedelta
from urllib.parse import urlencode

from django import forms
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Case, CharField, Count, DateTimeField, F, OuterRef, Q, Subquery, Value, When
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce, Trim
from django.utils import timezone

from .list_filters import DateRangeForm, filter_dates
from .models import AuditEvent, DocumentCapture


ISSUES = [("", "Todas"), ("exceptions", "Solo excepciones"),
          ("failed", "Lectura sin resultado"), ("stalled", "Espera prolongada"),
          ("missing", "Datos requeridos faltantes")]
STATUS_CHOICES = [(value, "Listo para aplicar" if value == "confirmed" else label)
                  for value, label in DocumentCapture.Status.choices]


class CaptureFilterForm(DateRangeForm):
    q = forms.CharField(label="Buscar documento", required=False, max_length=200,
                        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Título, folio, cliente o placa"}))
    status = forms.ChoiceField(label="Estado", required=False, choices=[("", "Todos")] + STATUS_CHOICES)
    kind = forms.ChoiceField(label="Documento", required=False,
                             choices=[("", "Todos"), ("order", "Orden de trabajo"), ("service", "Hoja de servicio")])
    uploader = forms.ModelChoiceField(label="Subida por", required=False, empty_label="Cualquier persona",
                                      queryset=User.objects.none())
    issue = forms.ChoiceField(label="Atención", required=False, choices=ISSUES)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("auto_id", "filter_%s")
        super().__init__(*args, **kwargs)
        self.fields["uploader"].queryset = User.objects.filter(uploaded_documents__isnull=False).distinct().order_by("first_name", "username")
        self.fields["uploader"].label_from_instance = lambda user: user.get_full_name() or user.username
        self.fields["start"].label = "Capturada desde"
        self.fields["end"].label = "Capturada hasta"
        self.order_fields(["q", "status", "kind", "uploader", "start", "end", "issue"])


def with_issues(queryset, now):
    # The same three-minute limit as the reader's interruption recovery. A long
    # wait signals attention, not proof that a process/provider has failed.
    cutoff = now - timedelta(minutes=3)
    fields = {f"inbox_{key}": Case(When(**{f"data__{key}": None}, then=Value("")),
        default=Trim(Coalesce(KeyTextTransform(key, "data"), Value(""), output_field=CharField())), output_field=CharField())
              for key in ("order_number", "complaint", "services")}
    retry = AuditEvent.objects.filter(entity_type="DocumentCapture", action="retry",
        entity_id=Cast(OuterRef("pk"), CharField())).order_by("-created_at", "-pk").values("created_at")[:1]
    fields["inbox_queued_at"] = Coalesce(Subquery(retry), F("created_at"), output_field=DateTimeField())
    return queryset.annotate(**fields).annotate(inbox_issue=Case(
        When(Q(status="review") & ~Q(reading_note__startswith="Captura manual:") & (
            Q(extraction__has_key="error_type") | Q(extraction__completion_observed=False) |
            Q(reading_note__startswith="La lectura se interrumpió.")), then=Value("failed")),
        When(Q(status="reading") & (Q(reading_started_at__lte=cutoff) | Q(reading_started_at__isnull=True)), then=Value("stalled")),
        When(status="pending", inbox_queued_at__lte=cutoff, then=Value("stalled")),
        When(Q(status="review") & (Q(inbox_order_number="") |
            (Q(inbox_complaint="", inbox_services="") & Q(service_items=[]))), then=Value("missing")),
        default=Value(""), output_field=CharField(),
    ))


def row_context(capture):
    issue = capture.inbox_issue
    if issue == "failed":
        label, detail, action = "Lectura sin resultado", "Reintenta desde el documento o completa los campos manualmente.", "Resolver lectura"
    elif issue == "stalled":
        label, detail, action = "Espera prolongada", "Más de 3 minutos en cola/lectura, o inicio de lectura sin registro. Revisa el lector o continúa manualmente.", "Revisar espera"
    elif issue == "missing":
        missing = []
        if not capture.inbox_order_number:
            missing.append("folio")
        if not capture.inbox_complaint and not capture.inbox_services and not capture.service_items:
            missing.append("solicitud o servicios")
        label, detail, action = "Datos requeridos faltantes", "Completa " + " y ".join(missing) + " comparando con la foto.", "Completar datos"
    else:
        label = ""
        detail, action = {
            "pending": ("Espera la lectura o continúa manualmente.", "Abrir documento"),
            "reading": ("La lectura está en curso.", "Ver lectura"),
            "review": ("Compara las propuestas con la foto y confirma los datos.", "Revisar datos"),
            "confirmed": ("Revisa las coincidencias y los cambios antes de guardarlos en el taller.", "Revisar aplicación"),
            "applied": ("Datos aplicados. La foto conserva su vínculo y su historial.", "Ver documento"),
        }[capture.status]
    return {"capture": capture, "issue": issue, "issue_label": label, "detail": detail, "action": action,
            "status_label": dict(STATUS_CHOICES)[capture.status]}


def inbox_context(params):
    form = CaptureFilterForm(params)
    valid = form.is_valid()
    values = form.cleaned_data
    queryset = with_issues(DocumentCapture.objects.all(), timezone.now())
    if not valid:
        queryset = queryset.none()
    else:
        if values.get("q"):
            query = values["q"]
            queryset = queryset.filter(Q(title__icontains=query) | Q(data__order_number__icontains=query) |
                Q(data__customer_name__icontains=query) | Q(data__vehicle_plate__icontains=query) |
                Q(work_order__number__icontains=query))
        for field in ("status", "kind"):
            if values.get(field):
                queryset = queryset.filter(**{field: values[field]})
        if values.get("uploader"):
            queryset = queryset.filter(uploaded_by=values["uploader"])
        queryset = filter_dates(queryset, values)
    counts = queryset.aggregate(total=Count("pk"), exceptions=Count("pk", filter=~Q(inbox_issue="")),
        review=Count("pk", filter=Q(status="review")), ready=Count("pk", filter=Q(status="confirmed")))
    issue = values.get("issue", "")
    if issue == "exceptions":
        queryset = queryset.exclude(inbox_issue="")
    elif issue:
        queryset = queryset.filter(inbox_issue=issue)
    page = Paginator(queryset.select_related("uploaded_by", "work_order").order_by("-created_at", "-pk"), 25).get_page(params.get("page"))
    # Whitelist keys; preserve only validated values in links, never arbitrary GET.
    filters = {key: (value.pk if key == "uploader" else value.isoformat() if key in {"start", "end"} else value)
               for key, value in values.items() if value and valid}
    common = {key: value for key, value in filters.items() if key != "issue"}
    from milenio_web.worker_health import status
    reader = status()["workers"]["documents"]
    return {"filters": form, "has_filters": bool(params), "counts": counts, "page": page,
            "capture_rows": [row_context(capture) for capture in page], "filter_query": urlencode(filters),
            "all_url": "?" + urlencode(common), "exceptions_url": "?" + urlencode({**common, "issue": "exceptions"}),
            "selected_issue": issue, "document_worker": reader}
