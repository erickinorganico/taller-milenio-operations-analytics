---
plan: 02-01
status: complete_local
requirements-completed: [UX-01]
---

# Interfaz por rol — ejecución

## Implementación

Pantallas españolas; técnicos limitados a órdenes/fotos/tareas propias; consulta gerencial explícita; errores, estados vacíos y controles adaptables.

Archivos principales: `workshop/templates/workshop, workshop/static/workshop`.

## Comprobación

test_web.py por rol y observación de navegador documentada en docs/V5-VERIFICACION.md.

El recibo final y la verificación por fase establecen lo observado. Las pruebas son desechables y sintéticas; no acreditan un piloto del cliente. No se creó ningún compromiso fiscal, bancario ni de mensajería externa.

## Decisiones

Se reutilizó la base Python con Django LTS y Waitress. SQLite corresponde a una estación/taller local. Los modelos externos no sustituyen reglas exactas; sus propuestas requieren evidencia y revisión. Los cambios V1–V4 se conservaron como toolkit separado. Commits gestionados por root para mantener una entrega integrada; los trabajadores no modificaron Git.

Recibos de cierre: `artifacts/v5-verification.json` (71/71, 0 omisiones), `artifacts/v5-browser-verification.json` y `artifacts/v5-installation-rehearsal.json`. Este último distingue instalación offline, imports/setup con entorno nuevo y restauración con intérprete del repositorio sobre código extraído.
