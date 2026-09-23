# Tablas y fuentes del estudio

`milenio.source_catalog.build_source_catalog(database, metric_registry)` lee la
base SQLite terminada y entrega un diccionario JSON con las 27 tablas fuente y
los seis marts. Cada entrada contiene **todas** las filas, en orden estable;
campo, tipo SQLite, nulabilidad y conteo de nulos; clave primaria realmente
declarada, clave lógica del grain, claves foráneas reales, métricas vinculadas,
rol propuesto y ruta del CSV `tables/<nombre>.csv`. La función abre rutas en
modo SQLite de solo lectura y sólo consulta nombres de una lista fija.

| Dominio | Tablas físicas fuente | Grain principal |
| --- | --- | --- |
| Particular y taller | `customers`, `vehicles`, `leads`, `quotes`, `appointments`, `technicians`, `bays`, `work_orders` | Una fila por ID de cada entidad |
| Partes | `suppliers`, `parts`, `purchases`, `stock_moves`, `reservations` | Una compra, movimiento o reserva por ID; cantidades no se sustituyen entre sí |
| Flotillas | `fleet_accounts`, `contacts`, `opportunities`, `contracts`, `maintenance` | Una cuenta, contacto, oportunidad, contrato o mantenimiento por ID |
| Grúas | `tow_units`, `tows` | Una unidad o solicitud por ID |
| Administración y growth | `invoices`, `payments`, `expenses`, `campaigns`, `proposals` | Una factura, pago, gasto, campaña o propuesta por ID |
| Evidencia temporal | `lifecycle_events`, `journey_links` | Un evento por `event_id`; un vínculo explícito por `id` |

Los campos `*_cents` son centavos MXN. `status` es estado al corte y no reconstruye
transiciones. En particular, una compra ordenada no aumenta existencia; una
referencia de seguridad de grúa no valida seguridad ni despacho; una propuesta
no equivale a acción ejecutada. Los textos de contacto, placa, ubicación y
condiciones son ficticios en esta entrega y requerirían tratamiento de datos
sensible para un piloto real.

| Mart | Clave lógica y grain | Lectura válida |
| --- | --- | --- |
| `mart_service_journey` | `work_order_id`; una orden | Ciclo entregado sólo con historial validado; edad abierta aparte |
| `mart_receivables` | `invoice_id`; una factura emitida | Saldo = factura menos pagos vinculados |
| `mart_daily_operations` | `day`; un día UTC | Aperturas, entregas, cobros y gastos registrados en fechas distintas |
| `mart_fleet_scorecard` | `fleet_account_id`; una cuenta | Pipeline, servicio y SLA siguen siendo conceptos separados |
| `mart_inventory` | `part_id`; una parte | Disponible = existencia por movimientos menos reservas activas |
| `mart_process_waits` | `entity_type` + `stage`; una pareja entidad/estado | Suma de intervalos cerrados por eventos consecutivos |

Los marts materializados no tienen clave primaria física ni claves foráneas
declaradas. El catálogo conserva `primary_key: []` y `relationships: []` en
ellos; `logical_key` describe su grain calculado sin atribuirle una restricción
SQLite inexistente. Las tablas físicas muestran sus claves y relaciones
declaradas mediante `PRAGMA table_info` y `PRAGMA foreign_key_list`.

`owner_role` es una hipótesis funcional y `owner_status` siempre indica
`proposed_unvalidated`. `source_status` distingue filas fuente de ejemplo
sintético y marts derivados de esos ejemplos. No hay sistema fuente real,
propietario de datos confirmado, cobertura del universo, uso operativo ni
impacto observado de Taller Milenio.
