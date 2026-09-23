---
phase: 01-operacion-persistente
status: passed
---
# Operación persistente y acceso — verificación integrada

Servicios/ORM y recorridos HTTP verificados; cuentas/roles/CSRF y recuperación de contraseña desde cuenta comprobados. La instalación live permanece vacía y demo se siembra explícitamente. Los 11 requisitos de esta fase están implementados y ensayados con datos desechables.

| ID | Evidencia local principal | Estado |
| --- | --- | --- |
| AUTH-01 | `test_web.py`: setup, login/logout, CSRF y rutas privadas | passed |
| AUTH-02 | `test_web.py`: permisos por rol, órdenes/fotos asignadas y viewer sin escritura | passed |
| RUN-01 | `artifacts/v5-browser-verification.json`: instancia live vacía y demo separada | passed |
| OPS-01 | `test_web.py`: alta cliente/vehículo, orden y agenda | passed |
| OPS-02 | `test_web.py`: inspección, foto privada e historial | passed |
| OPS-03 | `test_web.py`: versiones, autorización y documento imprimible | passed |
| OPS-04 | `test_domain.py` y `test_web.py`: transiciones, tiempo, calidad y entrega | passed |
| STK-01 | `test_domain.py` y `test_web.py`: compras, recepción, reserva y stock | passed |
| FIN-01 | `test_web.py`: comprobante 626.40, pago 100.00 y saldo 526.40 | passed |
| FLT-01 | `test_domain.py`: contrato y mantenimiento persistentes | passed |
| TOW-01 | `test_domain.py`: solicitud e hitos de grúa | passed |

Evidencia ejecutada: `artifacts/v5-verification.json` (71 pruebas, 0 omisiones) y `artifacts/v5-browser-verification.json`. Fuentes/definiciones: `workshop/`, contratos `specs/v5-*`. Este reporte integra comprobaciones de root y trabajadores; la fase 4 conserva además revisión independiente de un agente GSD. `passed` describe alcance local sintético; no declara aceptación de un cliente, datos de producción o impacto comercial.
