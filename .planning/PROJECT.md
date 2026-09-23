# Milenio — operación, inteligencia y seguimiento

## Core value
El personal puede llevar un vehículo desde recepción hasta entrega y cobro; gerencia puede explicar tiempos, costos y pendientes a partir de esos mismos registros. Las acciones sugeridas tienen responsable, evidencia y resultado.

## Current Milestone: v5.0 Aplicación operativa

El usuario confirmó operación diaria más análisis y agentes, rechazó V4 como entrega final y autorizó seguir las recomendaciones de investigación y GSD sin nuevas preguntas rutinarias. Esta aprobación sustituye la antigua restricción de producto de solo lectura. No autoriza mensajes reales a terceros, compras, movimientos de dinero ni diagnóstico mecánico automático.

## Decisions
- Aplicación Django 5.2 LTS, interfaz española de servidor, SQLite local para un taller y servidor Waitress. No introducir un ERP completo antes de validar su ajuste automotriz ni copiar código de terceros.
- Una instalación corresponde a un taller; varios usuarios con roles. La edición SaaS multiempresa no es parte de esta entrega.
- Captura persistente, eventos auditables, reglas transaccionales y fechas reales. Demo sintética separada; instalación real vacía.
- Reutilizar los conceptos y controles analíticos V4, preservando sus artefactos históricos. No presentar datos de demostración como datos de Milenio.
- IA opcional mediante CLI Codex nativa autenticada y lecturas acotadas, sin API de pago. Reglas exactas permanecen deterministas. Propuestas sujetas a revisión; acciones internas idempotentes. Sin envíos externos automáticos.
- Piloto, procesos particulares, umbrales y resultados del taller siguen sin evidencia real. Esto no impide construir y verificar el software; impide afirmar adopción o impacto.

## Experience represented
Contratos y calidad de datos, trazabilidad de métricas, análisis de negocio, orquestación con evidencia, revisión y medición posterior. Aplicar estos patrones con código nuevo y ejemplos sintéticos, sin material privado de Torre.

## Evolution
V1–V4: toolkit analítico reproducible. V5: producto operativo con autenticación, base transaccional, métricas vivas y seguimiento. Las etapas de implementación, verificación local, publicación y adopción se registran por separado.
