---
phase: "03"
slug: inteligencia-y-agentes
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-22
---

# Fase 03 — cobertura de validación reconstruida

Reconstrucción retrospectiva con planes, resúmenes, pruebas existentes y recibos. No afirma que hubiera un contrato Nyquist antes de implementar ni que el cliente haya aceptado el producto.

## Infraestructura y muestreo

Django 5.2 DiscoverRunner/unittest; configuración milenio_web/settings.py. Ejecución aislada completa: `.venv/Scripts/python.exe scripts/verify_web.py --output artifacts/v5-verification.json`. El script fuerza modo test y directorio temporal; nunca utiliza bases live/demo. Ejecución local observada: 71 pruebas en aproximadamente 33 segundos, sin omisiones. Para una modificación futura, ejecutar primero el módulo afectado y después la suite en cada conjunto de cambios; no usar modo watch.

## Mapa de tareas y requisitos

| Tarea / plan | Requisitos | Archivos existentes en workshop/tests | Comportamiento cubierto | Estado |
| --- | --- | --- | --- | --- |
| 03-01 | MET-01, MET-02 | test_intelligence.py | 18 definiciones ORM, coberturas y valores desconocidos | COVERED / green |
| 03-02 | AGT-01, AGT-02 | test_intelligence.py; test_web.py | Evidencia, vigencia, deduplicación, aceptación y cierre | COVERED / green |
| 03-02 | AGT-03 | test_intelligence.py | Contrato nativo, fallos, UTF-8, identidad de evidencia y límites | COVERED / green |

## Comprobaciones de operador

Inferencia nativa autenticada: ejecutada por el operador en demo y registrada en artifacts/v5-native-verification.json, sin runner simulado, turn.completed y salida válida. No se ejecuta contra cuentas reales en cada CI. El recibo de pruebas con mocks no sustituye este recibo.

## Validación de cierre

Infraestructura existente; no hay referencias de tests ausentes ni stubs por crear. Cada tarea del plan tiene verificación automatizada de su comportamiento y las comprobaciones de operador anteriores completan los aspectos que no acredita CI. Se reutilizan los recibos de la misma versión y se regeneran después de cambios de ejecución. Las observaciones de la auditoría de integración se cierran antes de publicar.

Validado por root a partir de los artefactos y de la auditoría independiente de integración; ejecución automática y aceptación comercial son evidencias distintas.
