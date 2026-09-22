# Corrección del alcance tras rechazo de la entrega inicial

La aceptación declarada para v1.0 fue demasiado estrecha. Esta ampliación se evalúa por recorridos de negocio ejecutados y artefactos inspeccionables, además de pruebas unitarias. La etiqueta v1.0 preserva la entrega anterior; no se reescribe su historia.

## Trabajo y dependencias

1. Sol: requisitos trazables, seis procesos formales, SOP/RACI y especificaciones. Aceptación: referencias válidas, nodos alcanzables y excepciones concretas.
2. Luna: 25 tablas SQL físicas con restricciones, catálogo y 90 días de casos sintéticos integrados. Aceptación: integridad SQL, conciliación, distribuciones e historias reproducibles.
3. Terra: nueve perfiles de agente, herramientas de lectura, runs/trazas, contratos de razonamiento y adaptador de inferencia nativa. Aceptación: evidencia exacta, fallos bloqueados, origen inmutable y distinción entre reglas/inferencia.
4. Principal: marts analíticos, diagnóstico causal limitado, métricas longitudinales, libro Excel y dossier que conecte tablas → proceso → hallazgo → agente → propuesta → revisión.
5. Principal: ejecutar inferencia real con herramientas disponibles, guardar evidencia de procedencia; no presentar respuestas simuladas como uso de un modelo.
6. Integración: CLI documentada, demostración completa, pruebas de contratos y análisis, auditoría adversarial, publicación de artefactos verificados.

## Criterios de aceptación

- SQL permite consultar entidades reales con PK/FK y tipos; no basta una colección JSON.
- Los procesos incluyen roles, decisiones, evidencia, excepciones, entradas/salidas y trazabilidad a requisitos.
- Los agentes tienen configuración individual, herramientas, trazas y productos de trabajo útiles. El modo de reglas se identifica como tal.
- El análisis incluye historial, denominadores, descomposiciones, incertidumbre y evidencia por caso; no solo conteos del snapshot.
- La entrega permite encontrar y abrir los datos, procesos, especificaciones, ejecución de agentes y resultados sin explorar código a ciegas.
- Un caso se recorre hasta una recomendación verificable y una revisión humana registrada; no hay acciones externas del negocio.
- La generación permanece local y gratuita; la inferencia nativa usa la suscripción disponible o queda identificada como no ejecutada. No se introduce facturación externa.

## Límites que permanecen

Los casos iniciales son sintéticos. La entrevista con el negocio y un piloto real no se simulan. El alcance sigue siendo Analytics y consultoría: no operación en vivo, interfaz de CRM/ERP, pagos ni despacho automático. El archivo temporal del handoff original ya no está disponible; el alcance se reconstruye desde el texto leído en esta conversación y PROJECT.md, conservando sus límites explícitos.
