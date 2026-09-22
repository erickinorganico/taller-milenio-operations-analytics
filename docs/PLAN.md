# Plan de entrega — Taller Milenio Operations & Growth Analytics

## 1. Resultado y autoridad

El resultado es un toolkit batch, local y reproducible de Analytics/consultoría. Modela información de particulares, taller/partes, flotillas, grúas y administración; calcula indicadores y excepciones; genera cuatro reportes y propuestas read-only; y conserva evidencia por corrida.

El proceso real sigue sin investigar. La primera versión usa únicamente datos sintéticos y no hace afirmaciones sobre desempeño de Taller Milenio.

Autorizado: desarrollo local, dependencias open source, fixtures, análisis, visualizaciones, tests, documentación y publicación frecuente del repositorio público `erickinorganico/taller-milenio-operations-analytics`.

No autorizado: datos reales/sensibles, contacto, mensajes, prospección enviada, precio/ETA comprometido, diagnóstico, despacho, fiscal/pagos, movimiento de dinero o conexión a sistemas reales.

Fuera de alcance: aplicación navegable, frontend/backend, servidor, CRM, ERP o software operacional en vivo.

## 2. Registro de orquestación

| Secuencia | Tarea | Modelo/esfuerzo | Salida | Check |
|---:|---|---|---|---|
| 1 | Plan, blueprint, grain, ownership, E2E | Sol `gpt-5.6-sol`, `medium` | `PLAN.md`, `PROCESS.md` | cobertura completa y supuestos visibles |
| 2A | fixtures, importadores, queries/tests mecánicos | Luna nativo | data/tests asignados | determinismo, fallos y contratos |
| 2B | análisis, visualizaciones y render de reportes | Terra nativo | módulos asignados | métricas/reportes reproducibles |
| 2C | pipeline, contratos e integración | agente principal | código core | paquete completo y receipt |
| 3 | integración/verificación cruzada | Sol `gpt-5.6-sol`, `medium` | `test_pipeline.py`, docs | E2E verde y fallo controlado |
| 4 | revisión sistémica de SLA, grúas, dinero, evidencia | Astra `gpt-6-astra` | findings | críticos corregidos y revalidados |

Registro honesto: la primera asignación de Sol se diseñó para una app local según el handoff anterior. La solicitud fue corregida y las tareas se redirigieron al toolkit analítico; los documentos se reescribieron y no se conserva app/servidor/UI como entregable.

## 3. Módulos analíticos

| Módulo | Hechos/dimensiones | Decisiones que informa | Control |
|---|---|---|---|
| Particulares | cliente, vehículo, lead, cotización, cita, work order | seguimiento, drop-off, carga, entrega/retrabajo, recurrencia | consentimiento/unknown explícitos |
| Taller y partes | tareas/estados, técnicos, bahías, compras, stock, reserva/consumo | WIP, bloqueos, capacidad, exposición de inventario | comprado != disponible; reservado != consumido |
| Flotillas | cuenta, contacto, oportunidad, propuesta/contrato, mantenimiento, downtime/SLA | pipeline, próximos servicios, riesgo y cobranza | oportunidad != contrato != servicio |
| Grúas | solicitud, hitos, precio, unidad, gates humanos | completitud, tiempos registrados y excepciones | análisis read-only; no seguridad/despacho |
| Administración | cotización, servicio, factura, pago, gasto/costo, saldo, efectivo | reconciliación y atención gerencial | estados financieros separados; no fiscal |
| Growth | fuente/seguimiento B2C y research/propuesta B2B | borradores de segmentación/value proposition | fuentes públicas no autorizan contacto |
| Control | reglas, excepciones, evidence refs, proposals | colas priorizadas y siguiente revisión | aprobación requerida; cero ejecución externa |

## 4. Fases y dependencias

### Fase 0 — repositorio público y contrato

Crear/enlazar el repositorio autorizado, README/licencia/.gitignore y commits pequeños. Proteger inputs/bases/artefactos locales mediante `.gitignore`. Salida: scaffold reproducible y alcance visible.

### Fase 1 — discovery y blueprint en paralelo

