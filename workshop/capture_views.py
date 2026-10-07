import hashlib
import mimetypes
import io
import uuid

from django import forms
from django.contrib import messages
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from PIL import Image, ImageOps, ImageDraw, ImageFont

from .access import require, can
from .document_capture import LABELS, export_content
from .models import AuditEvent, DocumentCapture, WorkOrder, Vehicle, Customer


class CaptureUploadForm(forms.Form):
    title = forms.CharField(label="Nombre del documento (opcional)", max_length=160, required=False)
    kind = forms.ChoiceField(label="Qué vas a capturar", choices=[("order", "Orden de trabajo"), ("service", "Hoja de servicio")],required=False)
    provider = forms.ChoiceField(label="Cómo leer la foto", choices=[("codex","GPT Luna · sesión de Codex"),("local","Lectura local de Windows"),("opencode","OpenCode · pendiente de conectar")],required=False)
    photo = forms.ImageField(label="Foto de una hoja", widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp", "capture": "environment"}),
                            help_text="JPEG, PNG o WebP; máximo 5 MB y 20 megapíxeles. Coloca la hoja completa, derecha y con buena luz.")

    def clean_photo(self):
        photo = self.cleaned_data["photo"]
        if photo.size > 5*1024*1024 or photo.image.width*photo.image.height > 20_000_000 or photo.image.format not in {"JPEG", "PNG", "WEBP"}:
            raise forms.ValidationError("Usa JPEG, PNG o WebP de hasta 5 MB y 20 megapíxeles.")
        return photo


class CaptureReviewForm(forms.Form):
    version = forms.IntegerField(widget=forms.HiddenInput)
    order_number = forms.CharField(label=LABELS["order_number"], max_length=40)
    customer_name = forms.CharField(label=LABELS["customer_name"], max_length=200, required=False)
    phone = forms.CharField(label=LABELS["phone"], max_length=40, required=False)
    vehicle_plate = forms.CharField(label=LABELS["vehicle_plate"], max_length=32, required=False)
    vehicle_description = forms.CharField(label=LABELS["vehicle_description"], max_length=200, required=False)
    vehicle_vin = forms.CharField(label="VIN / serie", max_length=32, required=False)
    vehicle_make = forms.CharField(label="Marca (necesaria si el vehículo es nuevo)", max_length=100, required=False)
    vehicle_model = forms.CharField(label="Modelo (necesario si el vehículo es nuevo)", max_length=100, required=False)
    vehicle_year = forms.IntegerField(label="Año", min_value=1886, max_value=timezone.localdate().year+1, required=False)
    odometer = forms.IntegerField(label=LABELS["odometer"], min_value=0, max_value=4294967295, required=False)
    complaint = forms.CharField(label=LABELS["complaint"], max_length=4000, required=False, widget=forms.Textarea(attrs={"rows":3}))
    services = forms.CharField(label=LABELS["services"], max_length=8000, required=False, widget=forms.Textarea(attrs={"rows":5}),
        help_text="Un servicio por renglón. Cantidades, precios y autorizaciones se revisan en la operación del taller.")
    checked = forms.BooleanField(label="Comparé estos datos con la foto y confirmo su revisión")

    def clean(self):
        values = super().clean()
        if not (values.get("complaint") or values.get("services")):
            raise forms.ValidationError("Captura la solicitud u observaciones, o al menos un servicio.")
        return values


class ServiceReviewForm(forms.Form):
    description = forms.CharField(label="Servicio",max_length=250)
    kind = forms.ChoiceField(label="Tipo",choices=[("unknown","Por clasificar"),("labor","Mano de obra"),("service","Servicio"),("part","Refacción")])
    quantity = forms.DecimalField(label="Cantidad",max_digits=12,decimal_places=3,min_value=0.001,required=False)
    unit_price = forms.DecimalField(label="Precio unitario",max_digits=14,decimal_places=2,min_value=0,required=False)
    unit_cost = forms.DecimalField(label="Costo unitario",max_digits=14,decimal_places=2,min_value=0,required=False)
    part_sku = forms.CharField(label="SKU",max_length=80,required=False)


ServiceReviewSet = forms.formset_factory(ServiceReviewForm,extra=0,max_num=50,validate_max=True,absolute_max=50)


class CaptureTargetForm(forms.Form):
    order = forms.ModelChoiceField(label="Orden existente (opcional)",queryset=WorkOrder.objects.all(),required=False)
    vehicle = forms.ModelChoiceField(label="Vehículo existente (opcional)",queryset=Vehicle.objects.select_related("customer"),required=False)
    customer = forms.ModelChoiceField(label="Cliente existente (si hay nombres repetidos)",queryset=Customer.objects.all(),required=False)


def event(user, capture, action, **after):
    AuditEvent.objects.create(actor=user, entity_type="DocumentCapture", entity_id=str(capture.pk), action=action, after=after)


