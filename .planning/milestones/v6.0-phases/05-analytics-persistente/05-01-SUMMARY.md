---
plan: 05-01
status: complete_local
requirements-completed: [ANA-02, ANA-03, ANA-04, ANA-05, ANA-06]
---

# Cortes analíticos persistentes — ejecución

`workshop/analytics.py` materializa seis tablas: `daily_operations`, `service_lines`, `part_usage`, `receivables`, `order_journeys` e `inventory`. `AnalyticsSnapshot` y `AnalyticsRow` conservan hora, huella, conteos de fuentes, filas y referencias. `build_analytics_dashboard` consulta un corte guardado; no reescribe el anterior si cambian las fuentes.

`workshop/tests/test_analytics.py` verifica rango y periodo anterior de igual duración, últimas cotizaciones aprobadas, consumo neto con devoluciones y sin compras, facturación y cobros con fechas distintas, tiempos basados en auditoría, segmentación y corte inmutable tras mutar una fuente. El revisor independiente ejecutó 38 pruebas de analytics, automatización e interfaz combinadas sin fallos; véase `.planning/V6-INTEGRATION-REVIEW.md`. La corrida más reciente registrada en `artifacts/v6-verification.json` reporta versión 6.0, 115 pruebas, 0 fallos/errores y 2 omisiones. Cada recibo acredita solo los hashes que registra.

Los saldos/estados son observaciones al corte; un filtro histórico no reconstruye estados pasados que V5 no guardó. No se asigna ingreso facturado por línea de servicio cuando el comprobante no tiene tal desglose. Semántica y límites: `docs/V6-ANALYTICS.md`.
