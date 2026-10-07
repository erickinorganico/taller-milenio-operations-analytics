"""Reviewed image data enters the same transactional workshop database."""
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from . import models as m, services as s
from .data_exchange import digest, integer, decimal, snapshot

SALT = "milenio-document-application-v1"
TTL = 15*60
FIELD_LABELS = {"name":"Nombre","phone":"Teléfono","email":"Correo","kind":"Tipo","notes":"Notas","plate":"Placas","vin":"VIN",
                "make":"Marca","model":"Modelo","year":"Año","odometer":"Kilometraje","number":"Folio","complaint":"Solicitud",
                "description":"Servicio","quantity":"Cantidad observada","unit_price":"Precio unitario observado","unit_cost":"Costo unitario observado","part_sku":"SKU"}


def one(query, label):
    found = list(query[:2])
    if len(found) > 1:
        raise ValidationError(f"{label}: hay varias coincidencias. Selecciona el registro correcto antes de aplicar.")
    return found[0] if found else None


def selected(model, key, selection):
    pk = selection.get(key)
    if not pk:
        return None
    obj = model.objects.filter(pk=pk).first()
    if not obj:
        raise ValidationError("El registro seleccionado ya no existe.")
    return obj


def normalized(value):
    return str(value or "").strip().upper()


def service_rows(capture):
    """Preserve structured values only while reviewed descriptions still match."""
    inputs = capture.service_items or [{"description":line} for line in capture.data.get("services", "").splitlines()]
    result, seen = [], {}
    for raw in inputs:
        description = str(raw.get("description", "")).strip()
        if not description:
            continue
        if len(description) > 250:
            raise ValidationError("Cada servicio debe tener como máximo 250 caracteres.")
        kind = raw.get("kind", "unknown")
        if kind not in {"unknown", "labor", "service", "part"}:
            raise ValidationError("Tipo de servicio inválido.")
        sku = normalized(raw.get("part_sku"))
        identity = digest([description.casefold(), kind, sku])
        def number(key, places, digits, positive=False):
            value = raw.get(key)
            return None if value in (None, "") else decimal(str(value), key, places, digits, positive)
        row = {"description":description, "kind":kind, "fingerprint":identity, "part_sku":sku,
               "quantity":number("quantity",3,12,True), "unit_price":number("unit_price",2,14), "unit_cost":number("unit_cost",2,14)}
        if identity in seen:
            if any(row[key] != seen[identity][key] for key in ["quantity","unit_price","unit_cost"]):
                raise ValidationError("Hay servicios con la misma descripción y SKU pero cantidades o importes distintos. Diferencia sus descripciones antes de aplicar.")
            continue
        seen[identity] = row
        result.append(row)
    if len(result) > 50:
        raise ValidationError("Revisa como máximo 50 servicios por documento.")
    return result


