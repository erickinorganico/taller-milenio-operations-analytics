# Analytics V6: cortes de la operación del taller

El tablero `/analytics/` lee hechos guardados del taller local. Un corte (`AnalyticsSnapshot`) registra su hora real, huella SHA-256 de las filas transformadas, último identificador de auditoría observado, conteos de fuentes y frescura. Cada `AnalyticsRow` guarda una fila de una tabla analítica y referencias `{model, id}` hacia los registros fuente. El tablero, las tablas y las descargas JSON/CSV de un corte seleccionado leen esas filas guardadas. Cambios posteriores de una orden o un pago no reescriben el corte anterior.

## Primer corte y alcance histórico

Al migrar desde V5 se conservan los registros operativos. V6 no crea cortes con fechas pretéritas ficticias. El primer corte nace cuando se procesa una actualización, manual o programada, y puede incluir eventos anteriores que sí estaban fechados en la base. Los saldos, estados y existencias representan lo observado **a la hora real del corte**; elegir fechas anteriores no reconstruye un estado que V5 nunca guardó. El tablero muestra el identificador y la hora del corte y avisa cuando el más reciente envejece.

El filtro predeterminado cubre 30 días locales inclusive, hasta el día del corte. El periodo anterior tiene la misma duración y termina el día previo. Se admiten fechas `AAAA-MM-DD`, hasta 366 días ordenados, sin fechas posteriores al corte. Se puede segmentar por todos, particular o flotilla. Una variación porcentual queda desconocida si el periodo anterior vale cero; cero registros no constituye una tasa medida. La fecha se interpreta en la zona local configurada para la instalación.

## Seis tablas analíticas

| Tabla | Grano y fuente | Uso |
| --- | --- | --- |
| `daily_operations` | Día local y tipo de cliente, desde WorkOrder y transiciones AuditEvent | Órdenes recibidas y entregadas verificables |
| `service_lines` | Línea de la última cotización aprobada por orden, desde Quote/QuoteLine | Demanda autorizada y su asociación con facturas no anuladas |
| `part_usage` | Movimiento `consume` o `return` de StockMovement | Consumo neto real por refacción; compras, ajustes y reservas quedan fuera |
| `receivables` | Comprobante o pago, desde Invoice/Payment | Facturación por emisión, cobro por recepción y saldo al corte |
| `order_journeys` | Orden, con transiciones AuditEvent | Estado actual, entrega comprobable, ciclo y esperas cerradas |
| `inventory` | Refacción Part al corte | Existencias, reservas y costo/precio catalogados |

Las tablas `/analytics/data/<tabla>/` muestran filas, campos y enlaces a fuentes según el rol. Su CSV incluye identificador, hora y huella del corte. El JSON del tablero incluye filtros, indicadores, tendencia, rankings y cobertura. El acceso a datos tabulares y exportaciones requiere el permiso de lectura de datos; la vista gerencial requiere lectura de inteligencia.

## Interpretación de indicadores y rankings

Las órdenes recibidas usan `WorkOrder.created_at`; las entregas usan una transición de auditoría a `delivered`. Un estado `delivered` sin ese evento cuenta como cobertura faltante, no como una entrega fechada inventada. El tiempo mediano hasta entrega requiere creación y transición comprobable. La espera de refacciones usa intervalos cerrados entre entradas y salidas auditadas de `waiting_parts`; un intervalo todavía abierto se muestra como cobertura, pero no entra a la mediana cerrada.

“Facturado” suma comprobantes no anulados según `issued_at`. “Cobrado” suma pagos según `received_at`, aunque la factura se haya emitido en otro periodo. El saldo por cobrar considera facturas no anuladas y pagos registrados hasta el corte. Las órdenes abiertas, promesas vencidas y ese saldo son estados **al corte**, independientes del rango de fechas seleccionado.

Las refacciones se ordenan por cantidad de órdenes con consumo neto positivo. Cada movimiento `consume` aporta cantidad usada y cada `return` la resta; las cantidades conservan su unidad (`pieza`, `litro`, etc.) y no se comparan como si fueran equivalentes. El costo neto proviene del costo registrado en cada movimiento, sin equipararlo con costo contable total.

Los servicios se ordenan por número de órdenes distintas con una línea autorizada en el periodo. Se agrupan por tipo y descripción exacta después de normalizar espacios y mayúsculas; no se adivinan sinónimos. Cantidad, órdenes y valor autorizado son medidas distintas. El valor “vinculado a facturas” suma **el valor de la línea cotizada** cuando existe una factura no anulada, con la fecha de emisión de esa factura. Invoice no guarda distribución por línea: ese valor no es ingreso facturado por servicio ni prueba ejecución. No sume los valores de líneas como si fueran asignaciones contables de factura.

La cobertura muestra faltantes de fecha de promesa, auditoría de entrega, autorización y costo unitario, además de comprobantes anulados excluidos. Costos de mano de obra reales, gastos generales y otros costos completos no están disponibles aquí; el tablero no calcula margen realizado. El [catálogo operativo V5](V5-METRICAS.md) conserva sus definiciones propias y no debe confundirse con estos cortes V6.

## Uso de la demo

Una instalación demo nueva añade automáticamente el escenario V5 y aproximadamente 60 días de registros ficticios V6, con identificadores `V6DEMO`. El actor temporal de siembra queda inactivo y sin contraseña utilizable; `/setup/` sigue creando el acceso personal de gerencia. En una demo anterior que ya contiene registros, el lanzador no vuelve a sembrar; un operador con superusuario demo activo puede agregar el escenario ejecutando `python manage.py seed_analytics_demo --demo` con `MILENIO_MODE=demo` y `MILENIO_DATA_DIR` apuntando a la carpeta `demo`. El comando rechaza live, conserva registros previos y no duplica una semilla completa. Sus fechas y montos son ficticios, no evidencia del negocio real.