@require("reception")
def capture_index(request):
    form = CaptureUploadForm(request.POST or None, request.FILES or None)
    from .capture_vision import provider_status
    availability = cache.get("capture:codex-availability")
    if availability is None:
        availability = provider_status("codex")
        cache.set("capture:codex-availability",availability,30)
    if not form.is_bound:
        form.initial["provider"] = "codex" if availability["available"] else "local"
    if request.method == "POST" and form.is_valid():
        provider = form.cleaned_data.get("provider") or "local"
        if provider != "local":
            availability = provider_status(provider)
            if not availability["available"]:
                form.add_error("provider",availability["message"])
                return render(request,"workshop/capture_index.html",{"title":"Capturar documentos","section":"Captura de documentos","form":form,"page":Paginator(DocumentCapture.objects.all(),25).get_page(1)})
        photo = form.cleaned_data["photo"]
        digest = hashlib.sha256()
        for chunk in photo.chunks():
            digest.update(chunk)
        photo.seek(0)
        fingerprint = digest.hexdigest()
        existing = DocumentCapture.objects.filter(fingerprint=fingerprint).first()
        if existing:
            messages.info(request, "Esta misma foto ya está en la bandeja. Abrimos el documento existente.")
            return redirect(f"/capture/{existing.pk}/")
        with Image.open(photo) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.thumbnail((3000, 3000))
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=95)
        capture = DocumentCapture(title=form.cleaned_data["title"] or f"Documento · {timezone.localtime():%d/%m %H:%M}", kind=form.cleaned_data["kind"] or "order",
            provider=provider,model_name="gpt-6-luna" if provider == "codex" else "",
            fingerprint=fingerprint, photo=ContentFile(output.getvalue(), name=uuid.uuid4().hex+".jpg"), uploaded_by=request.user)
        try:
            with transaction.atomic():
                capture.save()
                event(request.user, capture, "uploaded", title=capture.title, status=capture.status)
        except IntegrityError:
            # Storage can have saved a file before a concurrent unique violation.
            if capture.photo._committed:
                capture.photo.delete(save=False)
            existing = DocumentCapture.objects.get(fingerprint=fingerprint)
            return redirect(f"/capture/{existing.pk}/")
        messages.success(request, "Foto guardada. La lectura se hará en segundo plano; después podrás corregir los campos.")
        return redirect(f"/capture/{capture.pk}/")
    page = Paginator(DocumentCapture.objects.select_related("uploaded_by", "reviewed_by", "work_order"), 25).get_page(request.GET.get("page"))
    return render(request, "workshop/capture_index.html", {"title":"Capturar documentos", "section":"Captura de documentos", "form":form, "page":page,"reader_status":availability})


@require("reception")
def capture_detail(request, pk):
    capture = get_object_or_404(DocumentCapture.objects.select_related("reviewed_by"), pk=pk)
    form = CaptureReviewForm(request.POST if request.method == "POST" else None, initial={**capture.data, "version":capture.version})
    service_forms = ServiceReviewSet(request.POST if request.method == "POST" and (capture.service_items or "lines-TOTAL_FORMS" in request.POST) else None,prefix="lines",initial=capture.service_items)
    if capture.service_items:
        form.fields["services"].widget = forms.HiddenInput()
        form.fields["services"].required = False
    status = 200
    if request.method == "POST" and form.is_valid() and (not service_forms.is_bound or service_forms.is_valid()):
        with transaction.atomic():
            current = DocumentCapture.objects.select_for_update().get(pk=pk)
            if current.status not in {"review", "confirmed"} or current.version != form.cleaned_data["version"]:
                form.add_error(None, "El documento cambió o sigue en lectura. Actualiza la página antes de confirmar.")
                status = 409
            else:
                current.data = {key:str(form.cleaned_data.get(key, "") or "") for key in LABELS}
                # Zero mileage is a valid confirmed value.
                current.data["odometer"] = "" if form.cleaned_data["odometer"] is None else str(form.cleaned_data["odometer"])
                current.data["vehicle_year"] = "" if form.cleaned_data["vehicle_year"] is None else str(form.cleaned_data["vehicle_year"])
                if service_forms.is_bound:
                    current.service_items = [{key:str(value) if value is not None else None for key,value in values.items()} for values in service_forms.cleaned_data]
                    current.data["services"] = "\n".join(item["description"] for item in current.service_items) if current.service_items else current.data["services"]
                current.status = "confirmed"
                current.reviewed_by, current.reviewed_at = request.user, timezone.now()
                current.version += 1
                current.save(update_fields=["data", "service_items", "status", "reviewed_by", "reviewed_at", "version"])
                event(request.user, current, "confirmed", version=current.version, status=current.status)
                messages.success(request, "Datos revisados. Revisa los cambios para aplicarlos al taller.")
                return redirect(f"/capture/{pk}/")
    return render(request, "workshop/capture_detail.html", {"title":capture.title, "section":"Captura de documentos", "capture":capture, "form":form,"service_forms":service_forms,"target_form":CaptureTargetForm()}, status=status)


