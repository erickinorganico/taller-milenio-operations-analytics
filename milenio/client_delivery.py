"""Private local client reports and reviewable, portable delivery artifacts."""
from __future__ import annotations

import hashlib
from html import escape
import json
from pathlib import Path
import shutil
import sqlite3
import uuid

import xlsxwriter

from .client_decisions import analyze_client, compare_clients

ROOT = Path(__file__).resolve().parent.parent
MUTABLE = {'Seguimiento.xlsx', 'reviews.jsonl', 'REVISION.html'}
LABELS = {'cartera': 'Cartera', 'vencimiento': 'Datos de cobro', 'servicio': 'Servicio',
          'facturacion': 'Conciliación', 'inventario': 'Partes'}
STATES = {'received': 'Recibida', 'in_service': 'En servicio', 'waiting_parts': 'Espera de partes',
          'rework': 'Retrabajo', 'ready': 'Lista', 'delivered': 'Entregada', 'cancelled': 'Cancelada'}
CSS = '''
:root{--ink:#142d3d;--muted:#526574;--blue:#155d80;--paper:#f5f3ee;--line:#d4dedf;--red:#9b3532;--amber:#845619}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 Segoe UI,Arial,sans-serif}a{color:var(--blue)}
header{background:var(--ink);color:white;padding:48px max(24px,calc((100vw - 1180px)/2)) 36px}header p{max-width:850px;color:#cfdee4}
header a{color:#c6edf5}.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:700}h1{font-size:clamp(30px,4vw,49px);line-height:1.13;margin:14px 0}h2{font-size:26px;margin:0 0 14px}h3{margin:4px 0 10px;font-size:19px}
main{max-width:1228px;margin:auto;padding:24px}nav{display:flex;gap:18px;flex-wrap:wrap;margin:20px 0}.label{display:inline-block;padding:3px 10px;border-radius:3px;font-size:12px;font-weight:700;background:#e4eef2;color:var(--ink)}
.p1{background:#f9e3df;color:var(--red)}.p2{background:#fff0d0;color:var(--amber)}.p3{background:#e4eef2;color:var(--blue)}
.summary{display:grid;grid-template-columns:repeat(4,1fr);background:white;border:1px solid var(--line);margin:20px 0 28px}.metric{padding:22px;border-right:1px solid var(--line)}.metric:last-child{border:0}.metric strong{display:block;font-size:28px;line-height:1.3}.metric span{font-size:13px;color:var(--muted)}
section{background:white;border:1px solid var(--line);padding:26px;margin:24px 0}.note{padding:14px 18px;background:#edf3f4;border-left:4px solid var(--blue);font-size:14px}.muted,small{color:var(--muted)}
.actions{list-style:none;padding:0;counter-reset:actions}.actions>li{border-top:1px solid var(--line);padding:20px 0;display:grid;grid-template-columns:56px 1fr;gap:14px;counter-increment:actions}.actions>li:before{content:counter(actions,decimal-leading-zero);font-size:27px;color:#7997a3}.actions p{margin:7px 0}.action-top{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.action-top h3{flex:1;min-width:210px;margin:0}
.table-wrap{overflow:auto;max-height:550px;border:1px solid var(--line)}table{border-collapse:collapse;width:100%;font-size:14px;white-space:normal}th,td{padding:11px 13px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}th{background:#eaf0f1;position:sticky;top:0;white-space:nowrap}td.num{text-align:right;white-space:nowrap}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}.grid section{margin:0}details{margin:12px 0;font-size:13px}summary{cursor:pointer;color:var(--blue)}code{overflow-wrap:anywhere;font-size:12px}.bar-row{display:grid;grid-template-columns:120px 1fr 115px;align-items:center;gap:10px;margin:12px 0;font-size:13px}.bar{height:15px;background:var(--blue);min-width:1px}.bar-bg{background:#e8eff1}footer{padding:30px 0;color:var(--muted);font-size:13px}
input[type=search]{font:inherit;padding:10px;border:1px solid #93a9b2;width:min(100%,500px);margin-bottom:14px}.hidden{display:none!important}button{background:var(--blue);color:white;padding:10px 16px;border:0;cursor:pointer;font:inherit}.links{display:flex;gap:16px;flex-wrap:wrap}.empty{padding:20px;background:#f1f5f6}
@media(max-width:700px){main{padding:14px}.summary{grid-template-columns:1fr 1fr}.metric{padding:15px;border-bottom:1px solid var(--line)}.grid{grid-template-columns:1fr}section{padding:18px}.actions>li{grid-template-columns:32px 1fr;gap:8px}.bar-row{grid-template-columns:90px 1fr 95px;font-size:12px}header{padding:32px 20px}.metric strong{font-size:24px}}
@media print{header{padding:15px;background:white;color:black}header p{color:#333}nav,button,input,.links{display:none}main{max-width:none;padding:0}section,.summary{break-inside:avoid;margin:10px 0;padding:12px}.table-wrap{max-height:none;overflow:visible}th{position:static}.actions>li{break-inside:avoid}body{font-size:12px;background:white}}
'''


