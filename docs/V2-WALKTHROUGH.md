# Recorrido práctico del workbench V2

## 1. Abrir la entrega incluida

```powershell
.\Run-Studio.cmd
```

El launcher abre `artifacts/workbench-v2/DOSSIER.html` cuando ya existe. Si falta, construye esa carpeta; después ejecute el launcher otra vez o abra el dossier directamente. No se inicia servidor: todos los enlaces apuntan a archivos locales.

Para generar una entrega adicional, elija una ruta nueva:

```powershell
.\.venv\Scripts\python.exe -m milenio studio --output artifacts/workbench-review-02 --days 90
```

`studio` rechaza una carpeta existente y no intenta sobrescribir el workbench publicado.

Para comprobar el adaptador de entrada con el snapshot y la historia exportados:

```powershell
.\.venv\Scripts\python.exe -m milenio studio `
  --input artifacts/workbench-v2/dataset.json `
  --events artifacts/workbench-v2/events.json `
  --journeys artifacts/workbench-v2/journeys.json `
  --output artifacts/reanalisis
```

Para comprobar el fallback sin historia, use `--input artifacts/demo/csv` y una salida nueva. Se generan las 36 hojas, pero los marts de eventos quedan sin historia observada y la atribución permanece `unknown`. El adaptador es sintético, conserva `DEMO_NOW` y no debe usarse para datos de producción.

## 2. Confirmar la forma del paquete

En la sección **Empieza aquí**, abra:

- `Milenio_Analisis.xlsx`, para lectura y filtros;
- `warehouse.sqlite`, para reproducción SQL de solo lectura;
- `schema.sql`, para revisar restricciones y relaciones;
- `catalog.json`, para comprobar grano, columnas, referencias y conteos.

El catálogo debe mostrar 27 fuentes físicas y la base debe contener además seis marts, para 33 tablas físicas. El libro contiene una portada, una hoja por tabla, `Agentes` y `Procesos`: 36 hojas. Excel COM recalculó sus seis fórmulas con cero errores y resultados conciliados con SQL.

## 3. Seguir un caso operativo concreto

Use `WO-003` como hilo de revisión. En la tabla `work_orders` verá:

| Campo | Valor sintético | Interpretación permitida |
|---|---|---|
| `status` | `waiting_parts` | la orden está clasificada en espera al corte |
| `block_reason` | `Falta filtro` | existe una razón textual registrada |
| `technician_id` | vacío | no hay asignación registrada |
| `bay_id` | vacío | no hay bahía registrada |
| `qc_ref` | vacío | no existe evidencia de QC en el snapshot |
| `opened_at` | `2026-09-18T16:00:00Z` | inicio sintético observado |

No concluya que el filtro ya fue pedido, que llegará en una fecha o que un proveedor causó la espera. Esos hechos no están en la orden.

Ahora compare cuatro superficies:

1. `mart_service_journey`: clasificación del caso y tiempo de ciclo disponible.
2. `mart_process_waits`: horas acumuladas por etapa basadas únicamente en eventos explícitos.
3. `process_replay.json`: variante, transiciones y cobertura del historial.
4. `processes/b2c_workshop.svg` y `.md`: responsable analítico, excepción y aceptación.

El ejercicio demuestra trazabilidad; no valida que el proceso represente la práctica real del taller.

## 4. Revisar flujo y capacidad

En el dossier, compare recepciones y entregas por día. Son relojes diferentes: una orden recibida hoy puede entregarse otro día. La distribución de ciclo usa órdenes entregadas; las abiertas conservan antigüedad, no un ciclo final inventado.

En Excel:

- filtre `Servicios` por `waiting_parts`, `rework` y `sla_status`;
- revise `Diario` para los conteos por fecha;
- use `Tiempos proceso` para identificar etapas que concentran horas sintéticas;
- vuelva a `work_orders` o `lifecycle_events` para validar la evidencia subyacente.

## 5. Conciliar dinero

La hoja `INICIO` contiene tres medidas separadas: facturado, cobrado y saldo. El control debe resultar en cero:

```text
facturado - cobrado - saldo = 0
```

