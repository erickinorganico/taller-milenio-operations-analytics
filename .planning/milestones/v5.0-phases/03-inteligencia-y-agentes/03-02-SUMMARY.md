---
plan: 03-02
status: complete_local
requirements-completed: [AGT-01, AGT-02, AGT-03]
---

# Propuestas y tareas gobernadas — ejecución

## Implementación

Tres revisores por reglas persisten corridas y propuestas. Aceptación única de evidencia vigente, tarea responsable/plazo, cierre humano y nueva comprobación. El adaptador CLI aislado completó una corrida nativa real `collections` #5 con GPT-6 Luna sobre la demo sintética, sin hook de prueba.

Archivos principales: `workshop/intelligence.py, workshop/insight_views.py, specs/v5-intelligence.md`.

## Comprobación

Pruebas de PaymentSet, deduplicación, stale, rol y cierre; mocks adversariales y errores. AGT-03 se acredita además con `artifacts/v5-native-verification.json`: `turn.completed`, `model_invoked=true`, JSON válido, propuestas vacías permitidas y conteos de negocio intactos. La suite cerró 71/71 pruebas, incluidas 18 de inteligencia. El preflight `Not logged in` inicial queda como antecedente, no como estado actual de esta verificación.

El recibo final y la verificación por fase establecen lo observado. Las pruebas son desechables y sintéticas; no acreditan un piloto del cliente. No se creó ningún compromiso fiscal, bancario ni de mensajería externa.

## Decisiones

Se reutilizó la base Python con Django LTS y Waitress. SQLite corresponde a una estación/taller local. Los modelos externos no sustituyen reglas exactas; sus propuestas requieren evidencia y revisión. Los cambios V1–V4 se conservaron como toolkit separado. Commits gestionados por root para mantener una entrega integrada; los trabajadores no modificaron Git.

Recibos de cierre: `artifacts/v5-verification.json` (71/71, 0 omisiones), `artifacts/v5-browser-verification.json` y `artifacts/v5-installation-rehearsal.json`. Este último distingue instalación offline, imports/setup con entorno nuevo y restauración con intérprete del repositorio sobre código extraído.
