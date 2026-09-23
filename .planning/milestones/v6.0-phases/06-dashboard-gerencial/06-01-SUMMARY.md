---
plan: 06-01
status: complete_local
requirements-completed: [ANA-01, ANA-07]
---

# Dashboard gerencial — ejecución

La entrada `/` dirige al dashboard `/analytics/` cuando el rol tiene `intelligence_read`; recepción conserva `/today/`. `workshop/analytics_views.py` sirve filtros, comparación, seis tablas derivadas, referencias a fuentes y exportación. `dashboard.html`, `analytics_table.html` y `analytics.css` presentan cortes, piezas y servicios con cobertura. Lectura tabular, CSV y JSON requieren `data_read`; configuración del trabajador usa `manage`.

`workshop/tests/test_analytics_web.py` cubre entrada por rol, denegación de rutas, validación de filtros, seis tablas, CSV neutralizado y ausencia de mutaciones GET. El revisor independiente incluyó este módulo en 38 pruebas afectadas sin fallos (`.planning/V6-INTEGRATION-REVIEW.md`). `artifacts/v6-browser-verification.json` registra filtros predeterminado/flotilla, comparación visible, seis enlaces de tablas y pantalla móvil con ancho de contenido 375 px para cliente 375 px. El recibo de paquete extraído comprueba además HTTP autenticado 200 para `/analytics/` y `/automations/`; no sustituye el recorrido visual.
