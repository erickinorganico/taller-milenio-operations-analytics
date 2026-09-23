# Guía de uso de la entrega V4

Esta guía sirve para abrir y revisar la entrega local `artifacts/operating-model-v4/INICIO.html` en una reunión de 30 minutos. El paquete actual es sintético: los registros, los eventos y las propuestas no describen resultados observados del Taller Milenio.

## Antes de la reunión

Abra `INICIO.html` directamente en el navegador. No requiere servidor ni conexión. En **Panorama**, confirme el corte `2026-09-21 18:00 UTC` y `synthetic=true`. Para verificar el recibo de integridad, abra **Archivos y uso** y ejecute el comando `verify-studio` que aparece allí; el recibo no se muestra como evidencia de negocio en Panorama. Este es un escenario de 90 días, pero el corte analítico es fijo. La historia previa también es ficticia.

El paquete contiene 27 tablas fuente, seis marts derivados, 31 definiciones de métricas, seis procesos documentados y nueve perfiles de agente. `Milenio_Analisis.xlsx` contiene 36 hojas; `Metricas_y_fuentes.xlsx` separa métricas, fuentes y campos. `receipt.json` permite verificar la identidad de la entrega. Ninguno de estos artefactos certifica datos del negocio real.

En la pestaña **Prioridades y revisión**, lea los conteos OPS y AGT del paquete abierto; cambian cuando cambian las reglas, los casos visibles o los borradores de las corridas. OPS es la cola determinística de excepciones sobre la población escaneada. AGT reúne propuestas de borradores de las corridas actuales con todas sus referencias validadas; cada borrador sin asignación explícita a una entidad produce una propuesta de corrida, no una fila por caso. Las dos colas pueden hablar de la misma operación: no sume sus filas como casos únicos ni como acciones distintas.

Las nueve corridas de este paquete son `backend=rules` y `model_invoked=false`. Son una línea base reproducible, no inferencia de modelo. Existen corridas nativas en la entrega histórica V2, pero sus hashes pertenecen a otra base y no certifican inferencia en V4. Revise `agent_workspace.json` y `agent_index.json` de la entrega abierta para conocer el estado vigente.

## Reunión en 30 minutos

| Minutos | Qué hacer | Qué confirmar |
|---|---|---|
| 0–4 | Abra **Panorama** y lea sello, corte, fuentes, roles y controles de calidad. | Que los datos son sintéticos, el corte es el declarado y el recibo corresponde a esta carpeta. |
| 4–11 | Abra **Prioridades y revisión**, elija origen `OPS` y busque `WO-003`. Abra la ficha. | La regla encuentra la orden `waiting_parts`, con `Falta filtro`; `technician_id`, `bay_id` y `qc_ref` están vacíos. La propuesta aparece como `P2` y tiene referencias a la orden y al cálculo. |
| 11–16 | Desde la ficha, abra la fuente `work_orders`; siga los IDs relacionados que tienen enlace. Después abra `M-WIP-WAITING-PARTS`. | La fuente permite contrastar campos, grain y referencias físicas. La métrica muestra 1 orden esperando partes de 7 órdenes abiertas (0.142857); la cifra es del corte sintético, no un SLA ni tiempo de espera. |
| 16–21 | Abra `M-AR-OVERDUE` y `M-FLEET-SLA-RISK`; compare valor, estado, denominador, definición y limitación. | Cartera vencida medida: 3,227,500 centavos MXN al corte. `M-FLEET-SLA-RISK` está `unknown` por población elegible cero; no lo lea como riesgo cero. `M-WEEKLY-EXCEPTIONS` también está `unknown` porque esta base no materializa una fuente versionada de excepciones. |
| 21–26 | Filtre origen `AGT` y busque `WO-003`. Abra el perfil de operaciones y la traza de la corrida. | Confirme `rules`, `model_invoked=false`, el hash, las lecturas y el resultado. La propuesta AGT es de corrida y enlaza referencias exactas, no atribuye un borrador genérico a `WO-003`. La cola OPS es el lugar para revisar la excepción exhaustiva del caso. |
| 26–30 | Abra `Seguimiento.xlsx` y elija qué referencias verificar después de la reunión. | Asigne persona y fecha solo tras confirmación humana. Guarde una copia editable fuera de la entrega sellada. |

### Búsqueda y navegación

En **Prioridades y revisión**, el campo de búsqueda admite IDs como `WO-003`, título y texto de evidencia. Use el filtro de origen para separar OPS, AGT o ambas colas. Al abrir la ficha, los vínculos de métricas, procesos, fuente y agente conservan el recorrido.

En **Tablas fuente**, seleccione la tabla y busque el ID. Las relaciones declaradas como claves foráneas aparecen como enlaces a los registros relacionados; el catálogo distingue clave física de clave lógica. No suponga que dos filas coinciden por tener el mismo nombre, vehículo o importe: para atribución de lead a cotización se requieren vínculos `journey_links` explícitos.

En **Métricas y cálculo**, busque el ID o el tema. La página muestra fórmula, población, estado, unidad, corte, limitación, SQL de solo lectura, fuentes y una muestra acotada. Use la muestra para orientarse; reproduzca el cálculo con la consulta y la tabla fuente. La ausencia de denominador o cobertura produce `unknown`, no cero.

### Copia para seguimiento

No edite `Seguimiento.xlsx` dentro de la carpeta sellada. Para este paquete sintético, cree una copia y guárdela en una ruta nueva:

```powershell
New-Item -ItemType Directory -Force artifacts/review-v4 | Out-Null
Copy-Item artifacts/operating-model-v4/Seguimiento.xlsx artifacts/review-v4/Seguimiento-anotado.xlsx
```

