---
plan: 03-01
status: complete_local
requirements-completed: [MET-01, MET-02]
---

# Métricas vivas — ejecución

## Implementación

18 métricas con definición, grano, población, cobertura y evidencia. Stock, fechas/km, contratos y tiempos de grúa complementan orden/cobranza. Costos incompletos no se traducen en margen cero.

Archivos principales: `workshop/intelligence.py, workshop/insight_views.py`.

## Comprobación

test_intelligence.py y recorrido HTTP; catálogo generado en docs/V5-METRICAS.md.

El recibo final y la verificación por fase establecen lo observado. Las pruebas son desechables y sintéticas; no acreditan un piloto del cliente. No se creó ningún compromiso fiscal, bancario ni de mensajería externa.

## Decisiones

Se reutilizó la base Python con Django LTS y Waitress. SQLite corresponde a una estación/taller local. Los modelos externos no sustituyen reglas exactas; sus propuestas requieren evidencia y revisión. Los cambios V1–V4 se conservaron como toolkit separado. Commits gestionados por root para mantener una entrega integrada; los trabajadores no modificaron Git.

Recibos de cierre: `artifacts/v5-verification.json` (71/71, 0 omisiones), `artifacts/v5-browser-verification.json` y `artifacts/v5-installation-rehearsal.json`. Este último distingue instalación offline, imports/setup con entorno nuevo y restauración con intérprete del repositorio sobre código extraído.
