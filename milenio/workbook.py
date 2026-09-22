"""Readable Excel delivery: typed source tables, derived marts and live formulas."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name


LABELS = {'mart_service_journey': 'Servicios', 'mart_receivables': 'Cartera',
          'mart_daily_operations': 'Diario', 'mart_fleet_scorecard': 'Flotillas',
          'mart_inventory': 'Inventario', 'mart_process_waits': 'Tiempos proceso',
          'lifecycle_events': 'Eventos', 'journey_links': 'Vinculos journey'}


def build_workbook(database, destination, summary, agents, processes):
    destination = Path(destination)
    book = xlsxwriter.Workbook(destination, {'strings_to_formulas': False, 'strings_to_urls': False})
    book.set_properties({'title': 'Milenio | Libro de análisis y decisiones', 'author': 'Taller Milenio Analytics',
                         'comments': 'Datos sintéticos. Fórmulas con valores cacheados conciliados con SQL.',
                         'created': datetime(2026, 9, 21)})
    navy, gold, pale = '#182B3A', '#B75E36', '#EDF3F5'
    title = book.add_format({'font_name': 'Aptos', 'font_size': 22, 'bold': True, 'font_color': navy})
    note = book.add_format({'font_name': 'Aptos', 'font_size': 10, 'font_color': '#546975', 'text_wrap': True})
    text = book.add_format({'font_name': 'Aptos', 'font_size': 10, 'valign': 'top'})
    heading = book.add_format({'font_name': 'Aptos', 'bold': True, 'font_color': 'white', 'bg_color': navy})
    money = book.add_format({'font_name': 'Aptos', 'num_format': '$#,##0.00;($#,##0.00);"—"', 'font_color': '#000000'})
    count = book.add_format({'font_name': 'Aptos', 'num_format': '#,##0;(#,##0);"—"', 'font_color': '#000000'})
    cover = book.add_worksheet('INICIO')
    cover.hide_gridlines(2); cover.set_column('A:A', 3); cover.set_column('B:B', 43); cover.set_column('C:C', 26); cover.set_column('D:H', 14)
    cover.merge_range('B2:H3', 'MILENIO / Decisiones con evidencia', title)
    cover.merge_range('B4:H5', 'ESCENARIO SINTÉTICO · periodo calculado desde las tablas fuente · MXN. Los datos modelan casos de prueba, no resultados reales del taller.', note)
    con = sqlite3.connect(database)
    con.row_factory = sqlite3.Row
    source_tables = sorted(row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
    specs = {}
    row_index = 18
    cover.write(row_index, 1, 'ÍNDICE DE TABLAS', heading); cover.write(row_index, 2, 'Filas', heading)
    for index, name in enumerate(source_tables):
        sheet_name = LABELS.get(name, name[:31])
        sheet = book.add_worksheet(sheet_name)
        sheet.hide_gridlines(2); sheet.freeze_panes(5, 2); sheet.set_zoom(85)
        data = [dict(r) for r in con.execute('SELECT * FROM "' + name + '"')]
        columns = [r[1] for r in con.execute('PRAGMA table_info("' + name + '")')]
        specs[name] = (sheet_name, columns, len(data))
        sheet.merge_range(0, 0, 1, max(4, min(9, len(columns) - 1)), sheet_name, title)
        sheet.merge_range(2, 0, 2, max(4, min(9, len(columns) - 1)), f'{name} · {len(data)} filas · Fuente: warehouse.sqlite · importes *_cents en centavos MXN', note)
        sheet.write_url(3, 0, "internal:'INICIO'!B2", string='← Índice')
        for col, field in enumerate(columns):
            width = 24 if field.endswith('_at') else 18 if field.endswith('_id') or field == 'id' else 22
            if field in ('description', 'reason', 'name', 'label', 'title'): width = 34
            sheet.set_column(col, col, width, text)
        if data:
            sheet.add_table(4, 0, 4 + len(data), len(columns) - 1, {
                'name': 'Data_' + str(index), 'style': 'Table Style Medium 2',
                'columns': [{'header': c} for c in columns], 'data': [[r[c] for c in columns] for r in data]})
            if name == 'mart_receivables' and 'balance_cents' in columns:
                debt_col = columns.index('balance_cents')
                sheet.conditional_format(5, debt_col, 4 + len(data), debt_col, {'type': 'cell', 'criteria': '>', 'value': 0, 'format': book.add_format({'bg_color': '#FCE4D6', 'font_color': '#9C0006', 'num_format': '$#,##0.00;($#,##0.00);"—"'})})
            if name == 'mart_service_journey' and 'sla_status' in columns:
                sla_col = columns.index('sla_status')
                sheet.conditional_format(5, sla_col, 4 + len(data), sla_col, {'type': 'text', 'criteria': 'containing', 'value': 'breached', 'format': book.add_format({'bg_color': '#FCE4D6', 'font_color': '#9C0006'})})
        else:
            sheet.write_row(4, 0, columns, heading)
        cover.write_url(row_index + index + 1, 1, "internal:'" + sheet_name + "'!A1", string=sheet_name)
        cover.write_number(row_index + index + 1, 2, len(data), count)
    period_value = summary.get('period_label') or summary.get('as_of') or 'corte sintético'
    if 'mart_daily_operations' in specs:
        daily_sheet, daily_cols, daily_size = specs['mart_daily_operations']
        days = [row[0] for row in con.execute('SELECT day FROM mart_daily_operations ORDER BY day')]
        if days:
            period_value = f'{days[0]} → {days[-1]} ({len(days)} días)'
    con.close()
    cover.write(5, 1, 'Periodo fuente', text)
    cover.write(5, 2, period_value, text)
    def sum_formula(table, field, divide=1):
        sheet, cols, size = specs[table]
        col = xl_col_to_name(cols.index(field))
        return f"=SUM('{sheet}'!{col}6:{col}{size+5})" + (f'/{divide}' if divide != 1 else '')
    kpis = [('Facturado (MXN)', 'invoiced_cents'), ('Cobrado (MXN)', 'paid_cents'), ('Cuentas por cobrar (MXN)', 'balance_cents')]
    for row, (label, field) in enumerate(kpis, 7):
        cover.write(row, 1, label, text)
        cached_key = 'receivable_cents' if field == 'balance_cents' else field
        cover.write_formula(row, 2, sum_formula('mart_receivables', field, 100), money, summary[cached_key] / 100)
    cover.write(10, 1, 'Control: facturado - cobrado - saldo', text)
    cover.write_formula(10, 2, '=C8-C9-C10', money, 0)
    cover.write(12, 1, 'Órdenes entregadas', text)
    sheet, cols, size = specs['mart_service_journey']; status_col = xl_col_to_name(cols.index('status'))
    cover.write_formula(12, 2, f'=COUNTIF(\'{sheet}\'!{status_col}6:{status_col}{size+5},"delivered")', count, summary['delivered'])
    cover.write(13, 1, 'Órdenes abiertas', text)
    cover.write_formula(13, 2, f'=COUNTA(\'{sheet}\'!{status_col}6:{status_col}{size+5})-COUNTIF(\'{sheet}\'!{status_col}6:{status_col}{size+5},"delivered")-COUNTIF(\'{sheet}\'!{status_col}6:{status_col}{size+5},"cancelled")', count, summary['open_orders'])
    chart = book.add_chart({'type': 'line'})
    daily_name, columns, size = specs['mart_daily_operations']
    for field, color in [('opened', navy), ('delivered', gold)]:
        chart.add_series({'name': field, 'categories': [daily_name, 5, 0, size + 4, 0],
                          'values': [daily_name, 5, columns.index(field), size + 4, columns.index(field)], 'line': {'color': color}})
    chart.set_title({'name': 'Entradas y entregas por día sintético'}); chart.set_legend({'position': 'bottom'})
    cover.insert_chart('E7', chart, {'x_scale': 1.2, 'y_scale': .9})
    for name, rows in [('Agentes', agents), ('Procesos', processes)]:
        sheet = book.add_worksheet(name); sheet.hide_gridlines(2); sheet.freeze_panes(5, 1)
        sheet.merge_range('A1:F2', name + ' / catálogo ejecutable', title)
        columns = list(rows[0]) if rows else ['estado']
        values = [[json.dumps(r[c], ensure_ascii=False) if isinstance(r[c], (dict, list)) else r[c] for c in columns] for r in rows]
        sheet.set_column(0, len(columns)-1, 28, text)
        if rows: sheet.add_table(4, 0, 4+len(rows), len(columns)-1, {'columns': [{'header': c} for c in columns], 'data': values, 'style': 'Table Style Medium 2'})
    book.close()
    return {'file': destination.name, 'source_tables': len(source_tables), 'worksheets': len(source_tables) + 3,
            'formula_cells': 6, 'cached_formulas_reconciled_with_sql': True}
