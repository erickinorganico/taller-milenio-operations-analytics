"""Authenticated read surfaces and explicitly permissioned write workflows."""
import csv
import io
import json
import mimetypes
import uuid
from decimal import Decimal
from pathlib import Path
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum, F
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from . import models as m, services as s
from .access import can, require, ROLES
from .catalog import CATALOG, SOURCE_MODELS, SOURCE_TITLES
from .webforms import LABELS, SetupForm, TeamForm, TeamEditForm, MoneyLineForm, PaymentForm, InspectionForm, model_form

def fail(request, exc):
    messages.error(request, " · ".join(exc.messages) if isinstance(exc, ValidationError) else "No se pudo guardar: el registro ya existe o cambió. Actualiza la página e inténtalo otra vez.")

def snapshot(obj):
    return {f.name:str(getattr(obj, f.attname)) if getattr(obj, f.attname) is not None else None for f in obj._meta.fields}

def audit(actor, obj, action, before=None):
    m.AuditEvent.objects.create(actor=actor, entity_type=type(obj).__name__, entity_id=str(obj.pk), action=action, before=before or {}, after=snapshot(obj))

def role_check(request, capability):
    if not can(request.user, capability):
        raise PermissionDenied("Tu rol no permite esta acción.")

def setup(request):
    if request.META.get("REMOTE_ADDR") not in {"127.0.0.1", "::1"}:
        raise PermissionDenied("La configuración inicial se realiza desde este equipo.")
    form = SetupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            if User.objects.filter(is_superuser=True, is_active=True).exists():
                return redirect("/login/")
            user = form.save(commit=False)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            for name in ROLES:
                Group.objects.get_or_create(name=name)
            user.groups.add(Group.objects.get(name="manager"))
        login(request,user)
        messages.success(request,"Tu instalación está lista. Comienza por registrar clientes y vehículos, o agrega integrantes al equipo.")
        return redirect("/")
    return render(request,"workshop/login.html",{"title":"Prepara tu taller", "intro":"Crea el acceso de gerencia para esta instalación.", "form":form, "setup":True,"submit":"Crear mi acceso"})

def sign_in(request):
    if request.user.is_authenticated:
        return redirect("/")
    form = AuthenticationForm(request, data=request.POST or None)
    key = "login:" + request.META.get("REMOTE_ADDR", "unknown")
    if request.method == "POST":
        attempts = cache.get(key,0)
        if attempts >= 10:
            form.add_error(None,"Demasiados intentos. Espera cinco minutos antes de volver a intentar.")
        elif form.is_valid():
            cache.delete(key)
            login(request,form.get_user())
            return redirect("/")
        else:
            cache.set(key,attempts+1,300)
    return render(request,"workshop/login.html",{"title":"Bienvenido de vuelta", "intro":"Ingresa con tu cuenta del taller.", "form":form})

def static_asset(request, path):
    allowed = {"workshop/app.css":"text/css", "workshop/app.js":"text/javascript"}
    if path not in allowed:
        raise Http404
    filename = Path(__file__).parent / "static" / path
    return FileResponse(filename.open("rb"), content_type=allowed[path])

def home(request):
    orders = m.WorkOrder.objects.select_related("vehicle__customer","assigned_to").exclude(status__in=["delivered","cancelled"])
    if not can(request.user,"orders_read_all"):
        orders = orders.filter(assigned_to=request.user)
    today = timezone.localdate()
    invoices = m.Invoice.objects.filter(voided_at__isnull=True)
    balance = (invoices.aggregate(v=Sum("total"))["v"] or 0) - (m.Payment.objects.filter(invoice__voided_at__isnull=True).aggregate(v=Sum("amount"))["v"] or 0)
    return render(request,"workshop/home.html",{"title":"Hoy en el taller", "orders":orders.order_by("promised_at","created_at")[:12], "open_count":orders.count(), "late_count":orders.filter(promised_at__lt=timezone.now()).count(), "ready_count":orders.filter(status="ready").count(), "balance":balance,"appointments":m.Appointment.objects.select_related("vehicle__customer").filter(scheduled_at__date=today).order_by("scheduled_at") if can(request.user,"office_read") else [],"low_parts":m.Part.objects.filter(stock__lte=F("reserved")+F("reorder_point"))[:5],"tasks":m.ActionTask.objects.exclude(status__in=["completed","dismissed"]).filter(**({} if can(request.user,"review") else {"assigned_to":request.user})).select_related("assigned_to")[:5],"pending_proposals":m.Proposal.objects.filter(status="pending").count() if can(request.user,"intelligence_read") else 0})

