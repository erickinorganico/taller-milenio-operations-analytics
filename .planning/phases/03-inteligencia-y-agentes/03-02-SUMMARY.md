---
plan: 03-02
status: partial
---

# Propuestas y tareas gobernadas — ejecución

## Implementación

Tres revisores por reglas persisten corridas y propuestas. Aceptación única de evidencia vigente, tarea responsable/plazo, cierre humano y nueva comprobación. Adaptador CLI aislado existe, pero no hay corrida V5 nativa real sin login.

Archivos principales: `workshop/intelligence.py, workshop/insight_views.py, specs/v5-intelligence.md`.

## Comprobación

Pruebas de PaymentSet, deduplicación, stale, rol y cierre; mocks adversariales y errores. AGT-03 permanece parcial por autenticación ausente.

El recibo final y la verificación por fase establecen lo observado. Las pruebas son desechables y sintéticas; no acreditan un piloto del cliente. No se creó ningún compromiso fiscal, bancario ni de mensajería externa.

## Decisiones

Se reutilizó la base Python con Django LTS y Waitress. SQLite corresponde a una estación/taller local. Los modelos externos no sustituyen reglas exactas; sus propuestas requieren evidencia y revisión. Los cambios V1–V4 se conservaron como toolkit separado. Commits gestionados por root para mantener una entrega integrada; los trabajadores no modificaron Git.

Recibos de cierre: `artifacts/v5-verification.json` (70/70, 0 omisiones), `artifacts/v5-browser-verification.json` y `artifacts/v5-installation-rehearsal.json`. Este último distingue instalación offline, imports/setup con entorno nuevo y restauración con intérprete del repositorio sobre código extraído.
