# Milenio — operación, inteligencia y seguimiento

## Core value
El personal puede llevar un vehículo desde recepción hasta entrega y cobro; gerencia puede explicar tiempos, costos y pendientes a partir de esos mismos registros. Las acciones sugeridas tienen responsable, evidencia y resultado.

## Estado actual: v6.0 Analytics y automatización operativa — cierre técnico local

El usuario amplió explícitamente el alcance: conectar analytics, automatizaciones y agentes con un dashboard principal que incluya piezas y servicios más utilizados. V6 implementó cortes persistentes desde la operación V5, dashboard por rol, trabajador local y paquete candidato probado. [Requisitos V6 archivados](milestones/v6.0-REQUIREMENTS.md), [auditoría](milestones/v6.0-MILESTONE-AUDIT.md) y decisiones en V6-DECISIONS.md.

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

## Estado de verificación local

V5 archivó 22 requisitos, nueve planes y cuatro fases verificados. V6 archivó 14 requisitos, cuatro planes y cuatro fases verificados en alcance técnico local. `artifacts/v6-verification.json` registra 115 pruebas, 0 fallos/errores y 2 omisiones por puertos ocupados; `artifacts/v6-delivery-verification.json` comprueba migración, respaldo/restauración y el candidato 2 extraído e instalado offline. Los recibos separados `v6-browser-verification.json`, `v6-worker-restart.json` y `v6-native-verification.json` registran navegador, cierre del trabajador e inferencia real local con tres revisores GPT-6 Luna sobre demo sintética. [Verificación V6](../docs/V6-VERIFICACION.md). Publicar un ZIP posterior requiere un recibo del mismo hash; no se afirma aceptación comercial.

## Siguiente implantación

Publicar el ZIP final solo después de comprobar su hash y arranque extraído. Validar procesos con personal del taller, conciliar datos autorizados y acordar despliegue, soporte y retención. La entrega técnica y el piloto siguen separados.

Actualizado el 23 de septiembre de 2026 tras el cierre técnico local V6.
