"""Reviewed photo requests become draft quote lines, with provenance and replay guards."""
import hashlib
import json
import uuid
from decimal import Decimal

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from . import models as m, services as s

SALT = 'workshop.photo-quote.v1'
MAX_ROWS = 50


def digest(value):
    def encode(item):
        return format(item.normalize(), 'f') if isinstance(item, Decimal) else str(item)
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=encode).encode('utf-8')).hexdigest()


def source_state(source):
    fields = ('pk', 'work_order_id', 'description', 'kind', 'quantity', 'unit_price', 'unit_cost', 'part_sku')
    return digest({**{name:getattr(source, name) for name in fields},
        'documents': sorted((doc.pk, doc.version, doc.status, doc.work_order_id, doc.fingerprint) for doc in source.documents.all())})


def quote_state(order):
    return digest({'order':(order.pk, order.version, order.status),
        'quotes':list(order.quotes.order_by('pk').values('pk','version','status','tax_rate')),
        'lines':list(m.QuoteLine.objects.filter(quote__work_order=order).order_by('pk').values(
            'pk','quote_id','description','kind','quantity','unit_price','unit_cost','part_id','source_service_id'))})


def draft_for(order):
    if order.status not in {m.WorkOrder.Status.INSPECTION, m.WorkOrder.Status.AWAITING_APPROVAL}:
        raise ValidationError('Avanza a Inspección antes de preparar el presupuesto de las fotos.')
    if order.quotes.filter(status=m.Quote.Status.APPROVED).exists():
        raise ValidationError('El presupuesto autorizado está protegido.')
    active = list(order.quotes.filter(status__in=[m.Quote.Status.DRAFT,m.Quote.Status.SENT]))
    if len(active) > 1:
        raise ValidationError('Hay más de un presupuesto activo. Revisa sus versiones antes de continuar.')
    if active and active[0].status == m.Quote.Status.SENT:
        raise ValidationError('El presupuesto ya fue presentado. Crea una nueva versión desde Cotización para revisarlo.')
    return active[0] if active else None


def prepare(order, actor):
    s._actor(actor, 'reception')
    quote = draft_for(order)
    sources = order.captured_services.order_by('pk').prefetch_related('documents')
    if quote:
        sources = sources.exclude(quote_lines__quote=quote)
    sources = list(sources[:MAX_ROWS+1])
    more = len(sources) > MAX_ROWS
    sources = sources[:MAX_ROWS]
    token = signing.dumps({'actor':actor.pk, 'order':order.pk, 'quote':quote.pk if quote else None,
        'state':quote_state(order), 'nonce':uuid.uuid4().hex,
        'sources':{str(source.pk):source_state(source) for source in sources}}, salt=SALT)
    return {'quote':quote, 'sources':sources, 'more':more, 'receipt':token}


@transaction.atomic
def apply(*, order, actor, receipt, rows, tax_rate):
    s._actor(actor, 'reception')
    try:
        plan = signing.loads(receipt, salt=SALT, max_age=900)
    except signing.BadSignature:
        raise ValidationError('La revisión venció o cambió. Abre de nuevo los servicios de las fotos.')
    if plan['actor'] != actor.pk or plan['order'] != order.pk:
        raise ValidationError('La revisión pertenece a otra orden o persona.')
    if not rows or len(rows) > MAX_ROWS or len({row['source_id'] for row in rows}) != len(rows):
        raise ValidationError('Selecciona entre uno y 50 servicios distintos.')
    request_state = digest({'rows':sorted(rows, key=lambda row:row['source_id']), 'tax_rate':tax_rate})
    key = hashlib.sha256(receipt.encode('utf-8')).hexdigest()
    previous = m.PhotoQuoteBatch.objects.select_related('quote').filter(key=key).first()
    if previous:
        if previous.request_fingerprint != request_state or previous.created_by_id != actor.pk:
            raise ValidationError('Esta revisión ya se guardó con otros datos. Abre una revisión nueva.')
        return previous.quote
    order = s._lock_order(order)
    if quote_state(order) != plan['state']:
        raise ValidationError('El presupuesto o la orden cambió. Abre la página nuevamente antes de guardar.')
    quote = draft_for(order)
    if (quote.pk if quote else None) != plan['quote']:
        raise ValidationError('Cambió la versión del presupuesto. Vuelve a abrirlo.')
    sources = {source.pk:source for source in order.captured_services.select_for_update().filter(
        pk__in=[row['source_id'] for row in rows]).prefetch_related('documents')}
    for row in rows:
        source = sources.get(row['source_id'])
        if (not source or plan['sources'].get(str(source.pk)) != source_state(source)
                or not any(doc.status == 'applied' and doc.work_order_id == order.pk for doc in source.documents.all())):
            raise ValidationError('Un servicio o su foto cambió. Revisa nuevamente los datos de origen.')
    if not m.WorkOrder.objects.filter(pk=order.pk,version=order.version).update(version=F('version')+1):
        raise ValidationError('Otra persona actualizó la orden. Abre la revisión nuevamente.')
    if quote is None:
        quote = s.create_quote(actor=actor, work_order=order, tax_rate=tax_rate)
    for row in rows:
        source = sources[row['source_id']]
        part = None
        if row['kind'] == m.QuoteLine.Kind.PART:
            sku = str(row.get('part_sku') or '').strip()
            matches = list(m.Part.objects.filter(sku__iexact=sku)[:2]) if sku else []
            if len(matches) != 1:
                raise ValidationError(f'El SKU «{sku}» de «{row["description"]}» no existe o es ambiguo. Selecciona una refacción del inventario.')
            part = matches[0]
        line = s.add_quote_line(actor=actor, quote=quote, description=row['description'], kind=row['kind'],
            quantity=row['quantity'], unit_price=row['unit_price'], unit_cost=row.get('unit_cost'), part=part)
        line.source_service = source
        line.save(update_fields=['source_service'])
        s._audit(actor, line, 'photo_sourced', after={'quote_id':quote.pk, 'work_order_id':order.pk,
            'source_service_id':source.pk, 'document_ids':[doc.pk for doc in source.documents.all()],
            'quantity':str(line.quantity), 'unit_price':str(line.unit_price),
            'unit_cost':str(line.unit_cost) if line.unit_cost is not None else None})
    m.PhotoQuoteBatch.objects.create(key=key, request_fingerprint=request_state, quote=quote, created_by=actor)
    return quote
