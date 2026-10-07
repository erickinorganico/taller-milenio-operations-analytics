"""Transactional writes, explicit approvals, provenance and repeatable imports."""
import csv
import hashlib
import io
from datetime import date
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from .models import (AuditEvent, BusinessContact, Evidence, FleetProfile, ImportReceipt,
                     Interaction, ResearchBatch, SalesAccount, SalesOpportunity, SalesProposal, Suppression)
from .rules import domain_for, qualify, reviewed, suppressed


def audit(account, actor, action, **details):
    AuditEvent.objects.create(account=account, actor=actor, action=action, details=details)


def locked(pk, version):
    account = SalesAccount.objects.select_for_update().get(pk=pk)
    if account.version != int(version):
        raise ValidationError("La ficha cambió en otra ventana. Recarga antes de guardar.")
    return account


def bump(account):
    account.version += 1
    account.full_clean()
    account.save()


def recurrence_confirmed(account):
    return account.recurrence_basis in {"second_order", "current_plan"} and reviewed(account.recurrence_evidence, account, "recurrence")


def current_acceptance(opportunity):
    """The latest revision alone can authorize a new commercial handoff/link."""
    proposal = opportunity.proposals.order_by("-revision").first()
    if opportunity.status != "lost" and proposal and proposal.accepted_at and proposal.acceptance_reference.strip():
        return proposal
    return None


def identity_matches(values, exclude=None):
    matches = SalesAccount.objects.filter(name__iexact=values["name"].strip(), city__iexact=values.get("city", "Tijuana").strip(), branch__iexact=values.get("branch", "").strip(), domain=values.get("domain"))
    return matches.exclude(pk=exclude) if exclude else matches


@transaction.atomic
def create_account(data, actor, **extra):
    values = {**data, **extra}
    values["domain"] = domain_for(values.get("website") or values.get("domain"))
    values.setdefault("owner", actor)
    if values.get("recurrence_basis", "pending") != "pending" or values.get("recurrence_evidence"):
        raise ValidationError("Crea primero la ficha y su evidencia revisada; la recurrencia inicial queda por confirmar.")
    if identity_matches(values).exists():
        raise ValidationError("Posible cuenta existente: revisa la ficha o identifica la sucursal antes de crear otra.")
    account = SalesAccount(**values)
    account.full_clean()
    account.save()
    FleetProfile.objects.create(account=account)
    audit(account, actor, "created")
    return account


@transaction.atomic
def update_account(pk, version, data, actor):
    account = locked(pk, version)
    before = {key: str(getattr(account, key)) for key in data}
    for key, value in data.items():
        setattr(account, key, value)
    account.domain = domain_for(account.website or account.domain)
    if identity_matches({"name": account.name, "city": account.city, "branch": account.branch, "domain": account.domain}, exclude=account.pk).exists():
        raise ValidationError("Posible cuenta existente: revisa la identidad o identifica la sucursal.")
    if account.recurrence_basis != "pending" and not recurrence_confirmed(account):
        raise ValidationError("La recurrencia requiere evidencia revisada de esta empresa sobre segunda orden o plan vigente.")
    if account.stage == "active" and not recurrence_confirmed(account):
        account.stage = "recurrence_pending"
    if suppressed(account):
        account.stage = "suppressed"
        account.next_action = ""
        account.next_action_on = None
    bump(account)
    audit(account, actor, "updated", before=before)
    return account


