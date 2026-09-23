# Milenio — operación, inteligencia y seguimiento

## Core value
El personal puede llevar un vehículo desde recepción hasta entrega y cobro; gerencia puede explicar tiempos, costos y pendientes a partir de esos mismos registros. Las acciones sugeridas tienen responsable, evidencia y resultado.

## Estado actual: v5.0 Aplicación operativa — cierre técnico local

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

Los 22 requisitos, 9 planes y 4 fases tienen evidencia local (`passed` por fase). La suite cerró 71/71 pruebas, incluidas 18 de inteligencia. `artifacts/v5-native-verification.json` acredita una corrida V5 real con GPT-6 Luna y datos demo sintéticos, separada de los recibos V1–V4. La auditoría técnica pasó 22/22 requisitos; el hito se archivó con cuatro fases y nueve planes verificados. La publicación es un candidato para piloto, no una afirmación de aceptación comercial. La aprobación del usuario para la dirección de producto y las decisiones GSD recomendadas consta en la conversación del 22 de septiembre; no es una clave de configuración GSD.

## Siguiente implantación

Validar procesos con personal del taller, conciliar datos autorizados y acordar despliegue, soporte y retención. No se inicia un nuevo hito de desarrollo automáticamente.

Actualizado el 22 de septiembre de 2026 tras el cierre técnico V5.