Documentar los tres recorridos, actores, decisiones, esperas, excepciones, grain y preguntas. Construir sobre hipótesis `HYP-*` sin esperar entrevistas. Salida: `PROCESS.md` y ledger de validación.

### Fase 2 — contratos y dataset sintético

Definir entidades/campos/referencias/estados, fechas con zona, centavos MXN y semilla fija. Incluir normalidad, atraso, cancelación, retrabajo, pieza faltante, SLA en riesgo/breach, tow incompleto y cobranza parcial. Salida: fixture completo y validadores.

Exit: referencias resuelven, IDs únicos, invariantes financieras/inventario pasan, datos parecen inequívocamente ficticios.

### Fase 3 — pipeline batch

Implementar `run_pipeline(output, dataset=None)`: validar input, preservar snapshot JSON/CSV, materializar SQLite, transformar, analizar, renderizar y publicar receipt al final. Rechazar destino existente e input inválido sin artefacto completo.

Exit: setup inicial con Python 3.12+, wheelhouse preparado, instalación limpia offline probada; corrida sin red, source sin mutación, output completo y digest reproducible. Solo se acepta `DEMO_NOW`; otro cutoff falla.

### Fase 4 — análisis y reconciliaciones

Producir `analysis.json`, `quality.json`, `exceptions.json`, `timeline.json`. Cada métrica declara grain, población, cutoff, numerador/denominador, regla de null/unknown y limitación. Cada excepción cita evidencia.

Reconciliar al menos: pipeline por etapas; órdenes por estado; stock on-hand/reservado/disponible; contratos y mantenimiento; tow states/gates; facturación, pagos, saldo, costos/gastos y efectivo.

### Fase 5 — cuatro reportes y data storytelling

Generar:

- `reports/particulares.md`;
- `reports/flotillas.md`;
- `reports/gruas.md`;
- `reports/administracion.md`;
- `reports/informe_ejecutivo.html` imprimible;
- charts reproducibles en `reports/charts/`.

Cada reporte incluye objetivo, estado de evidencia, hallazgos sintéticos, tabla/chart, limitaciones, excepciones y playbook. No se publica una cifra sin definición/evidencia.

### Fase 6 — propuestas agentic y eficiencia

Generar `proposals.json` determinista: agente, título, rationale, evidencia, responsable sugerido, riesgo, `approval_required=true`, `external_execution=false`. Aprobar no ejecuta nada.

Crear `PROJECT-EFFICIENCY.md` solo si el código presenta una decisión repetida cerrada. Laya empieza en shadow con baseline etiquetado multilingüe, `REVIEW`, fallback, latencia cold/warm y evaluación completa. Queda prohibido en diagnóstico, precio, seguridad, despacho, contacto o dinero.

### Fase 7 — QA/E2E y evidencia

Ejecutar unittest, E2E de pipeline, fallo controlado, privacidad/secrets scan, reproducibilidad/hash y `git diff --check`. Conservar `verification.json` y receipt final. No considerar HTML visual como sustituto de reconciliación.

### Fase 8 — revisión Astra y cierre

Revisar arquitectura, SLA, grúas, dinero, acciones externas y claims. Corregir findings, rerun checks afectados y E2E completo. Publicar solo después de pruebas y revisión de artefactos sintéticos.

### Fase futura — piloto con exports reales

Requiere nueva autorización, discovery resuelto, extracto anonimizado, diccionario, controles, rollback y no publicación de datos.

## 5. Ownership e interfaces

| Workstream | Owner | Depende de | Interface |
|---|---|---|---|
| plan/process/docs/E2E | Sol | handoff corregido | artifacts y criterios de este plan |
| contracts/pipeline/CLI/integración | principal | contratos + módulos | `run_pipeline(output,dataset)->receipt` |
| fixtures/importers/tests mecánicos | Luna | fields/invariantes | dataset completo determinista |
| analysis/render/charts | Terra | dataset y definiciones | JSON/report paths contractuales |
| revisión adversarial | Astra | candidato verde | findings con evidencia/severidad |

Nadie modifica archivos de otro owner sin coordinación. Cambios de schema deben actualizar fixture, análisis, tests y docs juntos.

## 6. Contrato de artefactos