def records(request, key):
    if key not in CATALOG:
        raise Http404
    model,title,fields,capability = CATALOG[key]
    role_check(request,"stock_read" if key in {"parts","suppliers","purchases"} and can(request.user,"stock") else "office_read")
    query = request.GET.get("q", "").strip()[:200]
    qs = model.objects.all().order_by("-pk")
    qs = search(qs,query)
    page = Paginator(qs,25).get_page(request.GET.get("page"))
    columns = [LABELS.get(f,f) for f in fields]
    rows=[]
    for obj in page:
        cells=[{"text":getattr(obj,f),"status":getattr(obj,f) if f=="status" else ""} for f in fields]
        if key=="purchases":
            cells[1]["url"] = f"/purchases/{obj.pk}/"
        rows.append({"cells":cells,"edit_url":f"/records/{key}/{obj.pk}/edit/"})
    subnav=[]
    if key in {"customers","vehicles","appointments"}:
        subnav=[{"label":label,"url":f"/records/{k}/"} for k,label in [("customers","Clientes"),("vehicles","Vehículos"),("appointments","Agenda")]]
    return render(request,"workshop/table.html",{"title":title,"section":"Operación","intro":"Registros compartidos por el equipo del taller.","columns":columns,"rows":rows,"count":qs.count(),"page":page,"query":query,"editable":can(request.user,capability),"create_url":f"/records/{key}/new/" if can(request.user,capability) else None,"export_url":f"/data/{key}/?export=csv","subnav":subnav})

def search(qs, query):
    if not query:
        return qs
    conditions=Q(pk=int(query)) if query.isdigit() else Q(pk__in=[])
    for field in qs.model._meta.fields:
        if field.get_internal_type() in {"CharField","TextField","EmailField"}:
            conditions |= Q(**{field.name+"__icontains":query})
    return qs.filter(conditions)

