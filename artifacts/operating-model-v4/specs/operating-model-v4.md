# Modelo operativo de Taller Milenio V4

## Estado y propósito

V4 une tablas sintéticas, métricas versionadas, mapas de procesos, una cola determinística OPS, propuestas de agentes AGT y seguimiento local en una entrega offline. El artefacto inspeccionado es `artifacts/operating-model-v4/`. Sirve para demostrar trazabilidad y revisar si el paquete ayuda a preparar una conversación operativa.

V4 no es un mapa validado del negocio real ni un sistema conectado a producción. No se han aportado datos, entrevistas, observaciones, aprobación de procesos, aceptación del cliente, seguimiento de adopción ni medición de impacto. El recibo `status=pass` y sus hashes demuestran integridad de esa compilación; no convierten los datos de ejemplo en evidencia del taller.

## Corte y cobertura de la entrega actual

El escenario es `operating_90_day`, `seed=42`, con corte fijo `2026-09-21T18:00:00Z` y `synthetic=true`. El catálogo contiene 27 tablas fuente, seis marts y 33 tablas SQLite. El registro contiene 31 métricas. Hay seis procesos especificados y nueve perfiles. Consulta los conteos OPS y AGT en la entrega abierta; son salidas de la compilación, no metas de operación ni cantidades únicas de problemas. OPS y AGT pueden referirse a la misma operación.

Las nueve corridas actuales en `agent_index.json` usan `backend=rules`; todas declaran `model_invoked=false`. La entrega actual no demuestra inferencia de un modelo. Corridas nativas que existan en una carpeta V2 tienen otro hash de fuente y no deben promocionarse como corridas actuales de V4.

## Contrato de datos

`source_catalog.json` identifica 27 tablas fuente con filas, tipos, nulos, claves y relaciones que realmente declara SQLite. Los seis marts (`mart_service_journey`, `mart_receivables`, `mart_daily_operations`, `mart_fleet_scorecard`, `mart_inventory`, `mart_process_waits`) resumen fuentes con un grain definido. El catálogo indica su clave lógica, sin fingir claves foráneas o primarias que los marts no declaran.

`metric_registry.json` es la salida de `milenio.metric_registry.build_metric_registry`. Cada ID `M-*` define fórmula, unidad, grain, población, tablas/campos, numerador, denominador, valor, corte, estado y limitación. Los valores medidos provienen de SQL code-owned sobre el SQLite sellado. `evidence_rows` es una muestra de hasta 12 filas de las fuentes declaradas, no la población elegible de la fórmula. `source_sha256` ata una lectura desde ruta a la base; con una conexión SQLite entregada por otro llamador la identidad no se infiere.

El corte no admite proyección arbitraria. La historia de estados solo existe donde hay eventos sintéticos explícitos y validados. Sin denominador, vínculo, historial, cobertura contractual o tabla de excepciones requerida, el estado es `unknown` y el valor es `null`; no se sustituye por cero. Un count igual a cero solo es medido si su población y fuentes están presentes.

## Seis recorridos analíticos

| Recorrido | Fuentes/grain relevantes | Medidas y preguntas permitidas | Condición de revisión |
|---|---|---|---|
| Particular, taller y partes | `customers`, `vehicles`, `leads`, `quotes`, `appointments`, `work_orders`, `bays`, `parts`, `purchases`, `stock_moves`, `reservations`, `journey_links`, `lifecycle_events`; una fila por entidad, evento o vínculo | M-B2C-LEADS/WON/QUOTE-MATCH; M-WIP-OPEN/WAITING-PARTS; M-BAY-OCCUPANCY; M-SERVICE-CYCLE; M-PROCESS-WAIT; inventario M-STOCK-* | Separar estados actuales de transiciones. Conversión requiere vínculo explícito. Una compra no aumenta existencia sin movimiento recibido. Ocupación instantánea no equivale a utilización histórica. |
| Cartera y administración | `quotes`, `work_orders`, `tows`, `invoices`, `payments`, `expenses`; las facturas y pagos conservan grain independiente | M-FIN-QUOTES/INVOICED/PAID, M-AR-RECEIVABLE/OVERDUE, M-FIN-CASH-NET/EXPENSES | Pagar se atribuye por `invoice_id`; fuente parcial puede sobrestimar saldo. Cifras gerenciales no son CFDI, ingreso reconocido, banco ni decisión de cobro. |
| Inventario | `parts`, `purchases`, `stock_moves`, `reservations`; una fila por parte, compra, movimiento o reserva | M-STOCK-ON-HAND/RESERVED/AVAILABLE/REORDER y M-WIP-WAITING-PARTS | Reconciliar movimientos y reservas. Compra ordenada no es stock; déficit crea revisión, no orden de compra. |
| Flotillas | `fleet_accounts`, `contacts`, `opportunities`, `contracts`, `maintenance`, `vehicles`, `work_orders`, `invoices`, `payments` | M-FLEET-OPEN-OPPS/PIPELINE/ACCOUNT-COVERAGE/ACTIVE-CONTRACTS/MAINTENANCE/SLA-ELIGIBILITY/SLA-RISK y M-AR-RECEIVABLE | Mantener separadas oportunidad, contrato y servicio. SLA mide solo población elegible. Términos, ventanas y kilometraje de demo no son compromisos reales. |
| Grúas | `tows`, `tow_units`, `vehicles`, `customers`; eventos explícitos si se revisan hitos | M-TOW-OPEN/HUMAN-REFS/CLOSE-HOURS | Presencia de referencias no certifica seguridad o aprobación. Solicitud a cierre no mide llegada. No seleccionar unidad, precio, ETA ni despacho. |
| Revisión semanal | `proposals`, fuentes de los cinco recorridos y `process_replay.json` | M-WEEKLY-PROPOSALS; M-WEEKLY-EXCEPTIONS permanece `unknown` porque no hay tabla versionada de excepciones en esta base | Revisar calidad/cobertura primero; registrar dueños, fecha y resultado como anotaciones humanas separadas del origen. Un registro ausente no se da por resuelto. |

