# Métricas analíticas

**Corte congelado:** `2026-09-21T18:00:00Z`. Todas las fuentes son fixtures sintéticos. Los resultados son descriptivos y no prueban causalidad, rendimiento real ni una meta.

| Métrica | Grain y filtro | Numerador / denominador | Límite |
|---|---|---|---|
| Estado B2C | Lead particular al corte | Estado contado / todos los leads particulares | No es embudo temporal; lead→cotización es unknown sin llave de atribución. |
| WIP | Orden de trabajo | No terminales / no aplica | Antigüedad de `opened_at` al corte o cierre. |
| Partes detenidas | Orden abierta | `waiting_parts` / abiertas | No prueba que comprar resuelva el atraso. |
| Bahías | Bahía al corte | Bahías ocupadas / bahías | Es ocupación instantánea, no horas-utilización. |
| SLA | Orden de flotilla contractual | Elegibles / contractuales; cumplidas / entregadas elegibles | Excluye canceladas, unknown y no aplicables. |
| Grúas | Solicitud | Con refs humanas / total | Solicitud→cierre no mide respuesta ni llegada. |
| CxC | Factura emitida | Saldo por bucket / saldo emitido | Factura, cobro, efectivo y gasto no se combinan. |

Los reportes conservan evidencia granular como `entity_type`, `entity_id`, `field` y `version`; véase `milenio.analysis.analyze` y `milenio.presentation.render_reports`.

Un denominador cero se representa como `unknown`, nunca como cero. Los importes internos son centavos MXN y se presentan en MXN una sola vez.
