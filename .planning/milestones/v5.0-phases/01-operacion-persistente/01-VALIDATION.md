---
phase: "01"
slug: operacion-persistente
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-22
---

# Fase 01 — cobertura de validación reconstruida

Reconstrucción retrospectiva con planes, resúmenes, pruebas existentes y recibos. No afirma que hubiera un contrato Nyquist antes de implementar ni que el cliente haya aceptado el producto.

## Infraestructura y muestreo

Django 5.2 DiscoverRunner/unittest; configuración milenio_web/settings.py. Ejecución aislada completa: `.venv/Scripts/python.exe scripts/verify_web.py --output artifacts/v5-verification.json`. El script fuerza modo test y directorio temporal; nunca utiliza bases live/demo. Ejecución local observada: 71 pruebas en aproximadamente 33 segundos, sin omisiones. Para una modificación futura, ejecutar primero el módulo afectado y después la suite en cada conjunto de cambios; no usar modo watch.

## Mapa de tareas y requisitos

| Tarea / plan | Requisitos | Archivos existentes en workshop/tests | Comportamiento cubierto | Estado |
| --- | --- | --- | --- | --- |
| 01-01 | AUTH-01, AUTH-02, RUN-01 | test_web.py; test_recovery.py | Sesión/CSRF/roles, entorno separado y arranque | COVERED / green |
| 01-02 | OPS-01, OPS-02, OPS-03, OPS-04 | test_domain.py; test_web.py | Recepción a entrega, inspección, autorización, calidad y auditoría | COVERED / green |
| 01-03 | STK-01, FIN-01, FLT-01, TOW-01 | test_domain.py; test_web.py | Stock transaccional, saldo/pagos, contratos y hitos humanos | COVERED / green |

## Comprobaciones de operador

Instalación Windows y persistencia tras reinicio: observadas en artifacts/v5-browser-verification.json y ensayo extraído. Aceptación de personas del taller permanece fuera del cierre técnico.

## Validación de cierre

Infraestructura existente; no hay referencias de tests ausentes ni stubs por crear. Cada tarea del plan tiene verificación automatizada de su comportamiento y las comprobaciones de operador anteriores completan los aspectos que no acredita CI. Se reutilizan los recibos de la misma versión y se regeneran después de cambios de ejecución. Las observaciones de la auditoría de integración se cierran antes de publicar.

Validado por root a partir de los artefactos y de la auditoría independiente de integración; ejecución automática y aceptación comercial son evidencias distintas.
