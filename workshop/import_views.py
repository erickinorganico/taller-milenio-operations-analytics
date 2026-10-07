"""Two-step file import, with a source check and atomic confirmation."""
from collections import Counter
import secrets

from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render

from .access import require
from .data_exchange import (FIELDS, TITLES, GUIDANCE, LABELS, MAX_BYTES, MAX_ROWS,
                            apply_rows, digest, parse_file, source_digest, file_content)
from .models import AuditEvent
from .webforms import LABELS as FIELD_LABELS

RECEIPT_AGE = 15 * 60
SESSION_KEY = "catalog_import_preview_v2"
SALT = "workshop.catalog.import.v2"


def _page(request, *, entity="customers", errors=None, receipt=None, results=None, mode="upsert", status=200):
    labels = {**FIELD_LABELS, **LABELS}
    results = results or []
    for result in results:
        result["cells"] = [result["row"].get(field, "") for field in FIELDS[entity]]
        for change in result["changes"]:
            change["label"] = labels.get(change["field"], change["field"])
    summary = Counter(result["action"] for result in results)
    return render(request, "workshop/import.html", {
        "title": "Actualizar base de datos", "section": "Base de datos", "entity": entity,
        "entities": list(TITLES.items()), "fields": [(field, labels.get(field, field)) for field in FIELDS[entity]],
        "guidance": GUIDANCE[entity], "mode": mode, "errors": errors or [], "receipt": receipt,
        "results": results, "rows": [result["row"] for result in results],
        "summary": {action: summary[action] for action in ("created", "updated", "unchanged")},
    }, status=status)


@require("manage")
def import_catalog(request):
    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    entity = (request.GET.get("template", request.GET.get("entity", "customers"))
              if request.method == "GET" else request.POST.get("entity"))
    if entity not in FIELDS:
        return _page(request, errors=["Selecciona un catálogo válido."], status=400)
    if request.method == "GET":
        if "template" in request.GET:
            format = request.GET.get("format", "csv")
            if format not in {"csv", "xlsx"}:
                return _page(request, entity=entity, errors=["Formato inválido."], status=400)
            content, mime = file_content(entity, format, template=True)
            response = HttpResponse(content, content_type=mime)
            response["Content-Disposition"] = f'attachment; filename="milenio-{entity}.{format}"'
            response["X-Content-Type-Options"] = "nosniff"
            return response
        return _page(request, entity=entity)
    # Legacy callers still get append-only behavior unless they choose update.
    mode = request.POST.get("mode", "create")
    if mode not in {"create", "upsert"}:
        return _page(request, entity=entity, errors=["Selecciona una forma de actualización válida."], status=400)
    stage = request.POST.get("stage")
    if stage == "preview":
        request.session.pop(SESSION_KEY, None)
        rows, errors = parse_file(request.FILES.get("file"), entity)
        if errors:
            return _page(request, entity=entity, mode=mode, errors=errors, status=400)
        try:
            with transaction.atomic():
                source = source_digest(entity)
                results = apply_rows(request.user, entity, rows, mode)
                transaction.set_rollback(True)
        except (ValidationError, IntegrityError) as exc:
            return _page(request, entity=entity, mode=mode,
                         errors=exc.messages if isinstance(exc, ValidationError) else ["Hay datos duplicados o relaciones inválidas en el archivo."], status=400)
        payload = {"entity": entity, "rows": rows, "mode": mode, "source": source,
                   "user_id": request.user.pk, "nonce": secrets.token_urlsafe(24)}
        sha = digest(payload)
        request.session[SESSION_KEY] = {"payload": payload, "sha256": sha}
        receipt = signing.dumps({"sha256": sha, "user_id": request.user.pk, "nonce": payload["nonce"]}, salt=SALT)
        return _page(request, entity=entity, mode=mode, results=results, receipt=receipt)
    if stage != "commit":
        return _page(request, entity=entity, errors=["Etapa de importación inválida."], status=400)
    try:
        signed = signing.loads(request.POST.get("receipt", ""), salt=SALT, max_age=RECEIPT_AGE)
    except signing.BadSignature:
        return _page(request, entity=entity, errors=["La vista previa venció o su recibo es inválido. Vuelve a cargar el archivo."], status=400)
    staged = request.session.get(SESSION_KEY)
    payload = staged.get("payload") if isinstance(staged, dict) else None
    if (not isinstance(signed, dict) or not isinstance(payload, dict) or
            signed.get("user_id") != request.user.pk or payload.get("user_id") != request.user.pk or
            signed.get("sha256") != staged.get("sha256") or signed.get("nonce") != payload.get("nonce") or
            digest(payload) != staged.get("sha256") or payload.get("entity") != entity or payload.get("mode") != mode):
        return _page(request, entity=entity, errors=["La vista previa ya se usó o cambió. Vuelve a cargar el archivo."], status=400)
    rows = payload.get("rows")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        return _page(request, entity=entity, errors=["La vista previa ya no es válida."], status=400)
    sha = staged["sha256"]
    try:
        with transaction.atomic():
            if AuditEvent.objects.filter(entity_type="CatalogImport", entity_id=sha).exists():
                raise ValidationError("Este recibo ya se confirmó. No se duplicaron registros.")
            if source_digest(entity) != payload["source"]:
                raise ValidationError("La fuente cambió desde la vista previa. Vuelve a revisar el archivo antes de confirmar.")
            results = apply_rows(request.user, entity, rows, mode)
            counts = Counter(result["action"] for result in results)
            AuditEvent.objects.create(actor=request.user, entity_type="CatalogImport", entity_id=sha,
                                      action="import_csv", after={"catalog": entity, "count": len(results),
                                      "mode": mode, "summary": dict(counts), "receipt_sha256": sha,
                                      "record_ids": [result["id"] for result in results]})
            if counts["created"] or counts["updated"]:
                from .analytics import refresh_analytics
                refresh_analytics(actor=request.user, trigger="file_import")
    except (IntegrityError, ValidationError) as exc:
        return _page(request, entity=entity, mode=mode,
                     errors=exc.messages if isinstance(exc, ValidationError) else ["Los datos cambiaron. No se guardó ningún registro."], status=409)
    request.session.pop(SESSION_KEY, None)
    messages.success(request, f"{TITLES[entity]}: {counts['created']} agregados, {counts['updated']} actualizados y {counts['unchanged']} sin cambios.")
    return redirect("/data/?catalog=" + entity)