def edit_record(request,key,pk=None):
    if key not in CATALOG:
        raise Http404
    model,title,fields,capability=CATALOG[key]
    role_check(request,capability)
    obj=get_object_or_404(model,pk=pk) if pk else None
    before=snapshot(obj) if obj else None
    form=model_form(model,["supplier","number"] if key=="purchases" else fields,request.POST or None,instance=obj)
    if key=="vehicles" and request.GET.get("customer"):
        form.initial["customer"]=request.GET["customer"]
    if key=="contracts":
        form.fields["customer"].queryset=m.Customer.objects.filter(kind="fleet")
    if request.method=="POST" and form.is_valid():
        try:
            with transaction.atomic():
                if key=="purchases" and not pk:
                    record=s.create_purchase_order(actor=request.user,**form.cleaned_data)
                    messages.success(request,"Compra en borrador. Agrega las refacciones y confirma el pedido.")
                    return redirect(f"/purchases/{record.pk}/")
                record=form.save(commit=False)
                if key=="vehicles":
                    record.vin=record.vin.strip().upper() if record.vin else None
                    record.plate=record.plate.strip().upper()
                    if not record.vin and not record.plate:
                        raise ValidationError("Registra placas o VIN para identificar el vehículo.")
                    if pk:
                        previous=m.Vehicle.objects.select_for_update().get(pk=pk)
                        has_history=any(model.objects.filter(vehicle_id=pk).exists() for model in (m.WorkOrder,m.Appointment,m.MaintenancePlan,m.TowService))
                        if has_history and (record.customer_id!=previous.customer_id or record.vin!=previous.vin):
                            raise ValidationError("Este vehículo ya tiene historial. No se puede cambiar su cliente ni VIN desde el catálogo; conserva la identidad del expediente.")
                if key=="customers" and pk and record.kind!="fleet" and m.FleetContract.objects.filter(customer_id=pk).exists():
                    raise ValidationError("El cliente tiene contratos de flotilla. Conserva su tipo para proteger el historial.")
                if key=="parts" and any(getattr(record,n)<0 for n in ["cost","sale_price","reorder_point"]):
                    raise ValidationError("Costos, precios y punto de reposición deben ser positivos o cero.")
                if key=="contracts" and (record.end_date<record.start_date or record.monthly_fee<0):
                    raise ValidationError("Revisa el periodo y el importe del contrato.")
                if key=="maintenance":
                    if not record.due_date and record.due_odometer is None:
                        raise ValidationError("Indica una fecha o kilometraje de mantenimiento.")
                    if record.work_order and record.work_order.vehicle_id!=record.vehicle_id:
                        raise ValidationError("La orden debe corresponder al mismo vehículo.")
                    if record.status=="completed" and (not record.work_order or record.work_order.status!="delivered"):
                        raise ValidationError("Para completar mantenimiento vincula una orden entregada.")
                if key=="purchases" and pk and m.PurchaseOrder.objects.select_for_update().get(pk=pk).status!="draft":
                    raise ValidationError("Solo se edita una compra en borrador; una compra confirmada se administra desde su detalle.")
                record.full_clean()
                record.save()
                audit(request.user,record,"updated" if pk else "created",before)
            messages.success(request,"Registro guardado.")
            return redirect(f"/records/{key}/")
        except (ValidationError,IntegrityError) as exc:
            form.add_error(None," · ".join(exc.messages) if isinstance(exc,ValidationError) else "Ese registro ya existe.")
    return render(request,"workshop/form.html",{"title":("Editar · " if pk else "Nuevo · ")+title,"section":"Captura","form":form,"back":f"/records/{key}/"})

def orders(request):
    qs=m.WorkOrder.objects.select_related("vehicle__customer","assigned_to").order_by("-created_at")
    if not can(request.user,"orders_read_all"):
        qs=qs.filter(assigned_to=request.user)
    query=request.GET.get("q","").strip()[:200]
    if query:
        qs=qs.filter(Q(number__icontains=query)|Q(vehicle__plate__icontains=query)|Q(vehicle__customer__name__icontains=query))
    selected=request.GET.get("status","")
    if selected in m.WorkOrder.Status.values:
        qs=qs.filter(status=selected)
    if request.GET.get("mine")=="1":
        qs=qs.filter(assigned_to=request.user)
    page=Paginator(qs,25).get_page(request.GET.get("page"))
    rows=[{"cells":[{"text":o.number,"url":f"/orders/{o.pk}/"},{"text":o.vehicle},{"text":o.vehicle.customer.name},{"text":o.status,"status":o.status},{"text":o.assigned_to.get_full_name() or o.assigned_to.username if o.assigned_to else "Sin asignar"},{"text":o.promised_at}]} for o in page]
    return render(request,"workshop/table.html",{"title":"Órdenes de trabajo","intro":"Cada vehículo, su responsable y el siguiente paso.","section":"Taller","columns":["Orden","Vehículo","Cliente","Etapa","Responsable","Entrega prometida"],"rows":rows,"count":qs.count(),"page":page,"query":query,"create_url":"/orders/new/" if can(request.user,"reception") else None,"create_label":"Recibir vehículo","subnav":[{"label":"Todas","url":"/orders/"},{"label":"Mis órdenes","url":"/orders/?mine=1"},{"label":"Por autorizar","url":"/orders/?status=awaiting_approval"},{"label":"En trabajo","url":"/orders/?status=in_progress"},{"label":"Listas","url":"/orders/?status=ready"}]})

