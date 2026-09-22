"""Static consulting reports; no application, JavaScript, or external actions."""
from pathlib import Path
import os
import tempfile
from html import escape

def _mxn(v): return f"${(v or 0)/100:,.0f} MXN"
def _rate(x): return "Sin denominador" if x.get("rate") is None else f"{x['numerator']}/{x['denominator']} ({x['rate']:.1%})"
def _chart(path, labels, values, title, ylabel):
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "milenio-mpl-cache"))
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    import matplotlib; matplotlib.use("Agg"); matplotlib.rcParams["svg.hashsalt"]="taller-milenio-synthetic"
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,3)); ax.bar(labels,values,color="#b6572a"); ax.set_title(title); ax.set_ylabel(ylabel); ax.grid(axis="y",alpha=.2); fig.text(.01,.01,"Datos sintéticos · corte fijo",fontsize=8); fig.tight_layout(); fig.savefig(path,format="svg",metadata={"Date":None}); fig.savefig(path.with_suffix('.png'),format="png",metadata={"Date":None}); plt.close(fig)

def render_reports(result:dict, output_dir)->list[Path]:
    """Write four narrative Markdown reports, printable HTML, and an SVG when matplotlib exists."""
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True); charts=out/'charts'; charts.mkdir(exist_ok=True); paths=[]; p=result["particulares"];t=result["taller"];f=result["flotillas"];g=result["gruas"];a=result["administracion"]
    docs={
"particulares":f"""# Particulares: recorrido y operación

Corte sintético: **{result['meta']['as_of']}**. El recorrido es un estado observado, no un embudo temporal ni causal.

|Indicador|Resultado|
|---|---:|
|Leads|{p['journey']['leads']}|
|Calificados o posteriores|{_rate(p['journey']['qualified_or_later'])}|
|Ganados|{_rate(p['journey']['won'])}|
|Coincidencia candidata lead-cotización|{_rate(p['journey']['won_with_candidate_quote_match'])}|
|Pipeline abierto|{_mxn(p['journey']['quote_pipeline_cents'])}|

La conversión lead→cotización es **unknown**: falta llave explícita de atribución. La coincidencia cliente-vehículo solo prioriza revisión. Disparador: lead sin vehículo o consentimiento; dueño sugerido: recepción; evidencia: registro afectado; acción: completar datos antes de preparar un borrador de seguimiento. No hay contacto automático.
""",
"taller":f"""# Taller: WIP, capacidad y partes

|Indicador|Resultado|
|---|---:|
|Órdenes abiertas|{t['wip']['open_orders']}|
|Esperando partes|{_rate(t['wip']['waiting_parts'])}|
|Retrabajo|{_rate(t['wip']['rework'])}|
|Mediana de horas abiertas|{'Sin casos' if t['wip']['median_open_hours'] is None else t['wip']['median_open_hours']}|
|Bahías ocupadas al corte|{_rate(t['wip']['occupied_bays_instant'])}|
|Partes en/bajo reorden|{_rate(t['parts']['available_at_or_below_reorder'])}|

La capacidad es ocupación instantánea, no utilización por horas. Disparador: orden esperando parte; dueño sugerido: jefe de taller; evidencia: `waiting_order_evidence`; acción: revisar reserva, compra y disponibilidad antes de comprometer fecha o compra.
""",
"flotillas":f"""# Flotillas: comercial, contrato y entrega

|Indicador|Resultado|
|---|---:|
|Oportunidades abiertas|{f['commercial']['open_opportunities']}|
|Pipeline comercial|{_mxn(f['commercial']['pipeline_cents'])}|
|Cobertura de cuentas|{_rate(f['commercial']['account_coverage'])}|
|Contratos activos|{f['contracted']['active']}|
|Entregadas|{_rate(f['contracted']['delivered'])}|
|SLA elegible|{_rate(f['contracted']['sla_eligibility'])}|
|SLA cumplido, solo entregadas|{_rate(f['contracted']['sla_completed_met'])}|

## Priorización de investigación

|Cuenta|Prioridad|Hipótesis|
|---|---|---|
"""+''.join(f"|{x['fleet_account_id']}|{x['priority']}|{x['heuristic']}|\n" for x in f['targeting'])+"\nEs una heurística transparente: cambia al cerrar la oportunidad y no predice compra. Dueño sugerido: ventas B2B; disparador: oportunidad abierta; evidencia: oportunidad y cuenta; acción: investigación pública y propuesta para revisión humana, sin contacto ni promesa de precio/SLA.\n",
"gruas_administracion":f"""# Grúas y administración

## Grúas

|Indicador|Resultado|
|---|---:|
|Solicitudes abiertas|{g['human_review']['open_requests']}|
|Referencias humanas completas|{_rate(g['human_review']['complete_human_refs'])}|
|Cerradas con duración|{_rate(g['timing']['closed_with_duration'])}|
|Mediana solicitud→cierre|{'Sin casos' if g['timing']['median_request_to_close_hours'] is None else g['timing']['median_request_to_close_hours']} h|

La duración no mide respuesta ni llegada. Disparador: grúa abierta; dueño sugerido: supervisor; evidencia: referencias de seguridad y aprobación; acción: revisión humana. El informe no asigna ni despacha.

## Administración

|Medida separada|Resultado|
|---|---:|
|Cotizaciones|{_mxn(a['money']['quotes_cents'])}|
|Facturado|{_mxn(a['money']['invoiced_cents'])}|
|Cobrado registrado|{_mxn(a['money']['paid_cents'])}|
|Por cobrar|{_mxn(a['money']['receivable_cents'])}|
|Gasto observado|{_mxn(a['money']['expense_cents'])}|

Cobrado no equivale a ingreso reconocido. Cartera: {', '.join(k+' '+_mxn(v) for k,v in a['aging']['buckets_cents'].items())}. Disparador: saldo vencido; dueño sugerido: administración; evidencia: factura y pagos; acción: conciliación y borrador de recordatorio, sin mover dinero.
"""}
    combined=docs.pop('gruas_administracion')
    docs['gruas']=f"""# Grúas: tiempos y revisión humana

|Indicador|Resultado|
|---|---:|
|Solicitudes abiertas|{g['human_review']['open_requests']}|
|Referencias humanas completas|{_rate(g['human_review']['complete_human_refs'])}|
|Cerradas con duración|{_rate(g['timing']['closed_with_duration'])}|
|Mediana solicitud→cierre|{'Sin casos' if g['timing']['median_request_to_close_hours'] is None else g['timing']['median_request_to_close_hours']} h|

La duración mide solicitud→cierre, no respuesta ni llegada. Disparador: solicitud abierta; dueño sugerido: supervisor; evidencia: referencias de seguridad y aprobación; acción: revisión humana. Este reporte no asigna ni despacha.
"""
    docs['administracion']=f"""# Administración: facturación, cobro y cartera

|Medida separada|Resultado|
|---|---:|
|Cotizaciones|{_mxn(a['money']['quotes_cents'])}|
|Facturado|{_mxn(a['money']['invoiced_cents'])}|
|Cobrado registrado|{_mxn(a['money']['paid_cents'])}|
|Por cobrar|{_mxn(a['money']['receivable_cents'])}|
|Gasto observado|{_mxn(a['money']['expense_cents'])}|

Cobrado no equivale a ingreso reconocido. Cartera por antigüedad: {', '.join(k+' '+_mxn(v) for k,v in a['aging']['buckets_cents'].items())}. Disparador: saldo vencido; dueño sugerido: administración; evidencia: factura y pagos; acción: conciliación y borrador de recordatorio, sin mover dinero.
"""
    for name,body in docs.items():
        path=out/(name+'.md');path.write_text(body,encoding='utf-8');paths.append(path)
    specs=[('particulares',['Leads','Ganados'],[p['journey']['leads'],p['journey']['won']['numerator']],'Estado observado B2C','Registros'),('taller',['Abiertas','Partes','Retrabajo'],[t['wip']['open_orders'],t['wip']['waiting_parts']['numerator'],t['wip']['rework']['numerator']],'WIP sintético','Órdenes'),('flotillas',['Oportunidades','Activos','Entregadas'],[f['commercial']['open_opportunities'],f['contracted']['active'],f['contracted']['delivered']['numerator']],'Flotillas: comercial y servicio','Registros'),('gruas',['Abiertas','Cerradas','Revisión'],[g['human_review']['open_requests'],g['timing']['closed'],g['human_review']['complete_human_refs']['numerator']],'Grúas: estado y revisión humana','Solicitudes'),('finanzas',['Cotiz.','Fact.','Cobrado','CXC'],[a['money']['quotes_cents']/100,a['money']['invoiced_cents']/100,a['money']['paid_cents']/100,a['money']['receivable_cents']/100],'Medidas financieras sintéticas separadas','MXN')]
    for name,labels,values,title,ylabel in specs:
        chart=charts/(name+'.svg');_chart(chart,labels,values,title,ylabel)
        if chart.exists(): paths.extend([chart,chart.with_suffix('.png')])
    summary=f"<p><strong>Corte:</strong> {escape(result['meta']['as_of'])}. Datos sintéticos, descriptivos; no implican causalidad, meta ni ejecución externa.</p>"
    sections=''.join(f'<section><h2>{escape(name.replace("_"," ").title())}</h2><p>Reporte analítico con numeradores, denominadores y evidencia en el archivo Markdown homónimo.</p><figure><img src="charts/{name}.svg" alt="Gráfica {escape(name)}"><figcaption>Gráfica estática: {escape(name)}.</figcaption></figure></section>' for name in ('particulares','taller','flotillas','gruas','finanzas'))
    html='<!doctype html><html lang="es"><meta charset="utf-8"><title>Informe Taller Milenio</title><style>body{font:16px Georgia,serif;max-width:960px;margin:0 auto;color:#2d2925;background:#f7f1e7}main{background:#fffdf8;padding:36px}header{background:#2b2b27;color:#fff;padding:28px;border-bottom:5px solid #b6572a}h1{margin:0}h2{color:#934323;margin-top:34px}figure{margin:16px 0}img{max-width:100%;border:1px solid #ddd}figcaption{font:13px Arial;color:#666}@media print{body{background:#fff}main{padding:12px}header{padding:18px}}</style><header><h1>Taller Milenio · Informe analítico</h1><p>Operación, crecimiento y control gerencial</p></header><main><h2>Resumen ejecutivo</h2>'+summary+sections+'<p>Las fuentes de evidencia se expresan como tipo de entidad, ID, campo y versión en los reportes Markdown.</p></main></html>'
    path=out/'informe_ejecutivo.html';path.write_text(html,encoding='utf-8');paths.append(path);return paths
