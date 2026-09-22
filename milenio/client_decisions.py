"""Explainable weekly decisions over an explicitly supplied, local client snapshot.

No inference calls, recommendations to spend, or business state changes occur here.
Amounts are integer cents. Totals describe supplied rows, not an entire business.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib


POLICY = {
    'version': 'client-review-1',
    'overdue_p1_days': 15,
    'priority_meaning': {'P1': 'Revisar hoy', 'P2': 'Revisar esta semana', 'P3': 'Completar información'},
    'limitations': 'Prioridades de revisión configuradas en el producto; no son SLA pactados ni instrucciones de cobro o compra.',
}
OPEN_STATUSES = {'received', 'in_service', 'waiting_parts', 'rework', 'ready'}


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Se requiere fecha con zona horaria')
    return parsed.astimezone(timezone.utc)


def action_id(category, record_id):
    return category + '-' + hashlib.sha256(str(record_id).encode()).hexdigest()[:16]


def analyze_client(snapshot):
    meta = snapshot['metadata']
    cutoff = instant(meta['as_of'])
    tables = snapshot['tables']
    orders, invoices, payments, inventory = (tables[k] for k in ('orders', 'invoices', 'payments', 'inventory'))
    decisions, receivables, service, stock = [], [], [], []
    payments_by_invoice = {}
    for row in payments:
        payments_by_invoice.setdefault(row['invoice_id'], []).append(row)
    invoices_by_order = {}
    for row in invoices:
        if row['status'] == 'issued' and row.get('order_id'):
            invoices_by_order.setdefault(row['order_id'], []).append(row)

    def add(category, record_id, title, priority, owner, why, step, evidence, amount=None, missing=None):
        decisions.append({
            'action_id': action_id(category, record_id), 'category': category,
            'title': title, 'priority': priority, 'owner_role': owner,
            'why_now': why, 'recommended_next_step': step,
            'amount_at_risk_cents': amount,
            'evidence': evidence, 'source_ids': [record_id], 'missing_evidence': missing or [],
            'review_status': 'pending',
        })

    def evidence(table, row, fields):
        key = {'orders': 'order_id', 'invoices': 'invoice_id', 'payments': 'payment_id', 'inventory': 'part_id'}[table]
        return [{'table': table, 'record_id': row[key], 'field': name, 'value': row.get(name),
                 'snapshot_id': meta['snapshot_id']} for name in fields]

    for row in invoices:
        if row['status'] != 'issued':
            continue
        linked = payments_by_invoice.get(row['invoice_id'], [])
        paid = sum(item['amount_cents'] for item in linked)
        balance = row['amount_cents'] - paid
        due = instant(row['due_at']) if row.get('due_at') else None
        # Calendar days in UTC, the input contract's documented normalization.
        days = max(0, (cutoff.date() - due.date()).days) if due else None
        overdue = bool(balance > 0 and due and due < cutoff)
        bucket = 'Sin vencimiento' if due is None else ('Liquidada' if balance == 0 else
                 ('Al corriente' if not overdue else ('Menos de 1 día' if days == 0 else '1–14 días' if days < 15 else '15–30 días' if days <= 30 else '31+ días')))
        receivables.append({**row, 'paid_cents': paid, 'balance_cents': balance,
                            'days_overdue': days, 'overdue': overdue, 'aging_bucket': bucket,
                            'payment_ids': [p['payment_id'] for p in linked]})
        if balance <= 0:
            continue
        proof = evidence('invoices', row, ['amount_cents', 'issued_at', 'due_at', 'status'])
        for payment in linked:
            proof += evidence('payments', payment, ['invoice_id', 'amount_cents', 'paid_at'])
        if overdue:
            add('cartera', row['invoice_id'], f"Revisar saldo vencido · {row['invoice_id']}",
                'P1' if days >= POLICY['overdue_p1_days'] else 'P2', 'Administración',
                f"Saldo documentado con {days} días calendario de atraso; {len(linked)} pagos vinculados.",
                'Conciliar los pagos con la fuente y confirmar si existe disputa o acuerdo vigente. Registrar el siguiente paso autorizado y su fecha.',
                proof, balance, ['Disputa o acuerdo de pago vigente', 'Confirmación del saldo con la fuente'])
        elif due is None:
            add('vencimiento', row['invoice_id'], f"Completar vencimiento · {row['invoice_id']}", 'P3', 'Administración',
                'Hay saldo, pero falta el vencimiento; no se clasifica como vencido.',
                'Consultar las condiciones documentadas y completar el vencimiento en el archivo de origen.', proof, balance)

    for row in orders:
        status = row['status']
        is_open = status in OPEN_STATUSES
        promised = instant(row['promised_at']) if row.get('promised_at') else None
        overdue = bool(is_open and promised and promised < cutoff)
        age_hours = round((cutoff - instant(row['received_at'])).total_seconds() / 3600, 1)
        bill_ids = [r['invoice_id'] for r in invoices_by_order.get(row['order_id'], [])]
        service.append({**row, 'open': is_open, 'overdue': overdue, 'age_hours': age_hours,
                        'invoice_ids': bill_ids,
                        'billing_observation': 'Sin factura vinculada en el extracto' if status == 'delivered' and not bill_ids else 'Con factura vinculada' if bill_ids else 'No evaluada'})
        proof = evidence('orders', row, ['status', 'received_at', 'promised_at', 'delivered_at', 'block_reason', 'technician_ref'])
        # One operational decision per order, avoiding competing duplicate instructions.
        if status in {'waiting_parts', 'rework'}:
            add('servicio', row['order_id'], f"Desbloquear revisión · {row['order_id']}", 'P1' if overdue or status == 'rework' else 'P2',
                'Jefatura de taller', f"Estado {'en espera de partes' if status == 'waiting_parts' else 'en retrabajo'}; " + ('compromiso de entrega vencido.' if overdue else 'requiere confirmar causa y plan.'),
                'Confirmar causa, responsable y disponibilidad verificable. Definir el siguiente paso y revisar cualquier nuevo compromiso antes de comunicarlo.',
                proof, missing=[] if row.get('block_reason') else ['Causa del bloqueo o retrabajo'])
        elif overdue:
            add('servicio', row['order_id'], f"Revisar compromiso vencido · {row['order_id']}", 'P1', 'Jefatura de taller',
                'La orden sigue abierta después de la fecha prometida.',
                'Confirmar el avance físico, la causa del atraso y el responsable. Registrar una fecha de revisión sin prometer una entrega no validada.', proof)
        elif status == 'ready':
            add('servicio', row['order_id'], f"Preparar revisión de entrega · {row['order_id']}", 'P2', 'Recepción',
                'La orden figura lista y todavía no entregada.',
                'Verificar control de calidad, documentación y condiciones de entrega con el responsable; registrar qué falta.',
                proof, missing=['Control de calidad y autorización de entrega'])
        elif is_open and promised is None:
            add('servicio', row['order_id'], f"Completar compromiso · {row['order_id']}", 'P3', 'Recepción',
                'Orden abierta sin fecha prometida; el atraso no es evaluable.',
                'Confirmar si existe un compromiso acordado y registrarlo; conservarlo desconocido si no existe.', proof)
        elif status == 'delivered' and not bill_ids:
            add('facturacion', row['order_id'], f"Conciliar servicio entregado · {row['order_id']}", 'P2', 'Administración',
                'No hay factura vigente vinculada en los datos recibidos; esto no prueba falta de facturación.',
                'Buscar la factura o documentar garantía, cortesía o cobertura del contrato. Completar el vínculo sin estimar ingresos.',
                proof, missing=['Factura o motivo documentado de no facturación'])

    for row in inventory:
        available = row['on_hand'] - row['reserved']
        gap = max(0, row['reorder_point'] - available)
        stock.append({**row, 'available': available, 'gap_units': gap})
        if gap > 0:
            add('inventario', row['part_id'], f"Revisar disponibilidad · {row['part_id']}", 'P1' if available <= 0 and row['reserved'] > 0 else 'P2',
                'Responsable de partes', f"Disponibles: {available}; mínimo declarado: {row['reorder_point']}; diferencia: {gap} unidades.",
                'Validar conteo, reservas y consumo previsto. Consultar reposiciones ya abiertas antes de proponer una compra.',
                evidence('inventory', row, ['on_hand', 'reserved', 'reorder_point', 'unit_cost_cents']),
                missing=['Reposiciones en tránsito', 'Demanda prevista y vínculo de reservas a órdenes'])

    decisions.sort(key=lambda r: (r['priority'], -(r['amount_at_risk_cents'] or 0), r['category'], r['action_id']))
    summary = {
        'orders_loaded': len(orders), 'open_orders': sum(r['open'] for r in service) if orders else None,
        'late_orders': sum(r['overdue'] for r in service) if orders else None,
        'invoiced_cents': sum(r['amount_cents'] for r in receivables) if invoices else None,
        'paid_cents': sum(r['paid_cents'] for r in receivables) if invoices else None,
        'balance_cents': sum(r['balance_cents'] for r in receivables) if invoices else None,
        'overdue_balance_cents': sum(r['balance_cents'] for r in receivables if r['overdue']) if invoices else None,
        'low_stock_parts': sum(r['gap_units'] > 0 for r in stock) if inventory else None,
        'decisions': len(decisions), 'p1_reviews': sum(d['priority'] == 'P1' for d in decisions),
    }
    coverage = [{'table': table, 'rows': len(rows), 'status': 'supplied_rows_only' if rows else 'not_provided',
                 'meaning': 'Totales del extracto; integridad del universo no confirmada.' if rows else 'Sin registros: cobertura desconocida, no prueba ausencia de actividad.'}
                for table, rows in tables.items()]
    warnings = []
    for name, missing, total in (
        ('Órdenes abiertas sin compromiso', sum(r['open'] and not r.get('promised_at') for r in service), sum(r['open'] for r in service)),
        ('Facturas con saldo sin vencimiento', sum(r['balance_cents'] > 0 and not r.get('due_at') for r in receivables), sum(r['balance_cents'] > 0 for r in receivables)),
        ('Órdenes abiertas sin responsable técnico', sum(r['open'] and not r.get('technician_ref') for r in service), sum(r['open'] for r in service)),
    ):
        if missing:
            warnings.append({'check': name, 'missing': missing, 'population': total})
    return {'schema_version': 1, 'metadata': dict(meta), 'policy': POLICY, 'summary': summary,
            'coverage': coverage, 'warnings': warnings, 'decisions': decisions,
            'receivables': receivables, 'service': service, 'inventory': stock,
            'source_hashes': snapshot.get('source_hashes', {}),
            'limits': ['Sólo registros aportados; pagos omitidos pueden sobrestimar saldos.',
                       'Sin movimientos de stock, contratos, costos completos ni capacidad disponible: no calcula utilidad, SLA contractual ni utilización.',
                       'Las prioridades son propuestas pendientes de revisión; no acreditan acciones ejecutadas.',
                       'Los importes de las colas se superponen: no se suman como oportunidad o ahorro.']}


def compare_clients(before, after):
    """Compare matched evidence, never treating disappeared rows as paid/resolved."""
    bm, am = before['metadata'], after['metadata']
    if bm['business_name'] != am['business_name'] or bm['synthetic'] != am['synthetic']:
        raise ValueError('Los cortes deben corresponder al mismo negocio y modo de datos')
    if bm['snapshot_id'] == am['snapshot_id'] or instant(am['as_of']) <= instant(bm['as_of']):
        raise ValueError('El segundo corte debe ser posterior y tener un identificador nuevo')
    changes = []
    for table, key in [('receivables', 'invoice_id'), ('service', 'order_id'), ('inventory', 'part_id')]:
        old = {r[key]: r for r in before[table]}
        new = {r[key]: r for r in after[table]}
        for record_id in sorted(old.keys() | new.keys()):
            a, b = old.get(record_id), new.get(record_id)
            state = 'new' if a is None else 'missing_in_later_extract' if b is None else 'observed_in_both'
            change = {'table': table, 'record_id': record_id, 'state': state,
                      'before': a, 'after': b, 'balance_change_cents': None, 'observed_payment_increase_cents': None}
            if a is not None and b is not None and table == 'receivables':
                change['balance_change_cents'] = b['balance_cents'] - a['balance_cents']
                change['observed_payment_increase_cents'] = b['paid_cents'] - a['paid_cents']
                if a['amount_cents'] != b['amount_cents']:
                    change['state'] = 'invoice_amount_changed_review'
            changes.append(change)
    before_actions = {d['action_id']: d for d in before['decisions']}
    after_actions = {d['action_id']: d for d in after['decisions']}
    continuity = []
    for key in sorted(before_actions.keys() | after_actions.keys()):
        old, new = before_actions.get(key), after_actions.get(key)
        state = 'new' if old is None else 'still_flagged' if new else 'not_flagged_now_requires_review'
        continuity.append({'action_id': key, 'title': (new or old)['title'], 'state': state})
    return {'before_snapshot': bm['snapshot_id'], 'after_snapshot': am['snapshot_id'],
            'metadata': am, 'changes': changes, 'action_continuity': continuity,
            'limits': ['Un registro ausente no se considera cobrado, entregado ni resuelto.',
                       'Las variaciones observadas no demuestran impacto de la consultoría.',
                       'Los importes modificados requieren conciliación; comparar cobertura antes de comparar totales.']}