def _execute(capture, actor, selection):
    data, changes, sources = capture.data, [], []
    folio, plate, vin = normalized(data.get("order_number")), normalized(data.get("vehicle_plate")), normalized(data.get("vehicle_vin"))
    if not folio:
        raise ValidationError("Confirma el folio antes de aplicar al taller.")
    order = selected(m.WorkOrder, "order", selection) or one(m.WorkOrder.objects.filter(number__iexact=folio), "Folio")
    if order and order.number.casefold() != folio.casefold():
        raise ValidationError("El folio de la foto no corresponde a la orden seleccionada.")
    vehicle = selected(m.Vehicle, "vehicle", selection)
    if order:
        if vehicle and vehicle.pk != order.vehicle_id:
            raise ValidationError("La orden y el vehículo seleccionados no corresponden.")
        vehicle = order.vehicle
    def identifier_match(query, label):
        if vehicle and query.filter(pk=vehicle.pk).exists():
            return vehicle
        return one(query,label)
    plate_match = identifier_match(m.Vehicle.objects.filter(plate__iexact=plate), "Placas") if plate else None
    vin_match = identifier_match(m.Vehicle.objects.filter(vin__iexact=vin), "VIN") if vin else None
    if plate_match and vin_match and plate_match.pk != vin_match.pk:
        raise ValidationError("Placas y VIN corresponden a vehículos diferentes.")
    match = plate_match or vin_match
    if vehicle and match and vehicle.pk != match.pk:
        raise ValidationError("La identificación de la foto corresponde a otro vehículo.")
    vehicle = vehicle or match
    if vehicle and ((plate and vehicle.plate and normalized(vehicle.plate) != plate) or (vin and vehicle.vin and normalized(vehicle.vin) != vin)):
        raise ValidationError("Confirma placas y VIN: no corresponden al vehículo identificado.")
    customer = selected(m.Customer, "customer", selection)
    if vehicle:
        if customer and customer.pk != vehicle.customer_id:
            raise ValidationError("El cliente seleccionado no es propietario del vehículo registrado.")
        customer = vehicle.customer
        if data.get("customer_name") and data["customer_name"].strip().casefold() != customer.name.strip().casefold():
            raise ValidationError("El nombre del cliente difiere del propietario registrado. Corrige o revisa la relación fuera de esta captura.")
    if not customer:
        name = data.get("customer_name", "").strip()
        if not name:
            raise ValidationError("Indica el cliente o selecciona un vehículo existente.")
        customer = one(m.Customer.objects.filter(name__iexact=name), "Cliente")
    if customer and data.get("customer_name") and data["customer_name"].strip().casefold() != customer.name.strip().casefold():
        raise ValidationError("El cliente seleccionado y el nombre de la foto no coinciden. Revisa el nombre antes de aplicar.")
    def remember(obj, label):
        before = snapshot(obj) if obj and obj.pk else {}
        sources.append({"entity":label, "id":obj.pk if before else None, "before":before})
        return before
    def save_catalog(obj, before, label):
        obj.full_clean()
        after = snapshot(obj)
        differences = {key:{"before":before.get(key), "after":value} for key,value in after.items() if key not in {"id", "created_at", "updated_at"} and before.get(key) != value}
        if not before or differences:
            obj.save()
            m.AuditEvent.objects.create(actor=actor, entity_type=type(obj).__name__, entity_id=str(obj.pk),
                action="image_created" if not before else "image_updated", before=before, after={**snapshot(obj), "capture_id":capture.pk})
        changes.append({"entity":label,"action":"Crear" if not before else "Actualizar" if differences else "Conservar","fields":differences})
        return obj
    before_customer = remember(customer, "Cliente")
    customer = customer or m.Customer(name=data["customer_name"].strip())
    if data.get("phone"):
        customer.phone = data["phone"].strip()
    save_catalog(customer,before_customer,"Cliente")
    before_vehicle = remember(vehicle,"Vehículo")
    if not vehicle:
        if not (plate or vin):
            raise ValidationError("Confirma placas o VIN para crear el vehículo.")
        if not data.get("vehicle_make") or not data.get("vehicle_model"):
            raise ValidationError("Para un vehículo nuevo, confirma marca y modelo por separado.")
        vehicle = m.Vehicle(customer=customer, plate=plate, vin=vin or None, make=data["vehicle_make"], model=data["vehicle_model"])
    for key, attribute in [("vehicle_plate","plate"),("vehicle_vin","vin"),("vehicle_make","make"),("vehicle_model","model")]:
        if data.get(key):
            setattr(vehicle,attribute,normalized(data[key]) if key in {"vehicle_vin","vehicle_plate"} else data[key].strip())
    if data.get("vehicle_year") not in ("",None):
        year = integer(str(data["vehicle_year"]),"Año",65535)
        if not 1886 <= year <= timezone.localdate().year+1:
            raise ValidationError("Confirma un año de vehículo válido.")
        vehicle.year = year
    mileage = integer(str(data.get("odometer") or ""),"Kilometraje")
    if mileage is not None:
        known = [value for value in [vehicle.odometer, order.odometer if order else None] if value is not None]
        if known and mileage < max(known):
            raise ValidationError("El kilometraje de la foto es menor al registrado. Corrige la lectura antes de aplicar.")
        vehicle.odometer = mileage
    save_catalog(vehicle,before_vehicle,"Vehículo")
    before_order = remember(order,"Orden")
    if order and order.status in {"delivered","cancelled"}:
        raise ValidationError("La orden está cerrada. Esta captura no puede modificar su operación.")
    complaint = data.get("complaint", "").strip()
    if not order:
        if not complaint:
            raise ValidationError("Confirma la solicitud para crear una orden nueva.")
        order = s.create_work_order(actor=actor, vehicle=vehicle, number=folio, complaint=complaint, odometer=mileage)
        changes.append({"entity":"Orden","action":"Crear","fields":{"number":{"before":None,"after":folio},"complaint":{"before":None,"after":complaint}}})
    else:
        differences = {}
        # Preserve the intake complaint; additional service-sheet observations stay in the document.
        if complaint and order.status == "intake" and order.complaint != complaint:
            differences["complaint"] = {"before":order.complaint,"after":complaint}
            order.complaint = complaint
        if mileage is not None and order.odometer != mileage:
            differences["odometer"] = {"before":str(order.odometer) if order.odometer is not None else None,"after":str(mileage)}
            order.odometer = mileage
        if differences:
            order.version += 1
            order.save(update_fields=["complaint","odometer","version","updated_at"])
            m.AuditEvent.objects.create(actor=actor,entity_type="WorkOrder",entity_id=str(order.pk),action="image_updated",before=before_order,after={**snapshot(order),"capture_id":capture.pk})
        changes.append({"entity":"Orden","action":"Actualizar" if differences else "Vincular","fields":differences})
    service_results = []
    for values in service_rows(capture):
        item = m.CapturedService.objects.filter(work_order=order, fingerprint=values["fingerprint"]).first()
        before = remember(item,"Servicio solicitado")
        item = item or m.CapturedService(work_order=order)
        previous_values = {key:getattr(item,key) for key in values}
        for key,value in values.items():
            # Unknown values do not erase previously observed quantities/prices.
            if value is not None:
                setattr(item,key,value)
        item.full_clean()
        differences = {key:{"before":str(previous_values[key]) if previous_values[key] is not None and before else None,"after":str(value) if value is not None else None}
                       for key,value in values.items() if key != "fingerprint" and value is not None and (not before or previous_values[key] != value)}
        changed = not before or bool(differences)
        if changed:
            item.save()
            m.AuditEvent.objects.create(actor=actor,entity_type="CapturedService",entity_id=str(item.pk),action="image_created" if not before else "image_updated",before=before,after={**snapshot(item),"capture_id":capture.pk,"work_order_id":order.pk})
        item.documents.add(capture)
        changes.append({"entity":"Servicio solicitado","action":"Crear" if not before else "Actualizar" if changed else "Vincular","fields":differences})
        service_results.append(item.pk)
    # New surrogate IDs vary between preview and commit; identity is represented by the document.
    for change in changes:
        if change["action"] == "Crear":
            for key in ["customer","work_order"]:
                change["fields"].pop(key,None)
        for key,value in change["fields"].items():
            value["label"] = FIELD_LABELS.get(key,key)
    return {"changes":changes,"sources":sources,"order_id":order.pk,"service_ids":service_results}


