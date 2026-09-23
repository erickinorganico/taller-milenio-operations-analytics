import json
from datetime import timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from . import intelligence as intel, models as m
from .access import require, can
from .catalog import SOURCE_MODELS
from .views import fail, audit, snapshot, role_check

@require("intelligence_read")
def metrics(request):
    dashboard=intel.build_dashboard()
    reverse={model.__name__:key for key,model in SOURCE_MODELS.items()}
    for metric in dashboard["metrics"]:
        for row in metric.get("drilldown",[]):
            key=reverse.get(row.get("model"))
            row["url"]=f"/data/{key}/?id={row.get('pk')}" if key else "/data/"
        metric["coverage_text"]=json.dumps(metric.get("coverage",{}),ensure_ascii=False,cls=DjangoJSONEncoder)
    if request.GET.get("export")=="json":
        response=HttpResponse(json.dumps(dashboard,ensure_ascii=False,indent=2,cls=DjangoJSONEncoder),content_type="application/json")
        response["Content-Disposition"]='attachment; filename="milenio-metricas.json"'
        return response
    return render(request,"workshop/metrics.html",{"title":"Métricas del taller","section":"Inteligencia","dashboard":dashboard})

@require("intelligence_read")
def agents(request):
    proposals=list(m.Proposal.objects.select_related("run").order_by("-created_at")[:100])
    for proposal in proposals:
        proposal.evidence_text=json.dumps(proposal.evidence,ensure_ascii=False,indent=2,cls=DjangoJSONEncoder)
    return render(request,"workshop/agents.html",{"title":"Agentes y acciones","section":"Inteligencia","runs":m.AgentRun.objects.all().order_by("-started_at")[:15],"proposals":proposals,"tasks":m.ActionTask.objects.select_related("assigned_to","work_order","proposal").order_by("status","due_at","-created_at")[:100],"members":User.objects.filter(is_active=True).filter(Q(is_superuser=True)|Q(groups__name__in=["manager","advisor","finance","technician","parts"])).distinct(),"pending":m.Proposal.objects.filter(status="pending").count(),"open_tasks":m.ActionTask.objects.exclude(status__in=["completed","dismissed"]).count()})

@require("review")
@require_POST
def run_agents(request):
    mode=request.POST.get("mode","rules")
    role=request.POST.get("agent","all")
    try:
        runs=intel.run_agents(request.user,mode=mode,agent=role)
        errors=[run.error for run in runs if run.status in {"failed","blocked"}]
        if errors:
            messages.error(request,"La ejecución terminó con un bloqueo: "+" · ".join(errors))
        else:
            messages.success(request,"Revisión completada. Consulta las propuestas y su evidencia.")
    except ValidationError as exc:
        fail(request,exc)
    return redirect("/agents/")

@require("review")
@require_POST
def review_proposal(request,pk):
    get_object_or_404(m.Proposal,pk=pk)
    try:
        proposal=intel.review_proposal(pk,request.user,request.POST.get("decision"),request.POST.get("note",""))
        if proposal.status=="stale":
            messages.warning(request,"Los datos cambiaron. Ejecuta una nueva revisión antes de aceptar esta propuesta.")
        else:
            messages.success(request,"Decisión registrada. Las propuestas aceptadas tienen una tarea de seguimiento.")
    except ValidationError as exc:
        fail(request,exc)
    return redirect("/agents/")

@require_POST
def update_task(request,pk):
    task=get_object_or_404(m.ActionTask,pk=pk)
    if not can(request.user,"review") and not (can(request.user,"complete_task") and task.assigned_to_id==request.user.pk):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    try:
        action=request.POST.get("action")
        if action=="complete":
            intel.complete_action_task(pk,request.user,request.POST.get("outcome",""))
        elif action=="assign":
            role_check(request,"review")
            assigned_id=request.POST.get("assigned_to")
            assigned=get_object_or_404(User.objects.filter(is_active=True).filter(Q(is_superuser=True)|Q(groups__name__in=["manager","advisor","finance","technician","parts"])).distinct(),pk=assigned_id) if assigned_id else None
            due=forms.DateTimeField(required=False).clean(request.POST.get("due_at"))
            with transaction.atomic():
                current=m.ActionTask.objects.select_for_update().get(pk=pk)
                if current.status in {"completed","dismissed"}:
                    raise ValidationError("La tarea ya está cerrada.")
                before=snapshot(current)
                current.assigned_to=assigned
                current.due_at=due
                current.status="in_progress" if assigned else "open"
                current.save(update_fields=["assigned_to","due_at","status"])
                audit(request.user,current,"task_assigned",before)
        else:
            raise ValidationError("Acción de tarea inválida.")
        messages.success(request,"Seguimiento actualizado.")
    except ValidationError as exc:
        fail(request,exc)
    return redirect("/agents/#task-"+str(pk) if can(request.user,"intelligence_read") else "/#task-"+str(pk))