@require("reception")
def new_order(request):
    form=model_form(m.WorkOrder,["vehicle","complaint","assigned_to","promised_at","odometer"],request.POST or None)
    form.fields["assigned_to"].queryset=User.objects.filter(is_active=True).filter(Q(is_superuser=True)|Q(groups__name__in=["technician","manager","advisor"])).distinct()
    if request.GET.get("vehicle"):
        form.initial["vehicle"]=request.GET["vehicle"]
    if request.method=="POST" and form.is_valid():
        try:
            order=s.create_work_order(actor=request.user,**form.cleaned_data)
            messages.success(request,f"{order.number}: vehículo recibido.")
            return redirect(f"/orders/{order.pk}/")
        except (ValidationError,IntegrityError) as exc:
            fail(request,exc)
    return render(request,"workshop/form.html",{"title":"Recibir un vehículo","intro":"Selecciona el vehículo, registra la solicitud y asigna responsable. Si es nuevo, créalo primero en Clientes y vehículos.","form":form,"back":"/orders/","submit":"Crear orden"})

def order_detail(request,pk):
    order=get_object_or_404(m.WorkOrder.objects.select_related("vehicle__customer","assigned_to"),pk=pk)
    if not can(request.user,"orders_read_all") and order.assigned_to_id!=request.user.pk:
        raise Http404
    quotes=list(order.quotes.prefetch_related("lines").order_by("-version"))
    for quote in quotes:
        quote.subtotal=sum((line.quantity*line.unit_price for line in quote.lines.all()),Decimal("0"))
        quote.total=(quote.subtotal*(1+quote.tax_rate)).quantize(Decimal("0.01"))
    invoice=m.Invoice.objects.filter(work_order=order,voided_at__isnull=True).first()
    paid=invoice.payments.aggregate(v=Sum("amount"))["v"] or Decimal("0") if invoice else Decimal("0")
    assignment=model_form(m.WorkOrder,["assigned_to","promised_at"],instance=order)
    assignment.fields["assigned_to"].queryset=User.objects.filter(is_active=True).filter(Q(is_superuser=True)|Q(groups__name__in=["technician","manager","advisor"])).distinct()
    events=m.AuditEvent.objects.filter(Q(entity_type="WorkOrder",entity_id=str(pk))|Q(after__work_order=pk)|Q(after__work_order_id=pk)).select_related("actor").order_by("-created_at")[:30]
    return render(request,"workshop/order.html",{"title":order.number,"section":"Órdenes","order":order,"quotes":quotes,"invoice":invoice,"paid":paid,"balance":invoice.total-paid if invoice else None,"inspection_form":InspectionForm(),"line_form":MoneyLineForm(),"assignment_form":assignment,"payment_form":PaymentForm(initial={"idempotency_key":str(uuid.uuid4())}),"parts":m.Part.objects.all(),"reservations":order.reservations.select_related("part"),"inspections":order.inspections.order_by("-created_at"),"time_entries":order.time_entries.select_related("technician").order_by("-created_at"),"quality_checks":order.quality_checks.order_by("-created_at"),"events":events,"next_statuses":sorted(state for state in s.TRANSITIONS.get(order.status,set()) if can(request.user,"reception") or state not in {"delivered","cancelled"}),"stages":m.WorkOrder.Status.choices})

