# Oferta de servicio: diagnóstico operativo y analítica

Esta oferta describe un servicio local, acotado y revisable para convertir
exports autorizados en preguntas de decisión, hallazgos con evidencia y
seguimiento humano. El repositorio público contiene un demostrador sintético.
No demuestra que Taller Milenio haya contratado, desplegado o obtenido un
resultado.

El precio, la duración, la confidencialidad, la propiedad de los entregables y
el uso de datos se acuerdan por escrito para cada cliente. Este documento no
contiene una cotización, una promesa de ROI ni una aprobación de negocio.

## Resultado que se ofrece

El servicio deja una corrida local reproducible con una lectura ejecutiva,
tablas gerenciales curadas y un registro de decisiones y acciones. El cliente
conserva la autoridad sobre toda definición, prioridad, contacto, dinero,
seguridad y aceptación.

El flujo client-ready cubre cuatro datasets: `Ordenes`, `Facturas`, `Pagos` e
`Inventario`, con `Config` e `Instrucciones` en el libro de entrada. El alcance
no representa automáticamente flotillas, grúas, campañas, contratos, SLA,
consentimiento, seguridad vial, utilidad o capacidad completa del negocio.

La corrida puede trabajar con alias proporcionados por el cliente sin necesitar
PII. El adaptador conserva los valores que recibe y no redacciona ni anonimiza
PII. Un piloto real requiere una copia local autorizada, fuente y cutoff
declarados, minimización, tratamiento de consentimiento, acceso restringido,
retención y eliminación acordados. El piloto real todavía no se ha ejecutado.

## Paquetes de servicio

| Paquete | Resultado | Gate de aceptación | Dependencias |
|---|---|---|---|
| Preparación y lectura inicial | plantilla de entrada, contexto, calidad, `INICIO.html` y decisiones prioritarias | cliente confirma alcance, fuente, cutoff y preguntas de decisión | sponsor, dueño de fuente y extracto autorizado |
| Piloto de diagnóstico | `Gerencia.xlsx`, `Seguimiento.xlsx`, `analysis.json`, `receipt.json` y evidencia de controles | control totals y campos acordados cuadran o los issues quedan corregidos en otra corrida | snapshot estable, owners y criterio de aceptación |
| Cadencia de revisión | paquete fechado, comparación antes/después, acciones abiertas y resultados auto-reportados | owner revisa cada fila, usa un status permitido y confirma próxima revisión | export periódico, continuidad de IDs y action tracker |

El paquete de preparación no implica que el cliente haya aprobado una acción.
La aceptación del análisis tampoco autoriza contacto, pago, despacho, compra,
publicación ni cambio de datos operativos.

## Alcance de trabajo

1. **Entrada acotada.** Se reciben cuatro datasets: órdenes, facturas, pagos e
   inventario. El libro también contiene `Config` e `Instrucciones`; la
   configuración exige `as_of`, `snapshot_id` y `synthetic`.
2. **Calidad y reconciliación.** Se validan filas, referencias, estados,
   fechas, importes, pagos y cobertura del extracto. Un issue conserva hoja,
   fila, columna, código y mensaje. Consentimiento, seguridad, frescura,
   ownership y retención se revisan fuera del adaptador.
3. **Análisis para decisión.** Se preparan casos P1, P2 y P3 con evidencia,
   siguiente paso, rol sugerido, importe en riesgo cuando aplica y límites. La
   prioridad sirve para ordenar la agenda; no es autorización.
4. **Reunión accionable.** En una sesión de 20 minutos los owners revisan cada
   `action_id` y completan solamente owner, status, target_date, note y
   outcome_evidence.
5. **Seguimiento y comparación.** Una corrida posterior compara dos reportes
   con `receipt.json` de integridad verificada y snapshots compatibles. Un
   resultado solo se conserva como auto-reportado; la comparación no prueba
   atribución ni ejecución.

## Entregables y rutas

Las corridas de clientes se guardan bajo `private/clients/` por defecto y no se
publican. La demostración sintética se conserva bajo
`examples/client_delivery/`.

| Entregable | Para qué sirve | Se acepta cuando |
|---|---|---|
| `INICIO.html` | primera lectura y agenda | muestra cutoff, calidad, prioridades, limitaciones y próximos pasos |
| `Gerencia.xlsx` | revisión de tablas curadas | cada fila tiene definición, población, estado de evidencia y referencia |
| `Seguimiento.xlsx` | revisión y acciones humanas | cada fila conserva `action_id`, campos de origen, owner, status, target_date, note y outcome_evidence |
| `analysis.json` | reproducibilidad | identifica input, controles, estados y referencias |
| `receipt.json` | recibo técnico | identifica versión, hashes, cutoff y resultado de controles |
| `CALIDAD.json` | issues de entrada, si se solicitó | cada issue tiene `sheet`, `row`, `column`, `code` y `message` |
| `docs/CLIENT-ACCEPTANCE.md` | aceptación de cliente | queda firmado o marcado como pendiente por un aprobador real |

