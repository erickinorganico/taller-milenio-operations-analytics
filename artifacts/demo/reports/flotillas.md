# Flotillas: comercial, contrato y entrega

**DATOS SINTÉTICOS** · Corte fijo: 2026-09-21T18:00:00Z

|Indicador|Resultado|
|---|---:|
|Oportunidades abiertas|2|
|Pipeline comercial|$20,300.00 MXN|
|Cobertura de cuentas|2/2 (100.0%)|
|Contratos activos|1|
|Entregadas|1/2 (50.0%)|
|SLA elegible|1/1 (100.0%)|
|SLA cumplido, solo entregadas|0/1 (0.0%)|
|Órdenes con contrato vinculado|1/2 (50.0%)|
|SLA abierto en riesgo o incumplido|Sin denominador|
|Mediana de horas fuera de servicio, órdenes abiertas|74.0|
|Mantenimientos pendientes|3|
|Próximos 7 días, vencidos o por kilometraje|1|

## Priorización de investigación

|Cuenta|Prioridad|Hipótesis|
|---|---|---|
|FA-001|alta|Cuenta con oportunidad comercial abierta|
|FA-002|alta|Cuenta con oportunidad comercial abierta|

Es una heurística transparente: cambia al cerrar la oportunidad y no predice compra. Dueño sugerido: ventas B2B; disparador: oportunidad abierta; evidencia: oportunidad y cuenta; acción: investigación pública y propuesta para revisión humana, sin contacto ni promesa de precio/SLA.

## Trazabilidad

Fuentes del universo revisado en `../dataset.json` y vistas `v_*` de `../milenio.sqlite`. La población, filtros y denominadores están en `../analysis.json` y `docs/METRICS.md`.

- contracts: CT-001 (v1), CT-002 (v1)
- customers: C-001 (v1), C-002 (v1), C-003 (v1), C-004 (v1), C-005 (v1), C-006 (v1), C-007 (v1), C-008 (v1), C-009 (v1), C-010 (v1)
- fleet_accounts: FA-001 (v1), FA-002 (v1)
- maintenance: M-001 (v1), M-002 (v1), M-003 (v1)
- opportunities: OP-001 (v1), OP-002 (v1)
- vehicles: V-001 (v1), V-002 (v1), V-003 (v1), V-004 (v1), V-005 (v1), V-006 (v1), V-007 (v1), V-008 (v1), V-009 (v1), V-010 (v1), V-011 (v1), V-012 (v1)
- work_orders: WO-001 (v1), WO-002 (v1), WO-003 (v1), WO-004 (v1), WO-005 (v1), WO-006 (v1), WO-007 (v1), WO-008 (v1), WO-009 (v1), WO-010 (v1)