@require_POST
def order_action(request,pk,action):
    order=get_object_or_404(m.WorkOrder,pk=pk)
    capabilities={"transition":"work","assign":"reception","inspection":"work","new-quote":"reception","quote-line":"reception","send-quote":"reception","approve-quote":"reception","reject-quote":"reception","reserve":"stock","consume":"stock","release":"stock","return":"stock","time":"work","quality":"work","invoice":"finance","payment":"finance"}
    if action not in capabilities:
        raise Http404
    role_check(request,capabilities[action])
    try:
        if action=="transition":
            status=request.POST.get("status")
            if status in {"delivered","cancelled"}:
                role_check(request,"reception")
            s.transition_work_order(actor=request.user,work_order=order,status=status,expected_version=int(request.POST.get("version",0)))
        elif action=="assign":
            form=model_form(m.WorkOrder,["assigned_to","promised_at"],request.POST,instance=order)
            form.fields["assigned_to"].queryset=User.objects.filter(is_active=True).filter(Q(is_superuser=True)|Q(groups__name__in=["technician","manager","advisor"])).distinct()
            if not form.is_valid():
                raise ValidationError(form.errors.as_text())
            with transaction.atomic():
                current=m.WorkOrder.objects.select_for_update().get(pk=pk)
                before=snapshot(current)
                current.assigned_to=form.cleaned_data["assigned_to"]
                current.promised_at=form.cleaned_data["promised_at"]
                current.version+=1
                current.save(update_fields=["assigned_to","promised_at","version","updated_at"])
                audit(request.user,current,"assignment",before)
        elif action=="inspection":
            form=InspectionForm(request.POST,request.FILES)
            if not form.is_valid():
                raise ValidationError(form.errors.as_text())
            s.add_inspection(actor=request.user,work_order=order,**form.cleaned_data)
        elif action=="new-quote":
            s.create_quote(actor=request.user,work_order=order,tax_rate=request.POST.get("tax_rate","0"))
        elif action in {"quote-line","send-quote","approve-quote","reject-quote"}:
            quote=get_object_or_404(m.Quote,pk=request.POST.get("quote"),work_order=order)
            if action=="quote-line":
                form=MoneyLineForm(request.POST)
                if not form.is_valid():
                    raise ValidationError(form.errors.as_text())
                s.add_quote_line(actor=request.user,quote=quote,**form.cleaned_data)
            elif action=="send-quote":
                s.send_quote(actor=request.user,quote=quote)
            elif action=="approve-quote":
                s.approve_quote(actor=request.user,quote=quote,approval_name=request.POST.get("approval_name"),approval_reference=request.POST.get("approval_reference"))
            else:
                s.reject_quote(actor=request.user,quote=quote,reason=request.POST.get("reason",""))
        elif action=="reserve":
            s.reserve_part(actor=request.user,work_order=order,part=get_object_or_404(m.Part,pk=request.POST.get("part")),quantity=request.POST.get("quantity"))
        elif action in {"consume","release","return"}:
            reservation=get_object_or_404(m.Reservation,pk=request.POST.get("reservation"),work_order=order)
            fn={"consume":s.consume_reservation,"release":s.release_reservation,"return":s.return_consumed_part}[action]
            fn(actor=request.user,reservation=reservation,quantity=request.POST.get("quantity"))
        elif action=="time":
            s.add_time_entry(actor=request.user,work_order=order,minutes=int(request.POST.get("minutes",0)),notes=request.POST.get("notes",""))
        elif action=="quality":
            s.record_quality_check(actor=request.user,work_order=order,result=request.POST.get("result"),notes=request.POST.get("notes",""))
        elif action=="invoice":
            date_field=forms.DateTimeField()
            due_at=date_field.clean(request.POST.get("due_at"))
            s.issue_invoice(actor=request.user,work_order=order,number=request.POST.get("number"),due_at=due_at)
        elif action=="payment":
            form=PaymentForm(request.POST)
            if not form.is_valid():
                raise ValidationError(form.errors.as_text())
            s.record_payment(actor=request.user,invoice=get_object_or_404(m.Invoice,work_order=order,voided_at__isnull=True),**form.cleaned_data)
        messages.success(request,"Cambio guardado en la orden y su bitácora.")
    except (ValidationError,IntegrityError,ValueError,TypeError) as exc:
        fail(request,exc)
    return redirect(f"/orders/{pk}/")

def inspection_photo(request,pk):
    obj=get_object_or_404(m.Inspection,pk=pk)
    if not can(request.user,"orders_read_all") and obj.work_order.assigned_to_id!=request.user.pk:
        raise Http404
    if not obj.photo:
        raise Http404
    return FileResponse(obj.photo.open("rb"),content_type=mimetypes.guess_type(obj.photo.name)[0] or "application/octet-stream")

