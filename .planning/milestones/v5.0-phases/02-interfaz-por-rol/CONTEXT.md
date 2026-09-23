# Phase 2 context — Interfaz por rol y fuentes

## Outcome and scope

Recepción, técnico y gerencia completan sus recorridos en español desde teléfono o escritorio y pueden consultar la evidencia fuente de una orden. Requisitos: DAT-01 y UX-01. Depende de las reglas y permisos de Phase 1.

## Decisiones vigentes

- Plantillas Django renderizadas en servidor y CSS adaptable. Los formularios usan validaciones del dominio y muestran errores accionables.
- Navegación y acciones por rol; toda autorización se repite en servidor.
- Explorador de datos con tablas permitidas, búsqueda acotada y enlaces a relaciones, sin SQL libre. CSV evita fórmulas ejecutables, aplica filtros de permisos y registra la exportación.
- Estados vacíos explican qué acción iniciar; no simular registros reales ni presentar demos como datos del taller.

## Evidencia de salida

Capturas o pruebas de navegador de los recorridos móvil y escritorio; pruebas de acceso directo a URL y CSV por rol; ejemplos de errores y de instancia vacía. Mantener pendientes los hechos de adopción y facilidad de uso real hasta un piloto.
