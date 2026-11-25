"""Scoped machine access to workshop aggregates and the history of one order."""
import hashlib
import json
from uuid import UUID

from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from commercial.agent_models import AgentCredential, AgentRequest
from workshop.access import can
from workshop.models import AuditEvent, WorkOrder


SUMMARY_SCOPE = "workshop.summary"
ORDER_PREFIX = "workshop.note:"
MAX_BYTES = 8192
CLOSED = (WorkOrder.Status.DELIVERED, WorkOrder.Status.CANCELLED)


def summary():
    now = timezone.now()
    rows = WorkOrder.objects.values("status").annotate(
        total=Count("pk"), overdue=Count("pk", filter=Q(promised_at__lt=now) & ~Q(status__in=CLOSED)),
        unassigned=Count("pk", filter=Q(assigned_to__isnull=True) & ~Q(status__in=CLOSED)),
    )
    by_status = dict.fromkeys(WorkOrder.Status.values, 0)
    overdue = unassigned = 0
    for row in rows:
        if row["status"] in by_status:
            by_status[row["status"]] = row["total"]
        overdue += row["overdue"]
        unassigned += row["unassigned"]
    return {"as_of": now.isoformat(), "by_status": by_status,
            "open_overdue": overdue, "open_unassigned": unassigned}


def active_credential(token_hash):
    credential = AgentCredential.objects.filter(
        token_hash=token_hash, revoked=False, expires_at__gt=timezone.now(), owner__is_active=True,
    ).select_related("owner").first()
    if credential and can(credential.owner, "manage"):
        return credential
    return None


def error(code, status):
    return JsonResponse({"error": code}, status=status)


@transaction.atomic
def append_note(token_hash, order_id, data):
    # SQLite BEGIN IMMEDIATE orders concurrent notes, human updates and revocations.
    # Recheck authorization inside the transaction before reading a receipt or writing.
    credential = active_credential(token_hash)
    if not credential or credential.scopes != [f"{ORDER_PREFIX}{order_id}"]:
        return error("unauthorized", 401)
    try:
        request_id = UUID(str(data["request_id"]))
    except ValueError:
        return error("invalid_request_id", 400)
    note = data["note"]
    version = data["expected_version"]
    if (not isinstance(note, str) or not note.strip() or len(note) > 500
            or any(ord(char) < 32 and char != "\n" for char in note)
            or any(0xD800 <= ord(char) <= 0xDFFF for char in note)
            or type(version) is not int or version < 1):
        return error("invalid_note_or_version", 400)
    payload_hash = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    previous = AgentRequest.objects.filter(credential=credential, request_id=request_id).first()
    if previous:
        if previous.payload_hash != payload_hash:
            return error("request_id_conflict", 409)
        return JsonResponse(previous.result)
    order = WorkOrder.objects.select_for_update().filter(pk=order_id).first()
    if not order:
        return error("order_not_found", 404)
    if order.version != version:
        return error("stale_version", 409)
    if order.status in CLOSED:
        return error("order_closed", 409)
    order.version += 1
    order.save(update_fields=["version", "updated_at"])
    event = AuditEvent.objects.create(
        actor=credential.owner, entity_type="WorkOrder", entity_id=str(order.pk), action="agent_note",
        before={"version": version},
        after={"version": order.version, "note": note.strip(), "credential_id": str(credential.pk),
               "label": credential.label, "request_id": str(request_id)},
    )
    result = {"order_id": order.pk, "version": order.version, "event_id": event.pk, "request_id": str(request_id)}
    AgentRequest.objects.create(credential=credential, request_id=request_id, payload_hash=payload_hash, result=result)
    return JsonResponse(result)


@csrf_exempt
def endpoint(request):
    # This endpoint never authorizes browser sessions. The commercial endpoint stays closed in cloud.
    if request.method != "POST":
        response = error("post_required", 405)
        response["Allow"] = "POST"
        return response
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme != "Bearer" or not 32 <= len(token) <= 128:
        return error("unauthorized", 401)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    credential = active_credential(token_hash)
    if not credential:
        return error("unauthorized", 401)
    if request.content_type != "application/json":
        return error("json_required", 415)
    body = request.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        return error("payload_too_large", 413)
    try:
        data = json.loads(body)
    except (ValueError, RecursionError):
        return error("invalid_json", 400)
    if not isinstance(data, dict):
        return error("invalid_payload", 400)
    action = data.get("action")
    scopes = credential.scopes
    if action == "workshop.summary" and scopes == [SUMMARY_SCOPE]:
        return JsonResponse(summary()) if set(data) == {"action"} else error("invalid_fields", 400)
    if (action not in ("order.status", "order.note") or not isinstance(scopes, list) or len(scopes) != 1
            or not isinstance(scopes[0], str) or not scopes[0].startswith(ORDER_PREFIX)):
        return error("forbidden", 403)
    order_id = scopes[0][len(ORDER_PREFIX):]
    if not order_id.isascii() or not order_id.isdigit() or len(order_id) > 18:
        return error("forbidden", 403)
    if action == "order.status":
        if set(data) != {"action"}:
            return error("invalid_fields", 400)
        order = WorkOrder.objects.filter(pk=order_id).values("pk", "version", "status").first()
        if not order:
            return error("order_not_found", 404)
        return JsonResponse({"order_id": order["pk"], "version": order["version"], "status": order["status"]})
    if set(data) != {"action", "request_id", "note", "expected_version"}:
        return error("invalid_fields", 400)
    return append_note(token_hash, int(order_id), data)
