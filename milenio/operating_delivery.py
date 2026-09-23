"""Join source tables, metric definitions and agent evidence in an offline delivery."""
from __future__ import annotations

import json
import shutil
from html import escape
from pathlib import Path

import xlsxwriter

from .pipeline import write_json

UI = Path(__file__).parent / 'ui'


def _metric_workbook(path, registry, sources):
    with xlsxwriter.Workbook(path, {'strings_to_formulas': False, 'strings_to_urls': False}) as book:
        heading = book.add_format({'bold': True, 'bg_color': '#173A3C', 'font_color': '#FFFFFF', 'text_wrap': True})
        wrap = book.add_format({'text_wrap': True, 'valign': 'top'})
        for name, columns, rows in [
            ('Metricas', ['metric_id','label','domain','status','value','unit','numerator','denominator','reason','definition','grain','source_tables','source_fields','process_ids','owner_role','limitations','query'], registry['metrics']),
            ('Fuentes', ['name','label','kind','grain','owner_role','source_status','row_count','primary_key','metric_ids'], sources['tables']),
            ('Campos', ['table','name','type','nullable','description','null_count'], [{'table': table['name'], **field} for table in sources['tables'] for field in table['fields']]),
        ]:
            sheet = book.add_worksheet(name)
            sheet.freeze_panes(1, 2); sheet.hide_gridlines(2)
            sheet.set_column(0, len(columns)-1, 24, wrap)
            sheet.write_row(0, 0, columns, heading)
            for index, row in enumerate(rows, 1):
                for col, key in enumerate(columns):
                    value = row.get(key)
                    if isinstance(value, (dict, list)): value = json.dumps(value, ensure_ascii=False)
                    sheet.write(index, col, value)
            sheet.autofilter(0, 0, len(rows), len(columns)-1)


def build_operating_delivery(output):
    """Enrich a staged studio before its immutable receipt is written."""
    from .agent_workspace import build_agent_workspace
    from .client_actions import write_action_workbook
    from .metric_registry import build_metric_registry
    from .operating_cases import build_operating_cases
    from .source_catalog import build_source_catalog

    output = Path(output)
    database = output / 'warehouse.sqlite'
    registry = build_metric_registry(database)
    sources = build_source_catalog(database, registry)
    agent_index = json.loads((output / 'agent_index.json').read_text(encoding='utf8'))
    native = bool(agent_index) and all(row['backend'] == 'native_codex' for row in agent_index)
    agents = build_agent_workspace(database, registry, output / ('native_runs' if native else 'agent_runs'))
    for agent in agents['agents']:
        run = agent['current_run']
        if run.get('run_path'): run['run_path'] = Path(run['run_path']).relative_to(output).as_posix()
    operations = build_operating_cases(database, registry)
    processes = [json.loads(p.read_text(encoding='utf-8-sig')) for p in sorted((output / 'processes').glob('*.json'))]
    summary = json.loads((output / 'analysis.json').read_text(encoding='utf8'))['summary']
    decisions = [*operations['decisions'], *agents['decisions']]
    metadata = {'snapshot_id': agents['source']['sha256'], 'as_of': registry['as_of'], 'synthetic': True}
    payload = {'schema_version': 4, 'metadata': metadata, 'summary': summary, 'sources': sources,
               'registry': registry, 'agents': agents, 'operations': operations, 'processes': processes,
               'decisions': decisions}
    for name, data in [('source_catalog', sources), ('metric_registry', registry), ('agent_workspace', agents), ('operating_cases', operations), ('operating_model', payload)]:
        write_json(output / (name + '.json'), data)
    write_action_workbook(output / 'Seguimiento.xlsx', decisions, metadata)
    _metric_workbook(output / 'Metricas_y_fuentes.xlsx', registry, sources)
    client_dir = output / 'client_input'; client_dir.mkdir()
    repository = Path(__file__).resolve().parent.parent
    for filename in ('client_input_blank.xlsx', 'client_input_sample.xlsx'):
        shutil.copyfile(repository / 'examples/client_data' / filename, client_dir / filename)
    content = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    html = (UI / 'operating.html').read_text(encoding='utf8').replace('__PAYLOAD__', content)
    (output / 'INICIO.html').write_text(html, encoding='utf8')
    for filename in ('operating.css', 'operating.js'):
        (output / filename).write_bytes((UI / filename).read_bytes())
    (output / 'LEEME.txt').write_text(
        'Abra INICIO.html en su navegador. Funciona sin servidor e internet.\n'
        'Las filas son sintéticas; este corte no describe la operación real del taller.\n'
        'Fuentes permite buscar todas las filas y navegar sus relaciones; Métricas expone cálculos y evidencia.\n'
        'Las prioridades OPS recorren la población completa. Las propuestas AGT provienen de lecturas acotadas por rol.\n'
        'Para seguimiento: copie Seguimiento.xlsx fuera de esta carpeta, anote responsable, estado, fecha y evidencia.\n'
        'Importe esa copia mediante studio-review; no modifique el original sellado.\n', encoding='utf8')
    return {'metrics': len(registry['metrics']), 'source_rows': sum(t['row_count'] for t in sources['tables'] if t['kind'] == 'physical_source'),
            'operational_cases': len(operations['decisions']), 'agent_proposals': len(agents['decisions'])}


def import_operating_review(report, workbook, output, reviewer):
    """Import human annotations beside, never into, the immutable source delivery."""
    from .studio import verify_studio
    from .client_actions import load_action_reviews, append_review_log
    report, workbook, output = Path(report).resolve(), Path(workbook).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(report):
        raise ValueError('Use una carpeta nueva fuera de la entrega sellada.')
    verify_studio(report)
    payload = json.loads((report / 'operating_model.json').read_text(encoding='utf8'))
    reviews = load_action_reviews(workbook, payload['decisions'], payload['metadata'])
    if not reviewer.strip(): raise ValueError('Se requiere nombre de la persona revisora.')
    output.mkdir(parents=True)
    from .pipeline import file_hash
    append_review_log(output / 'reviews.jsonl', reviews, source_hash=file_hash(workbook), reviewer=reviewer)
    write_json(output / 'review_origin.json', {'source_sha256': payload['metadata']['snapshot_id'], 'source_delivery': str(report),
               'self_reported': True, 'external_business_action': False, 'reviewer': reviewer})
    rows = ''.join('<tr>'+''.join('<td>'+escape(str(row.get(k, '')))+'</td>' for k in ('action_id','owner','status','target_date','note','outcome_evidence'))+'</tr>' for row in reviews)
    (output / 'REVISION.html').write_text('<!doctype html><html lang="es"><meta charset="utf-8"><title>Milenio · Revisión</title>'
        '<style>body{font:16px/1.6 Segoe UI;margin:32px;color:#173a3c}table{border-collapse:collapse}td,th{padding:12px;border:1px solid #ccc}</style>'
        '<h1>Seguimiento del corte</h1><p>Anotaciones declaradas por '+escape(reviewer)+'. No acreditan ejecución externa.</p>'
        '<table><thead><tr><th>ID</th><th>Responsable</th><th>Estado</th><th>Fecha</th><th>Nota</th><th>Evidencia</th></tr></thead><tbody>'+rows+'</tbody></table></html>', encoding='utf8')
    return {'status': 'pass', 'reviews': len(reviews), 'output': str(output), 'external_business_action': False}