@require("stock_read")
def inventory(request):
    return render(request,"workshop/inventory.html",{"title":"Refacciones","section":"Inventario","parts":m.Part.objects.all().order_by("sku"),"purchases":m.PurchaseOrder.objects.select_related("supplier").order_by("-created_at")[:12],"movements":m.StockMovement.objects.select_related("part","created_by").order_by("-created_at")[:15]})

@require("stock")
@require_POST
def stock_adjust(request,pk):
    try:
        s.adjust_stock(actor=request.user,part=get_object_or_404(m.Part,pk=pk),quantity=request.POST.get("quantity"),reason=request.POST.get("reason"))
        messages.success(request,"Ajuste registrado con su motivo.")
    except (ValidationError,IntegrityError) as exc:
        fail(request,exc)
    return redirect("/inventory/")

@require("orders_read_all")
def purchase_detail(request,pk):
    purchase=get_object_or_404(m.PurchaseOrder.objects.select_related("supplier"),pk=pk)
    form=model_form(m.PurchaseLine,["part","quantity","unit_cost"],request.POST or None)
    if request.method=="POST":
        role_check(request,"stock")
        if form.is_valid():
            try:
                s.add_purchase_line(actor=request.user,purchase_order=purchase,**form.cleaned_data)
                return redirect(f"/purchases/{pk}/")
            except (ValidationError,IntegrityError) as exc:
                fail(request,exc)
    return render(request,"workshop/purchase.html",{"title":purchase.number,"purchase":purchase,"lines":purchase.lines.select_related("part"),"form":form})

@require("stock")
@require_POST
def place_purchase(request,pk):
    try:
        s.place_purchase_order(actor=request.user,purchase_order=get_object_or_404(m.PurchaseOrder,pk=pk))
        messages.success(request,"Pedido confirmado. Registra cada recepción cuando lleguen las piezas.")
    except (ValidationError,IntegrityError) as exc:
        fail(request,exc)
    return redirect(f"/purchases/{pk}/")

@require("stock")
@require_POST
def receive_purchase(request,pk):
    line=get_object_or_404(m.PurchaseLine,pk=pk)
    try:
        s.receive_purchase_line(actor=request.user,line=line,quantity=request.POST.get("quantity"),reference=request.POST.get("reference",""))
        messages.success(request,"Recepción registrada; existencias actualizadas.")
    except (ValidationError,IntegrityError) as exc:
        fail(request,exc)
    return redirect(f"/purchases/{line.purchase_order_id}/")

@require("finance_read")
def finance(request):
    invoices=list(m.Invoice.objects.filter(voided_at__isnull=True).select_related("work_order__vehicle__customer").prefetch_related("payments").order_by("-issued_at"))
    for invoice in invoices:
        invoice.paid=sum((p.amount for p in invoice.payments.all()),Decimal("0"))
        invoice.balance=invoice.total-invoice.paid
    return render(request,"workshop/finance.html",{"title":"Caja y cobranza","section":"Administración","invoices":invoices,"payments":m.Payment.objects.select_related("invoice__work_order").order_by("-received_at")[:30],"total":sum((i.total for i in invoices),Decimal("0")),"paid":sum((i.paid for i in invoices),Decimal("0")),"balance":sum((i.balance for i in invoices),Decimal("0")),"overdue":sum((i.balance for i in invoices if i.due_at<timezone.now()),Decimal("0"))})

@require("office_read")
def fleets(request):
    return render(request,"workshop/fleets.html",{"title":"Flotillas","section":"Clientes empresariales","contracts":m.FleetContract.objects.select_related("customer").order_by("end_date"),"plans":m.MaintenancePlan.objects.select_related("vehicle__customer","work_order").order_by("due_date"),"today":timezone.localdate()})

@require("office_read")
def towing(request):
    return render(request,"workshop/towing.html",{"title":"Servicios de grúa","section":"Asistencia","tows":m.TowService.objects.select_related("customer","vehicle").order_by("-requested_at"),"statuses":m.TowService.Status.choices})

