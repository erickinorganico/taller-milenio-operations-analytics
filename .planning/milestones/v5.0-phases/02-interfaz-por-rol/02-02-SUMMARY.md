---
plan: 02-02
status: complete_local
requirements-completed: [DAT-01]
---

# Fuentes e importación — ejecución

## Implementación

24 fuentes físicas con búsqueda y relaciones. CSV protege fórmulas. Catálogos de clientes/vehículos/refacciones se previsualizan y confirman con recibo firmado ligado a sesión, revalidación y transacción.

Archivos principales: `workshop/catalog.py, workshop/import_views.py, scripts/export_web_contracts.py`.

## Comprobación

test_import.py: roles, CSRF, límites, campos, filas inválidas, duplicados, caducidad y reintento; test_web fuentes/CSV.

El recibo final y la verificación por fase establecen lo observado. Las pruebas son desechables y sintéticas; no acreditan un piloto del cliente. No se creó ningún compromiso fiscal, bancario ni de mensajería externa.

## Decisiones

Se reutilizó la base Python con Django LTS y Waitress. SQLite corresponde a una estación/taller local. Los modelos externos no sustituyen reglas exactas; sus propuestas requieren evidencia y revisión. Los cambios V1–V4 se conservaron como toolkit separado. Commits gestionados por root para mantener una entrega integrada; los trabajadores no modificaron Git.

Recibos de cierre: `artifacts/v5-verification.json` (71/71, 0 omisiones), `artifacts/v5-browser-verification.json` y `artifacts/v5-installation-rehearsal.json`. Este último distingue instalación offline, imports/setup con entorno nuevo y restauración con intérprete del repositorio sobre código extraído.
