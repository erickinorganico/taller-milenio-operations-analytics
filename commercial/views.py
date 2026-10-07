import csv
import io
import json
from urllib.parse import quote
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_GET
from workshop.access import require
from . import forms, services, outreach
from .models import AuditEvent, Evidence, SalesAccount, SalesProposal
from .rules import domain_for, qualify


def query_accounts(request):
    accounts = SalesAccount.objects.select_related("owner", "fleet").all()
    if request.GET.get("q"):
        accounts = accounts.filter(Q(name__icontains=request.GET["q"]) | Q(segment__icontains=request.GET["q"]) | Q(domain__icontains=request.GET["q"]))
    if request.GET.get("stage"): accounts = accounts.filter(stage=request.GET["stage"])
    if request.GET.get("source"): accounts = accounts.filter(source=request.GET["source"])
    if request.GET.get("due") == "1": accounts = accounts.filter(next_action_on__lte=timezone.localdate()).exclude(stage__in=["lost", "suppressed"])
    return accounts


@require("reception")
@require_GET
def index(request):
    from django.core.paginator import Paginator
    accounts = query_accounts(request)
    all_accounts = SalesAccount.objects.all()
    sources = all_accounts.values("source").annotate(total=Count("id", distinct=True), won=Count("id", filter=Q(opportunities__status="won"), distinct=True))
    return render(request, "commercial/index.html", {"title": "Desarrollo comercial", "section": "Comercial", "page": Paginator(accounts, 30).get_page(request.GET.get("page")), "stages": SalesAccount.Stage.choices, "sources": sources, "total": all_accounts.count(), "due": all_accounts.filter(next_action_on__lte=timezone.localdate()).exclude(stage__in=["lost", "suppressed"]).count(), "missing_next": all_accounts.exclude(stage__in=["lost", "suppressed"]).filter(Q(next_action_on__isnull=True) | Q(next_action="")).count(), "no_contact": all_accounts.filter(stage="suppressed").count(), "today": timezone.localdate()})


@require("reception")
@require_http_methods(["GET", "POST"])
def new_account(request):
    form = forms.AccountForm(request.POST or None, initial={"owner": request.user})
    if request.method == "POST" and form.is_valid():
        try:
            account = services.create_account(form.cleaned_data, request.user)
            return redirect("commercial:detail", pk=account.pk)
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, "; ".join(exc.messages) if isinstance(exc, ValidationError) else "La empresa ya existe; revisa el dominio.")
    return render(request, "commercial/form.html", {"title": "Nueva empresa", "form": form})


def account_forms(account, data=None, action=None):
    bind = lambda key: data if action == key else None
    return {
        "account": forms.AccountForm(bind("account"), instance=account, prefix="account"),
        "evidence": forms.EvidenceForm(bind("evidence"), prefix="evidence"),
        "contact": forms.ContactForm(bind("contact"), account=account, prefix="contact"),
        "fleet": forms.FleetForm(bind("fleet"), account=account, instance=account.fleet, prefix="fleet"),
        "interaction": forms.InteractionForm(bind("interaction"), prefix="interaction"),
        "opportunity": forms.OpportunityForm(bind("opportunity"), prefix="opportunity"),
        "proposal": forms.ProposalForm(bind("proposal"), account=account, prefix="proposal"),
        "stage": forms.StageForm(bind("stage"), initial={"stage": account.stage}, prefix="stage"),
        "accept": forms.AcceptForm(bind("accept"), prefix="accept"),
        "handoff": forms.HandoffForm(bind("handoff"), prefix="handoff"),
        "link": forms.LinkForm(bind("link"), account=account, prefix="link"),
        "extract": forms.ExtractForm(),
    }


@require("reception")
@require_http_methods(["GET", "POST"])
def detail(request, pk):
    account = get_object_or_404(SalesAccount.objects.select_related("fleet", "owner"), pk=pk)
    action = request.POST.get("action")
    panels = account_forms(account, request.POST if request.method == "POST" else None, action)
    response_status = 200
    if request.method == "POST":
        form = panels.get(action)
        if form is None or action == "extract": return HttpResponse("Acción no disponible", status=400)
        if form.is_valid():
            try:
                version = int(request.POST.get("version", "0"))
                data = form.cleaned_data.copy()
                actor = request.user
                if action == "account": services.update_account(pk, version, data, actor)
                elif action in {"evidence", "contact", "opportunity"}: services.add_record(pk, version, action, data, actor)
                elif action == "fleet": services.update_fleet(pk, version, data, actor)
                elif action == "interaction": services.add_interaction(pk, version, data, actor)
                elif action == "stage": services.change_stage(pk, version, data["stage"], actor)
                elif action == "proposal": services.create_proposal(pk, version, data, actor)
                elif action == "accept": services.accept_proposal(pk, version, actor=actor, **data)
                elif action == "handoff": services.handoff(pk, version, actor, data["customer"])
                elif action == "link": services.link_service(pk, version, actor=actor, **data)
                messages.success(request, "Registro guardado.")
                return redirect("commercial:detail", pk=pk)
            except (ValidationError, IntegrityError, ValueError, ObjectDoesNotExist) as exc:
                form.add_error(None, "; ".join(exc.messages) if isinstance(exc, ValidationError) else "No se guardó: revisa el registro, el dominio o la versión de la ficha.")
                response_status = 400
        else: response_status = 400
    # ModelForms may mutate their instances during validation: reload the displayed truth.
    account.refresh_from_db()
    account = SalesAccount.objects.select_related("fleet", "owner").get(pk=pk)
    latest = dict(account.opportunities.annotate(latest=Max("proposals__revision")).values_list("pk", "latest"))
    proposals = list(SalesProposal.objects.filter(opportunity__account=account).select_related("opportunity").order_by("-created_at"))
    for proposal in proposals:
        proposal.is_current = proposal.revision == latest[proposal.opportunity_id]
    shared_domain = SalesAccount.objects.filter(domain=account.domain).exclude(pk=account.pk) if account.domain else SalesAccount.objects.none()
    return render(request, "commercial/detail.html", {"title": account.name, "section": "Comercial", "account": account, "panels": panels, "qualification": qualify(account), "proposals": proposals, "shared_domain": shared_domain, "events": account.interactions.order_by("-occurred_at")[:40], "audit": AuditEvent.objects.filter(account=account).select_related("actor").order_by("-created_at")[:30], "error_action": action if response_status == 400 else None}, status=response_status)


