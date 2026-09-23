---
plan: 01-02
status: complete_local
---

# Orden, autorización y existencias — ejecución

## Implementación

Cotizaciones versionadas, autorización identificada, inspección con fotos, stock con reserva/consumo/devolución, horas, calidad y transiciones transaccionales. Compras en borrador y recepción parcial con referencia única.

Archivos principales: `workshop/models.py, workshop/services.py, workshop/migrations/0001_initial.py`.

## Comprobación

test_domain.py y recorrido HTTP: invalidez de etapa/rol, falta de stock, reintento, QC fallido y aprobación protegida.

El recibo final y la verificación por fase establecen lo observado. Las pruebas son desechables y sintéticas; no acreditan un piloto del cliente. No se creó ningún compromiso fiscal, bancario ni de mensajería externa.

## Decisiones

Se reutilizó la base Python con Django LTS y Waitress. SQLite corresponde a una estación/taller local. Los modelos externos no sustituyen reglas exactas; sus propuestas requieren evidencia y revisión. Los cambios V1–V4 se conservaron como toolkit separado. Commits gestionados por root para mantener una entrega integrada; los trabajadores no modificaron Git.

Recibos de cierre: `artifacts/v5-verification.json` (70/70, 0 omisiones), `artifacts/v5-browser-verification.json` y `artifacts/v5-installation-rehearsal.json`. Este último distingue instalación offline, imports/setup con entorno nuevo y restauración con intérprete del repositorio sobre código extraído.