@require("reception")
def new_tow(request):
    form=model_form(m.TowService,["customer","vehicle","origin","destination","notes"],request.POST or None)
    if request.method=="POST" and form.is_valid():
        try:
            s.create_tow_service(actor=request.user,**form.cleaned_data)
            messages.success(request,"Solicitud de grúa registrada.")
            return redirect("/towing/")
        except (ValidationError,IntegrityError) as exc:
            fail(request,exc)
    return render(request,"workshop/form.html",{"title":"Registrar solicitud de grúa","form":form,"back":"/towing/"})

@require("reception")
@require_POST
def tow_action(request,pk):
    try:
        s.transition_tow_service(actor=request.user,tow_service=get_object_or_404(m.TowService,pk=pk),status=request.POST.get("status"),operator_name=request.POST.get("operator_name",""),safety_reference=request.POST.get("safety_reference",""))
        messages.success(request,"Hito de servicio registrado.")
    except (ValidationError,IntegrityError) as exc:
        fail(request,exc)
    return redirect("/towing/")

@require("data_read")
def data_index(request):
    return render(request,"workshop/data.html",{"title":"Fuentes de datos","section":"Datos","sources":[{"key":key,"title":SOURCE_TITLES[key],"count":model.objects.count(),"table":model._meta.db_table,"columns":len(model._meta.fields)} for key,model in SOURCE_MODELS.items()]})

@require("data_read")
def data_table(request,key):
    if key not in SOURCE_MODELS:
        raise Http404
    model=SOURCE_MODELS[key]
    fields=[f for f in model._meta.fields]
    query=request.GET.get("q","")[:200]
    qs=search(model.objects.all().order_by("-pk"),query)
    if request.GET.get("id","").isdigit():
        qs=qs.filter(pk=int(request.GET["id"]))
    if request.GET.get("export")=="csv":
        response=HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"]=f'attachment; filename="milenio-{key}.csv"'
        response.write("\ufeff")
        writer=csv.writer(response)
        writer.writerow([f.name for f in fields])
        for obj in qs.iterator():
            row=[]
            for field in fields:
                value=getattr(obj,field.attname)
                text=json.dumps(value,ensure_ascii=False,cls=DjangoJSONEncoder) if isinstance(value,(dict,list)) else str(value) if value is not None else ""
                if text.lstrip().startswith(("=","+","-","@","\t","\r")):
                    text="'"+text
                row.append(text)
            writer.writerow(row)
        return response
    page=Paginator(qs,25).get_page(request.GET.get("page"))
    rows=[]
    reverse={value:key for key,value in SOURCE_MODELS.items()}
    for obj in page:
        cells=[]
        for field in fields:
            raw=getattr(obj,field.attname)
            text=json.dumps(raw,ensure_ascii=False,cls=DjangoJSONEncoder) if isinstance(raw,(dict,list)) else raw
            cell={"text":text}
            if field.is_relation and field.related_model in reverse and raw:
                cell["url"]=f"/data/{reverse[field.related_model]}/?id={raw}"
            if field.name=="number" and model is m.WorkOrder:
                cell["url"]=f"/orders/{obj.pk}/"
            cells.append(cell)
        rows.append({"cells":cells})
    return render(request,"workshop/table.html",{"title":SOURCE_TITLES[key],"section":"Fuentes de datos","intro":f"Tabla: {model._meta.db_table}. Registros de esta instalación; relaciones navegables por identificador.","columns":[f.name for f in fields],"rows":rows,"count":qs.count(),"page":page,"query":query,"export_url":f"?q={query}&export=csv"})

@require("manage")
def team(request):
    form=TeamForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        with transaction.atomic():
            user=form.save()
            group,_=Group.objects.get_or_create(name=form.cleaned_data["role"])
            user.groups.add(group)
            m.AuditEvent.objects.create(actor=request.user,entity_type="User",entity_id=str(user.pk),action="account_created",after={"username":user.username,"role":form.cleaned_data["role"],"active":True})
        messages.success(request,"Cuenta creada. Comparte la contraseña con su titular por un canal privado.")
        return redirect("/team/")
    return render(request,"workshop/team.html",{"title":"Equipo y acceso","section":"Configuración","form":form,"members":User.objects.all().prefetch_related("groups")})

