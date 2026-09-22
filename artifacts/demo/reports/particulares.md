# Particulares: recorrido y operación

**DATOS SINTÉTICOS** · Corte fijo: 2026-09-21T18:00:00Z

Corte sintético: **2026-09-21T18:00:00Z**. El recorrido es un estado observado, no un embudo temporal ni causal.

|Indicador|Resultado|
|---|---:|
|Leads|4|
|Calificados o posteriores|2/4 (50.0%)|
|Ganados|0/4 (0.0%)|
|Coincidencia candidata lead-cotización|Sin denominador|
|Pipeline abierto|$1,370.00 MXN|

La conversión lead→cotización es **unknown**: falta llave explícita de atribución. La coincidencia cliente-vehículo solo prioriza revisión. Disparador: lead sin vehículo o consentimiento; dueño sugerido: recepción; evidencia: registro afectado; acción: completar datos antes de preparar un borrador de seguimiento. No hay contacto automático.

## Cobertura antes de contactar

|Control|Resultado|
|---|---:|
|Leads sin vehículo|0/4 (0.0%)|
|Leads de clientes sin consentimiento|1/4 (25.0%)|
|Citas pendientes|1|

## Trazabilidad

Fuentes del universo revisado en `../dataset.json` y vistas `v_*` de `../milenio.sqlite`. La población, filtros y denominadores están en `../analysis.json` y `docs/METRICS.md`.

- appointments: A-001 (v1), A-002 (v1), A-003 (v1)
- customers: C-001 (v1), C-002 (v1), C-003 (v1), C-004 (v1), C-005 (v1), C-006 (v1), C-007 (v1), C-008 (v1), C-009 (v1), C-010 (v1)
- leads: L-001 (v1), L-002 (v1), L-003 (v1), L-004 (v1), L-005 (v1), L-006 (v1)
- quotes: Q-001 (v1), Q-002 (v1), Q-003 (v1), Q-004 (v1), Q-005 (v1), Q-006 (v1), Q-007 (v1), Q-008 (v1), Q-009 (v1), Q-010 (v1)
- vehicles: V-001 (v1), V-002 (v1), V-003 (v1), V-004 (v1), V-005 (v1), V-006 (v1), V-007 (v1), V-008 (v1), V-009 (v1), V-010 (v1), V-011 (v1), V-012 (v1)
- work_orders: WO-001 (v1), WO-002 (v1), WO-003 (v1), WO-004 (v1), WO-005 (v1), WO-006 (v1), WO-007 (v1), WO-008 (v1), WO-009 (v1), WO-010 (v1)
