"""Export version-controlled V5 contracts from model metadata; never query client rows."""
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','milenio_web.settings')
import django
django.setup()
from workshop.catalog import SOURCE_MODELS,SOURCE_TITLES
from workshop.intelligence import build_metric_catalog

def cell(value):
    return str(value).replace('|','\\|').replace('\n',' ')

lines=['# Diccionario de fuentes · V5','', 'Generado con `scripts/export_web_contracts.py` desde la migración/modelos y catálogo publicados. No contiene filas ni información del cliente. Cada entidad usa clave primaria propia; las relaciones indicadas son claves foráneas. El campo vacío admitido no equivale a valor cero. La ruta Fuentes muestra filas, búsqueda, navegación y CSV para los roles autorizados.','']
for key,model in SOURCE_MODELS.items():
    lines.extend([f'## {SOURCE_TITLES[key]} · {model.__name__}', '',f'Tabla: `{model._meta.db_table}`. Ruta: `/data/{key}/`. Una fila corresponde a una instancia de {model.__name__}.','', '| Campo | Tipo | Nulo | Relación / opciones / unicidad |','| --- | --- | --- | --- |'])
    for f in model._meta.fields:
        details=[]
        if f.is_relation: details.append(f'→ {f.related_model.__name__}.{f.target_field.name}; {f.remote_field.on_delete.__name__}')
        if f.unique: details.append('único')
        if f.choices: details.append('; '.join(f'{k}: {v}' for k,v in f.choices))
        if getattr(f,'max_length',None): details.append(f'máximo {f.max_length} caracteres')
        if getattr(f,'decimal_places',None) is not None: details.append(f'{f.max_digits} dígitos / {f.decimal_places} decimales')
        lines.append('| '+' | '.join(map(cell,[f.name,f.get_internal_type(),'sí' if f.null else 'no',', '.join(details)]))+' |')
    if model._meta.constraints: lines.extend(['','Restricciones de base: '+', '.join('`'+c.name+'`' for c in model._meta.constraints)+'.'])
    lines.append('')
lines.extend(['## Captura e integridad','','Clientes, vehículos y refacciones pueden cargarse por CSV con previsualización, recibo firmado y confirmación atómica. Órdenes, cotizaciones, compras, movimientos, cobros, grúas y propuestas pasan por servicios de dominio; el explorador de fuentes es de consulta. La bitácora registra actor, entidad, acción y antes/después. No es almacenamiento inmutable frente a un administrador del equipo con acceso directo a SQLite. Las cuentas/sesiones y secretos de autenticación no forman parte de este explorador.'])
(ROOT/'docs/V5-DATOS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
metrics=build_metric_catalog()
lines=['# Catálogo de métricas · V5','','Generado desde `workshop.intelligence.build_metric_catalog()`. Las 18 definiciones se evalúan sobre los registros actuales, con instante de cálculo, cobertura, motivo de desconocido y muestra de evidencia limitada a 12 filas. La muestra no representa la población completa. El parámetro de corte no reconstruye una base histórica.','']
for metric in metrics:
    lines.extend([f'## {metric["metric_id"]} · {metric["label"]}','',metric['definition'],'', '| Propiedad | Definición |','| --- | --- |'])
    for k,label in [('domain','Dominio'),('grain','Grano'),('unit','Unidad'),('numerator','Numerador / expresión'),('denominator','Población elegible'),('source_tables','Fuentes'),('owner_role','Responsable')]:
        value=metric[k]
        lines.append(f'| {label} | {cell(", ".join(value) if isinstance(value,list) else value)} |')
    lines.append('')
lines.extend(['## Interpretación','','Cada indicador conserva estado `measured` o `unknown`; una población vacía no prueba cero actividad ni cobertura total. Pagos registrados no prueban depósitos bancarios. Margen directo estimado no es utilidad neta ni costo real de inventario; exige costos en todas las líneas de cada cotización elegible. No se calculan utilización sin capacidad, tendencias históricas sin snapshots ni cumplimiento de SLA no medido. El [contrato de inteligencia](../specs/v5-intelligence.md) detalla cada frontera y la relación con propuestas.'])
(ROOT/'docs/V5-METRICAS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'domain_tables':len(SOURCE_MODELS),'metrics':len(metrics),'queried_client_rows':False}))
