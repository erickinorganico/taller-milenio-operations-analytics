# Blueprint sintético, metodología y discovery

## Estado de evidencia

**El proceso real de Taller Milenio no ha sido observado ni validado.** Este mapa es una hipótesis de trabajo para construir fixtures, contratos, análisis y reportes. No es SOP ni descripción del negocio.

- `HYP-*`: supuesto del modelo sintético.
- `OPEN-*`: pregunta pendiente.
- `CTRL-*`: límite que el toolkit debe conservar.
- `SYNTHETIC`: dato fabricado de demo.

Discovery y construcción avanzan en paralelo: la falta de entrevista no bloquea el pipeline sintético, pero sí bloquea claims reales y fijar KPIs/targets definitivos.

## Frontera

Inicio analítico: se registra una necesidad, actividad comercial, evento de servicio, movimiento de parte, solicitud de grúa o hecho financiero. Fin: el snapshot permite reconstruir estado/hitos, calcular controles y producir excepciones/recomendaciones con evidencia.

Incluye modelado, ingestión, transformaciones, calidad, análisis, reportes y playbooks. Excluye operación en vivo, contacto, diagnóstico, seguridad vial, despacho, fiscal, pagos, pricing y decisiones automáticas.

## Roles hipotéticos

| Rol | Decisión/información posible | Pendiente de validar |
|---|---|---|
| cliente/conductor | necesidad, autorización, recepción | canales, identidad, consentimiento |
| contacto de flotilla | vehículos, aprobación, coordinación | buyer/user/approver y escalamiento |
| intake/admin | registro y seguimiento | campos, herramientas, duplicados |
| asesor/operaciones | alcance, estado, coordinación | autoridad de precio/promesa |
| técnico/control/QC | ejecución, bloqueos, verificación | asignación, tiempo, checklist |
| partes | compra, recepción, reserva, consumo | fuente física y ajustes |
| fleet sales/planner | oportunidad, contrato, mantenimiento/SLA | etapas, clocks, autoridad |
| tow coordinator/approver | request, revisión, unidad/precio/dispatch | checklist/regulación/seguros |
| finanzas/admin | factura, pago, saldo, gastos, efectivo | sistema fiscal y reconciliación |
| owner/manager | prioridades, excepciones, aprobación | cadencia/umbrales/delegación |

## Grain mínimo

| Registro | Una fila representa |
|---|---|
| customer/vehicle | identidad sintética y relación actual del fixture |
| lead | una necesidad/intake, no un servicio |
| quote | una versión de alcance/precio; no ingreso/pago |
| appointment | una ventana/resultado de visita |
| work order | un alcance de servicio para un vehículo |
| stock movement | un movimiento atómico de item/cantidad |
| reservation | cantidad de parte retenida para una orden |
| opportunity | un deal potencial, no contrato |
| contract/SLA term | acuerdo/medida versionada, no cumplimiento |
| maintenance | una obligación de servicio por vehículo/contrato |
| downtime interval | un intervalo de indisponibilidad |
| tow request | una necesidad de asistencia, no despacho |
| invoice | un documento gerencial; no CFDI |
| payment | un evento observado; allocation/saldo son separados |
| exception | un rule finding por sujeto/corrida |
| proposal | una recomendación read-only con evidencia |

## Recorridos sintéticos

### Particulares/taller

```text
lead -> calificación -> cotización -> cita -> recepción -> inspección
     -> autorización -> trabajo/capacidad/partes -> QC -> entrega
     -> factura/pago/saldo -> follow-up o retrabajo
```

Puntos analíticos: conversión por etapa, tiempos registrados, quotes sin respuesta, citas no confirmadas/no-show, WIP/bloqueos, parte faltante, QC/rework, entrega, pago parcial y recurrencia. `HYP-01`: las fuentes pueden enlazarse por customer/vehicle/work order; validar IDs y ownership real.

Excepciones fixture: quote aging, no-show/cancel, scope revisado, autorización parcial/faltante, capacidad, missing part, QC fail, rework y pago parcial/disputado.

### Flotillas

```text
cuenta/research -> oportunidad -> propuesta -> contrato activo
 -> roster/mantenimiento -> servicio/downtime/SLA
 -> factura/cobranza -> review/renewal
```

Puntos: pipeline comercial separado de delivery, mantenimiento próximo/overdue, downtime, SLA `met|at_risk|breached|review`, facturación/cobranza y next-step drafts. `HYP-02`: SLA usa términos sintéticos y reloj fijo. Sin términos/clocks/exclusiones no se calcula cumplimiento.

Excepciones: autoridad/contacto inciertos, roster duplicado, propuesta/contrato desalineados, mantenimiento sin fuente, downtime abierto, pausa SLA faltante, capacidad conflictiva y receivable disputado.

### Grúas

```text
request -> información/revisión humana -> quote -> assignment proposal
 -> human-confirmed dispatch record -> salida/llegada/traslado/handoff -> cierre
```

