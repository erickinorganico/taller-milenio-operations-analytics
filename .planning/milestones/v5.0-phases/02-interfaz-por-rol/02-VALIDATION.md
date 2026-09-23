---
phase: "02"
slug: interfaz-por-rol
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-22
---

# Fase 02 — cobertura de validación reconstruida

Reconstrucción retrospectiva con planes, resúmenes, pruebas existentes y recibos. No afirma que hubiera un contrato Nyquist antes de implementar ni que el cliente haya aceptado el producto.

## Infraestructura y muestreo

Django 5.2 DiscoverRunner/unittest; configuración milenio_web/settings.py. Ejecución aislada completa: `.venv/Scripts/python.exe scripts/verify_web.py --output artifacts/v5-verification.json`. El script fuerza modo test y directorio temporal; nunca utiliza bases live/demo. Ejecución local observada: 71 pruebas en aproximadamente 33 segundos, sin omisiones. Para una modificación futura, ejecutar primero el módulo afectado y después la suite en cada conjunto de cambios; no usar modo watch.

## Mapa de tareas y requisitos

| Tarea / plan | Requisitos | Archivos existentes en workshop/tests | Comportamiento cubierto | Estado |
| --- | --- | --- | --- | --- |
| 02-01 | UX-01 | test_web.py | Rutas por rol, formularios, errores y recorrido HTTP | COVERED / green |
| 02-02 | DAT-01 | test_web.py; test_import.py | Fuentes/CSV, fórmula escapada e importación firmada/atómica | COVERED / green |

## Comprobaciones de operador

Apariencia y recorrido móvil: observación documentada en artifacts/v5-browser-verification.json. No se afirma prueba física de teléfono ni estudio de usabilidad con cliente.

## Validación de cierre

Infraestructura existente; no hay referencias de tests ausentes ni stubs por crear. Cada tarea del plan tiene verificación automatizada de su comportamiento y las comprobaciones de operador anteriores completan los aspectos que no acredita CI. Se reutilizan los recibos de la misma versión y se regeneran después de cambios de ejecución. Las observaciones de la auditoría de integración se cierran antes de publicar.

Validado por root a partir de los artefactos y de la auditoría independiente de integración; ejecución automática y aceptación comercial son evidencias distintas.
