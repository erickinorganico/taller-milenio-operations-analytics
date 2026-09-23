"""Management dashboard and inspectable, immutable analytical cuts."""
import csv
import json
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import analytics, automation, models as m
from .access import can, require
from .catalog import SOURCE_MODELS

MART_LABELS = {
    'daily_operations': 'Actividad diaria', 'service_lines': 'Líneas de cotización',
    'part_usage': 'Consumo de refacciones', 'receivables': 'Facturación y cobranza',
    'order_journeys': 'Recorrido de las órdenes', 'inventory': 'Inventario al corte',
}
KPI_LABELS = {'opened': 'Órdenes recibidas', 'delivered': 'Órdenes entregadas',
              'invoiced': 'Facturación administrativa', 'payments': 'Cobros registrados'}


def landing(request):
    if can(request.user, 'intelligence_read'):
        return dashboard(request)
    from .views import home
    return home(request)


def _snapshot(request):
    value = request.GET.get('snapshot', '')
    if value:
        if not value.isdigit() or len(value) > 18:
            raise Http404
        return get_object_or_404(m.AnalyticsSnapshot, pk=int(value))
    return m.AnalyticsSnapshot.objects.first()


def _references(references, user):
    if not can(user, 'data_read'):
        return []
    reverse = {model.__name__: key for key, model in SOURCE_MODELS.items()}
    result = []
    for ref in references or []:
        model = ref.get('model')
        pk = str(ref.get('id', ref.get('pk', '')))
        if model in reverse and pk.isdigit():
            result.append({'label': f'{model} #{pk}', 'url': f'/data/{reverse[model]}/?id={pk}'})
    return result[:12]


def _worker_context():
    state = m.AutomationWorkerState.objects.first()
    policy = m.AutomationPolicy.objects.first()
    now = timezone.now()
    active = bool(state and state.heartbeat_at and state.heartbeat_at >= now - timedelta(seconds=90))
    running = bool(state and state.status == 'running' and state.lease_expires_at and state.lease_expires_at > now)
    label = 'En ejecución' if running else 'Activo' if active else 'Sin latido reciente'
    if policy and policy.paused:
        label += ' · en pausa'
    if state and state.last_error:
        label += ' · revisar error'
    return {'worker': state, 'policy': policy, 'worker_active': active,
            'worker_running': running, 'worker_label': label}


@require('intelligence_read')
def dashboard(request):
    selected = _snapshot(request)
    try:
        data = analytics.build_analytics_dashboard(
            start=request.GET.get('start') or None, end=request.GET.get('end') or None,
            snapshot=selected, segment=request.GET.get('segment', 'all'))
    except (ValidationError, ValueError) as exc:
        return render(request, 'workshop/dashboard.html', {'title': 'Dashboard', 'section': 'Analytics',
                      'filter_error': '; '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc)}, status=400)
    if request.GET.get('export') == 'json':
        if not can(request.user, 'data_read'):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="milenio-analytics.json"'
        return response
    cards = [{'key': key, 'label': KPI_LABELS[key], **value} for key, value in data.get('kpis', {}).items() if key in KPI_LABELS]
    rankings = data.get('rankings', {})
    for key, field in [('parts', 'orders'), ('services', 'authorized_orders')]:
        rows = rankings.get(key, [])
        maximum = max((Decimal(str(row.get(field) or 0)) for row in rows), default=Decimal('0'))
        for row in rows:
            row['bar_width'] = round(max(Decimal('0'), Decimal(str(row.get(field) or 0))) / maximum * 100, 2) if maximum > 0 else 0
            row['references'] = _references(row.get('source_refs'), request.user)
    trend = data.get('trend', [])
    maximum = max((max(Decimal(str(day.get('invoiced_mxn') or 0)), Decimal(str(day.get('payments_mxn') or 0))) for day in trend), default=Decimal('0'))
    points = {key: [] for key in ['invoiced_mxn', 'payments_mxn']}
    for i, day in enumerate(trend):
        for key in points:
            x = 12 + 736 * i / max(1, len(trend)-1)
            y = 168 - float(Decimal(str(day.get(key) or 0)) / maximum) * 145 if maximum > 0 else 168
            points[key].append(f'{x:.2f},{y:.2f}')
    jobs = m.AutomationJob.objects.order_by('-created_at')[:5]
    filters = data.get('filters', {})
    preserved = {key: request.GET[key] for key in ['start', 'end', 'segment', 'snapshot'] if request.GET.get(key)}
    if selected:
        preserved['snapshot'] = selected.pk
    return render(request, 'workshop/dashboard.html', {
        'title': 'Dashboard gerencial', 'section': 'Analytics', 'd': data, 'cards': cards,
        'selected_snapshot': selected, 'snapshots': m.AnalyticsSnapshot.objects.all()[:30],
        'snapshot_age': (timezone.now()-selected.recorded_at).total_seconds()/60 if selected else None,
        'historical': bool(request.GET.get('snapshot')), 'parts': rankings.get('parts', [])[:10],
        'services': rankings.get('services', [])[:10], 'trend': trend,
        'invoice_points': ' '.join(points['invoiced_mxn']), 'payment_points': ' '.join(points['payments_mxn']),
        'trend_max': maximum, 'jobs': jobs, 'pending': m.Proposal.objects.filter(status='pending').count(),
        'tasks_open': m.ActionTask.objects.exclude(status__in=['completed','dismissed']).count(),
        'tasks_done': m.ActionTask.objects.filter(status='completed').count(),
        'coverage': json.dumps(data.get('coverage', {}), ensure_ascii=False, indent=2, cls=DjangoJSONEncoder),
        'mart_links': [{'key': key, 'label': label, 'count': selected.rows.filter(mart=key).count() if selected else 0} for key,label in MART_LABELS.items()],
        'export_query': urlencode({**preserved, 'export': 'json'}), **_worker_context(),
    })


