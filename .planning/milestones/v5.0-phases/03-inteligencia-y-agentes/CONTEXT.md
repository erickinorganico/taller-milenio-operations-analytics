# Phase 3 context — Inteligencia y seguimiento de agentes

## Outcome and scope

Gerencia explica métricas desde transacciones persistentes y decide propuestas de operación, cobranza y calidad con seguimiento. Requisitos: MET-01, MET-02, AGT-01, AGT-02 y AGT-03.

## Decisiones vigentes

- Métricas tienen definición, denominador, filtros, período, cobertura y vínculo a registros fuente. No contar pagos como ingresos devengados ni inferir margen sin costos.
- Falta de historial o campos esenciales produce desconocido, no cero. Demos sintéticas se etiquetan.
- Reglas exactas deterministas. La CLI Codex nativa autenticada es modo opcional; salida JSON validada, timeout y errores persistidos. No introducir API de pago.
- Ejecutar agentes con lectura acotada; guardar snapshot/identificadores y frescura de evidencia. Propuestas caducan si cambia el registro pertinente.
- Aceptación humana crea tarea interna idempotente. Ningún agente envía mensajes externos, compra, mueve dinero o hace diagnóstico mecánico automático.

## Evidencia de salida

Fixtures completas e incompletas para métricas; ejecución real de CLI autenticada si disponible, más caso de fallo visible; duplicación y obsolescencia de propuestas probadas. La falta de CLI activa deja la capacidad nativa sin verificar, nunca marcada como éxito.
