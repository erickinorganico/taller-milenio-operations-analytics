---
gsd_state_version: 1.0
milestone: v6.0
milestone_name: Analytics y automatización operativa
status: complete_local
last_updated: "2026-09-23"
last_activity: 2026-09-23 — Cierre técnico local V6 archivado
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 4
  completed_plans: 4
  percent: 100
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (actualizado el 23 de septiembre de 2026).

**Core value:** El taller lleva un vehículo desde recepción hasta entrega/cobro y Gerencia explica tiempos, costos y pendientes desde esos registros.
**Current focus:** Publicar y verificar el ZIP final; después, piloto con datos autorizados del taller.

## Current position

Phase: 8 completada; fases 5–8 archivadas en `.planning/milestones/v6.0-phases/`.
Plan: 4/4 completados localmente.
Status: Hito técnico V6 cerrado; publicación y aceptación separadas.

## Evidence

- `.planning/milestones/v6.0-MILESTONE-AUDIT.md`: 14/14 requisitos, 4/4 fases, 6/6 conexiones y 4/4 recorridos en alcance técnico local. `gsd-tools query audit-open --json` devolvió cero asuntos abiertos; `query init.manager` devolvió `all_complete=true` antes del archivo.
- `artifacts/v6-verification.json`: versión 6.0, 115 pruebas, 0 fallos, 0 errores, 0 omisiones. El arranque extraído se comprobó separadamente.
- `artifacts/v6-delivery-verification.json`: candidato 2 SHA-256 `a0845d2f2a418f863e86d06a0da2a42999849018146c0b92081a4cf916e8fa1f`, instalación offline extraída, HTTP autenticado, trabajo de reglas/latido, migración V5→V6 y respaldo/restauración.
- `artifacts/v6-browser-verification.json` y `artifacts/v6-worker-restart.json`: filtros, comparación, móvil sin desbordamiento, pausa/reanudación y fin del trabajador hijo con el servidor.
- `artifacts/v6-native-verification.json`: trabajo nativo real #5 completado con tres revisores GPT-6 Luna y `model_invoked=true`; intento previo #4 fallido preservado sin reintento automático. Demo sintética.
- `docs/V6-VERIFICACION.md`: procedimiento reproducible y límites; recibos V5 permanecen en su hito.

## Decisions

Django 5.2 LTS, SQLite local por taller, Waitress en loopback, datos fuera del código y demo separada. Cortes y cola en la misma base para respaldo íntegro. Reglas deterministas por defecto; Codex CLI nativa opt-in, con propuesta revisable y sin envío externo automático. Las fechas de emisión, pago y actividad se mantienen distintas. Un filtro histórico no reconstruye estados pasados no guardados.

## Remaining work

1. Generar ZIP final tras congelar archivos; comprobar SHA del ZIP, suite, instalación extraída y CI del mismo contenido. El candidato 2 no acredita automáticamente el ZIP publicado.
2. Piloto con personal del taller, datos autorizados, despliegue, soporte y retención. La verificación sintética no demuestra adopción ni resultado de negocio.

## Continuity

Roadmap, requisitos, auditoría y fases V6 están en `.planning/milestones/`. El cierre técnico se registró sin excepción de verificación. Los documentos y recibos distinguen pruebas locales, paquete candidato, publicación y aceptación comercial.

## Operator Next Steps

- Publicar únicamente un ZIP cuyo hash coincida con su verificación final; registrar los recibos de publicación por separado.