En la copia, conserve las columnas de origen. Complete únicamente `owner`, `status`, `target_date`, `note` y `outcome_evidence`. Los estados admitidos son `pending`, `accepted`, `in_progress`, `done` y `dismissed`. Marcar `done` requiere responsable, nota y evidencia declarada. El dato es auto-reportado y no verifica que alguien haya ejecutado la acción.

Importe la copia en una carpeta nueva, fuera de la entrega original:

```powershell
.\.venv\Scripts\python.exe -m milenio studio-review `
  --report artifacts/operating-model-v4 `
  --input artifacts/review-v4/Seguimiento-anotado.xlsx `
  --output artifacts/review-v4/importacion `
  --reviewer "Nombre y rol declarados"
```

El comando verifica el recibo y crea `reviews.jsonl`, `review_origin.json` y `REVISION.html`. No modifica la base, `INICIO.html` ni el libro sellado; tampoco cambia el sistema del cliente. Use una ruta de salida nueva para cada importación.

## Qué revisar en cada recorrido

| Recorrido | Criterio de aceptación para esta demo | Límite que debe quedar visible |
|---|---|---|
| Particular, taller y partes | Buscar un lead, cotización y orden; seguir solo vínculos explícitos. Separar órdenes abiertas, espera de partes, retrabajo, bahías, movimientos y reservas. Para `WO-003`, comprobar estado, bloqueo y campos vacíos. | Estado de snapshot no es funnel temporal; ocupación de bahías no es utilización histórica; compra ordenada no incrementa stock sin movimiento de recepción. La historia y los enlaces incluidos son sintéticos. |
| Cartera y administración | Reproducir facturas emitidas, pagos vinculados por `invoice_id`, saldo y vencimiento. Revisar el puente `20,982,500 - 17,081,250 = 3,901,250` centavos MXN. | No equivale a ingreso reconocido, contabilidad fiscal, banco ni autorización de cobro. Cotización, factura, pago, gasto y efectivo son medidas distintas. |
| Inventario | Verificar `disponible = existencia por movimientos - reservas activas`, con el detalle de movimientos y reservas. Un faltante aparece como revisión. | No se crea una orden de compra ni se supone que el proveedor entregará. Conteos ficticios no son inventario físico. |
| Flotillas | Separar oportunidad, pipeline, contrato vigente, mantenimiento, servicio elegible, SLA y cartera. Leer el denominador y el estado de evidencia. | El pipeline no es contrato ni ingreso. Cobertura contractual y relojes son supuestos sintéticos; `unknown` no es cumplimiento ni incumplimiento. |
| Grúas | Comprobar hitos y presencia de referencias de seguridad/aprobación; leer la fórmula de tiempo solicitud-a-cierre. | Una referencia presente no autentica la aprobación ni certifica seguridad. Solicitud-a-cierre no es tiempo de respuesta ni llegada. No seleccionar unidad ni despachar. |
| Revisión semanal | Revisar primero calidad/cobertura; luego OPS, AGT, procesos, responsables pendientes y evidencia faltante. Mantener los IDs al copiar el libro. | Propuesta pendiente no es acción ejecutada. Registro ausente entre cortes no demuestra resolución. La entrega no mide adopción ni impacto. |

La persona que recibe el paquete puede aceptarlo para practicar el flujo si puede encontrar el ID de una excepción, abrir su fuente, reproducir una métrica con su población, distinguir `unknown`, separar OPS de AGT y guardar una anotación humana sin alterar el origen.

## Cómo leer los archivos

- `INICIO.html`: panorama, buscadores, fichas y enlaces locales entre casos, fuentes, métricas, agentes y procesos.
- `operating_model.json`: paquete integrado versionado con fuentes, métricas, procesos, OPS y AGT.
- `source_catalog.json` y `tables/*.csv`: 27 tablas fuente y seis marts, filas y metadatos de columnas.
- `metric_registry.json`: 31 definiciones ejecutadas; `source_sha256` enlaza la lectura por ruta con la base de esta entrega.
- `operating_cases.json`: cola OPS y cobertura de escaneo por tabla.
- `agent_workspace.json`: nueve corridas actuales, hash, estado, traza, propuestas AGT e IDs de métrica/proceso.
- `agent_runs/<rol>/run.json`, `input_packet.json`, `result.json`, `tool_trace.jsonl`: línea base del rol, entradas y lecturas acotadas.
- `processes/*.json`, `.md` y `.svg`: grafo, controles/roles y mapa de cada uno de los seis procesos.
- `Seguimiento.xlsx`: copia de trabajo para anotaciones humanas; preserve la original.
- `receipt.json`: integridad de artefactos. Un recibo correcto confirma integridad técnica del paquete, no veracidad de la operación. 

## Cuando se use un extracto real del cliente

El flujo V4 anterior no importa datos reales. El adaptador privado V3 es una herramienta separada y solo acepta cuatro fuentes: órdenes, facturas, pagos e inventario. Se usa con `client-template` y `client-analyze`, cuyas salidas deben permanecer bajo `private/clients/`.

Esas cuatro fuentes no permiten reconstruir leads, conversión, citas, historia de estados, relaciones con flotillas, términos de SLA, mantenimiento, gastos completos, compras/movimientos detallados ni hitos de grúa. Esos dominios quedan fuera de cobertura o `unknown`; no se infieren de blancos, notas o coincidencias. Antes de un piloto real se necesita autorización y acuerdo de fuente, minimización, acceso, retención, diccionario, control totals y revisión del cliente. La disponibilidad del adaptador no acredita que el piloto haya ocurrido.