def money(value):
    return 'Sin datos' if value is None else f'${value / 100:,.2f}'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def _safe_output(output, synthetic, private_root=None):
    output = Path(output).resolve()
    private = Path(private_root or ROOT / 'private').resolve()
    if not synthetic and not output.is_relative_to(private):
        raise ValueError('Datos de cliente: use una carpeta nueva dentro de private/; no se permite publicar este reporte')
    if output.exists():
        raise ValueError('La salida ya existe; use otra carpeta para conservar el corte anterior')
    return output


def _table(headers, rows, table_id=''):
    heading = ''.join('<th>' + escape(h) + '</th>' for h in headers)
    body = ''.join('<tr>' + ''.join('<td>' + escape(str(v if v is not None else 'Sin dato')) + '</td>' for v in row) + '</tr>' for row in rows)
    if not body:
        return '<p class="empty">Sin registros aportados para esta vista. No equivale a ausencia de actividad.</p>'
    return f'<div class="table-wrap"><table id="{table_id}"><thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table></div>'


def _page(title, subtitle, body, meta):
    synthetic = meta['synthetic']
    label = 'Muestra ficticia · practicar sin datos del negocio' if synthetic else 'Confidencial · copia local del cliente'
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · Milenio</title><style>{CSS}</style></head><body>
<header><div class="eyebrow">Milenio / Mesa de trabajo del cliente</div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p><span class="label">{label}</span><p><small style="color:inherit">Corte: {escape(meta['as_of'])} · Identificador: {escape(meta['snapshot_id'])}</small></p></header>
<main>{body}<footer>Importes MXN. Fechas normalizadas a UTC. Los resultados describen los registros aportados. No se contactó a clientes ni se ejecutaron cobros, compras o cambios operativos.</footer></main></body></html>'''


def write_report(path, analysis):
    a, s = analysis, analysis['summary']
    e = escape
    metrics = [('Saldo documentado', money(s['balance_cents']), 'Facturas vigentes menos pagos aportados'),
               ('Saldo vencido', money(s['overdue_balance_cents']), 'Subconjunto del saldo; no sumarlo'),
               ('Servicios abiertos', s['open_orders'], 'Estados abiertos del extracto'),
               ('Revisar hoy', s['p1_reviews'], 'Casos P1, pendientes de validación')]
    kpis = ''.join(f'<div class="metric"><span>{e(label)}</span><strong>{e(str(value if value is not None else "Sin datos"))}</strong><span>{e(note)}</span></div>' for label, value, note in metrics)
    actions = ''
    for d in a['decisions']:
        evidence = _table(['Fuente', 'Registro', 'Campo', 'Valor'], [[x['table'], x['record_id'], x['field'], x['value']] for x in d['evidence']])
        actions += f'''<li data-search="{e((d['title']+' '+d['owner_role']+' '+d['category']).lower(), quote=True)}"><div><div class="action-top"><span class="label {d['priority'].lower()}">{d['priority']}</span><h3>{e(d['title'])}</h3></div>
