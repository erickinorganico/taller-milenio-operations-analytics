"""Inspectable analytical marts built from typed source tables and event evidence."""
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median

from .contracts import DEMO_NOW
from .domain import date_value


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    low, high = math.floor(index), math.ceil(index)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (index - low), 3)


def build_marts(database, as_of=DEMO_NOW):
    """Materialize derived tables in a newly built warehouse, before agent reads."""
    at = date_value(as_of)
    if at != date_value(DEMO_NOW):
        raise ValueError('This synthetic snapshot supports only its declared cutoff; rebuild the snapshot for another as_of.')
    con = sqlite3.connect(database)
    con.row_factory = sqlite3.Row
    tables = {name: [dict(r) for r in con.execute('SELECT * FROM "' + name + '"')]
              for name in ('customers', 'vehicles', 'leads', 'quotes', 'appointments', 'work_orders',
                           'invoices', 'payments', 'expenses', 'parts', 'stock_moves', 'reservations',
                           'fleet_accounts', 'contracts', 'opportunities', 'tows', 'lifecycle_events', 'journey_links')}
    lookup = lambda name: {r['id']: r for r in tables[name]}
    customers, contracts = lookup('customers'), lookup('contracts')
    payments, invoices, histories = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in tables['payments']:
        payments[row['invoice_id']].append(row)
    for row in tables['invoices']:
        if row['work_order_id'] and row['status'] == 'issued':
            invoices[row['work_order_id']].append(row)
    for row in tables['lifecycle_events']:
        histories[(row['entity_type'], row['entity_id'])].append(row)
    services = []
    for row in tables['work_orders']:
        events = sorted(histories[('work_orders', row['id'])], key=lambda e: (date_value(e['at']), e['event_id']))
        observed = bool(events)
        waiting, hands_on = 0., 0.
        for a, b in zip(events, events[1:]):
            elapsed = (date_value(b['at']) - date_value(a['at'])).total_seconds() / 3600
            if a['to_state'] == 'waiting_parts': waiting += elapsed
            if a['to_state'] == 'in_service': hands_on += elapsed
        opened = date_value(row['opened_at'])
        finish = date_value(row['completed_at']) if row['completed_at'] else at
        elapsed = (finish - opened).total_seconds() / 3600
        contract = contracts.get(row['contract_id'])
        eligible = bool(contract and contract['approval_ref'] and contract['status'] in ('active', 'expired')
                        and date_value(contract['starts_at']) <= opened < date_value(contract['ends_at']))
        if row['status'] == 'cancelled': sla = 'excluded'
        elif customers[row['customer_id']]['segment'] != 'fleet': sla = 'not_applicable'
        elif not eligible: sla = 'unknown'
        elif row['completed_at']: sla = 'met' if elapsed <= contract['sla_hours'] else 'breached'
        else: sla = 'breached' if elapsed > contract['sla_hours'] else 'at_risk' if contract['sla_hours'] - elapsed <= 4 else 'on_track'
        billed = sum(x['amount_cents'] for x in invoices[row['id']])
        paid = sum(p['amount_cents'] for inv in invoices[row['id']] for p in payments[inv['id']])
        services.append({'work_order_id': row['id'], 'customer_id': row['customer_id'],
            'segment': customers[row['customer_id']]['segment'], 'vehicle_id': row['vehicle_id'],
            'status': row['status'], 'opened_at': row['opened_at'], 'completed_at': row['completed_at'],
            'cycle_hours': round(elapsed, 3), 'history_available': int(observed),
            'waiting_parts_hours': round(waiting, 3) if observed else None,
            'in_service_hours': round(hands_on, 3) if observed else None,
            'rework_observed': int(any(e['to_state'] == 'rework' for e in events)) if observed else None,
            'contract_id': row['contract_id'], 'sla_status': sla, 'invoiced_cents': billed,
            'paid_cents': paid, 'receivable_cents': billed - paid})
    aging = []
    for row in tables['invoices']:
        if row['status'] != 'issued': continue
        paid = sum(p['amount_cents'] for p in payments[row['id']])
        days = max(0, (at - date_value(row['due_at'])).days)
        bucket = 'current' if date_value(row['due_at']) >= at else '1-30' if days <= 30 else '31-60' if days <= 60 else '61-90' if days <= 90 else '90+'
        aging.append({'invoice_id': row['id'], 'customer_id': row['customer_id'],
            'segment': customers[row['customer_id']]['segment'], 'due_at': row['due_at'],
            'invoiced_cents': row['amount_cents'], 'paid_cents': paid, 'balance_cents': row['amount_cents'] - paid,
            'days_overdue': days, 'aging_bucket': bucket})
    daily = defaultdict(lambda: {'opened': 0, 'delivered': 0, 'collected_cents': 0, 'expense_cents': 0})
    for row in services:
        daily[date_value(row['opened_at']).astimezone(at.tzinfo).date().isoformat()]['opened'] += 1
        if row['completed_at']: daily[date_value(row['completed_at']).astimezone(at.tzinfo).date().isoformat()]['delivered'] += 1
    for row in tables['payments']: daily[date_value(row['paid_at']).astimezone(at.tzinfo).date().isoformat()]['collected_cents'] += row['amount_cents']
    for row in tables['expenses']: daily[date_value(row['paid_at']).astimezone(at.tzinfo).date().isoformat()]['expense_cents'] += row['amount_cents']
    daily_rows = [{'day': day, **values} for day, values in sorted(daily.items())]
    fleet_rows = []
    for account in tables['fleet_accounts']:
        own = [w for w in services if w['customer_id'] == account['customer_id']]
        measured = [w for w in own if w['status'] == 'delivered' and w['sla_status'] in ('met', 'breached')]
        opps = [o for o in tables['opportunities'] if o['fleet_account_id'] == account['id'] and o['status'] not in ('won', 'lost')]
        fleet_rows.append({'fleet_account_id': account['id'], 'customer_id': account['customer_id'],
            'industry': account['industry'], 'declared_vehicles': account['fleet_size'],
            'captured_vehicles': sum(v['customer_id'] == account['customer_id'] for v in tables['vehicles']),
            'services': len(own), 'eligible_delivered': len(measured),
            'sla_met': sum(w['sla_status'] == 'met' for w in measured),
            'sla_breached': sum(w['sla_status'] == 'breached' for w in measured),
            'sla_unknown': sum(w['sla_status'] == 'unknown' for w in own),
            'cycle_p90_hours': percentile([w['cycle_hours'] for w in own if w['status'] == 'delivered'], .9),
            'pipeline_cents': sum(o['value_cents'] for o in opps),
            'receivable_cents': sum(x['balance_cents'] for x in aging if x['customer_id'] == account['customer_id'])})
    stock = []
    for part in tables['parts']:
        moves = [m for m in tables['stock_moves'] if m['part_id'] == part['id']]
        on_hand = sum(m['quantity'] * (-1 if m['move_type'] == 'consume' else 1) for m in moves)
        reserved = sum(r['quantity'] for r in tables['reservations'] if r['part_id'] == part['id'] and r['status'] == 'reserved')
        consumed = sum(m['quantity'] * m['unit_cost_cents'] * (1 if m['move_type'] == 'consume' else -1) for m in moves if m['move_type'] in ('consume', 'return'))
        stock.append({'part_id': part['id'], 'name': part['name'], 'on_hand': on_hand, 'reserved': reserved,
                      'available': on_hand - reserved, 'reorder_point': part['reorder_point'], 'net_consumed_cost_cents': consumed})
    stages = defaultdict(lambda: {'intervals': 0, 'hours': 0., 'cases': set()})
    for key, events in histories.items():
        events.sort(key=lambda e: (date_value(e['at']), e['event_id']))
        for a, b in zip(events, events[1:]):
            stage = stages[a['to_state']]
            stage['intervals'] += 1
            stage['hours'] += (date_value(b['at']) - date_value(a['at'])).total_seconds() / 3600
            stage['cases'].add(key)
    stage_rows = [{'stage': stage, 'intervals': v['intervals'], 'cases': len(v['cases']),
                   'total_hours': round(v['hours'], 3), 'mean_interval_hours': round(v['hours'] / v['intervals'], 3)}
                  for stage, v in sorted(stages.items())]
    marts = {'mart_service_journey': services, 'mart_receivables': aging, 'mart_daily_operations': daily_rows,
             'mart_fleet_scorecard': fleet_rows, 'mart_inventory': stock, 'mart_process_waits': stage_rows}
    empty_schemas = {'mart_process_waits': [('stage', 'TEXT'), ('intervals', 'INTEGER'), ('cases', 'INTEGER'), ('total_hours', 'REAL'), ('mean_interval_hours', 'REAL')]}
    try:
        with con:
            for name, rows in marts.items():
                if not rows:
                    if name in empty_schemas:
                        con.execute('CREATE TABLE "' + name + '" (' + ','.join('"' + c + '" ' + t for c, t in empty_schemas[name]) + ')')
                    continue
                columns = list(rows[0])
                definitions = []
                for column in columns:
                    sample = next((r[column] for r in rows if r[column] is not None), None)
                    typ = 'INTEGER' if type(sample) is int else 'REAL' if type(sample) is float else 'TEXT'
                    definitions.append('"' + column + '" ' + typ)
                con.execute('CREATE TABLE "' + name + '" (' + ','.join(definitions) + ')')
                con.executemany('INSERT INTO "' + name + '" VALUES (' + ','.join('?' for _ in columns) + ')',
                                [tuple(row[c] for c in columns) for row in rows])
        delivered = [r for r in services if r['status'] == 'delivered']
        measured = [r for r in delivered if r['history_available']]
        summary = {'as_of': as_of, 'synthetic': True, 'open_orders': sum(r['status'] not in ('delivered', 'cancelled') for r in services),
            'delivered': len(delivered), 'cycle_p50_hours': percentile([r['cycle_hours'] for r in delivered], .5),
            'cycle_p90_hours': percentile([r['cycle_hours'] for r in delivered], .9),
            'history_coverage': {'numerator': len(measured), 'denominator': len(delivered)},
            'rework': {'numerator': sum(r['rework_observed'] for r in measured), 'denominator': len(measured)},
            'invoiced_cents': sum(r['invoiced_cents'] for r in aging), 'paid_cents': sum(r['paid_cents'] for r in aging),
            'receivable_cents': sum(r['balance_cents'] for r in aging),
            'overdue_cents': sum(r['balance_cents'] for r in aging if date_value(r['due_at']) < at),
            'explicit_journey_links': len(tables['journey_links']), 'lead_population': len(tables['leads']),
            'limitations': ['Synthetic history; not measured workshop performance.', 'Elapsed state time is not paid labor time.',
                           'SLA uses elapsed calendar hours; no contractual pauses inferred.', 'No causal attribution or predicted monetary impact.']}
        assert summary['invoiced_cents'] == summary['paid_cents'] + summary['receivable_cents']
        return {'summary': summary, 'marts': marts}
    finally:
        con.close()