Una corrida exitosa contiene exactamente los outputs descritos en `ARCHITECTURE.md`. El receipt incluye status, schema/policy versions, frozen cutoff, counts, checks, relative paths y hashes. El content digest excluye metadatos de runtime no deterministas.

Los reportes comparten una sola fuente: `analysis.json`/artefactos estructurados. No recalculan métricas de forma divergente dentro de templates.

## 7. E2E acceptance

| ID | Escenario | Pass |
|---|---|---|
| E2E-01 | `run_pipeline` con fixture default | genera todos los archivos obligatorios y receipt completo |
| E2E-02 | snapshot fuente | `dataset.json` y CSV cubren todas las entidades; input Python no muta |
| E2E-03 | SQLite | contiene snapshots/relaciones esperadas y reconcilia conteos |
| E2E-04 | particulares | reporte contiene funnel, follow-up, citas, autorización/delivery/rework con evidencia sintética |
| E2E-05 | flotillas | separa pipeline, contrato, mantenimiento, downtime/SLA y cobranza |
| E2E-06 | grúas | muestra hitos/gates/excepciones y declara no decidir seguridad/despacho |
| E2E-07 | administración | separa cotización, factura, pago, saldo, costo/gasto y efectivo; reconcilia stock/capacidad |
| E2E-08 | ejecutivo/charts | HTML estático imprimible enlaza/embed outputs; charts existen y no introducen métricas nuevas |
| E2E-09 | proposals | toda propuesta tiene evidencia válida, aprobación requerida y ejecución externa false |
| E2E-10 | quality/exceptions | unknown/review/blocked no son cero; excepciones apuntan a registros/controles |
| E2E-11 | invalid dataset | lanza error y no deja `receipt.json` completo |
| E2E-12 | overwrite | destino existente es rechazado y sus bytes permanecen intactos |
| E2E-13 | reproducibilidad | mismas entradas generan mismo content digest/hashes deterministas |
| E2E-14 | source immutability | dataset provisto queda byte/equality idéntico tras éxito/fallo |
| E2E-15 | CLI demo/analyze/verify | comandos documentados terminan con códigos correctos y outputs indicados |
| E2E-16 | offline/privacy | no red, secretos, PII real, conectores o rutas de acción externa |
| E2E-17 | controlled failure | evidencia el fallo esperado sin etiquetarlo como corrida verde |
| E2E-18 | orchestration review | registro completo y findings Astra corregidos/revalidados |

## 8. Métricas candidatas (no definitivas)

Particulares: leads por etapa, quote response, appointment confirmation/no-show, WIP/blocked age, first-pass QC/rework. Flotillas: pipeline por etapa, active-contract count, maintenance due/overdue, downtime, SLA risk/breach con término disponible, receivable aging. Grúas: completitud/hitos y tiempos registrados, cancelaciones, gates faltantes. Administración: bay/technician utilization, stock exposure, quote pipeline, invoiced/paid/receivable, expenses/cash.

Ninguna definición se presenta como KPI real hasta validación. El informe siempre muestra cutoff, población, grain y limitación.

## 9. Tests mínimos

- unitarios de validación, fechas, centavos, estados y reconciliaciones;
- integridad referencial, IDs/duplicados y datasets incompletos;
- inventario/factura/pago/SLA/tow gate como reglas analíticas;
- snapshot/CSV/SQLite coherentes;
- report completeness y evidence refs;
- proposals sin ejecución;
- E2E éxito/fallo/overwrite/inmutabilidad/reproducibilidad;
- secrets/PII fixture scan y fórmulas CSV neutralizadas.

## 10. Terminado

Setup limpio probado; demo offline reproducible; modelo completo; escenarios normales/problemáticos; cuatro reportes + ejecutivo/charts; excepciones/propuestas con evidencia; tests y fallo controlado; receipt/hash; docs ES/EN/metodología/playbooks/real-data; registro Sol/Terra/Luna/Astra; Astra cerrado; repo público con commits verificados.

No está terminado si hay solo visualización, flotillas/grúas como notas, claims reales inventados, estados financieros mezclados, fixtures plausibles como reales, dependencia SaaS, ausencia de pruebas/evidencia o cualquier capacidad de enviar/dispatch/cobrar/promover automáticamente.