## Flujo operativo

```powershell
python -m milenio client-template --output private/clients/<cliente>/Entrada.xlsx --business "<cliente>"
python -m milenio client-analyze --input private/clients/<cliente>/Entrada.xlsx --output private/clients/<cliente>/corrida-<cutoff> --errors private/clients/<cliente>/CALIDAD-<cutoff>.json
python -m milenio client-review --input private/clients/<cliente>/corrida-<cutoff>/Seguimiento.xlsx --report private/clients/<cliente>/corrida-<cutoff> --reviewer "<nombre y rol>"
python -m milenio client-compare --before private/clients/<cliente>/corrida-anterior --after private/clients/<cliente>/corrida-<cutoff> --output private/clients/<cliente>/comparacion-<cutoff>
```

La muestra sintética se genera por separado con un corte explícito:

```powershell
python -m milenio client-template --output examples/client_delivery/client_input_sample.xlsx --sample --as-of 2026-09-22T18:00:00Z --business "Ejemplo sintético"
```

La fecha de corte de entrada puede ser la que corresponda al snapshot
autorizado. Los comandos no llaman modelos ni servicios externos y no modifican
la fuente. Los errores se emiten como issues JSON en consola; `--errors <ruta>`
los conserva además como `CALIDAD.json` en una ruta privada junto a la corrida,
fuera de la carpeta de salida nueva. El reporte de `client-review` se
agrega en la raíz de corrida indicada por `--report`; no se crea una subcarpeta
`review` por defecto.

## Ficha de alcance

| Campo | Acuerdo del cliente |
|---|---|
| Cliente y sponsor | `[nombre / responsable]` |
| Preguntas prioritarias | `[3–5 decisiones concretas]` |
| Periodo, fecha de corte y zona horaria | `[inicio, fin, cutoff, zona]` |
| Fuente y propietario | `[archivo o sistema / owner]` |
| Dataset incluido | `[órdenes / facturas / pagos / inventario]` |
| Identificadores y grain | `[IDs, unidad de análisis]` |
| Datos excluidos | `[PII, notas libres, documentos, campos sensibles]` |
| Tratamiento de PII y consentimiento fuera del adaptador | `[tratamiento acordado]` |
| Retención y eliminación | `[ubicación, plazo, responsable]` |
| Responsables de validación | `[operación, partes, flotillas, grúas, finanzas]` |
| Criterio de aceptación | `[controles, preguntas respondidas, límites]` |

## Prerrequisitos y responsabilidades

El cliente designa sponsor, dueño de fuente, owners operativos, revisor y
aprobador. Autoriza el extracto mínimo, confirma que puede compartirlo,
explica procesos y definiciones, valida control totals y hallazgos, y protege
las decisiones de seguridad, dinero y contacto.

El proveedor prepara el mapa, valida el paquete, separa medido de desconocido,
conserva el recibo, expone limitaciones y deja el registro editable para el
cliente. El proveedor no inventa consentimiento, autorización, seguridad,
disponibilidad, pago, efectivo, impacto o resultado.

## Aceptación y cadencia

La primera lectura dura aproximadamente 30 minutos:

1. confirmar alcance, privacidad y cutoff;
2. revisar los controles que pueden bloquear una decisión;
3. seleccionar las decisiones prioritarias en `Gerencia.xlsx`;
4. completar owner, status, target_date, note y outcome_evidence en
   `Seguimiento.xlsx`.

La reunión semanal dura aproximadamente 20 minutos:

1. confirmar cutoff, frescura y calidad;
2. revisar P1 y confirmar evidencia con el owner de la fuente;
3. revisar P2 y P3 según impacto y faltantes;
4. cerrar cada item con un status permitido, owner, target_date y nota;
5. confirmar el próximo export y dejar abiertas las preguntas sin evidencia.

La aceptación de la entrega se registra en `docs/CLIENT-ACCEPTANCE.md`. Nombre,
rol, fecha, estado y firma permanecen en blanco hasta la decisión humana. Los
estados de fila de `Seguimiento.xlsx` son solamente `pending`, `accepted`,
`in_progress`, `done` y `dismissed`; el acta tiene estados de aceptación
separados y no ejecuta acciones.

## Límites y exclusiones

El servicio no opera CRM/ERP, no envía mensajes, no contacta prospectos, no
diagnostica vehículos, no fija precios, no despacha grúas, no autoriza
reparaciones, no emite documentos fiscales, no procesa pagos, no mueve dinero
y no publica campañas. Las propuestas, aunque una persona las marque como
revisadas, no ejecutan acciones externas.

Los agentes V2 son una opción para análisis especializado del demostrador
sintético. La entrega client-ready simple funciona sin modelos y sin agentes.

## Lo que no se afirma

El demostrador no prueba demanda, conversión, calidad de servicio, seguridad,
adopción, ahorro, ROI, ingresos, SLA real ni mejora causal. Una corrida verde
demuestra que los controles locales funcionaron con ese input; no certifica el
proceso real ni la aptitud para producción.
