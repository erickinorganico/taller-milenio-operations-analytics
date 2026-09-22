# Administración: facturación, cobro y cartera

**DATOS SINTÉTICOS** · Corte fijo: 2026-09-21T18:00:00Z

|Medida separada|Resultado|
|---|---:|
|Cotizaciones|$13,055.00 MXN|
|Facturado|$6,950.00 MXN|
|Cobrado registrado|$1,850.00 MXN|
|Por cobrar|$5,100.00 MXN|
|Gasto observado|$420.00 MXN|

Cobrado no equivale a ingreso reconocido. Cartera por antigüedad: current $4,250.00 MXN, 1_30 $850.00 MXN, 31_60 $0.00 MXN, 61_90 $0.00 MXN, 90_plus $0.00 MXN. Disparador: saldo vencido; dueño sugerido: administración; evidencia: factura y pagos; acción: conciliación y borrador de recordatorio, sin mover dinero.

## Caja y costo de refacciones

|Medida|MXN|
|---|---:|
|Movimiento neto de efectivo|$-180.00 MXN|
|Consumo neto de refacciones a costo registrado|$18.00 MXN|

El efectivo es entradas menos salidas registradas, sin saldo inicial; no representa caja disponible. El costo de piezas no se resta otra vez como gasto ni constituye margen contable.

## Trazabilidad

Fuentes del universo revisado en `../dataset.json` y vistas `v_*` de `../milenio.sqlite`. La población, filtros y denominadores están en `../analysis.json` y `docs/METRICS.md`.

- expenses: EXP-001 (v1), EXP-002 (v1)
- invoices: INV-001 (v1), INV-002 (v1), INV-003 (v1), INV-004 (v1)
- payments: PAY-001 (v1), PAY-002 (v1)
- quotes: Q-001 (v1), Q-002 (v1), Q-003 (v1), Q-004 (v1), Q-005 (v1), Q-006 (v1), Q-007 (v1), Q-008 (v1), Q-009 (v1), Q-010 (v1)
- stock_moves: SM-001 (v1), SM-002 (v1), SM-003 (v1), SM-004 (v1), SM-005 (v1)