def guide(request):
    return render(request,"workshop/guide.html",{"title":"Guía del taller","section":"Ayuda"})

def health(request):
    return JsonResponse({"status":"ok","application":"milenio-operations"})


@require("manage")
def edit_team(request, pk):
    member = get_object_or_404(User, pk=pk)
    if member.is_superuser and not request.user.is_superuser:
        raise PermissionDenied("Solo el titular administrador puede modificar esta cuenta.")
    if not member.has_usable_password() and member.username == "demo_admin":
        raise PermissionDenied("La cuenta técnica de la semilla permanece deshabilitada.")
    initial = {"first_name":member.first_name, "role":member.groups.values_list("name", flat=True).first() or "viewer", "is_active":member.is_active}
    form = TeamEditForm(request.POST or None, member=member, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                current = User.objects.select_for_update().get(pk=member.pk)
                active = form.cleaned_data["is_active"]
                if not active and (current.pk == request.user.pk or current.is_superuser):
                    raise ValidationError("Tu sesión y el acceso administrador deben permanecer activos.")
                before = {"username":current.username, "role":list(current.groups.values_list("name", flat=True)), "active":current.is_active}
                current.first_name = form.cleaned_data["first_name"]
                current.is_active = active
                changed_password = bool(form.cleaned_data["password1"])
                if changed_password:
                    current.set_password(form.cleaned_data["password1"])
                current.save()
                group, _ = Group.objects.get_or_create(name=form.cleaned_data["role"])
                current.groups.set([group])
                m.AuditEvent.objects.create(actor=request.user,entity_type="User",entity_id=str(current.pk),action="account_updated",before=before,after={"username":current.username,"role":group.name,"active":active,"password_changed":changed_password})
            if changed_password and current.pk == request.user.pk:
                update_session_auth_hash(request,current)
            messages.success(request,"Acceso actualizado. Las cuentas desactivadas conservan su historial.")
            return redirect("/team/")
        except ValidationError as exc:
            form.add_error(None,exc)
    return render(request,"workshop/form.html",{"title":"Acceso de " + member.username,"form":form,"back":"/team/"})


def account(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request,user)
        m.AuditEvent.objects.create(actor=user,entity_type="User",entity_id=str(user.pk),action="password_changed",after={"username":user.username})
        messages.success(request,"Contraseña actualizada.")
        return redirect("/")
    return render(request,"workshop/form.html",{"title":"Cambiar mi contraseña","form":form,"back":"/","submit":"Actualizar contraseña"})


@require("office_read")
def document(request, kind, pk):
    if kind not in {"quote", "invoice"}:
        raise Http404
    invoice = None
    if kind == "invoice":
        role_check(request,"finance_read")
        invoice = get_object_or_404(m.Invoice.objects.select_related("work_order__vehicle__customer"),pk=pk)
        order = invoice.work_order
        quote = order.quotes.filter(status="approved").first()
    else:
        quote = get_object_or_404(m.Quote.objects.select_related("work_order__vehicle__customer"),pk=pk)
        order = quote.work_order
    lines = list(quote.lines.all()) if quote else []
    for line in lines:
        line.amount = (line.quantity*line.unit_price).quantize(Decimal("0.01"))
    subtotal = invoice.subtotal if invoice else sum((line.quantity*line.unit_price for line in lines),Decimal("0.00"))
    tax = invoice.tax if invoice else (subtotal*quote.tax_rate).quantize(Decimal("0.01"))
    total = invoice.total if invoice else (subtotal+tax).quantize(Decimal("0.01"))
    payments = list(invoice.payments.order_by("received_at")) if invoice else []
    paid = sum((payment.amount for payment in payments),Decimal("0.00"))
    return render(request,"workshop/document.html",{"title":invoice.number if invoice else f"Cotización {order.number} v{quote.version}","kind":kind,"order":order,"quote":quote,"invoice":invoice,"lines":lines,"subtotal":subtotal,"tax":tax,"total":total,"payments":payments,"paid":paid,"balance":total-paid})
