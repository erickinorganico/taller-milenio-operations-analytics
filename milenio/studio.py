"""Integrated analyst workbench delivery: data, processes, agents and evidence."""
import csv
import hashlib
import json
import shutil
import sqlite3
import uuid
import os
import tempfile
from contextlib import closing
from html import escape
from pathlib import Path

from .pipeline import file_hash, write_json
from .scenarios import make_operating_scenario
from .warehouse import build_warehouse
from .studio_analytics import build_marts
from .workbook import build_workbook
from .agent_runtime import list_available_agents, prepare_agent_run
from .process_replay import analyze_process_events
from .process_diagrams import process_svg

ROOT = Path(__file__).resolve().parent.parent


def render_charts(analysis, output):
    os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'milenio-mpl-cache'))
    from .presentation import _chart
    import matplotlib.pyplot as plt
    plt.rcParams['svg.hashsalt'] = 'milenio-v2'
    output.mkdir(exist_ok=True)
    daily = analysis['marts']['mart_daily_operations']
    fig, ax = plt.subplots(figsize=(11, 3.6))
    x = range(len(daily))
    ax.plot(x, [r['opened'] for r in daily], color='#182b3a', label='Recepciones')
    ax.plot(x, [r['delivered'] for r in daily], color='#b75e36', label='Entregas')
    ticks = list(range(0, len(daily), max(1, len(daily)//8)))
    ax.set_xticks(ticks, [daily[i]['day'] for i in ticks], rotation=25, ha='right')
    ax.set(title='Flujo diario · historial sintético', ylabel='Órdenes'); ax.legend(frameon=False); ax.spines[['top','right']].set_visible(False)
    fig.tight_layout()
    for ext in ('svg', 'png'): fig.savefig(output / ('flujo_diario.' + ext), metadata={'Date': None})
    plt.close(fig)
    service = analysis['marts']['mart_service_journey']
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.hist([r['cycle_hours'] for r in service if r['status']=='delivered'], bins=16, color='#b75e36', edgecolor='white')
    ax.set(title='Distribución de tiempo recepción → entrega', xlabel='Horas calendario · casos sintéticos', ylabel='Órdenes entregadas')
    fig.tight_layout()
    for ext in ('svg', 'png'): fig.savefig(output / ('tiempo_servicio.' + ext), metadata={'Date': None})
    plt.close(fig)
    buckets = ['current', '1-30', '31-60', '61-90', '90+']
    rows = analysis['marts']['mart_receivables']
    _chart(output/'cartera.svg', buckets, [sum(r['balance_cents'] for r in rows if r['aging_bucket']==b)/100 for b in buckets], 'Cartera por antigüedad · sintética', 'Saldo MXN')
    stages = analysis['marts']['mart_process_waits']
    labels = {'received':'Recepción','inspected':'Inspeccionado','authorized':'Autorizado','waiting_parts':'Espera de partes','in_service':'En servicio','quality_check':'Control de calidad','rework':'Retrabajo','ready':'Listo para entrega'}
    fig, ax = plt.subplots(figsize=(9,4.5))
    ordered = sorted(stages,key=lambda r:r['total_hours'])
    ax.barh([labels.get(r['stage'],r['stage']) for r in ordered],[r['total_hours'] for r in ordered],color='#b75e36')
    ax.set(title='Tiempo observado en estados · sintético',xlabel='Horas calendario acumuladas; no horas de mano de obra')
    fig.tight_layout()
    for ext in ('svg','png'): fig.savefig(output/('estados.'+ext),metadata={'Date':None})
    plt.close(fig)


def html_table(rows, columns, limit=12):
    return '<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+escape(c)+'</th>' for c in columns)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(str(row.get(c, '')) if row.get(c) is not None else 'Sin evidencia')+'</td>' for c in columns)+'</tr>' for row in rows[:limit])+'</tbody></table></div>'


def render_dossier(output, analysis, catalog, processes, agent_runs):
    s = analysis['summary']
    cards = ''.join('<div class="metric"><span>'+escape(label)+'</span><strong>'+escape(str(value))+'</strong></div>' for label,value in [
        ('Tablas físicas de origen',27),('Órdenes entregadas',s['delivered']),('Ciclo mediano / horas',s['cycle_p50_hours']),('Ciclo p90 / horas',s['cycle_p90_hours'])])
    process_body = ''
    for process in processes:
        nodes = process.get('nodes', [])
        process_body += '<article><h3>'+escape(process['title'])+'</h3><p>'+escape(process.get('purpose',''))+'</p>'
        process_body += '<p><a href="processes/'+process['process_id']+'.json">Definición estructurada</a> · <a href="processes/'+process['process_id']+'.md">SOP, RACI y excepciones</a></p>'
        process_body += '<details><summary>Ver mapa de responsables y decisiones</summary><img alt="Mapa del proceso" src="processes/'+process['process_id']+'.svg"></details>'
        process_body += '<details><summary>Actividades, responsables y evidencia</summary>'+html_table(nodes, ['id','type','label','owner','evidence_ids'], 100)+'</details></article>'
    ledger = [{'tabla':name,'filas':spec['count'],'campos':len(spec['columns']),'relaciones':len(spec.get('refs',{}))} for name,spec in {**catalog['tables'],**catalog.get('marts',{})}.items()]
    cards_agents = ''
    for run in agent_runs:
        run_folder = run.get('folder', 'agent_runs/'+run['agent_id'])
        result_path = output/run_folder/'result.json'
        result = json.loads(result_path.read_text(encoding='utf8')) if result_path.exists() else {}
        diagnosis = result.get('result',{}).get('diagnosis','No completado; revisar run.json.')
        cards_agents += '<article><h3>'+escape(run['agent_id'])+'</h3><p>'+escape(diagnosis)+'</p><p>Modo: <b>'+escape(run['backend'])+'</b> · '+escape(run['status'])+'</p><a href="'+run_folder+'/result.json">Resultado y evidencia</a> · <a href="'+run_folder+'/tool_trace.jsonl">Traza de herramientas</a>'
        if run['backend']=='native_codex': cards_agents += ' · <a href="'+run_folder+'/plan.json">Plan elegido por el modelo</a>'
        cards_agents += '</article>'
        detail = result.get('result',{})
        drafts = detail.get('drafts',[])
        if drafts:
            cards_agents = cards_agents[:-10] + '<details><summary>Ver borradores y sustento</summary>' + html_table(drafts,['kind','text','requires_human_review'],20) + html_table(detail.get('evidence',[]),['entity_type','entity_id','field','value','version'],12) + '</details></article>'
    services = sorted(analysis['marts']['mart_service_journey'], key=lambda r:r['cycle_hours'], reverse=True)
    body = '<header><p class="eyebrow">TALLER MILENIO / WORKBENCH ANALÍTICO</p><h1>Del dato a una<br>decisión revisable.</h1><p>Procesos, tablas, análisis y agentes conectados en una entrega local.</p><span class="badge">DATOS SINTÉTICOS · CORTE '+escape(s['as_of'])+'</span></header>'
    body += '<main><section class="metrics">'+cards+'</section><section><h2>Empieza aquí</h2><p>Abre el libro para filtrar las tablas y revisar controles; consulta la base SQL para reproducir los cálculos. Los resultados de cada agente incluyen las referencias que permiten cuestionar su recomendación.</p><p><a class="button" href="Milenio_Analisis.xlsx">Abrir libro Excel</a> <a class="button" href="warehouse.sqlite">Base relacional</a> <a class="button" href="schema.sql">SQL del modelo</a></p></section>'
    body += '<section><h2>01 / Lectura operativa</h2><p>Recepciones y entregas pertenecen a fechas distintas. La distribución usa solo órdenes entregadas; las abiertas mantienen su antigüedad como otra medida.</p><img src="charts/flujo_diario.svg"><img src="charts/tiempo_servicio.svg">'+html_table(services,['work_order_id','segment','status','cycle_hours','waiting_parts_hours','sla_status'])+'</section>'
    body += '<section><h2>02 / Dinero y exposición</h2><p>Facturado: '+f"${s['invoiced_cents']/100:,.2f}"+' MXN · Cobrado: '+f"${s['paid_cents']/100:,.2f}"+' MXN · Saldo: '+f"${s['receivable_cents']/100:,.2f}"+' MXN. El control facturado = cobrado + saldo se verifica en SQL, Python y Excel.</p><img src="charts/cartera.svg">'+html_table(sorted(analysis['marts']['mart_receivables'], key=lambda r:r['balance_cents'], reverse=True),['invoice_id','customer_id','balance_cents','aging_bucket'])+'</section>'
    body += '<section><h2>03 / Flotillas e inventario</h2>'+html_table(analysis['marts']['mart_fleet_scorecard'],['fleet_account_id','services','eligible_delivered','sla_met','sla_breached','sla_unknown'])+html_table(analysis['marts']['mart_inventory'],['part_id','on_hand','reserved','available','reorder_point'])+'</section>'
    replay = json.loads((output/'process_replay.json').read_text(encoding='utf8'))
    body += '<section><h2>04 / Procesos y responsables</h2><p>Hipótesis de proceso con decisiones, excepciones y evidencia exigida. Los mapas se generan desde las definiciones versionadas.</p>'+process_body+'<h3>Variantes observadas en el historial sintético</h3><img alt="Horas acumuladas por estado" src="charts/estados.svg">'+html_table(replay['variants'],['entity_type','variant','count'],100)+'<p><a href="process_replay.json">Conformidad, intervalos y cobertura por caso</a></p></section>'
    body += '<section><h2>05 / Mesa de agentes</h2><p>El modo rules es una línea base reproducible. Las ejecuciones native_codex identifican por separado la inferencia efectivamente observada. Ningún modo realiza acciones externas del negocio.</p><p><a href="DECISIONES.md">Cuaderno de revisión</a> · <a href="review_queue.csv">Cola editable de propuestas</a></p>'+cards_agents+'</section>'
    requirements = json.loads((output/'specs/requirements.json').read_text(encoding='utf8'))['requirements']
    body += '<section><h2>06 / Catálogo de tablas</h2>'+html_table(ledger,['tabla','filas','campos','relaciones'],100)+'<p><a href="catalog.json">Diccionario y relaciones completas</a> · <a href="specs/requirements.json">Matriz de requisitos</a></p></section>'
    body += '<section><h2>07 / Especificación y aceptación</h2><p><a href="specs/product.md">Producto</a> · <a href="specs/data.md">Datos</a> · <a href="specs/agents.md">Agentes</a> · <a href="specs/analytics.md">Métricas</a> · <a href="specs/acceptance.md">Aceptación</a></p>'+html_table(requirements,['id','statement','processes','agents','acceptance'],100)+'</section><footer>Los valores son fabricados para probar el sistema. Las horas de estado no equivalen a horas pagadas de trabajo. No se ha demostrado impacto ni adopción real. Los agentes producen propuestas para revisión humana.</footer></main>'
    css = 'body{margin:0;background:#f1eee7;color:#182b3a;font:16px/1.65 Segoe UI,Arial,sans-serif}header{background:#182b3a;color:#faf7ef;padding:64px max(6vw,24px)}h1{font:600 66px/1.05 Georgia,serif;margin:18px 0 24px}.eyebrow{letter-spacing:.17em;font-size:12px}.badge{display:inline-block;background:#35505c;padding:8px 15px;font-size:12px}main{max-width:1120px;margin:auto;padding:32px}section{margin:32px 0 54px}h2{font:normal 34px Georgia,serif;border-top:2px solid #c6bcae;padding-top:25px}h3{font-size:19px;margin-bottom:8px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.metric{background:#fffdf7;padding:22px;border-bottom:3px solid #b75e36}.metric span{display:block;font-size:12px}.metric strong{font:36px Georgia,serif}a{color:#96502e}.button{display:inline-block;padding:12px 18px;background:#fffdf7;text-decoration:none;border:1px solid #bdac96;margin:8px 8px 8px 0}article{background:#fffdf7;padding:22px;margin:18px 0;overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:12px;background:#fffdf7}td,th{padding:10px;text-align:left;border-bottom:1px solid #e1d8cd;vertical-align:top}th{background:#dfe7e8}td{overflow-wrap:anywhere}img{max-width:100%;background:white;margin:14px 0}footer{font-size:13px;padding:24px;border-top:1px solid #bfb4a6}@media(max-width:800px){h1{font-size:42px}.metrics{grid-template-columns:repeat(2,1fr)}main{padding:16px}}@media print{header{padding:25px}h1{font-size:36px}section{break-before:page}article{break-inside:avoid}}'
    css += '.table-scroll{overflow-x:auto;max-width:100%}details summary{cursor:pointer;color:#96502e;padding:8px 0}.metric{min-width:0}'
    (output/'DOSSIER.html').write_text('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>Milenio · Análisis y decisiones</title><style>'+css+'</style>'+body+'</html>', encoding='utf8')


def seal_studio(output):
    """Finalize a locally prepared delivery; hashes prove integrity, not authorship."""
    output = Path(output)
    hashes = {p.relative_to(output).as_posix():file_hash(p) for p in sorted(output.rglob('*')) if p.is_file() and p != output/'receipt.json'}
    canonical = json.dumps(hashes,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    write_json(output/'receipt.json',{'version':2,'status':'pass','synthetic':True,'artifacts_sha256':hashes,
        'content_sha256':hashlib.sha256(canonical.encode('utf8')).hexdigest(),
        'source_sha256':{p.relative_to(ROOT).as_posix():file_hash(p) for p in sorted((ROOT/'milenio').glob('*.py'))},
        'scope':'relational warehouse, longitudinal marts, workbook, processes, specs and traceable agent runs'})


def write_decision_book(output, runs):
    lines = ['# Milenio / Cuaderno de revisión', '', 'Escenario sintético. Propuestas pendientes: ninguna equivale a autorización ni se ha ejecutado.', '',
             'Abra `review_queue.csv` para priorizar y asignar revisores. Conserve el original sellado y trabaje en una copia para registrar decisiones humanas.', '']
    queue = []
    for run in runs:
        folder = run.get('folder','agent_runs/'+run['agent_id'])
        payload = json.loads((output/folder/'result.json').read_text(encoding='utf8'))
        result = payload['result']
        lines.extend(['## '+run['agent_id'],'',result.get('diagnosis',''),'',f"Modo: `{payload['backend']}`. Inferencia observada: `{payload['model_invoked']}`.",''])
        for index,draft in enumerate(result.get('drafts',[]),1):
            lines.extend([f"### Borrador {index} / {draft['kind']}",'',draft['text'],''])
            queue.append({'proposal_id':run['agent_id']+'-'+str(index),'agent':run['agent_id'],'kind':draft['kind'],
                'draft':draft['text'],'status':'pending_review','human_reviewer':'','human_decision':'','decision_note':'','evidence_file':folder+'/result.json'})
        lines.extend(['Siguientes pasos para revisión:', '']+['- '+value for value in result.get('manual_next_steps',[])] + ['',f'[Resultado y referencias]({folder}/result.json) · [Traza]({folder}/tool_trace.jsonl)',''])
    (output/'DECISIONES.md').write_text('\n'.join(lines),encoding='utf8')
    with (output/'review_queue.csv').open('w',encoding='utf-8-sig',newline='') as file:
        fields=['proposal_id','agent','kind','draft','status','human_reviewer','human_decision','decision_note','evidence_file']
        writer=csv.DictWriter(file,fieldnames=fields); writer.writeheader()
        for row in queue:
            writer.writerow({k:"'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for k,v in row.items()})


def verify_studio(output):
    output = Path(output).resolve()
    receipt = json.loads((output/'receipt.json').read_text(encoding='utf8'))
    if receipt.get('version') != 2 or receipt.get('status') != 'pass' or receipt.get('synthetic') is not True:
        raise ValueError('Invalid studio receipt')
    if any(p.is_symlink() for p in output.rglob('*')): raise ValueError('Symlinks are not supported in a delivery')
    actual = {p.relative_to(output).as_posix():file_hash(p) for p in sorted(output.rglob('*')) if p.is_file() and p != output/'receipt.json'}
    canonical = json.dumps(actual,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    if actual != receipt['artifacts_sha256'] or hashlib.sha256(canonical.encode('utf8')).hexdigest() != receipt['content_sha256']:
        raise ValueError('Studio content changed after finalization')
    return {'status':'pass','files':len(actual),'content_sha256':receipt['content_sha256']}


def build_studio(output, days=90, native=False, input_path=None, events_path=None, journeys_path=None):
    output = Path(output).resolve()
    if output.exists(): raise ValueError('El destino ya existe; use una carpeta nueva.')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.parent/('.studio-' + uuid.uuid4().hex); stage.mkdir()
    try:
        if input_path:
            from .studio_input import load_studio_input
            scenario = load_studio_input(input_path,events_path,journeys_path)
        else:
            if events_path or journeys_path: raise ValueError('Event/journey inputs require a source snapshot')
            scenario = make_operating_scenario(days)
        write_json(stage/'dataset.json', scenario['dataset']); write_json(stage/'scenario.json', scenario['manifest'])
        write_json(stage/'events.json',scenario['events']); write_json(stage/'journeys.json',scenario['journeys'])
        catalog = build_warehouse(stage/'warehouse.sqlite', scenario['dataset'], scenario['events'], scenario['journeys'])
        catalog['database'] = 'warehouse.sqlite'; catalog['schema_sql'] = 'schema.sql'
        write_json(stage/'catalog.json', catalog)
        (stage/'model.mmd').write_text(catalog['mermaid'],encoding='utf8')
        analysis = build_marts(stage/'warehouse.sqlite'); write_json(stage/'analysis.json',analysis)
        with closing(sqlite3.connect(stage/'warehouse.sqlite')) as con:
            catalog['marts'] = {}
            for name,rows in analysis['marts'].items():
                columns = [r[1] for r in con.execute('PRAGMA table_info("'+name+'")')]
                catalog['marts'][name] = {'grain':columns[0], 'count':len(rows), 'columns':columns,'kind':'derived'}
            schema = '\n\n'.join(row[0]+';' for row in con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type DESC, rowid"))
            (stage/'schema.sql').write_text('PRAGMA foreign_keys = ON;\n\n'+schema+'\n',encoding='utf8')
        write_json(stage/'catalog.json',catalog)
        write_json(stage/'process_replay.json',analyze_process_events(scenario['events'],scenario['dataset']))
        csv_dir = stage/'tables'; csv_dir.mkdir()
        with closing(sqlite3.connect(stage/'warehouse.sqlite')) as con:
            for name, in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
                cur = con.execute('SELECT * FROM "'+name+'"')
                with (csv_dir/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as file:
                    writer = csv.writer(file); writer.writerow([d[0] for d in cur.description])
                    for row in cur:
                        writer.writerow(["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for v in row])
        for folder in ('processes','specs','agents'):
            if (ROOT/folder).exists(): shutil.copytree(ROOT/folder,stage/folder)
        processes = [json.loads(p.read_text(encoding='utf-8-sig')) for p in sorted((stage/'processes').glob('*.json'))]
        for process in processes:
            (stage/'processes'/(process['process_id']+'.svg')).write_text(process_svg(process),encoding='utf8')
        profiles = list_available_agents()
        runs = [prepare_agent_run(stage/'warehouse.sqlite',stage/'agent_runs'/p['id'],p['id']) for p in profiles]
        if any(r['status'] != 'completed' for r in runs): raise ValueError('Un agente base no completó su revisión.')
        if native:
            native_runs = []
            for profile in profiles:
                run = prepare_agent_run(stage/'warehouse.sqlite',stage/'native_runs'/profile['id'],profile['id'],backend='native_codex',timeout_seconds=300)
                print(json.dumps({'agent':profile['id'],'status':run['status'],'backend':'native_codex'}),flush=True)
                if run['status'] != 'completed':
                    # Preserve the entire incomplete attempt and its failure evidence.
                    stage.rename(output)
                    raise ValueError('Native execution blocked; incomplete delivery preserved without a success receipt: '+profile['id'])
                run['folder'] = 'native_runs/'+profile['id']; native_runs.append(run)
            runs = native_runs
        write_json(stage/'agent_index.json',[{'agent_id':r['agent_id'],'backend':r['backend'],'status':r['status'],'folder':r.get('folder','agent_runs/'+r['agent_id'])} for r in runs])
        workbook = build_workbook(stage/'warehouse.sqlite',stage/'Milenio_Analisis.xlsx',analysis['summary'],profiles,
                                  [{k:p[k] for k in ('process_id','title','purpose')} for p in processes])
        write_json(stage/'workbook_check.json',workbook)
        write_decision_book(stage,runs)
        render_charts(analysis,stage/'charts'); render_dossier(stage,analysis,catalog,processes,runs)
        seal_studio(stage)
        stage.rename(output)
        return {'status':'pass','output':str(output),'physical_source_tables':len(catalog['tables']),
                'marts':len(analysis['marts']),'processes':len(processes),'agents':len(runs),'worksheets':workbook['worksheets']}
    finally:
        if stage.exists() and stage.parent==output.parent and stage.name.startswith('.studio-'): shutil.rmtree(stage)
