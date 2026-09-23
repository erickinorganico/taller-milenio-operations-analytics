# Entrega Milenio V6

La aplicación actual se abre desde [CLIENTE.html](CLIENTE.html). Prepare el entorno con `Setup-Web.ps1` y ejecute `Iniciar-Demo.cmd` para practicar o `Iniciar-Milenio.cmd` para una instancia vacía. El dashboard principal muestra demanda de servicios, consumo de refacciones, facturación, cobros, atrasos y tiempos observables. Los filtros y los cortes permiten comparar periodos y revisar sus fuentes.

La operación diaria alimenta seis tablas analíticas persistentes. Un trabajador local actualiza cortes y ejecuta tres revisores por intervalo o cambios de negocio; sus propuestas pasan a revisión humana y tareas con responsable. La pantalla de automatizaciones muestra programación, pausa, latido, intentos y errores. El servidor debe permanecer abierto para procesar la cola.

La entrega incluye código, migraciones, dependencias offline para Windows x64/Python 3.12, [manual de instalación](README-WEB.md), [definiciones analíticas](docs/V6-ANALYTICS.md), [operación de automatizaciones](docs/V6-AUTOMATIZACIONES.md) y [verificación V6](docs/V6-VERIFICACION.md). La demo tiene datos ficticios y aproximadamente 60 días de actividad. La instalación real comienza vacía y requiere crear accesos y registrar o importar datos autorizados.

El cierre técnico incluye pruebas, arranque del paquete extraído, migración desde V5, respaldo/restauración y una ejecución real de los tres revisores con Codex. La validación con el personal y los datos del taller sigue siendo un piloto de implantación; no se afirma aceptación comercial ni impacto financiero observado.

---

## Archivo de la entrega V3

La entrada principal es [CLIENTE.html](CLIENTE.html). Añade la plantilla mínima
de datos, informe de prioridades, libro gerencial de siete hojas, seguimiento
editable y comparación semanal. Las salidas de cliente se guardan en private/.
Consulte el [playbook](docs/CLIENT-PLAYBOOK.md), el
[contrato V3](specs/client-delivery.md) y la
[aceptación pendiente de personas](docs/CLIENT-ACCEPTANCE.md).

Los recorridos V3 se verificaron con datos ficticios. No se ha realizado un piloto
real ni se ha obtenido aceptación de un cliente. El estudio V2 que sigue se
conserva como profundidad técnica, con sus propios recibos y fecha de corte.

## Inventario técnico V2 conservado

## Propósito

Esta entrega convierte un escenario sintético de operación automotriz en un paquete local que una persona puede inspeccionar, cuestionar y conciliar. No es una demostración de resultados reales ni un sistema transaccional. Es un workbench de análisis y decisión asistida con evidencia.

## Punto de entrada

Abra primero la entrega incluida:

```powershell
.\Run-Studio.cmd
```

El launcher abre [artifacts/workbench-v2/DOSSIER.html](artifacts/workbench-v2/DOSSIER.html) si ya existe; solo genera esa carpeta cuando falta. Después de una primera generación, ejecútelo otra vez o abra el dossier directamente. Para una corrida nueva use `python -m milenio studio --output <carpeta-nueva> --days 90`. El dossier enlaza libro, SQL, procesos, resultados de agentes base, catálogo y especificaciones sin requerir servidor.

## Inventario contractual

| Entregable | Contenido | Revisión sugerida |
|---|---|---|
| `DOSSIER.html` | siete secciones conectadas a evidencia local | navegar enlaces y comprobar que no haya controles operativos |
| `Milenio_Analisis.xlsx` | 36 hojas; seis fórmulas recalculadas por Excel COM, cero errores y valores conciliados con SQL | abrir `INICIO`, comprobar control financiero y filtrar `Servicios` |
| `warehouse.sqlite` | 33 tablas físicas | contar 27 tablas fuente y seis marts; ejecutar solo consultas de lectura |
| `schema.sql` y `catalog.json` | DDL, campos, grano, referencias, conteos | contrastar catálogo con SQLite |
| `tables/*.csv` | export de las 33 tablas con escape de fórmulas | abrir muestras y conservar tipos/importes en centavos |
| `analysis.json` | resumen y seis marts serializados | conciliar con Excel y SQL |
| `dataset.json`, `events.json`, `journeys.json` | snapshot y fuentes longitudinales sintéticas reutilizables | conservar separado el dato actual, los eventos y los enlaces explícitos |
| `process_replay.json` | variantes, transiciones, duraciones y cobertura | distinguir historia observada sintética de cobertura desconocida |
| `processes/` | 6 JSON + 6 SVG + 6 SOP Markdown | comparar mapa, definición y aceptación |
| `specs/` | 5 especificaciones y 18 requisitos | seguir cada requisito a proceso, agente, métrica y prueba |
| `agent_runs/` | nueve resultados `rules`, paquetes y trazas | confirmar `model_invoked=false` para la línea base |
| `DECISIONES.md` y `review_queue.csv` | lectura humana y cola tabular de propuestas | confirmar `pending` y campos humanos vacíos; no inferir aprobación |
| `charts/` | flujo, ciclo, cartera y estados en formatos imprimibles | revisar unidades y etiqueta sintética |
| `receipt.json` | hashes del paquete y fuentes | verificar antes de distribuir |

## Modelo físico

Las 33 tablas se dividen en:

- 25 entidades contractuales: clientes, vehículos, leads, cotizaciones, citas, taller, inventario, flotillas, grúas, finanzas, campañas y propuestas;
- dos fuentes longitudinales: `lifecycle_events` y `journey_links`;
- seis marts: servicio, cartera, operación diaria, scorecard de flotilla, inventario y esperas de proceso.

El escenario cubre 90 días, contiene 170 órdenes y conserva 160 enlaces explícitos entre lead, cotización, cita y orden histórica. Los 160 casos históricos son ficticios y reproducibles. La coincidencia por cliente o vehículo sin un `journey_link` explícito no se presenta como atribución.

El corte exacto del escenario es `2026-09-21T18:00:00Z`. Las llamadas nativas registradas el 2026-09-22 analizaron ese snapshot congelado; sus timestamps de ejecución no son fechas de negocio ni extienden el periodo analizado.

## Procesos y responsabilidades

| Proceso | Pregunta que responde | Decisión humana preservada |
|---|---|---|
| Particulares y taller | ¿Dónde está el caso y qué evidencia falta? | contacto, autorización, prioridad y entrega |
| Partes y abastecimiento | ¿Qué está disponible, reservado o en espera? | compra, proveedor, sustitución y secuencia |
| Flotillas | ¿Qué oportunidad, contrato, mantenimiento o SLA merece revisión? | contacto, compromiso, precio y agenda |
| Grúas | ¿Qué gate humano o evidencia falta? | seguridad, asignación y despacho |
| Cobranza | ¿Qué factura, pago o saldo requiere conciliación? | recordatorio, ajuste, cobro y documento fiscal |
| Revisión semanal | ¿Qué excepciones y preguntas llegan a la reunión? | responsable, prioridad y acción externa |

Cada proceso tiene una definición JSON validable/renderizable, mapa SVG, SOP, excepciones, RACI y tres pruebas de aceptación. El JSON describe una hipótesis analítica; no ejecuta un proceso de negocio ni funciona como motor BPMN.

## Agentes

Los nueve perfiles cubren recepción, control de taller, mantenimiento, investigación de flotillas, SLA, grúas, cobranza, marketing y revisión semanal. Sus herramientas son de lectura acotada: inspección de casos, evidencia exacta y métricas SQL predefinidas.

- `rules` genera una línea base reproducible y declara que no hubo inferencia.
- `native_codex` usa una etapa de plan/selección y otra de salida final. Rechaza tablas, campos, IDs, versiones o métricas fuera de alcance.
- Ambos producen material para revisión. Ninguno envía, publica, agenda, despacha, compra o modifica la fuente.

La capacidad nativa usa la CLI oficial fijada en `0.155.1`, instalada de forma opt-in con `Setup-Agents.ps1` y autenticada con la suscripción existente. Los nueve perfiles completaron dos llamadas cada uno: 18 eventos `turn.completed`, recibos `verified_two_stage_local_cli`, `model_invoked=true` y cero acciones externas. Esto prueba ejecución técnica, no efectividad. La revisión corrigió relaciones de facturas/pagos, alcance de flotillas y denominadores de muestra; los resultados mantienen evidencia y revisión humana pendiente.

## Criterios de aceptación

La entrega está lista para revisión cuando:

1. `studio` termina con estado `pass` en una ruta nueva.
2. SQLite contiene 33 tablas físicas y el libro reporta 36 hojas.
3. Facturado = cobrado + saldo en SQL, Python y Excel.
4. Los seis mapas provienen de las seis definiciones JSON.
5. Los 18 requisitos resuelven a procesos, entidades, agentes, métricas y pruebas existentes.
6. Las 160 historias tienen enlaces explícitos y el replay no fabrica historia para registros sin eventos.
7. Los resultados `rules` declaran `model_invoked=false`.
8. Los nueve resultados nativos conservan recibos válidos de las dos etapas; su calidad se revisa por separado.
9. `receipt.json` contiene hashes de todos los archivos publicados.
10. Toda pantalla y reporte conserva la etiqueta sintética y el límite de no ejecución externa.
11. `DECISIONES.md` y `review_queue.csv` mantienen propuestas `pending` y no rellenan actor, decisión o nota humana inexistentes.

La suite integrada actual pasa sin fallas ni errores. El conteo exacto se registra en el recibo de verificación del mismo estado fuente, no en esta narrativa.

## Reanálisis controlado

```powershell
.\.venv\Scripts\python.exe -m milenio studio `
  --input artifacts/workbench-v2/dataset.json `
  --events artifacts/workbench-v2/events.json `
  --journeys artifacts/workbench-v2/journeys.json `
  --output artifacts/reanalisis
```

`--input` también puede señalar una carpeta completa de 25 CSV sintéticos, como `artifacts/demo/csv`. Si se omiten eventos o journeys, la entrega conserva historia/atribución `unknown` y no reconstruye rutas. El adaptador mantiene el corte `DEMO_NOW` y no habilita datos de producción.

## Uso en una reunión semanal

1. Verificar recibo y controles de calidad.
2. Revisar WIP y esperas; usar `WO-003` como ejercicio de rastreo.
3. Conciliar cartera antes de discutir cobro.
4. Separar SLA elegible, desconocido y en riesgo.
5. Revisar inventario disponible después de reservas.
6. Leer propuestas y alternativas, asignar responsables humanos fuera del sistema y registrar solo la anotación de revisión.

Las decisiones y sus resultados reales deben medirse en un piloto gobernado posterior. Esta entrega no los presupone.
