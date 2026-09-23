---
plan: 04-01
status: complete_local
---

# Regresión y recuperación — ejecución

## Implementación

Suite de operación/transacciones/permisos/inteligencia/importación/recuperación y recibo con hashes. Backups consistentes con media y manifiesto; restore valida antes de reemplazar, preserva estado previo y purga sesiones.

Archivos principales: `workshop/tests, backup_workshop.py, restore_workshop.py, scripts/verify_web.py`.

## Comprobación

artifacts/v5-verification.json; test_recovery verifica conteos y saldo en destino separado; ensayo extraído conserva esquema completo.

El recibo final y la verificación por fase establecen lo observado. Las pruebas son desechables y sintéticas; no acreditan un piloto del cliente. No se creó ningún compromiso fiscal, bancario ni de mensajería externa.

## Decisiones

Se reutilizó la base Python con Django LTS y Waitress. SQLite corresponde a una estación/taller local. Los modelos externos no sustituyen reglas exactas; sus propuestas requieren evidencia y revisión. Los cambios V1–V4 se conservaron como toolkit separado. Commits gestionados por root para mantener una entrega integrada; los trabajadores no modificaron Git.

Recibos de cierre: `artifacts/v5-verification.json` (70/70, 0 omisiones), `artifacts/v5-browser-verification.json` y `artifacts/v5-installation-rehearsal.json`. Este último distingue instalación offline, imports/setup con entorno nuevo y restauración con intérprete del repositorio sobre código extraído.