@require("reception")
@require_GET
def capture_status(request, pk):
    capture = get_object_or_404(DocumentCapture, pk=pk)
    return JsonResponse({"status":capture.status})


@require("reception")
@require_POST
def capture_retry(request, pk):
    try:
        version = int(request.POST.get("version", "0"))
    except (TypeError, ValueError):
        return HttpResponse("Versión inválida. Actualiza la página.", status=400)
    with transaction.atomic():
        capture = get_object_or_404(DocumentCapture.objects.select_for_update(), pk=pk)
        if capture.status == "review" and capture.version == version:
            capture.status, capture.reading_note = "pending", ""
            capture.version += 1
            capture.save(update_fields=["status", "reading_note", "version"])
            event(request.user, capture, "retry", status="pending")
        else:
            messages.error(request, "La lectura ya está en curso o el documento cambió. Actualiza la página.")
    return redirect(f"/capture/{pk}/")


@require("reception")
@require_POST
def capture_manual(request, pk):
    try:
        version = int(request.POST.get("version", "0"))
    except (TypeError, ValueError):
        return HttpResponse("Versión inválida. Actualiza la página.", status=400)
    with transaction.atomic():
        capture = get_object_or_404(DocumentCapture.objects.select_for_update(), pk=pk)
        if capture.status in {"pending", "reading"} and capture.version == version:
            capture.status, capture.reading_token = "review", ""
            capture.reading_note = "Captura manual: completa los campos comparando con la foto."
            capture.version += 1
            capture.save(update_fields=["status", "reading_token", "reading_note", "version"])
            event(request.user, capture, "manual_capture", status="review")
        else:
            messages.info(request, "El documento ya está listo para revisar o cambió. Revisa su estado actual.")
    return redirect(f"/capture/{pk}/")


@require("reception")
def capture_photo(request, pk):
    capture = get_object_or_404(DocumentCapture, pk=pk)
    response = FileResponse(capture.photo.open("rb"), content_type=mimetypes.guess_type(capture.photo.name)[0] or "application/octet-stream")
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require("reception")
def capture_export(request, pk, format):
    capture = get_object_or_404(DocumentCapture.objects.select_related("reviewed_by"), pk=pk, status__in=["confirmed","applied"])
    if format not in {"csv", "xlsx"}:
        return HttpResponse(status=404)
    content, mime = export_content(capture, format)
    response = HttpResponse(content, content_type=mime)
    response["Content-Disposition"] = f'attachment; filename="milenio-documento-{pk}.{format}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require("reception")
@require_POST
def capture_apply(request, pk):
    from . import capture_application as application
    capture = get_object_or_404(DocumentCapture,pk=pk)
    form = CaptureTargetForm(request.POST)
    if request.POST.get("stage") == "commit":
        try:
            result = application.commit(capture,request.user,request.POST.get("receipt",""))
            messages.success(request,"Captura aplicada: la orden y sus datos ya están actualizados en el taller.")
            return redirect(f"/orders/{result['order_id']}/")
        except ValidationError as error:
            messages.error(request," · ".join(error.messages))
            return redirect(f"/capture/{pk}/")
    if form.is_valid():
        selection = {key:obj.pk for key,obj in form.cleaned_data.items() if obj}
        try:
            plan, receipt = application.preview(capture,request.user,selection)
            return render(request,"workshop/capture_apply.html",{"title":"Aplicar captura al taller","section":"Captura de documentos","capture":capture,"plan":plan,"receipt":receipt})
        except ValidationError as error:
            messages.error(request," · ".join(error.messages))
    else:
        messages.error(request,"Selecciona registros válidos para preparar los cambios.")
    return redirect(f"/capture/{pk}/")


@require("reception")
@require_POST
def capture_example(request):
    if settings.MILENIO_MODE != "demo":
        return HttpResponse(status=404)
    image = Image.new("RGB", (1800, 1500), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=40)
    lines = ["MILENIO - MUESTRA FICTICIA PARA PILOTO", "Orden: PILOTO-DEMO-001", "Cliente: Cliente de ejemplo",
        "Telefono: 0000000000", "Placas: DEMO123", "Vehiculo: Nissan Versa 2020", "Marca: Nissan", "Modelo: Versa", "Ano: 2020", "Kilometraje: 85000",
        "Solicitud: Revision por ruido al frenar", "Servicio: Revision de frenos", "Servicio: Cambio de aceite"]
    for index, line in enumerate(lines):
        draw.text((70, 70+index*95), line, fill="black", font=font)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95)
    content = output.getvalue()
    fingerprint = hashlib.sha256(content).hexdigest()
    with transaction.atomic():
        capture = DocumentCapture.objects.filter(fingerprint=fingerprint).first()
        if not capture:
            capture = DocumentCapture.objects.create(title="Hoja de ejemplo · datos ficticios", kind="order", fingerprint=fingerprint,
                photo=ContentFile(content, name="muestra-piloto.jpg"), uploaded_by=request.user)
            event(request.user, capture, "uploaded", example=True, status=capture.status)
    return redirect(f"/capture/{capture.pk}/")