El análisis observa completitud y tiempos. `CTRL-01`: nunca certifica seguridad, unidad apropiada, precio, ETA o autorización de despacho. Un estado avanzado sin `safety_ref`, `human_approval_ref`, unidad/precio y confirmación se reporta como inconsistencia/gate faltante.

Excepciones: ubicación/condición incompleta, autoridad incierta, unidad no confirmada, price change, assignment replacement, cancel after dispatch, failed access/load, destination refusal e incidente/disputa.

### Partes y dinero

Inventario: catálogo -> purchase ordered -> received -> reserve -> consume/release -> return/adjust. Comprado/recibido/on-hand/reservado/disponible/consumido no se confunden.

Dinero: quote -> authorized service -> fulfilled charge -> invoice/receipt -> payment -> allocation -> receivable/cash evidence. Cost/expense tiene grain propio. `CTRL-02`: el toolkit es gerencial, no fiscal.

## Metodología por reporte

### Particulares

Preguntas: ¿dónde se pierde seguimiento?, ¿qué casos esperan acción?, ¿cuánto WIP/bloqueo hay?, ¿qué entrega genera rework? Salida: funnel/estado, cola de follow-up, citas, work-order journey, partes/QC, recomendaciones. Limitación: sin procesos/captura reales, conversiones son sintéticas.

### Flotillas

Preguntas: ¿qué es pipeline vs contrato?, ¿qué mantenimiento se aproxima?, ¿qué downtime/SLA puede evaluarse?, ¿qué saldo requiere revisión? Salida: commercial funnel, contract/maintenance matrix, SLA/downtime con definiciones y collections playbook. Limitación: términos/capacidad son supuestos.

### Grúas

Preguntas: ¿qué hitos existen?, ¿qué gates humanos faltan?, ¿dónde hay espera/cancelación? Salida: estados, milestone completeness/durations, excepción y safety evidence checklist. Nunca recomendaciones de conducción/diagnóstico/despacho.

### Administración

Preguntas: ¿qué capacidad/trabajo/stock está expuesto?, ¿cómo reconcilian cotización, factura, pago, saldo, gastos y efectivo? Salida: WIP/capacidad, inventory reconciliation, managerial money bridge y exception priorities. No contabilidad fiscal.

## Definiciones candidatas (no KPIs reales)

| Métrica | Definición sintética | Unknown/review cuando |
|---|---|---|
| quote follow-up backlog | quotes en estado enviado sin cierre después de threshold de fixture | falta timestamp/respuesta/owner |
| appointment outcomes | conteo por appointment y estado al cutoff | reschedule/cancel semantics no definidas |
| WIP/blocked | work orders por estado y edad desde hito | timestamps/bloqueos ausentes |
| first-pass QC | órdenes entregadas sin loop rework / elegibles | QC evidence incompleta |
| available stock | on-hand menos reservas activas | movimientos no reconcilian |
| maintenance due | plan item vs cutoff/km con término sintético | fuente odometer/clock desconocida |
| fleet downtime | suma de intervalos por vehículo | intervalo abierto sin regla |
| SLA status | término versionado aplicado a contexto elegible | término, clock o exclusión faltan |
| tow milestone duration | diferencia entre dos timestamps observados | hitos/zone faltan |
| receivable | invoice amount menos allocations válidas | invoice/payment no reconcilian |

Cada output declara grain, cutoff, población, fórmula, null policy y limitación.

## Escenarios fixture

| ID | Caso |
|---|---|
| SYN-B2C-01 | recorrido completo sano |
| SYN-B2C-02 | quote sin respuesta |
| SYN-B2C-03 | cancel/no-show |
| SYN-WRK-01 | scope revisado |
| SYN-WRK-02 | espera de pieza y resume |
| SYN-WRK-03 | retrabajo trazable |
| SYN-INV-01 | receipt parcial; ordenado no disponible |
| SYN-INV-02 | consumo/reserva inválidos detectados |
| SYN-FLT-01 | oportunidad/contrato/mantenimiento/SLA met |
| SYN-FLT-02 | SLA at-risk/breached |
| SYN-FLT-03 | roster con duplicado/review |
| SYN-TOW-01 | hitos y gates completos |
| SYN-TOW-02 | safety/conditions ambiguos |
| SYN-TOW-03 | assignment reemplazado |
| SYN-FIN-01 | pago parcial/overdue/final |
| SYN-FIN-02 | pago unmatched |
| SYN-AGT-01 | propuesta grounded/read-only |
| SYN-AGT-02 | solicitud adversarial de enviar/dispatch/mark-paid rechazada |

## Playbooks de evidencia

Cada recomendación debe incluir: `claim`, estado de evidencia, métrica/regla versionada, IDs/control refs, cutoff, limitación, owner sugerido, siguiente paso humano, riesgo y `approval_required`.

Prioridad sintética sugerida:

1. integridad/seguridad/dinero no reconciliado;
2. tow human gate o autorización faltante;
3. trabajo/stock/SLA bloqueado o vencido;
4. cobranza/follow-up atrasado;
5. oportunidad/marketing draft para revisión.

No calcular impacto monetario inventado. Reportar `unknown` si no existe baseline/costo/resultado observado.

## Guía de entrevistas priorizada

Entrevistar owner primero; después intake/asesor, taller/QC, partes, fleet sales/planner, tow approver y finanzas. Pedir un caso reciente normal y uno difícil; recorrer artefactos y decisiones, no el proceso ideal. No incorporar datos personales al repo.

### P0 — fronteras y autoridad

1. ¿Qué decisiones desea informar y cuáles siempre quedan humanas?
2. ¿Dónde empieza/termina cada journey y quién lo declara completo?
3. ¿Quién aprueba precio, trabajo, contrato, tow safety/unit/dispatch, write-off/refund?
4. ¿Qué sistema/documento es autoridad para vehículo, stock, factura, pago y efectivo?
5. ¿Qué información no debe entrar en este toolkit?

### P1 — particulares/taller/partes

1. Recorra intake, quote, cita, recepción, inspección, autorización, ejecución, QC, entrega y rework.
2. ¿Qué campos/hitos se capturan realmente y con qué timestamp?
3. ¿Cómo se asignan bahía/técnico y se registran esperas?
4. ¿Cómo se distingue ordered/received/on-hand/reserved/consumed/returned?
5. ¿Cómo se evita duplicar customer/vehicle y cómo funciona consentimiento/follow-up?

### P1 — flotillas

1. ¿Quién es buyer, service approver y payer?
2. ¿Qué diferencia oportunidad, propuesta, contrato activo y servicio cumplido?
3. ¿Cómo llegan roster, odometer/mantenimiento y autorizaciones?
4. ¿Qué inicia/pausa/detiene SLA y qué exclusiones/business calendar aplica?
5. ¿Qué define downtime, breach, dispute, review y renewal?

### P0 — grúas

1. ¿Qué información es obligatoria antes de quote/assignment/dispatch?
2. ¿Quién evalúa escena, vehículo, equipo, unidad y operador?
3. ¿Qué evidencia confirma precio, seguridad, disponibilidad y despacho?
4. ¿Qué significan exactamente salida, llegada, carga, traslado, handoff y cierre?
5. ¿Qué ocurre con acceso inseguro, failed load, cancel, destination refusal o incidente?

### P1 — dinero/reporting/privacy

1. ¿Qué representa quote/order/invoice/payment/allocation/expense/cash y cómo reconcilian?
2. ¿Qué reportes se revisan y qué acción sigue de cada uno?
3. ¿Qué denominador/cutoff/grain vuelve engañosa una métrica?
4. ¿Quién puede ver qué campos y cuánto se retienen?
5. ¿Cómo se autorizaría, anonimizaría y destruiría un export piloto?

## Checklist de observación futura

- artefactos blank/redacted y field dictionaries;
- caso normal y exception por journey;
- owner/actor/backup por estado;
- timestamp/source y wait-state real;
- approval evidence y versioning;
- reconciliation/control total actual;
- business calendar/SLA exclusions;
- access/retention/deletion;
- decisión/acción que consume cada reporte.

Solicitar permiso antes de ver/copiar. Metadata/definiciones primero; datos solo con autorización adicional.

## Ledger de validación

| Item | Decisión sintética | Evidencia requerida | Estado |
|---|---|---|---|
| HYP-01 IDs shared journey | customer/vehicle/work order enlazan fuentes | walkthrough + source map | unresolved |
| HYP-02 SLA | terms versionados y fixed clock | contract template + calculation | unresolved |
| OPEN-01 consent | boolean/version conceptual | wording/channel/withdrawal | unresolved |
| OPEN-02 authorization | evidence ref scoped | authority matrix/artifact | unresolved |
| OPEN-03 capacity | bay/technician states | scheduling observation | unresolved |
| OPEN-04 inventory | movement ledger | PO/receipt/issue/return walkthrough | unresolved |
| OPEN-05 tow safety | human gate refs | checklist/legal/insurance/roles | unresolved |
| OPEN-06 finance | managerial vs fiscal boundary | system map/reconciliation | unresolved |
| OPEN-07 metrics | candidate definitions only | fields/clocks/actions/counterexamples | unresolved |
| OPEN-08 privacy | no real data | approved policy/threat review | unresolved |

## Después de discovery

Crear una revisión fechada: citar evidencia privacy-safe; marcar cada item confirmed/changed/rejected/unknown; actualizar contrato y mapping; añadir fixture/regression antes de procesar export; rerun QA/E2E; mantener bloqueadas acciones externas. El toolkit es completo como demo sintética cuando pasa sus contratos; representa Taller Milenio solo después de validar este ledger.