Las seis definiciones de proceso viven en `processes/*.json`, con documentos `.md` y mapas `.svg`. Cada mapa es una hipótesis de trabajo con lanes, decisiones y controles; debe validarse con las personas responsables antes de llamarlo SOP.

## Cola OPS y perfiles AGT

`operating_cases.json` contiene excepciones generadas por reglas sobre fuentes completas. Cada decisión conserva ID, prioridad, evidencia, fuente, métricas, proceso y hash. La prioridad ordena revisión; no manda ejecutar una acción.

`agent_workspace.json` reúne nueve perfiles gobernados por `specs/agent_operating_contract.json`. Se permiten lecturas acotadas de casos/evidencia y métricas code-owned. Una corrida debe coincidir con el hash de la base actual y cada referencia citada se vuelve a comprobar contra la base de solo lectura, el alcance del rol, los casos visibles y las lecturas incluidas en el paquete. Si falla una comprobación, la corrida queda bloqueada y no genera propuestas actuales. Cada perfil ve una muestra pequeña de casos; esa muestra no reemplaza la cola OPS exhaustiva. En esta entrega el backend es `rules`, por lo que las propuestas AGT no son salida de un LLM. Un borrador sin mapeo explícito a una entidad produce una propuesta de corrida con todas las referencias verificadas; no se copia como si cada caso hubiera recibido una decisión individual.

Una futura corrida `native_codex` solo podrá usar la CLI local de la suscripción Codex cuando esté disponible y explícitamente seleccionada. Los recibos de ambas etapas deben acreditar el modelo. Una corrida bloqueada permanece bloqueada. No existe fallback a un servicio de inferencia pagado ni a acciones externas.

## Seguimiento y aceptación

`Seguimiento.xlsx` combina OPS y AGT para facilitar anotaciones. Mantenga separadas las columnas de origen y complete en una copia los campos humanos `owner`, `status`, `target_date`, `note` y `outcome_evidence`. `studio-review` verifica el artefacto sellado e importa anotaciones a una ruta nueva. Las declaraciones de la persona revisora son auto-reportadas: el paquete no verifica identidad, autorización ni resultado del negocio.

Una revisión del paquete V4 acepta el flujo cuando la persona puede:

1. confirmar modo sintético, corte, recibo y conteos sin confundirlos con cobertura real;
2. buscar un caso como `WO-003` y abrir su fuente;
3. navegar claves foráneas declaradas y distinguirlas de coincidencias o claves lógicas;
4. explicar una métrica desde ID y definición hasta numerador, denominador, estado, fuentes y limitación;
5. tratar `unknown` como evidencia insuficiente y conservar cero medido únicamente con población conocida;
6. distinguir la cola completa de excepciones OPS de las lecturas acotadas AGT;
7. copiar y revisar el libro sin alterar fuente, recibo o artefactos sellados.

La aceptación humana de estas condiciones no valida los procesos, convierte métricas sintéticas en metas ni activa un piloto de datos reales.

## Frontera con el adaptador privado del cliente

El adaptador independiente descrito en `docs/CLIENT-PLAYBOOK.md` acepta cuatro tablas: órdenes, facturas, pagos e inventario. No tiene leads, quotes completos, appointments, roster/fleet, contratos, maintenance, tow, compras/movimientos detallados, eventos ni journey links de V4. No se deben trasladar las 31 métricas ni las seis journeys a esa fuente reducida. La falta de una tabla o relación significa fuera de alcance/`unknown`, nunca ausencia de actividad. Datos autorizados deben quedarse en `private/clients/`, con acceso, minimización, retención, eliminación y fuente acordados por separado.