@transaction.atomic
def add_record(pk, version, kind, data, actor):
    account = locked(pk, version)
    if kind == "evidence":
        if not data.get("source_url") and not data.get("source_note"):
            raise ValidationError("La evidencia necesita URL o referencia de una conversación directa.")
        obj = Evidence(account=account, created_by=actor, **data)
    elif kind == "contact":
        existing = data.pop("existing_contact", None)
        if existing and existing.account_id != account.pk:
            raise ValidationError("El contacto debe pertenecer a esta empresa.")
        if not data.get("email") and not data.get("phone"):
            raise ValidationError("Captura al menos un canal de contacto.")
        if not data.get("source_url") and not data.get("source_note"):
            raise ValidationError("Registra la procedencia del contacto.")
        data["email"] = data.get("email", "").strip().lower()
        if data["email"] and account.contacts.filter(email__iexact=data["email"]).exclude(pk=existing.pk if existing else None).exists():
            raise ValidationError("Este correo ya está registrado en la empresa.")
        obj = existing or BusinessContact(account=account)
        for key, value in data.items(): setattr(obj, key, value)
    elif kind == "opportunity":
        if suppressed(account):
            raise ValidationError("La empresa está en no contactar.")
        if not account.fleet.need_confirmed or not reviewed(account.fleet.need_evidence, account, "need"):
            raise ValidationError("Confirma la necesidad con evidencia revisada antes de abrir la oportunidad.")
        if not account.owner_id or not account.next_action.strip() or not account.next_action_on:
            raise ValidationError("Registra responsable, siguiente paso acordado y fecha antes de abrir la oportunidad.")
        obj = SalesOpportunity(account=account, **data)
    else:
        raise ValidationError("Acción desconocida.")
    obj.full_clean()
    obj.save()
    bump(account)
    details = {"record_id": obj.pk}
    if kind == "opportunity":
        details.update(need_evidence=account.fleet.need_evidence_id, owner=account.owner_id, agreed_next_step=account.next_action, follow_up_on=account.next_action_on.isoformat())
    audit(account, actor, kind + "_added", **details)
    return obj


@transaction.atomic
def update_fleet(pk, version, data, actor):
    account = locked(pk, version)
    fleet = account.fleet
    for key, value in data.items(): setattr(fleet, key, value)
    if fleet.total_units is not None and fleet.compatible_units is not None and fleet.compatible_units > fleet.total_units:
        raise ValidationError("Las unidades compatibles no pueden superar el total.")
    if (fleet.compatible_units or 0) > 0 and (fleet.fuel not in {"gasoline", "mixed"} or fleet.vehicle_type != "light"):
        raise ValidationError("Solo registra como compatibles las unidades ligeras a gasolina de una flotilla confirmada.")
    for field, topic in [("vehicle_evidence", "vehicles"), ("need_evidence", "need"), ("towing_evidence", "coverage")]:
        evidence = getattr(fleet, field)
        if evidence and not reviewed(evidence, account, topic):
            raise ValidationError("La evidencia debe pertenecer a esta empresa, ser del tipo correcto y estar revisada.")
    fleet.full_clean()
    fleet.save()
    bump(account)
    audit(account, actor, "fleet_updated", result=qualify(account))


@transaction.atomic
def change_stage(pk, version, stage, actor):
    account = locked(pk, version)
    result = qualify(account)
    if suppressed(account): raise ValidationError("No se puede reabrir una baja desde el flujo comercial.")
    if stage not in SalesAccount.Stage.values or stage == "suppressed": raise ValidationError("Usa el registro de baja para no contactar.")
    if stage in {"ready", "conversation"} and not result["exploratory"]:
        raise ValidationError("Antes de contactar, revisa identidad, evidencia y canal empresarial.")
    if stage in {"qualified", "proposal", "pilot", "active", "recurrence_pending"} and not (result["mechanics"] or result["towing"]):
        raise ValidationError("Aún no existe necesidad y compatibilidad confirmadas.")
    if stage == "proposal" and not SalesProposal.objects.filter(opportunity__account=account).exists():
        raise ValidationError("Primero registra una propuesta comercial.")
    if stage in {"pilot", "active"} and not any(current_acceptance(op) for op in account.opportunities.all()):
        raise ValidationError("Registra la aceptación de la propuesta antes del primer servicio.")
    if stage == "active" and not recurrence_confirmed(account):
        raise ValidationError("Recurrencia por confirmar: registra segunda orden real o plan vigente, con evidencia revisada. Una primera orden no basta.")
    if stage not in {"lost", "research"} and (not account.next_action or not account.next_action_on):
        raise ValidationError("Asigna la próxima acción y su fecha en la ficha.")
    before = account.stage
    account.stage = stage
    if stage == "lost":
        account.next_action = ""
        account.next_action_on = None
    bump(account)
    audit(account, actor, "stage_changed", before=before, after=stage)


