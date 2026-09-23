---
plan: 04-02
status: complete_local
requirements-completed: [DOC-01]
---

# Entrega local y manuales — ejecución

## Implementación

Paquete allowlist con seis wheels fijados CPython3.12 Windowsx64, hashes, código, tests, documentos y planificación. No incluye bases ni secretos del taller.

Archivos principales: `scripts/package_web.py, README-WEB.md, docs/V5*.md`.

## Comprobación

artifacts/v5-installation-rehearsal.json; docs/V5-VERIFICACION.md. Aceptación real del cliente pendiente; no equivale a instalación en su equipo.

El recibo final y la verificación por fase establecen lo observado. Las pruebas son desechables y sintéticas; no acreditan un piloto del cliente. No se creó ningún compromiso fiscal, bancario ni de mensajería externa.

## Decisiones

Se reutilizó la base Python con Django LTS y Waitress. SQLite corresponde a una estación/taller local. Los modelos externos no sustituyen reglas exactas; sus propuestas requieren evidencia y revisión. Los cambios V1–V4 se conservaron como toolkit separado. Commits gestionados por root para mantener una entrega integrada; los trabajadores no modificaron Git.

Recibos de cierre: `artifacts/v5-verification.json` (71/71, 0 omisiones), `artifacts/v5-browser-verification.json` y `artifacts/v5-installation-rehearsal.json`. Este último distingue instalación offline, imports/setup con entorno nuevo y restauración con intérprete del repositorio sobre código extraído.
