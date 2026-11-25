from uuid import UUID, uuid4

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect

from .models import ReceptionReceipt


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