def _cell(value):
    if value is None:
        return '—'
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, cls=DjangoJSONEncoder)
    return str(value)


@require('data_read')
def mart(request, key):
    if key not in MART_LABELS:
        raise Http404
    selected = _snapshot(request)
    rows = selected.rows.filter(mart=key).order_by('key') if selected else m.AnalyticsRow.objects.none()
    columns = []
    # All rows define the schema, so a nullable field in the first row cannot hide a column.
    for row in rows.iterator():
        columns.extend(name for name in row.data if name != 'source_refs' and name not in columns)
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="milenio-{key}-corte-{selected.pk if selected else 0}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['snapshot_id','recorded_at','source_fingerprint','key',*columns,'source_refs'])
        for row in rows.iterator():
            values = [selected.pk, selected.recorded_at.isoformat(), selected.source_fingerprint, row.key,
                      *[row.data.get(column) for column in columns], row.data.get('source_refs', [])]
            texts = [_cell(value) for value in values]
            writer.writerow(["'"+value if value.lstrip().startswith(('=', '+', '-', '@')) else value for value in texts])
        return response
    page = Paginator(rows, 35).get_page(request.GET.get('page'))
    rendered = [{'key': row.key, 'cells': [_cell(row.data.get(column)) for column in columns],
                 'references': _references(row.data.get('source_refs'), request.user)} for row in page]
    return render(request, 'workshop/analytics_table.html', {'title': MART_LABELS[key], 'section': 'Tablas analíticas',
                  'snapshot': selected, 'columns': columns, 'rows': rendered, 'page': page, 'count': rows.count(), 'mart_key': key})


@require('intelligence_read')
def automations(request):
    return render(request, 'workshop/automations.html', {'title': 'Automatizaciones', 'section': 'Inteligencia',
                  'jobs': m.AutomationJob.objects.order_by('-created_at')[:60], **_worker_context()})


@require('manage')
@require_POST
def configure_automation(request):
    try:
        minutes = int(request.POST.get('interval_minutes', '60'))
        if not 1 <= minutes <= 1440:
            raise ValidationError('El intervalo debe estar entre 1 y 1440 minutos.')
        automation.set_policy(request.user, interval_minutes=minutes,
            automatic_enabled='automatic_enabled' in request.POST, paused='paused' in request.POST,
            native_enabled='native_enabled' in request.POST)
        messages.success(request, 'Configuración guardada. El trabajador aplicará los cambios en el siguiente ciclo.')
    except (ValueError, ValidationError) as exc:
        messages.error(request, '; '.join(exc.messages) if isinstance(exc, ValidationError) else 'Intervalo inválido.')
    return redirect('/automations/')


@require('review')
@require_POST
def enqueue(request):
    try:
        job = automation.enqueue_manual(request.user, mode=request.POST.get('mode','rules'))
        messages.success(request, f'Ejecución #{job.pk} en cola: actualización analítica y revisión de agentes.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect('/automations/')
