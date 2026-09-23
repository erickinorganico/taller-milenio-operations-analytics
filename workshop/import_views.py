"""Manager-only, two-step CSV import of append-only workshop catalogs."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render

from .access import require
from .models import AuditEvent, Customer, Part, Vehicle


MAX_BYTES = 1024 * 1024
MAX_ROWS = 1000
RECEIPT_AGE = 15 * 60
SESSION_KEY = "catalog_import_preview_v1"
FIELDS = {
    "customers": ("name", "phone", "email", "kind", "notes"),
    "vehicles": ("customer_name", "plate", "vin", "make", "model", "year", "odometer"),
    "parts": ("sku", "name", "unit", "cost", "sale_price", "reorder_point"),
}
TITLES = {"customers": "Clientes", "vehicles": "Vehículos", "parts": "Refacciones"}


def _digest(payload):
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _parse(upload, entity):
    if upload is None:
        return [], ["Seleccione un archivo CSV."]
    if upload.size > MAX_BYTES:
        return [], ["El archivo supera 1 MB."]
    raw = upload.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        return [], ["El archivo supera 1 MB."]
    try:
        content = raw.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        return [], ["El CSV debe estar codificado en UTF-8."]
    if "\x00" in content:
        return [], ["El CSV contiene caracteres nulos."]
    try:
        reader = csv.reader(io.StringIO(content, newline=""), strict=True)
        header = next(reader, None)
        if header is None or len(header) != len(FIELDS[entity]) or set(header) != set(FIELDS[entity]):
            return [], ["Los encabezados deben ser exactamente: " + ", ".join(FIELDS[entity]) + "."]
        rows = []
        errors = []
        for number, cells in enumerate(reader, start=2):
            if number > MAX_ROWS + 1:
                errors.append("El archivo supera 1,000 filas de datos.")
                break
            if len(cells) != len(header):
                errors.append(f"Fila {number}: se esperaban {len(header)} columnas y hay {len(cells)}.")
                continue
            rows.append({key: value.strip() for key, value in zip(header, cells)})
    except csv.Error as exc:
        return [], [f"CSV inválido: {exc}."]
    if not rows and not errors:
        errors.append("El archivo no contiene filas de datos.")
    return rows, errors


def _decimal(raw, field, max_digits, places):
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError):
        raise ValidationError({field: "Debe ser un número decimal válido."})
    if not value.is_finite() or value < 0:
        raise ValidationError({field: "Debe ser un número finito no negativo."})
    whole = len(value.as_tuple().digits) + value.as_tuple().exponent if value.as_tuple().exponent < 0 else len(value.as_tuple().digits) + value.as_tuple().exponent
    if value.as_tuple().exponent < -places or whole > max_digits - places:
        raise ValidationError({field: f"Use hasta {max_digits - places} enteros y {places} decimales."})
    return value


def _integer(raw, field, maximum):
    if not raw:
        return None
    if not raw.isascii() or not raw.isdecimal():
        raise ValidationError({field: "Debe ser un entero no negativo."})
    value = int(raw)
    if value > maximum:
        raise ValidationError({field: "Fuera del rango permitido."})
    return value


def _errors(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(f"{field}: {', '.join(values)}" for field, values in exc.message_dict.items())
    return "; ".join(exc.messages)


def _validate(entity, rows):
    errors = []
    objects = []
    seen = set()
    customer_map = {}
    if entity == "customers":
        existing = {name.casefold() for name in Customer.objects.values_list("name", flat=True)}
    elif entity == "vehicles":
        customers = list(Customer.objects.all())
        for customer in customers:
            customer_map.setdefault(customer.name.casefold(), []).append(customer)
        existing_plate = {plate.casefold() for plate in Vehicle.objects.exclude(plate="").values_list("plate", flat=True)}
        existing_vin = {vin.casefold() for vin in Vehicle.objects.exclude(vin__isnull=True).exclude(vin="").values_list("vin", flat=True)}
    else:
        existing = {sku.casefold() for sku in Part.objects.values_list("sku", flat=True)}
    for line, row in enumerate(rows, start=2):
        try:
            if set(row) != set(FIELDS[entity]) or not all(isinstance(value, str) for value in row.values()):
                raise ValidationError("El contenido cambió: columnas inválidas.")
            if entity == "customers":
                name = row["name"].strip()
                if not name or name.casefold() in existing or ("name", name.casefold()) in seen:
                    raise ValidationError({"name": "Falta el nombre o ya existe otro cliente con ese nombre."})
                obj = Customer(name=name, phone=row["phone"].strip(), email=row["email"].strip(),
                               kind=row["kind"].strip(), notes=row["notes"].strip())
                seen.add(("name", name.casefold()))
            elif entity == "vehicles":
                matches = customer_map.get(row["customer_name"].strip().casefold(), [])
                if len(matches) != 1:
                    raise ValidationError({"customer_name": "Debe coincidir con un único cliente existente."})
                plate = row["plate"].strip().upper()
                vin = row["vin"].strip().upper()
                if not plate and not vin:
                    raise ValidationError("Se requiere placa o VIN.")
                if plate and (plate.casefold() in existing_plate or ("plate", plate.casefold()) in seen):
                    raise ValidationError({"plate": "La placa ya existe o se repite en el archivo."})
                if vin and (vin.casefold() in existing_vin or ("vin", vin.casefold()) in seen):
                    raise ValidationError({"vin": "El VIN ya existe o se repite en el archivo."})
                year = _integer(row["year"].strip(), "year", 65535)
                if year is not None and not 1886 <= year <= date.today().year + 1:
                    raise ValidationError({"year": "Indique un año de vehículo válido."})
                obj = Vehicle(customer=matches[0], plate=plate, vin=vin or None,
                              make=row["make"].strip(), model=row["model"].strip(), year=year,
                              odometer=_integer(row["odometer"].strip(), "odometer", 4294967295))
                if plate:
                    seen.add(("plate", plate.casefold()))
                if vin:
                    seen.add(("vin", vin.casefold()))
            else:
                sku = row["sku"].strip().upper()
                if not sku or sku.casefold() in existing or ("sku", sku.casefold()) in seen:
                    raise ValidationError({"sku": "Falta el SKU o ya existe una refacción con ese SKU."})
                obj = Part(sku=sku, name=row["name"].strip(), unit=row["unit"].strip(),
                           cost=_decimal(row["cost"].strip(), "cost", 14, 2),
                           sale_price=_decimal(row["sale_price"].strip(), "sale_price", 14, 2),
                           reorder_point=_decimal(row["reorder_point"].strip(), "reorder_point", 12, 3))
                seen.add(("sku", sku.casefold()))
            obj.full_clean()
            objects.append(obj)
        except ValidationError as exc:
            errors.append(f"Fila {line}: {_errors(exc)}")
    return objects, errors


def _page(request, *, entity="customers", rows=None, errors=None, receipt=None, saved=None, status=200):
    return render(request, "workshop/import.html", {
        "title": "Importar catálogos", "section": "Datos", "entity": entity,
        "entities": [(key, title) for key, title in TITLES.items()],
        "fields": FIELDS[entity], "rows": rows, "errors": errors or [],
        "receipt": receipt, "saved": saved,
    }, status=status)


@require("manage")
def import_catalog(request):
    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    entity = request.GET.get("template") if request.method == "GET" and "template" in request.GET else request.POST.get("entity") if request.method == "POST" else request.GET.get("entity", "customers")
    if entity not in FIELDS:
        return _page(request, errors=["Seleccione un catálogo válido."], status=400)
    if request.method == "GET":
        if "template" in request.GET:
            output = io.StringIO(newline="")
            csv.writer(output).writerow(FIELDS[entity])
            response = HttpResponse("\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="milenio-{entity}.csv"'
            response["X-Content-Type-Options"] = "nosniff"
            return response
        return _page(request, entity=entity)
    stage = request.POST.get("stage")
    if stage == "preview":
        request.session.pop(SESSION_KEY, None)
        rows, errors = _parse(request.FILES.get("file"), entity)
        if not errors:
            _, errors = _validate(entity, rows)
        if errors:
            return _page(request, entity=entity, errors=errors, status=400)
        nonce = secrets.token_urlsafe(24)
        payload = {"entity": entity, "rows": rows, "user_id": request.user.pk, "nonce": nonce}
        digest = _digest(payload)
        request.session[SESSION_KEY] = {"payload": payload, "sha256": digest}
        receipt = signing.dumps({"sha256": digest, "user_id": request.user.pk, "nonce": nonce}, salt="workshop.catalog.import")
        return _page(request, entity=entity, rows=rows, receipt=receipt)
    if stage != "commit":
        return _page(request, entity=entity, errors=["Etapa de importación inválida."], status=400)
    token = request.POST.get("receipt", "")
    try:
        signed = signing.loads(token, salt="workshop.catalog.import", max_age=RECEIPT_AGE)
    except signing.BadSignature:
        return _page(request, entity=entity, errors=["La vista previa venció o su recibo es inválido. Vuelva a cargar el CSV."], status=400)
    staged = request.session.get(SESSION_KEY)
    if (not isinstance(staged, dict) or not isinstance(staged.get("payload"), dict)
            or not isinstance(staged.get("sha256"), str) or signed.get("user_id") != request.user.pk
            or staged["payload"].get("user_id") != request.user.pk
            or signed.get("sha256") != staged["sha256"] or signed.get("nonce") != staged["payload"].get("nonce")
            or _digest(staged["payload"]) != staged["sha256"] or staged["payload"].get("entity") != entity):
        return _page(request, entity=entity, errors=["La vista previa ya se usó o cambió. Vuelva a cargar el CSV."], status=400)
    rows = staged["payload"].get("rows")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        return _page(request, entity=entity, errors=["La vista previa ya no es válida."], status=400)
    digest = staged["sha256"]
    try:
        with transaction.atomic():
            if AuditEvent.objects.filter(entity_type="CatalogImport", entity_id=digest, action="import_csv").exists():
                return _page(request, entity=entity, errors=["Este recibo ya se confirmó. No se duplicaron registros."], status=409)
            objects, errors = _validate(entity, rows)
            if errors:
                return _page(request, entity=entity, errors=["La fuente cambió desde la vista previa."] + errors, status=409)
            for obj in objects:
                obj.save()
            AuditEvent.objects.create(actor=request.user, entity_type="CatalogImport", entity_id=digest,
                                      action="import_csv", before={}, after={"catalog": entity, "count": len(objects),
                                      "receipt_sha256": digest, "record_ids": [obj.pk for obj in objects]})
    except (IntegrityError, ValidationError) as exc:
        return _page(request, entity=entity, errors=[f"No se importó ningún registro: {_errors(exc) if isinstance(exc, ValidationError) else 'conflicto de datos concurrente'}."], status=409)
    request.session.pop(SESSION_KEY, None)
    messages.success(request, f"Se importaron {len(objects)} registros de {TITLES[entity]}. Recibo: {digest[:12]}.")
    return redirect("/import/?entity=" + entity)
