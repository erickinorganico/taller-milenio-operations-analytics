# Taller: WIP, capacidad y partes

**DATOS SINTÉTICOS** · Corte fijo: 2026-09-21T18:00:00Z

|Indicador|Resultado|
|---|---:|
|Órdenes abiertas|7|
|Esperando partes|1/7 (14.3%)|
|Retrabajo|1/10 (10.0%)|
|Mediana de horas abiertas|74.0|
|Bahías ocupadas al corte|4/4 (100.0%)|
|Partes en/bajo reorden|4/6 (66.7%)|

La capacidad es ocupación instantánea, no utilización por horas. Disparador: orden esperando parte; dueño sugerido: jefe de taller; evidencia: `waiting_order_evidence`; acción: revisar reserva, compra y disponibilidad antes de comprometer fecha o compra.

## Trazabilidad

Fuentes del universo revisado en `../dataset.json` y vistas `v_*` de `../milenio.sqlite`. La población, filtros y denominadores están en `../analysis.json` y `docs/METRICS.md`.

- bays: B-001 (v1), B-002 (v1), B-003 (v1), B-004 (v1)
- parts: P-001 (v1), P-002 (v1), P-003 (v1), P-004 (v1), P-005 (v1), P-006 (v1)
- purchases: PO-001 (v1), PO-002 (v1), PO-003 (v1)
- reservations: RS-001 (v1), RS-002 (v1), RS-003 (v1)
- stock_moves: SM-001 (v1), SM-002 (v1), SM-003 (v1), SM-004 (v1), SM-005 (v1)
- technicians: T-001 (v1), T-002 (v1), T-003 (v1), T-004 (v1)
- work_orders: WO-001 (v1), WO-002 (v1), WO-003 (v1), WO-004 (v1), WO-005 (v1), WO-006 (v1), WO-007 (v1), WO-008 (v1), WO-009 (v1), WO-010 (v1)
