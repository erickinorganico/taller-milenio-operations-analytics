---
plan: 01-03
status: complete_local
---

# Cobro, flotillas y grúas — ejecución

## Implementación

Comprobante administrativo tras entrega; pagos parciales y saldo con Decimal, contratos y mantenimiento fecha/km, grúas con operador e hitos humanos. Documentos imprimibles sin costos internos.

Archivos principales: `workshop/services.py, workshop/views.py, templates finance/fleets/towing/document`.

## Comprobación

Recorrido HTTP: total626.40, pago100, saldo526.40; dominio: sobrepago, duplicados, contratos/mantenimiento y grúas.

El recibo final y la verificación por fase establecen lo observado. Las pruebas son desechables y sintéticas; no acreditan un piloto del cliente. No se creó ningún compromiso fiscal, bancario ni de mensajería externa.

## Decisiones

Se reutilizó la base Python con Django LTS y Waitress. SQLite corresponde a una estación/taller local. Los modelos externos no sustituyen reglas exactas; sus propuestas requieren evidencia y revisión. Los cambios V1–V4 se conservaron como toolkit separado. Commits gestionados por root para mantener una entrega integrada; los trabajadores no modificaron Git.

Recibos de cierre: `artifacts/v5-verification.json` (70/70, 0 omisiones), `artifacts/v5-browser-verification.json` y `artifacts/v5-installation-rehearsal.json`. Este último distingue instalación offline, imports/setup con entorno nuevo y restauración con intérprete del repositorio sobre código extraído.