<p>{e(d['why_now'])}</p><p><b>Siguiente paso:</b> {e(d['recommended_next_step'])}</p><p class="muted">Responsable sugerido: {e(d['owner_role'])}{' · Saldo: '+money(d['amount_at_risk_cents']) if d['amount_at_risk_cents'] is not None else ''}</p>
{'<p><b>Falta confirmar:</b> '+e('; '.join(d['missing_evidence']))+'</p>' if d['missing_evidence'] else ''}<details><summary>Ver evidencia y referencia para seguimiento</summary><p><code>{e(d['action_id'])}</code></p>{evidence}</details></div></li>'''
    buckets = {}
    for r in a['receivables']:
        if r['balance_cents']:
            buckets[r['aging_bucket']] = buckets.get(r['aging_bucket'], 0) + r['balance_cents']
    peak = max(buckets.values(), default=1)
    bars = ''.join(f'<div class="bar-row"><span>{e(k)}</span><div class="bar-bg"><div class="bar" style="width:{v / peak * 100:.1f}%"></div></div><span>{money(v)}</span></div>' for k, v in buckets.items())
    coverage = _table(['Fuente', 'Filas', 'Interpretación'], [[r['table'], r['rows'], r['meaning']] for r in a['coverage']])
    warnings = ''.join(f'<li>{e(r["check"])}: {r["missing"]} de {r["population"]}.</li>' for r in a['warnings'])
    body = f'''<nav><a href="#hoy">Prioridades</a><a href="#cartera">Cartera</a><a href="#servicios">Servicios</a><a href="#partes">Partes</a><a href="#calidad">Calidad</a></nav>
<div class="links"><a href="Gerencia.xlsx">Abrir libro gerencial</a><a href="Seguimiento.xlsx">Asignar responsables en Excel</a><a href="GUIA.html">Cómo usar esta entrega</a><button onclick="window.print()">Imprimir informe</button></div>
<div class="summary">{kpis}</div>
<p class="note">Empiece por tres casos. Confirme la evidencia, asigne responsable y fecha en <b>Seguimiento.xlsx</b>. Guarde el archivo para registrar la revisión. Una prioridad es una propuesta; nadie ha sido asignado todavía.</p>
<section id="hoy"><div class="eyebrow">01 / Reunión de decisiones</div><h2>Qué revisar primero</h2><p>P1: hoy · P2: esta semana · P3: completar información. Cartera pasa a P1 desde 15 días de atraso; servicio con promesa vencida o retrabajo, también. El criterio es visible y revisable.</p>
<label for="find">Buscar caso, área o responsable sugerido</label><br><input id="find" type="search" placeholder="Ejemplo: Administración"><p id="count" class="muted" aria-live="polite">{len(a['decisions'])} casos</p><ol class="actions" id="actions">{actions}</ol>{'<p class="empty">No se activaron reglas con los registros recibidos. Revise la cobertura antes de concluir que no hay pendientes.</p>' if not actions else ''}</section>
<section id="cartera"><div class="eyebrow">02 / Administración</div><h2>Qué saldos requieren conciliación</h2><p>Facturado: <b>{money(s['invoiced_cents'])}</b> · pagos aportados: <b>{money(s['paid_cents'])}</b> · saldo: <b>{money(s['balance_cents'])}</b>. Los pagos no representan efectivo disponible ni utilidad.</p>{bars}
{_table(['Factura', 'Cliente (alias)', 'Importe', 'Pagos', 'Saldo', 'Antigüedad'], [[r['invoice_id'],r['customer_ref'],money(r['amount_cents']),money(r['paid_cents']),money(r['balance_cents']),r['aging_bucket']] for r in a['receivables']])}</section>
<section id="servicios"><div class="eyebrow">03 / Taller y recepción</div><h2>Qué impide avanzar o entregar</h2>{_table(['Orden', 'Estado', 'Responsable', 'Compromiso UTC', 'Bloqueo', 'Facturación'], [[r['order_id'],STATES[r['status']],r.get('technician_ref'),r.get('promised_at'),r.get('block_reason'),r['billing_observation']] for r in a['service']])}</section>
<section id="partes"><div class="eyebrow">04 / Partes</div><h2>Qué disponibilidad conviene revisar</h2><p>Disponible = existencia − reservado. La diferencia al mínimo es una señal de revisión, no una orden de compra.</p>{_table(['Parte', 'Descripción', 'Existencia', 'Reservado', 'Disponible', 'Mínimo', 'Diferencia'], [[r['part_id'],r['description'],r['on_hand'],r['reserved'],r['available'],r['reorder_point'],r['gap_units']] for r in a['inventory']])}</section>
<section id="calidad"><div class="eyebrow">05 / Confianza y alcance</div><h2>Antes de decidir</h2>{coverage}<ul>{warnings}</ul><ul>{''.join('<li>'+e(line)+'</li>' for line in a['limits'])}</ul><p>El corte normalizado y el modelo local se conservan en esta entrega: <a href="analysis.json">análisis</a>, <a href="snapshot.json">datos normalizados</a>, <a href="warehouse.sqlite">tablas locales</a>, <a href="receipt.json">recibo de integridad</a>. Conserve la entrada original por separado. Las referencias se muestran tal como fueron aportadas; confirme que son alias y que las notas no contienen datos personales.</p></section>
<script>const input=document.getElementById('find');input.addEventListener('input',()=>{{let n=0;for(const row of document.querySelectorAll('#actions>li')){{const show=row.dataset.search.includes(input.value.toLowerCase());row.classList.toggle('hidden',!show);if(show)n++;}}document.getElementById('count').textContent=n+' casos visibles';}});</script>'''
    Path(path).write_text(_page(a['metadata']['business_name'], 'Una reunión semanal con casos concretos, evidencia y responsables por acordar.', body, a['metadata']), encoding='utf-8')


def write_guide(path, meta):
    body = '''<section><h2>Primera reunión: 30 minutos</h2><ol>