Después abra `Cartera` y ordene `balance_cents` de mayor a menor. Un saldo positivo es una exposición registrada, no autorización para cobrar. Una factura no emitida queda fuera de la cartera; un pago no conciliable debe bloquear el paquete.

## 6. Revisar flotillas e inventario

En `Flotillas`, separe:

- servicios elegibles con contrato y ventana temporal suficiente;
- SLA `met`, `at_risk` o `breached` solo cuando la evidencia lo permite;
- `unknown` cuando falta cobertura contractual.

En `Inventario`, use:

```text
disponible = existencia por movimientos - reservas activas
```

Una compra ordenada no incrementa existencia hasta que exista un movimiento de recepción. Un nivel bajo genera una pregunta de revisión, nunca una orden de compra.

## 7. Entender los seis procesos

Cada tarjeta del dossier enlaza tres representaciones:

- `.json`: grafo autoritativo para validación y visualización, con lanes, nodos, decisiones, evidencia, controles, métricas y agentes;
- `.svg`: mapa generado desde el JSON;
- `.md`: SOP, excepciones, RACI y pruebas de aceptación.

Revise en especial que toda decisión tenga más de una rama, que cada nodo llegue a un final y que las ramas de excepción preserven una decisión humana. Estas definiciones no son un motor BPMN ni cambian estados de negocio.

## 8. Ejecutar un agente de revisión

Primero liste perfiles:

```powershell
.\.venv\Scripts\python.exe -m milenio agents
```

Ejecute la línea base reproducible:

```powershell
.\.venv\Scripts\python.exe -m milenio agent `
  --warehouse artifacts/workbench-v2/warehouse.sqlite `
  --output artifacts/agent-runs/wo003-rules `
  --id operations_controller `
  --backend rules
```

Compruebe `run.json`, `input_packet.json`, `result.json` y `tool_trace.jsonl`. La línea base debe decir `model_invoked=false`.

Para inferencia nativa opt-in:

```powershell
.\Setup-Agents.ps1
.\.venv\Scripts\python.exe -m milenio agent `
  --warehouse artifacts/workbench-v2/warehouse.sqlite `
  --output artifacts/agent-runs/wo003-native `
  --id operations_controller `
  --backend native_codex `
  --timeout 300
```

La primera etapa selecciona de 1 a 12 lecturas exactas y métricas permitidas. La segunda recibe solo esa evidencia y devuelve diagnóstico, alternativas, pasos manuales, información faltante y borradores. Un fallo de autenticación, CLI, timeout, plan, esquema o salida deja el run `blocked`; no hay fallback silencioso.

Los nueve perfiles del paquete completaron las dos etapas con la CLI oficial `0.155.1`: 18 eventos `turn.completed`, recibos `verified_two_stage_local_cli` y cero acciones externas. Revise `plan_receipt.json`, `final_receipt.json`, el modelo observado y `model_invoked` antes de atribuir cada resultado.

La ejecución técnica no demuestra impacto real. La revisión corrigió la selección de facturas/pagos y conserva los saldos calculados por código. Distinga los casos seleccionados de las métricas globales; revise siempre el borrador antes de usarlo.

## 9. Registrar revisión humana

Antes de registrar una decisión, abra `artifacts/workbench-v2/DECISIONES.md` para la lectura ejecutiva y `review_queue.csv` para la cola tabular. Las propuestas publicadas empiezan `pending`; los campos de decisión, persona revisora y nota humana permanecen vacíos hasta que una persona actúe. No se fabrican aprobaciones para completar la muestra.

```powershell
.\.venv\Scripts\python.exe -m milenio review `
  --run artifacts/agent-runs/wo003-native `
  --reviewer "Responsable de taller" `
  --decision needs_information `
  --note "Confirmar compra, proveedor y fecha prometida del filtro."
```

La revisión agrega una anotación local. No cambia `WO-003`, no compra la pieza y no comunica nada a un cliente o proveedor.

## 10. Cerrar la reunión

Registre fuera del toolkit quién validará cada dato, qué fuente falta y cuándo se vuelve a revisar. En un piloto real, compare decisiones con resultados posteriores usando permisos, retención y controles aprobados. No reutilice los valores sintéticos como línea base comercial.