@transaction.atomic
def add_interaction(pk, version, data, actor):
    account = locked(pk, version)
    kind = data["kind"]
    if kind == "sent" and not qualify(account)["exploratory"]:
        raise ValidationError("Contacto bloqueado: revisa identidad, contacto o baja antes de registrar un envío.")
    if data["occurred_at"] > timezone.now(): raise ValidationError("Un evento realizado no puede tener fecha futura.")
    obj = Interaction(account=account, created_by=actor, **data)
    obj.full_clean()
    obj.save()
    if kind in {"reply", "meeting", "bounce", "optout"}:
        account.next_action = ""
        account.next_action_on = None
    if kind == "optout":
        Suppression.objects.get_or_create(account=account, defaults={"reason": data["summary"][:240], "emails": [e.lower() for e in account.contacts.exclude(email="").values_list("email", flat=True)], "domain": account.domain or "", "created_by": actor})
        account.stage = "suppressed"
    if kind == "bounce":
        # No target guessing: suspend email outreach until a person reviews channels.
        account.contacts.exclude(email="").update(deliverability="bounced")
    bump(account)
    audit(account, actor, "interaction", kind=kind, record_id=obj.pk)
    if kind in {"sent", "reply", "meeting", "bounce", "optout"}:
        from .mail_flow import pause_account
        pause_account(account.pk, "Intervención humana: " + kind, manual=True)
    return obj


@transaction.atomic
def create_proposal(pk, version, data, actor):
    account = locked(pk, version)
    supplied = data.pop("opportunity")
    opportunity = SalesOpportunity.objects.select_for_update().get(pk=supplied.pk, account=account)
    if opportunity.status == "lost": raise ValidationError("Oportunidad no disponible.")
    if not qualify(account)[opportunity.service]: raise ValidationError("El servicio aún no tiene compatibilidad y necesidad confirmadas.")
    if data["valid_until"] < timezone.localdate(): raise ValidationError("La vigencia debe ser hoy o posterior.")
    revision = (opportunity.proposals.aggregate(n=Max("revision"))["n"] or 0) + 1
    proposal = SalesProposal(opportunity=opportunity, revision=revision, created_by=actor, **data)
    proposal.full_clean()
    proposal.save()
    opportunity.status = "pending_acceptance"
    opportunity.save(update_fields=["status", "updated_at"])
    bump(account)
    audit(account, actor, "proposal_created", proposal=proposal.pk, revision=revision)
    return proposal


@transaction.atomic
def accept_proposal(pk, version, proposal_id, reference, actor):
    account = locked(pk, version)
    proposal = SalesProposal.objects.get(pk=proposal_id, opportunity__account=account)
    if not reference.strip(): raise ValidationError("Registra quién autorizó y la referencia de la aceptación.")
    if proposal.revision != proposal.opportunity.proposals.aggregate(n=Max("revision"))["n"]:
        raise ValidationError("Solo puede aceptarse la revisión más reciente.")
    if not qualify(account)[proposal.opportunity.service]: raise ValidationError("Revisa compatibilidad o baja antes de aceptar.")
    if proposal.opportunity.status == "lost": raise ValidationError("La oportunidad está cerrada sin venta.")
    if proposal.accepted_at: return proposal
    if proposal.valid_until < timezone.localdate(): raise ValidationError("Propuesta vencida; prepara una nueva revisión.")
    proposal.accepted_at = timezone.now()
    proposal.acceptance_reference = reference.strip()
    proposal.full_clean()
    proposal.save()
    proposal.opportunity.status = "won"
    proposal.opportunity.save(update_fields=["status", "updated_at"])
    bump(account)
    audit(account, actor, "proposal_accepted", proposal=proposal.pk, reference=reference)
    return proposal


@transaction.atomic
def handoff(pk, version, actor, customer=None):
    from workshop.models import Customer
    account = locked(pk, version)
    if account.operational_customer_id: return account.operational_customer
    if suppressed(account): raise ValidationError("Empresa en no contactar: resolver la situación antes del traspaso comercial.")
    accepted = [p for op in account.opportunities.all() if (p := current_acceptance(op))]
    if not accepted:
        raise ValidationError("Se requiere aceptación de una revisión vigente antes de crear el cliente operativo.")
    if customer is None:
        contact = account.contacts.filter(published_business=True).exclude(deliverability="bounced").first()
        if Customer.objects.filter(name__iexact=account.name).exists() or (contact and contact.email and Customer.objects.filter(email__iexact=contact.email).exists()):
            raise ValidationError("Puede existir un cliente operativo: selecciónalo para evitar duplicados.")
        customer = Customer(name=account.name, kind=Customer.Kind.FLEET, email=contact.email if contact else "", phone=contact.phone if contact else "", notes=f"Origen comercial {account.pk}")
        customer.full_clean()
        customer.save()
    account.operational_customer = customer
    bump(account)
    audit(account, actor, "handoff", customer_id=customer.pk, accepted_proposals=[{"id": p.pk, "revision": p.revision} for p in accepted])
    return customer