def signature_plan(plan):
    # Targets before a new row exists are represented by id=None, never speculative PKs.
    return digest({"changes":plan["changes"],"sources":plan["sources"]})


def preview(capture, actor, selection):
    s._actor(actor,"reception")
    with transaction.atomic():
        current = m.DocumentCapture.objects.select_for_update().get(pk=capture.pk)
        if current.status != "confirmed":
            raise ValidationError("Confirma los datos de la foto antes de aplicar.")
        plan = _execute(current,actor,selection)
        receipt = signing.dumps({"capture":current.pk,"version":current.version,"actor":actor.pk,"selection":selection,"plan":signature_plan(plan)},salt=SALT,compress=True)
        transaction.set_rollback(True)
    return plan, receipt


def commit(capture, actor, receipt):
    s._actor(actor,"reception")
    try:
        token = signing.loads(receipt,salt=SALT,max_age=TTL)
    except signing.BadSignature:
        raise ValidationError("La vista previa venció o no es válida. Revisa los cambios de nuevo.")
    if token.get("capture") != capture.pk or token.get("actor") != actor.pk:
        raise ValidationError("La vista previa pertenece a otra captura o usuario.")
    with transaction.atomic():
        current = m.DocumentCapture.objects.select_for_update().get(pk=capture.pk)
        if current.status == "applied":
            return current.application_result
        if current.status != "confirmed" or current.version != token["version"]:
            raise ValidationError("La captura cambió. Revisa una nueva vista previa.")
        plan = _execute(current,actor,token["selection"])
        if signature_plan(plan) != token["plan"]:
            raise ValidationError("Los registros del taller cambiaron después de la vista previa. Revisa nuevamente antes de aplicar.")
        result = {"order_id":plan["order_id"],"service_ids":plan["service_ids"],"changes":plan["changes"]}
        current.status = "applied"
        current.work_order_id = result["order_id"]
        current.applied_by, current.applied_at = actor, timezone.now()
        current.application_result = result
        current.version += 1
        current.save(update_fields=["status","work_order","applied_by","applied_at","application_result","version"])
        m.AuditEvent.objects.create(actor=actor,entity_type="DocumentCapture",entity_id=str(current.pk),action="applied",after=result)
        # Analytics observes only committed business rows, with background execution.
        from .automation import enqueue_manual
        enqueue_manual(actor, mode="rules") if actor.is_superuser or actor.groups.filter(name__in=["manager","advisor"]).exists() else None
        return result
