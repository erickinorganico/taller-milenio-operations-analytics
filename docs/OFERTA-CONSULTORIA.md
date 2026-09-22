# Propuesta de servicio — Diagnóstico operativo y analítica de Taller Milenio

> Plantilla de alcance para conversación comercial. El repositorio público es un demostrador sintético de la metodología; no prueba que Taller Milenio haya contratado, desplegado o obtenido resultados de este servicio.

## Objetivo del servicio

Convertir exports autorizados de la operación en un diagnóstico reconciliado de particulares, taller/partes, flotillas, grúas y administración. El servicio entrega definiciones, hallazgos verificables, excepciones priorizadas y una cadencia de revisión para que responsables humanos decidan los siguientes pasos.

No incluye operar un CRM/ERP, enviar mensajes, contactar prospectos, diagnosticar vehículos, fijar precios, despachar grúas, emitir facturas fiscales, procesar pagos ni mover dinero.

## Ficha de alcance a completar

| Campo | Acuerdo del piloto |
|---|---|
| Cliente y sponsor | `[nombre / responsable]` |
| Preguntas prioritarias | `[3–5 decisiones concretas]` |
| Periodo y fecha de corte | `[inicio, fin, zona horaria]` |
| Fuentes autorizadas | `[archivo, propietario, sistema de origen]` |
| Módulos incluidos | `[particulares / taller-partes / flotillas / grúas / administración]` |
| Responsables de validación | `[operación, partes, flotillas, grúas, administración]` |
| Datos excluidos | `[PII, notas libres, documentos, campos sensibles]` |
| Criterio de aceptación | `[controles, preguntas respondidas, limitaciones aceptadas]` |

## Prerrequisitos de discovery

Antes de recibir datos se realiza una sesión con el sponsor y walkthroughs breves con quienes capturan y usan la información. Se confirma:

- dónde empieza y termina cada recorrido, sus estados y responsables;
- qué sistema/archivo es autoridad para cliente, vehículo, stock, servicio, contrato, factura y pago;
- grain, IDs, fechas, zona horaria, moneda, duplicados, estados terminales y significado de faltantes;
- gates humanos de autorización, seguridad de grúa, precio, despacho, cobranza y publicación;
- propósito, minimización, acceso, retención y eliminación del extracto.

Si una definición o evidencia no existe, se registra como `unknown`, `review` o `blocked`; no se convierte en cero ni se inventa.

## Trabajo incluido

1. **Mapa y contrato de datos.** Diccionario fuente→modelo, relaciones, reglas de estado, supuestos y preguntas pendientes.
2. **Perfil y calidad.** Conteos, unicidad, referencias, completitud, fechas, importes, duplicados, inconsistencias y filas en revisión.
3. **Reconciliación operacional.** Taller/WIP/capacidad, movimientos y disponibilidad de partes, pipeline/contrato/mantenimiento/SLA, hitos de grúa y puente gerencial entre cotización, factura, pago, saldo, gastos y efectivo.
4. **Reporte de decisión.** Cuatro lentes separados, informe ejecutivo imprimible, charts, evidencia por hallazgo, excepciones priorizadas y limitaciones.
5. **Reunión accionable.** Revisión con owners para aceptar, corregir o rechazar definiciones; asignar responsable y siguiente paso humano; registrar decisiones sin ejecutar acciones externas.

## Entregables y aceptación

| Entregable | Se acepta cuando |
|---|---|
| Mapa de fuentes, grain y definiciones | responsables confirman autoridad, significado y límites o dejan pendientes explícitos |
| Reporte de calidad | cada issue indica fuente/fila/campo, severidad y disposición; no hay descartes silenciosos |
| Paquete analítico reconciliado | totales de control acordados coinciden o la diferencia queda explicada/bloqueada |
| Reportes por módulo + ejecutivo | toda cifra declara cutoff, población, fórmula, grain y limitación |
| Cola de excepciones/propuestas | cada item cita evidencia, owner sugerido y aprobación humana; no contiene ejecución automática |
| Playbook de revisión | quedan frecuencia, participantes, agenda, decisiones y criterio de cierre acordados |
| Recibo técnico | identifica input/código/artefactos y resultados de controles para esa corrida |

La aceptación técnica no equivale a validar causalidad, impacto, cumplimiento fiscal, seguridad vial o aptitud para producción.

## Responsabilidades del cliente

El cliente designa sponsor y owners, autoriza el extracto mínimo, confirma que puede compartirlo, explica procesos/definiciones, valida control totals y hallazgos, protege decisiones de seguridad/dinero/contacto, y revisa que ningún artefacto sensible se publique. La calidad del resultado depende de la cobertura y veracidad de las fuentes autorizadas.

## Adopción por fases

| Fase | Resultado | Gate para avanzar |
|---|---|---|
| 0. Demostrador sintético | metodología reproducible sin datos reales | comprensión del alcance; ningún claim del negocio |
| 1. Discovery | proceso, owners, diccionario y riesgos validados | sponsor aprueba preguntas y extracto mínimo |
| 2. Piloto aislado | análisis read-only sobre copia autorizada y anonimizada/seudonimizada | calidad/reconciliación aceptables y rollback probado |
| 3. Cadencia asistida | actualización periódica de archivos y reunión de decisiones | owners usan definiciones de forma consistente |
| 4. Evolución opcional | automatización de ingestión/reporting bajo nuevo alcance | seguridad, acceso, operación y soporte aprobados por separado |

Cada fase requiere una aceptación propia. No se prometen precio, retorno, ahorro o mejora antes de acordar volumen, alcance, calidad de datos, responsabilidades y una línea base medible.

## Resultado de la propuesta

Al cerrar el piloto, el cliente recibe un diagnóstico trazable y un proceso de revisión; conserva la autoridad sobre toda decisión. Cualquier integración, mensaje, contacto comercial, despacho, pago, publicación de datos o uso operacional requiere un contrato y autorización adicionales.
