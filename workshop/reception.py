from uuid import UUID, uuid4

from django.contrib import messages
from django.core.signing import Signer
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect

from .models import ReceptionReceipt, WorkOrder


def review_open_orders(request, vehicle):
    orders = list(vehicle.work_orders.exclude(
        status__in=(WorkOrder.Status.DELIVERED, WorkOrder.Status.CANCELLED),
    ).only("pk", "number", "status", "complaint").order_by("-pk"))
    if not orders:
        return {}
    ids = ",".join(str(order.pk) for order in orders)
    stamp = Signer(salt="workshop.reception.open-orders").signature(
        f"{request.user.pk}/{request.reception_token}/{vehicle.pk}/{ids}"
    )
    if request.POST.get("confirm_open_orders") == stamp:
        return {}
    return {"vehicle": vehicle, "orders": orders, "stamp": stamp}


def reception_form(request, step, view, *args):
    """Commit the result and its redirect together, including on mobile retries."""
    request.reception_token = uuid4()
    if request.method != "POST" or "reception_token" not in request.POST:
        # Existing clients and pre-update pages use the original POST contract.
        return view(request, *args)

    try:
        request.reception_token = UUID(request.POST["reception_token"])
    except ValueError:
        return HttpResponseBadRequest("Vuelve a abrir el formulario de recepción.")

    with transaction.atomic():
        receipt, first = ReceptionReceipt.objects.get_or_create(
            token=request.reception_token,
            defaults={"actor": request.user, "step": step},
        )
        if not first:
            if receipt.actor_id != request.user.pk or receipt.step != step:
                return HttpResponseBadRequest("Vuelve a abrir el formulario con tu cuenta.")
            messages.info(request, "Este formulario ya se guardó. Se abrió el resultado original.")
            return redirect(receipt.next_url)

        response = view(request, *args)
        if response.status_code == 302:
            receipt.next_url = response.url
            receipt.save(update_fields=["next_url"])
        else:
            # Validation errors keep the form and token available for correction.
            receipt.delete()
        return response
