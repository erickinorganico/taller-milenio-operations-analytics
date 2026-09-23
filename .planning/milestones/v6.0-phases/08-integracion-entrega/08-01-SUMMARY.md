---
plan: 08-01
status: complete_local
requirements-completed: [DEL-05]
---

# Integración y entrega — ejecución local

`scripts/verify_v6_delivery.py` ensayó sobre datos sintéticos desechables migración desde esquema V5, conservación de dos clientes/dos órdenes/factura/saldo, corte y trabajo de reglas V6, respaldo/restauración con conteos y huella iguales y sesiones purgadas. El recibo `artifacts/v6-delivery-verification.json` indica `status=pass` y `version=6.0`.

El candidato extraído `dist/Milenio-V6-review-candidate2.zip` fue comprobado contra SHA-256 `a0845d2f2a418f863e86d06a0da2a42999849018146c0b92081a4cf916e8fa1f`: 157 archivos del manifiesto verificados, instalación de ruedas sin índice en entorno nuevo, Django check, demo inicial con 36 órdenes V6 y primer corte, actor temporal deshabilitado, páginas autenticadas de analytics y automatizaciones HTTP 200, trabajo de reglas y latido observados, cierre del servidor al cerrar canal de supervisión. Este hash pertenece al **candidato 2**; la publicación final requiere un paquete reconstruido y recibo propio si cambia cualquier fuente.

`artifacts/v6-verification.json` registra suite local V6 de 115 pruebas, 0 fallos, 0 errores y 0 omisiones; el arranque extraído se comprobó por separado. `artifacts/v6-browser-verification.json` y `v6-worker-restart.json` registran filtros, móvil, pausa/reanudación y fin del trabajador hijo. `artifacts/v6-native-verification.json` acredita inferencia real local opcional con tres revisores; no forma parte del smoke offline de paquete, que ejecuta reglas. Procedimientos y límites están en `README-WEB.md`, `docs/V6-ANALYTICS.md`, `docs/V6-AUTOMATIZACIONES.md` y `docs/V6-VERIFICACION.md`.

La entrega técnica local no demuestra instalación en el taller, conciliación de datos reales, publicación del ZIP final, aceptación ni mejora comercial.
