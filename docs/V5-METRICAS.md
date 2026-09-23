# Catálogo de métricas · V5

Generado desde `workshop.intelligence.build_metric_catalog()`. Las 18 definiciones se evalúan sobre los registros actuales, con instante de cálculo, cobertura, motivo de desconocido y muestra de evidencia limitada a 12 filas. La muestra no representa la población completa. El parámetro de corte no reconstruye una base histórica.

## OPS-WIP · Órdenes abiertas

Conteo de órdenes en estado no terminal; entregadas y canceladas se excluyen.

| Propiedad | Definición |
| --- | --- |
| Dominio | operaciones |
| Grano | corte |
| Unidad | órdenes |
| Numerador / expresión | órdenes en estados operativos |
| Población elegible | órdenes abiertas |
| Fuentes | WorkOrder |
| Responsable | gerencia |

## OPS-LATE · Órdenes vencidas

Órdenes abiertas con promised_at anterior al corte; sólo las que tienen fecha prometida son elegibles.

| Propiedad | Definición |
| --- | --- |
| Dominio | operaciones |
| Grano | orden |
| Unidad | órdenes |
| Numerador / expresión | órdenes abiertas vencidas |
| Población elegible | órdenes abiertas con fecha prometida |
| Fuentes | WorkOrder |
| Responsable | recepción |

## OPS-DELIVERY-CYCLE · Ciclo hasta entrega

Mediana entre creación de la orden y AuditEvent que registra su transición a delivered. No representa horas de mano de obra.

| Propiedad | Definición |
| --- | --- |
| Dominio | operaciones |
| Grano | orden entregada |
| Unidad | horas calendario |
| Numerador / expresión | duraciones de órdenes con evento de entrega |
| Población elegible | órdenes con evento verificable de entrega |
| Fuentes | WorkOrder, AuditEvent |
| Responsable | gerencia |

## FIN-INVOICED · Facturación administrativa

Suma de total de comprobantes administrativos no anulados. No es CFDI.

| Propiedad | Definición |
| --- | --- |
| Dominio | finanzas |
| Grano | factura administrativa |
| Unidad | MXN |
| Numerador / expresión | suma de Invoice.total |
| Población elegible | comprobantes no anulados |
| Fuentes | Invoice |
| Responsable | administración |

## FIN-PAYMENTS · Pagos registrados

Suma de Payment.amount recibidos localmente; no acredita depósito bancario.

| Propiedad | Definición |
| --- | --- |
| Dominio | finanzas |
| Grano | pago registrado |
| Unidad | MXN |
| Numerador / expresión | suma de Payment.amount |
| Población elegible | pagos registrados |
| Fuentes | Payment |
| Responsable | administración |

## FIN-OPEN-BALANCE · Saldo por cobrar

Suma por factura de max(total - pagos asociados, 0), sólo sobre comprobantes no anulados.

| Propiedad | Definición |
| --- | --- |
| Dominio | finanzas |
| Grano | factura administrativa |
| Unidad | MXN |
| Numerador / expresión | total no anulado menos pagos asociados por comprobante |
| Población elegible | comprobantes no anulados |
| Fuentes | Invoice, Payment |
| Responsable | administración |

## SALES-QUOTE-APPROVAL · Aprobación de cotizaciones

Cotizaciones aprobadas / órdenes con una cotización en estado approved o rejected; superseded y draft no entran al denominador.

| Propiedad | Definición |
| --- | --- |
| Dominio | ventas |
| Grano | orden con decisión de cotización |
| Unidad | % |
| Numerador / expresión | órdenes con cotización approved |
| Población elegible | órdenes con cotización approved o rejected |
| Fuentes | Quote |
| Responsable | recepción |

## FIN-DIRECT-MARGIN · Margen directo estimado

Estimación: subtotal facturado menos costos unitarios capturados en la cotización aprobada cuando todas las líneas tienen unit_cost. No es costo real de inventario ni incluye nómina, gastos generales o costos desconocidos.

| Propiedad | Definición |
| --- | --- |
| Dominio | finanzas |
| Grano | factura con costo conocido |
| Unidad | MXN |
| Numerador / expresión | subtotal - suma(quantity * unit_cost) |
| Población elegible | facturas con cotización aprobada y costo conocido en todas las líneas |
| Fuentes | Invoice, Quote, QuoteLine |
| Responsable | administración |

## DATA-LAST-EVENT · Antigüedad del último evento

Minutos desde el evento de auditoría más reciente observado hasta generated_at; mide actividad registrada, no frescura de sistemas externos.

| Propiedad | Definición |
| --- | --- |
| Dominio | calidad |
| Grano | AuditEvent |
| Unidad | minutos |
| Numerador / expresión | generated_at - max(AuditEvent.created_at) |
| Población elegible | eventos de auditoría |
| Fuentes | AuditEvent |
| Responsable | gerencia |

## INV-LOW-STOCK · Refacciones en o bajo punto de reposición