<li><b>5 min · Verificar el corte.</b> Abra INICIO.html. Confirme negocio, fecha y cobertura. Una tabla vacía significa que no se aportaron datos.</li>
<li><b>10 min · Elegir tres casos.</b> Revise los P1 y su evidencia. Confirme saldo, estado y contexto con el responsable de la fuente.</li>
<li><b>10 min · Acordar el siguiente paso.</b> Abra Seguimiento.xlsx. Complete responsable, estado, fecha objetivo y nota sólo para los casos revisados. Use pending si todavía no hay una decisión.</li>
<li><b>5 min · Fijar la próxima revisión.</b> Guarde el archivo y entréguelo al analista para importar la revisión. No marque done sin describir lo realizado y aportar una referencia de evidencia.</li></ol></section>
<section><h2>La próxima semana</h2><p>Actualice una copia de la plantilla con otro identificador y fecha de corte. Incluya el historial de pagos de cada factura aportada, no sólo los pagos de la última semana. Mantenga los mismos identificadores y alias del negocio.</p><p>El analista genera una carpeta nueva y compara ambos cortes. Un caso que desaparece del extracto queda pendiente de verificar. Un saldo menor es una variación observada, no un ahorro atribuible a este servicio.</p></section>
<section><h2>Qué archivo usar</h2><table><tr><th>Archivo</th><th>Uso</th></tr><tr><td>INICIO.html</td><td>Reunión, búsqueda de casos e impresión.</td></tr><tr><td>Gerencia.xlsx</td><td>Filtrar y consultar prioridades, saldos, servicios, partes y calidad.</td></tr><tr><td>Seguimiento.xlsx</td><td>Único libro para editar responsables, fechas, estados y evidencia de cierre.</td></tr><tr><td>Seguimiento_original.xlsx</td><td>Plantilla original conservada para comprobar el origen.</td></tr><tr><td>reviews.jsonl / REVISION.html</td><td>Aparecen después de importar la revisión: historial local y resumen de lo declarado por personas.</td></tr><tr><td>receipt.json</td><td>Hashes de los archivos inmutables; no certifica veracidad ni identidad del revisor.</td></tr></table></section>
<section><h2>Si un dato está mal</h2><p>Corrija la fuente y genere otro corte. No edite analysis.json, Gerencia.xlsx ni los saldos del informe para hacerlos coincidir. Los errores de entrada indican hoja, fila y columna. No elimine registros sólo para hacer pasar una validación.</p><p>No ingrese nombres, teléfonos, placas, domicilios o documentos: use alias. Las notas de seguimiento también pueden ser sensibles. La carpeta privada no está cifrada por el producto; el responsable de la entrega debe aplicar el acceso y retención acordados.</p></section>
<p><a href="INICIO.html">Volver a prioridades</a></p>'''
    Path(path).write_text(_page('Cómo trabajar con esta entrega', 'Guía para gerencia, recepción, administración y partes.', body, meta), encoding='utf-8')


def write_management_book(path, analysis):
    a = analysis
    with xlsxwriter.Workbook(str(path), {'strings_to_formulas': False, 'strings_to_urls': False}) as book:
        book.set_properties({'title': 'Milenio · Revisión gerencial', 'author': 'Milenio Analytics'})
        header = book.add_format({'bold': True, 'bg_color': '#142D3D', 'font_color': 'white', 'text_wrap': True})
        text = book.add_format({'text_wrap': True, 'valign': 'top'})
        amount = book.add_format({'num_format': '$#,##0.00;[Red]-$#,##0.00', 'valign': 'top'})

        def sheet(name, columns, rows):
            ws = book.add_worksheet(name)
            ws.freeze_panes(1, 0)
            ws.set_row(0, 32)
            ws.set_landscape()
            ws.fit_to_pages(1, 0)
            ws.repeat_rows(0)
            for col, (title, field, kind) in enumerate(columns):
                ws.write_string(0, col, title, header)
                ws.set_column(col, col, 42 if kind == 'long' else 23)
            for i, row in enumerate(rows, 1):
                for j, (_, field, kind) in enumerate(columns):
                    value = row.get(field)
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    if value is None:
                        ws.write_string(i, j, 'Sin dato', text)
                    elif kind == 'money':
                        ws.write_number(i, j, value / 100, amount)
                    elif isinstance(value, (int, float)) and not isinstance(value, bool):
                        ws.write_number(i, j, value, text)
                    else:
                        ws.write_string(i, j, str(value), text)
            if rows:
                ws.autofilter(0, 0, len(rows), len(columns)-1)
            return ws

        intro = [{'label': 'Negocio', 'value': a['metadata']['business_name']}, {'label': 'Corte UTC', 'value': a['metadata']['as_of']},
                 {'label': 'Datos', 'value': 'Ficticios' if a['metadata']['synthetic'] else 'Cliente · confidencial'},
                 {'label': 'Cómo decidir', 'value': 'Filtre Prioridades por P1, confirme evidencia y complete Seguimiento.xlsx.'},
                 {'label': 'Alcance', 'value': 'Sólo registros aportados; no se confirma integridad del universo.'}]
        intro += [{'label': 'Límite', 'value': x} for x in a['limits']]
        sheet('INICIO', [('Campo', 'label', 'text'), ('Contenido', 'value', 'long')], intro)
        sheet('Prioridades', [('Prioridad','priority','text'),('Caso','title','long'),('Responsable sugerido','owner_role','text'),('Motivo','why_now','long'),('Siguiente paso','recommended_next_step','long'),('Saldo relacionado MXN','amount_at_risk_cents','money'),('Por confirmar','missing_evidence','long'),('Referencia','action_id','text')], a['decisions'])
        sheet('Cartera', [('Factura','invoice_id','text'),('Cliente alias','customer_ref','text'),('Vencimiento UTC','due_at','text'),('Importe MXN','amount_cents','money'),('Pagos MXN','paid_cents','money'),('Saldo MXN','balance_cents','money'),('Antigüedad','aging_bucket','text'),('Pagos vinculados','payment_ids','long')], a['receivables'])
        sheet('Servicios', [('Orden','order_id','text'),('Estado','status','text'),('Cliente alias','customer_ref','text'),('Técnico alias','technician_ref','text'),('Compromiso UTC','promised_at','text'),('Bloqueo','block_reason','long'),('Facturación','billing_observation','long')], a['service'])
        sheet('Partes', [('Parte','part_id','text'),('Descripción','description','long'),('Existencia','on_hand','number'),('Reservado','reserved','number'),('Disponible','available','number'),('Mínimo','reorder_point','number'),('Diferencia unidades','gap_units','number')], a['inventory'])
        sheet('Calidad', [('Fuente','table','text'),('Filas','rows','number'),('Estado','status','text'),('Interpretación','meaning','long')], a['coverage'])
        sheet('Faltantes', [('Revisión','check','long'),('Sin dato','missing','number'),('Población','population','number')], a['warnings'])


def _warehouse(path, snapshot, analysis):
    con = sqlite3.connect(path)
    try:
        for name, rows, key in [(name, rows, {'orders':'order_id','invoices':'invoice_id','payments':'payment_id','inventory':'part_id'}[name]) for name, rows in snapshot['tables'].items()]:
            # Canonical typed JSON retains nulls and integer cents. Curated views expose useful fields.
            con.execute(f'CREATE TABLE "{name}" (record_id TEXT PRIMARY KEY, data_json TEXT NOT NULL CHECK(json_valid(data_json))) STRICT')
            con.executemany(f'INSERT INTO "{name}" VALUES (?,?)', [(r[key], json.dumps(r, ensure_ascii=False)) for r in rows])
        con.execute('CREATE TABLE review_priorities (action_id TEXT PRIMARY KEY, priority TEXT NOT NULL, category TEXT NOT NULL, title TEXT NOT NULL, evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json))) STRICT')
        con.executemany('INSERT INTO review_priorities VALUES (?,?,?,?,?)', [(d['action_id'], d['priority'], d['category'], d['title'], json.dumps(d, ensure_ascii=False)) for d in analysis['decisions']])
        con.execute('CREATE TABLE receivables (invoice_id TEXT PRIMARY KEY, amount_cents INTEGER NOT NULL, paid_cents INTEGER NOT NULL, balance_cents INTEGER NOT NULL, CHECK(amount_cents-paid_cents=balance_cents)) STRICT')
        con.executemany('INSERT INTO receivables VALUES (?,?,?,?)', [(r['invoice_id'],r['amount_cents'],r['paid_cents'],r['balance_cents']) for r in analysis['receivables']])
        con.commit()
    finally:
        con.close()


def seal_client(output, synthetic):
    output = Path(output)
    analysis = json.loads((output / 'analysis.json').read_text(encoding='utf-8'))
    artifacts = {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.relative_to(output).as_posix() not in MUTABLE | {'receipt.json'}}
    receipt = {'format': 'milenio-client-v3', 'synthetic': synthetic, 'status': 'pass', 'artifacts_sha256': artifacts,
               'snapshot_id':analysis['metadata']['snapshot_id'],'as_of':analysis['metadata']['as_of'],
               'source_hashes':analysis['source_hashes'],
               'code_sha256':{p.name:sha(p) for p in sorted((ROOT / 'milenio').glob('client_*.py'))},
               'mutable_files': sorted(MUTABLE), 'scope': 'Integridad de artefactos inmutables; no acredita verdad de la fuente o aprobación humana.'}
    write_json(output / 'receipt.json', receipt)
    return receipt


def verify_client(output):
    output = Path(output)
    receipt = json.loads((output / 'receipt.json').read_text(encoding='utf-8'))
    if receipt.get('format') != 'milenio-client-v3' or receipt.get('status') != 'pass':
        raise ValueError('Recibo de cliente inválido')
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob('*')):
        raise ValueError('La entrega no admite enlaces simbólicos')
    actual = {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.relative_to(output).as_posix() not in MUTABLE | {'receipt.json'}}
    if actual != receipt.get('artifacts_sha256') or not {'analysis.json', 'snapshot.json', 'INICIO.html', 'Seguimiento_original.xlsx'}.issubset(actual):
        raise ValueError('La entrega fue alterada o está incompleta; regenere desde el archivo fuente')
    analysis = json.loads((output / 'analysis.json').read_text(encoding='utf-8'))
    for field in ('snapshot_id','as_of','synthetic'):
        if receipt.get(field) != analysis['metadata'][field]:
            raise ValueError('La identidad del recibo no corresponde al análisis')
    if receipt.get('source_hashes') != analysis['source_hashes'] or receipt.get('mutable_files') != sorted(MUTABLE):
        raise ValueError('Contrato de fuentes o archivos mutables alterado')
    return receipt


def build_client(snapshot, output, private_root=None):
    from .client_actions import write_action_workbook
    output = _safe_output(output, snapshot['metadata']['synthetic'], private_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.parent / ('.' + output.name + '-' + uuid.uuid4().hex)
    stage.mkdir()
    try:
        analysis = analyze_client(snapshot)
        write_json(stage / 'snapshot.json', snapshot)
        write_json(stage / 'analysis.json', analysis)
        _warehouse(stage / 'warehouse.sqlite', snapshot, analysis)
        write_management_book(stage / 'Gerencia.xlsx', analysis)
        write_action_workbook(stage / 'Seguimiento_original.xlsx', analysis['decisions'], analysis['metadata'])
        shutil.copyfile(stage / 'Seguimiento_original.xlsx', stage / 'Seguimiento.xlsx')
        write_report(stage / 'INICIO.html', analysis)
        write_guide(stage / 'GUIA.html', analysis['metadata'])
        receipt = seal_client(stage, analysis['metadata']['synthetic'])
        stage.rename(output)
        return {'status': 'pass', 'output': str(output), 'decisions': len(analysis['decisions']), 'synthetic': receipt['synthetic']}
    except Exception:
        # Preserve failed staging for diagnostics; no successful receipt is published.
        raise


def load_client_report(path):
    verify_client(path)
    return json.loads((Path(path) / 'analysis.json').read_text(encoding='utf-8'))


def build_comparison(before, after, output, private_root=None):
    before_path, after_path = Path(before), Path(after)
    before, after = load_client_report(before_path), load_client_report(after_path)
    comparison = compare_clients(before, after)
    reviews = latest_reviews(before_path)
    reviews.update(latest_reviews(after_path))
    for item in comparison['action_continuity']:
        item['human_review'] = reviews.get(item['action_id'])
    output = _safe_output(output, after['metadata']['synthetic'], private_root)
    output.mkdir(parents=True)
    write_json(output / 'comparison.json', comparison)
    states = {'new': 'Nuevo en el extracto', 'missing_in_later_extract': 'Ausente; verificar', 'observed_in_both': 'Presente en ambos', 'invoice_amount_changed_review': 'Importe de factura modificado; conciliar'}
    invoice_rows = [[c['record_id'], states[c['state']], money(c['before']['balance_cents']) if c['before'] else 'Sin registro', money(c['after']['balance_cents']) if c['after'] else 'Sin registro', money(c['observed_payment_increase_cents'])] for c in comparison['changes'] if c['table'] == 'receivables']
    service_rows = [[c['record_id'],states[c['state']],STATES[c['before']['status']] if c['before'] else 'Sin registro',STATES[c['after']['status']] if c['after'] else 'Sin registro'] for c in comparison['changes'] if c['table'] == 'service']
    inventory_rows = [[c['record_id'],states[c['state']],c['before']['available'] if c['before'] else 'Sin registro',c['after']['available'] if c['after'] else 'Sin registro',c['after']['gap_units'] if c['after'] else 'Sin registro'] for c in comparison['changes'] if c['table'] == 'inventory']
    continuity_states = {'new':'Nueva señal', 'still_flagged':'Sigue señalada', 'not_flagged_now_requires_review':'Ya no activa regla; verificar cierre'}
    body = '<section><h2>Qué cambió entre los cortes</h2><p>Antes: '+escape(comparison['before_snapshot'])+' · después: '+escape(comparison['after_snapshot'])+'</p><ul>'+''.join('<li>'+escape(x)+'</li>' for x in comparison['limits'])+'</ul></section>'
    body += '<section><h2>Saldos y pagos documentados</h2>'+_table(['Factura','Cobertura','Saldo anterior','Saldo actual','Variación de pagos'],invoice_rows)+'</section>'
    body += '<section><h2>Servicios</h2>'+_table(['Orden','Cobertura','Estado anterior','Estado actual'],service_rows)+'</section>'
    body += '<section><h2>Disponibilidad de partes</h2>'+_table(['Parte','Cobertura','Disponible antes','Disponible después','Diferencia actual al mínimo'],inventory_rows)+'</section>'
    body += '<section><h2>Continuidad de las prioridades</h2><p>Las asignaciones y cierres son declaraciones humanas importadas, no comprobaciones de ejecución. Una señal que persiste después de un cierre declarado requiere conciliación.</p>'+_table(['Caso','Lectura','Estado declarado','Responsable','Fecha objetivo','Referencia'],[[c['title'],continuity_states[c['state']],(c['human_review'] or {}).get('status'),(c['human_review'] or {}).get('owner'),(c['human_review'] or {}).get('target_date'),c['action_id']] for c in comparison['action_continuity']])+'</section>'
    (output / 'COMPARACION.html').write_text(_page('La siguiente revisión', 'Cambios observados y pendientes por confirmar; no atribución de resultados.', body, after['metadata']),encoding='utf-8')
    return {'status':'pass','output':str(output),'changes':len(comparison['changes'])}


def latest_reviews(report):
    """Local self-reported annotations; not an identity or authorization proof."""
    path = Path(report) / 'reviews.jsonl'
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            event = json.loads(line)
            for item in event['reviews']:
                result[item['action_id']] = item
    return result


def import_client_review(workbook, report, reviewer):
    from .client_actions import load_action_reviews, append_review_log
    analysis = load_client_report(report)
    if not analysis['metadata']['synthetic'] and not Path(report).resolve().is_relative_to((ROOT / 'private').resolve()):
        raise ValueError('La revisión con datos de cliente debe guardarse dentro de private/')
    reviews = load_action_reviews(workbook, analysis['decisions'], analysis['metadata'])
    result = append_review_log(Path(report) / 'reviews.jsonl', reviews, sha(workbook), reviewer)
    # An idempotent import of an older workbook must not roll the displayed review back.
    last_event = json.loads([line for line in (Path(report) / 'reviews.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()][-1])
    reviews = last_event['reviews']
    reviewer = last_event['reviewer']
    titles = {d['action_id']:d['title'] for d in analysis['decisions']}
    cutoff = analysis['metadata']['as_of'][:10]
    rows = [[titles[r['action_id']], r['owner'], r['status'], r['target_date'],
             'Vencida al corte; revisar' if r['target_date'] and r['target_date'] < cutoff and r['status'] not in ('done','dismissed') else 'Sin alerta de fecha',
             r['note'], r['outcome_evidence']] for r in reviews]
    body = '<section><h2>Lo que se registró en la reunión</h2><p>Revisor declarado: '+escape(reviewer)+'. Las notas y evidencias son autodeclaradas. La importación no acredita identidad, ejecución, autorización ni resultado del negocio.</p>'+_table(['Caso','Responsable','Estado','Fecha','Revisión de fecha','Nota','Evidencia declarada'],rows)+'</section><p><a href="INICIO.html">Volver a prioridades</a></p>'
    (Path(report) / 'REVISION.html').write_text(_page('Seguimiento de acuerdos', 'Registro local de revisión humana.',body,analysis['metadata']),encoding='utf-8')
    return result


def run_client_command(args):
    from datetime import datetime, timezone
    import re
    from .client_input import ClientInputError, load_client_input, write_client_template
    try:
        if args.command == 'client-template':
            result = {'status':'pass','output':str(write_client_template(args.output, sample=args.sample,
                      as_of=args.as_of, business_name=args.business, snapshot_id=args.snapshot_id))}
        elif args.command == 'client-analyze':
            # Quality error files may contain source identifiers. Keep them private even for a bad/unknown input.
            if args.errors and not Path(args.errors).resolve().is_relative_to((ROOT / 'private').resolve()):
                raise ValueError('--errors debe apuntar dentro de private/')
            try:
                snapshot = load_client_input(args.input)
            except ClientInputError as exc:
                document = {'status':'fail','issues':exc.issues,'report_generated':False}
                if args.errors:
                    target = Path(args.errors)
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with target.open('x',encoding='utf-8') as handle:
                        json.dump(document,handle,ensure_ascii=False,indent=2)
                print(json.dumps(document,ensure_ascii=True))
                return 2
            slug = re.sub(r'[^a-zA-Z0-9_-]+','-',snapshot['metadata']['snapshot_id'])[:70]
            output = args.output or ROOT / 'private' / 'clients' / (slug + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:6])
            result = build_client(snapshot,output)
        elif args.command == 'client-review':
            result = import_client_review(args.input,args.report,args.reviewer)
        elif args.command == 'client-compare':
            result = build_comparison(args.before,args.after,args.output)
        else:
            result = verify_client(args.input)
        print(json.dumps(result,ensure_ascii=True))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({'status':'fail','error':str(exc)},ensure_ascii=True))
        return 2
