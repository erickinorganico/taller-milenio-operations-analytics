from uuid import uuid4

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from .access import can, require
from .models import WorkOrder
from .services import add_inspection
from .webforms import InspectionForm


def visible_order(user, pk):
    orders = WorkOrder.objects.all()
    if not can(user, "orders_read_all"):
        orders = orders.filter(assigned_to=user)
    return get_object_or_404(orders, pk=pk)


@require_GET
def inspection_feed(request, pk):
    order = visible_order(request.user, pk)
    if request.GET.get("session") == "1":
        return JsonResponse({"actor": str(request.user.pk), "csrf": get_token(request)})
    items = order.inspections.select_related("created_by").order_by("-pk")
    latest = items.values_list("pk", flat=True).first() or 0
    revision = f"{order.status}-{latest}"
    if request.GET.get("revision") == revision:
        return HttpResponse(status=204)
    html = render_to_string("workshop/inspection_list.html", {"inspections": items}, request=request)
    return JsonResponse({"html": html, "stage": order.status, "revision": revision})


@require("work")
@require_POST
def submit_inspection(request, pk):
    order = visible_order(request.user, pk)
    if request.POST.get("submission_actor", str(request.user.pk)) != str(request.user.pk):
        message = "La cuenta que abrió el formulario cambió. Vuelve a entrar con tu cuenta para guardar el punto."
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"error": message}, status=409)
        return HttpResponse(message, status=409)
    form = InspectionForm(request.POST, request.FILES)
    json_response = request.headers.get("Accept") == "application/json"
    if form.is_valid():
        try:
            inspection = add_inspection(actor=request.user, work_order=order, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            confirmation = f"Inspección guardada en la orden {order.number}."
            if json_response:
                return JsonResponse({"id": inspection.pk, "message": confirmation, "next_key": str(uuid4())})
            messages.success(request, confirmation)
            return redirect(f"/orders/{pk}/#inspection" if form.cleaned_data["submission_key"] else f"/orders/{pk}/")
    problems = []
    for field, errors in form.errors.items():
        label = f"{form.fields[field].label}: " if field in form.fields else ""
        problems.extend(label + error for error in errors)
    if json_response:
        return JsonResponse({"error": " ".join(problems)}, status=400)
    # Native form fallback keeps text and resubmission key; browsers require
    # selecting the file again after a full navigation.
    from .views import order_detail
    return order_detail(request, pk, inspection_form=form)