Conteo de SKU cuyo disponible (stock físico menos reservado) es menor o igual al punto de reposición configurado.

| Propiedad | Definición |
| --- | --- |
| Dominio | inventario |
| Grano | Part |
| Unidad | refacciones |
| Numerador / expresión | SKU con stock - reservado <= reorder_point |
| Población elegible | SKU catalogados |
| Fuentes | Part |
| Responsable | refacciones |

## INV-STOCK-VALUE-COST · Existencias valorizadas a costo de catálogo

Suma de stock físico por costo de catálogo positivo. Costos cero/no positivos quedan fuera y se informan como cobertura no valorizada; no es valuación contable.

| Propiedad | Definición |
| --- | --- |
| Dominio | inventario |
| Grano | Part con existencia y costo positivo |
| Unidad | MXN |
| Numerador / expresión | suma(stock * Part.cost con cost > 0) |
| Población elegible | SKU con existencia y costo positivo |
| Fuentes | Part |
| Responsable | refacciones |

## OPS-HOURS-LOGGED · Horas de mano de obra registradas

Suma de minutos capturados / 60. No estima utilización ni horas faltantes.

| Propiedad | Definición |
| --- | --- |
| Dominio | operaciones |
| Grano | TimeEntry |
| Unidad | horas |
| Numerador / expresión | suma(TimeEntry.minutes) |
| Población elegible | partes de tiempo |
| Fuentes | TimeEntry |
| Responsable | gerencia |

## MAINT-OVERDUE-DATE · Mantenimientos vencidos por fecha

Planes programados con due_date anterior a la fecha local de corte.

| Propiedad | Definición |
| --- | --- |
| Dominio | mantenimiento |
| Grano | MaintenancePlan |
| Unidad | planes |
| Numerador / expresión | planes programados con fecha vencida |
| Población elegible | planes programados con due_date |
| Fuentes | MaintenancePlan |
| Responsable | gerencia |

## MAINT-OVERDUE-ODOMETER · Mantenimientos vencidos por kilometraje

Planes programados con odómetro actual conocido mayor o igual al due_odometer.

| Propiedad | Definición |
| --- | --- |
| Dominio | mantenimiento |
| Grano | MaintenancePlan |
| Unidad | planes |
| Numerador / expresión | planes con odómetro actual >= due_odometer |
| Población elegible | planes con due_odometer y odómetro actual conocido |
| Fuentes | MaintenancePlan, Vehicle |
| Responsable | gerencia |

## FLEET-EXPIRING-30D · Contratos de flotilla que vencen en 30 días

Contratos activos con end_date desde la fecha local del corte hasta 30 días después, ambos inclusive.

| Propiedad | Definición |
| --- | --- |
| Dominio | flotillas |
| Grano | FleetContract |
| Unidad | contratos |
| Numerador / expresión | contratos activos en ventana de 30 días |
| Población elegible | contratos activos |
| Fuentes | FleetContract |
| Responsable | gerencia |

## TOW-OPEN · Servicios de grúa abiertos

Servicios en requested, assigned, en_route o arrived. Completed y cancelled se excluyen.

| Propiedad | Definición |
| --- | --- |
| Dominio | grúa |
| Grano | TowService |
| Unidad | servicios |
| Numerador / expresión | servicios abiertos |
| Población elegible | servicios registrados |
| Fuentes | TowService |
| Responsable | gerencia |

## TOW-MEDIAN-ARRIVAL-MIN · Mediana solicitud a llegada de grúa

Mediana de arrived_at - requested_at cuando ambas marcas existen y el intervalo no es negativo.

| Propiedad | Definición |
| --- | --- |
| Dominio | grúa |
| Grano | TowService con ambas marcas válidas |
| Unidad | minutos |
| Numerador / expresión | duraciones válidas request -> arrival |
| Población elegible | servicios con ambas marcas válidas |
| Fuentes | TowService |
| Responsable | gerencia |

## TOW-MEDIAN-COMPLETE-MIN · Mediana solicitud a cierre de grúa

Mediana de completed_at - requested_at cuando ambas marcas existen y el intervalo no es negativo.

| Propiedad | Definición |
| --- | --- |
| Dominio | grúa |
| Grano | TowService con ambas marcas válidas |
| Unidad | minutos |
| Numerador / expresión | duraciones válidas request -> completed |
| Población elegible | servicios con ambas marcas válidas |
| Fuentes | TowService |
| Responsable | gerencia |

## Interpretación

Cada indicador conserva estado `measured` o `unknown`; una población vacía no prueba cero actividad ni cobertura total. Pagos registrados no prueban depósitos bancarios. Margen directo estimado no es utilidad neta ni costo real de inventario; exige costos en todas las líneas de cada cotización elegible. No se calculan utilización sin capacidad, tendencias históricas sin snapshots ni cumplimiento de SLA no medido. El [contrato de inteligencia](../specs/v5-intelligence.md) detalla cada frontera y la relación con propuestas.