@transaction.atomic
def link_service(pk, version, opportunity, work_order, tow_service, actor):
    account = locked(pk, version)
    opportunity = SalesOpportunity.objects.select_for_update().get(pk=opportunity.pk, account=account)
    if opportunity.account_id != account.pk or not account.operational_customer_id: raise ValidationError("Primero vincula el cliente operativo de esta oportunidad.")
    if not qualify(account)[opportunity.service]: raise ValidationError("Revisa compatibilidad actual o baja antes de vincular el servicio.")
    proposal = current_acceptance(opportunity)
    if not proposal: raise ValidationError("Falta aceptación de la revisión vigente de esta oportunidad.")
    if opportunity.service == "mechanics":
        if tow_service or not work_order or work_order.vehicle.customer_id != account.operational_customer_id: raise ValidationError("Selecciona una orden del mismo cliente.")
    elif work_order or not tow_service or tow_service.customer_id != account.operational_customer_id:
        raise ValidationError("Selecciona una grúa del mismo cliente.")
    if opportunity.work_order_id and opportunity.work_order_id != getattr(work_order, "pk", None): raise ValidationError("La oportunidad ya tiene otra orden.")
    if opportunity.tow_service_id and opportunity.tow_service_id != getattr(tow_service, "pk", None): raise ValidationError("La oportunidad ya tiene otro servicio de grúa.")
    opportunity.work_order = work_order
    opportunity.tow_service = tow_service
    opportunity.service_proposal = proposal
    opportunity.save()
    bump(account)
    audit(account, actor, "service_linked", opportunity=opportunity.pk, order=opportunity.work_order_id, tow=opportunity.tow_service_id, proposal=proposal.pk, revision=proposal.revision)


CSV_FIELDS = ["external_id", "name", "website", "city", "segment", "source", "source_url", "notes"]
CSV_BRANCH_FIELDS = CSV_FIELDS + ["branch"]


@transaction.atomic
def import_candidates(raw, actor):
    if len(raw) > 1_000_000: raise ValidationError("Máximo 1 MB por importación.")
    digest = hashlib.sha256(raw).hexdigest()
    receipt = ImportReceipt.objects.filter(fingerprint=digest).first()
    if receipt: return {**receipt.summary, "repeated": True}
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if reader.fieldnames not in (CSV_FIELDS, CSV_BRANCH_FIELDS): raise ValidationError("Usa las columnas de la plantilla CSV; se acepta también la versión anterior sin sucursal.")
        rows = list(reader)
    except UnicodeError as exc:
        raise ValidationError("El archivo debe estar en UTF-8.") from exc
    if not rows or len(rows) > 500: raise ValidationError("Importa entre 1 y 500 candidatos por lote.")
    summary = {"created": 0, "skipped": 0, "repeated": False, "review_rows": []}
    batch = ResearchBatch.objects.create(key=digest, title=f"CSV {timezone.localdate()}", source="csv", created_by=actor)
    for index, row in enumerate(rows, start=2):
        if None in row or any(v is None for v in row.values()): raise ValidationError(f"Fila {index}: columnas incompletas.")
        domain = domain_for(row["website"])
        row.setdefault("branch", "")
        if row["external_id"] and SalesAccount.objects.filter(pk=row["external_id"]).exists():
            summary["skipped"] += 1
            continue
        if identity_matches({**row, "domain": domain}).exists():
            summary["skipped"] += 1
            summary["review_rows"].append({"row": index, "reason": "Confirmar si es la misma cuenta o una sucursal distinta; no se fusionó.", "candidate": row})
            continue
        # Imports never update confirmed facts, channels, ownership, stage or suppression.
        account = create_account({k: v.strip() for k, v in row.items() if k != "external_id"}, actor, batch=batch)
        audit(account, actor, "imported", batch=batch.key, row=index)
        summary["created"] += 1
    ImportReceipt.objects.create(fingerprint=digest, summary=summary, created_by=actor)
    return summary


def safe_cell(value):
    text = str(value or "")
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text


def export_candidates(accounts):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CSV_BRANCH_FIELDS)
    for account in accounts:
        writer.writerow([safe_cell(getattr(account, "pk" if key == "external_id" else key)) for key in CSV_BRANCH_FIELDS])
    return output.getvalue()