@require("reception")
@require_http_methods(["GET", "POST"])
def import_csv(request):
    form = forms.ImportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            raw = form.cleaned_data["file"].read(1_000_001)
            result = services.import_candidates(raw, request.user)
            messages.success(request, f"Importación: {result['created']} nuevas, {result['skipped']} omitidas. Repetida: {'sí' if result['repeated'] else 'no'}.")
            for item in result.get("review_rows", []):
                messages.warning(request, f"Fila {item['row']}: {item['candidate']['name']}. {item['reason']}")
            return redirect("commercial:index")
        except (ValidationError, ValueError, IntegrityError) as exc:
            form.add_error(None, "; ".join(exc.messages) if isinstance(exc, ValidationError) else "Archivo no válido; no se importó ninguna fila.")
    return render(request, "commercial/form.html", {"title": "Importar candidatos", "form": form, "importing": True})


@require("reception")
@require_GET
def export_csv(request):
    content = services.export_candidates([] if request.GET.get("template") else query_accounts(request))
    response = HttpResponse("\ufeff" + content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="milenio-candidatos.csv"'
    return response


@require("reception")
@require_http_methods(["POST"])
@transaction.atomic
def import_extract(request, pk):
    account = get_object_or_404(SalesAccount, pk=pk)
    try:
        account = services.locked(pk, int(request.POST.get("version", "0")))
        upload = request.FILES.get("file")
        if not upload: raise ValidationError("Selecciona un reporte JSON.")
        raw = upload.read(500_001)
        if len(raw) > 500_000: raise ValidationError("Máximo 500 KB.")
        report = json.loads(raw.decode("utf-8"))
        if report.get("schema") != "milenio-research-v1" or not isinstance(report.get("pages"), list) or len(report["pages"]) > 4:
            raise ValidationError("Formato de reporte no reconocido.")
        candidates = []
        for page in report["pages"]:
            if domain_for(page["url"]) != account.domain: raise ValidationError("El dominio del reporte no coincide con la empresa.")
            if page.get("status") != "ok": continue
            captured = forms.EvidenceForm.base_fields["captured_at"].clean(page["captured_at"])
            obj = Evidence(account=account, topic="website", source_url=page["url"], excerpt=str(page["text"])[:16000], captured_at=captured, reviewed=False, created_by=request.user)
            obj.full_clean()
            candidates.append(obj)
        count = 0
        for obj in candidates:
            if not account.evidence.filter(source_url=obj.source_url, excerpt=obj.excerpt).exists():
                obj.save()
                count += 1
        services.bump(account)
        services.audit(account, request.user, "extract_imported", pages=count, failed_pages=sum(p.get("status") != "ok" for p in report["pages"]))
        messages.success(request, f"{count} páginas incorporadas como evidencia sin revisar. No se infirió combustible ni se crearon contactos.")
    except (ValidationError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        messages.error(request, "; ".join(exc.messages) if isinstance(exc, ValidationError) else "Reporte no válido; revisa su formato.")
    return redirect("commercial:detail", pk=pk)


@require("reception")
@require_GET
def research(request):
    segments = ["mantenimiento industrial", "aire acondicionado", "control de plagas", "distribuidora", "seguridad privada", "mensajería"]
    searches = []
    for segment in segments:
        for source, expression in [("Google / Maps", f'"{segment}" "Tijuana"'), ("CANACINTRA", f'site:canacintra.net "{segment}" Tijuana'), ("Facebook", f'site:facebook.com "{segment}" "Tijuana"'), ("Instagram", f'site:instagram.com "{segment}" "Tijuana"'), ("LinkedIn", f'site:linkedin.com/company "{segment}" "Tijuana"')]:
            searches.append({"segment": segment, "source": source, "query": expression, "url": "https://www.google.com/search?q=" + quote(expression), "maps": "https://www.google.com/maps/search/" + quote(segment + " Tijuana")})
    return render(request, "commercial/research.html", {"title": "Investigación", "searches": searches})


@require("reception")
@require_GET
def draft(request, pk):
    account = get_object_or_404(SalesAccount, pk=pk)
    return render(request, "commercial/draft.html", {"title": "Borrador de contacto", "account": account, **outreach.prepare(account)})
