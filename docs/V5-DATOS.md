# Diccionario de fuentes · V5

Generado con `scripts/export_web_contracts.py` desde la migración/modelos y catálogo publicados. No contiene filas ni información del cliente. Cada entidad usa clave primaria propia; las relaciones indicadas son claves foráneas. El campo vacío admitido no equivale a valor cero. La ruta Fuentes muestra filas, búsqueda, navegación y CSV para los roles autorizados.

## Clientes · Customer

Tabla: `workshop_customer`. Ruta: `/data/customers/`. Una fila corresponde a una instancia de Customer.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| name | CharField | no | máximo 200 caracteres |
| phone | CharField | no | máximo 40 caracteres |
| email | CharField | no | máximo 254 caracteres |
| kind | CharField | no | individual: Particular; fleet: Flotilla, máximo 12 caracteres |
| notes | TextField | no |  |

## Vehículos · Vehicle

Tabla: `workshop_vehicle`. Ruta: `/data/vehicles/`. Una fila corresponde a una instancia de Vehicle.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| customer | ForeignKey | no | → Customer.id; PROTECT |
| plate | CharField | no | máximo 32 caracteres |
| vin | CharField | sí | único, máximo 32 caracteres |
| make | CharField | no | máximo 100 caracteres |
| model | CharField | no | máximo 100 caracteres |
| year | PositiveSmallIntegerField | sí |  |
| odometer | PositiveIntegerField | sí |  |

## Citas · Appointment

Tabla: `workshop_appointment`. Ruta: `/data/appointments/`. Una fila corresponde a una instancia de Appointment.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| vehicle | ForeignKey | no | → Vehicle.id; PROTECT |
| scheduled_at | DateTimeField | no |  |
| reason | TextField | no |  |
| status | CharField | no | scheduled: Programada; confirmed: Confirmada; completed: Atendida; cancelled: Cancelada, máximo 12 caracteres |

## Órdenes · WorkOrder

Tabla: `workshop_workorder`. Ruta: `/data/orders/`. Una fila corresponde a una instancia de WorkOrder.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| vehicle | ForeignKey | no | → Vehicle.id; PROTECT |
| number | CharField | no | único, máximo 40 caracteres |
| status | CharField | no | intake: Recepción; inspection: Inspección; awaiting_approval: Espera autorización; approved: Autorizada; in_progress: En trabajo; waiting_parts: Espera refacciones; quality: Calidad; ready: Lista; delivered: Entregada; cancelled: Cancelada, máximo 24 caracteres |
| complaint | TextField | no |  |
| assigned_to | ForeignKey | sí | → User.id; SET_NULL |
| promised_at | DateTimeField | sí |  |
| odometer | PositiveIntegerField | sí |  |
| created_at | DateTimeField | no |  |
| updated_at | DateTimeField | no |  |
| version | PositiveIntegerField | no |  |

## Inspecciones · Inspection

Tabla: `workshop_inspection`. Ruta: `/data/inspections/`. Una fila corresponde a una instancia de Inspection.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| work_order | ForeignKey | no | → WorkOrder.id; PROTECT |
| area | CharField | no | máximo 120 caracteres |
| result | CharField | no | okay: Correcto; watch: Vigilar; urgent: Urgente, máximo 8 caracteres |
| notes | TextField | no |  |
| photo | FileField | sí | máximo 100 caracteres |
| created_by | ForeignKey | no | → User.id; PROTECT |
| created_at | DateTimeField | no |  |

## Cotizaciones · Quote

Tabla: `workshop_quote`. Ruta: `/data/quotes/`. Una fila corresponde a una instancia de Quote.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| work_order | ForeignKey | no | → WorkOrder.id; PROTECT |
| version | PositiveIntegerField | no |  |
| status | CharField | no | draft: Borrador; sent: Enviada; approved: Autorizada; rejected: Rechazada; superseded: Sustituida, máximo 12 caracteres |
| approval_name | CharField | no | máximo 150 caracteres |
| approval_reference | CharField | no | máximo 200 caracteres |
| authorized_at | DateTimeField | sí |  |
| tax_rate | DecimalField | no | 6 dígitos / 4 decimales |
| created_at | DateTimeField | no |  |

Restricciones de base: `uniq_quote_order_version`, `uniq_approved_quote_order`.

## Conceptos cotizados · QuoteLine

Tabla: `workshop_quoteline`. Ruta: `/data/quote-lines/`. Una fila corresponde a una instancia de QuoteLine.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| quote | ForeignKey | no | → Quote.id; PROTECT |
| description | CharField | no | máximo 250 caracteres |
| kind | CharField | no | labor: Mano de obra; part: Refacción; service: Servicio, máximo 10 caracteres |
| quantity | DecimalField | no | 12 dígitos / 3 decimales |
| unit_price | DecimalField | no | 14 dígitos / 2 decimales |
| unit_cost | DecimalField | sí | 14 dígitos / 2 decimales |
| part | ForeignKey | sí | → Part.id; PROTECT |

Restricciones de base: `quote_line_quantity_positive`.

## Refacciones · Part

Tabla: `workshop_part`. Ruta: `/data/parts/`. Una fila corresponde a una instancia de Part.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| sku | CharField | no | único, máximo 80 caracteres |
| name | CharField | no | máximo 200 caracteres |
| unit | CharField | no | máximo 30 caracteres |
| cost | DecimalField | no | 14 dígitos / 2 decimales |
| sale_price | DecimalField | no | 14 dígitos / 2 decimales |
| reorder_point | DecimalField | no | 12 dígitos / 3 decimales |
| stock | DecimalField | no | 12 dígitos / 3 decimales |
| reserved | DecimalField | no | 12 dígitos / 3 decimales |

Restricciones de base: `part_stock_nonnegative`, `part_reserved_nonnegative`, `part_reservation_covered`.

## Movimientos de inventario · StockMovement

Tabla: `workshop_stockmovement`. Ruta: `/data/stock/`. Una fila corresponde a una instancia de StockMovement.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| part | ForeignKey | no | → Part.id; PROTECT |
| work_order | ForeignKey | sí | → WorkOrder.id; PROTECT |
| purchase_order | ForeignKey | sí | → PurchaseOrder.id; PROTECT |
| kind | CharField | no | receipt: Entrada; consume: Consumo; return: Devolución; adjustment: Ajuste, máximo 12 caracteres |
| quantity | DecimalField | no | 12 dígitos / 3 decimales |
| unit_cost | DecimalField | no | 14 dígitos / 2 decimales |
| reference | CharField | no | máximo 200 caracteres |
| created_by | ForeignKey | no | → User.id; PROTECT |
| created_at | DateTimeField | no |  |

## Reservas de refacciones · Reservation

Tabla: `workshop_reservation`. Ruta: `/data/reservations/`. Una fila corresponde a una instancia de Reservation.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| work_order | ForeignKey | no | → WorkOrder.id; PROTECT |
| part | ForeignKey | no | → Part.id; PROTECT |
| quantity | DecimalField | no | 12 dígitos / 3 decimales |
| consumed | DecimalField | no | 12 dígitos / 3 decimales |
| returned | DecimalField | no | 12 dígitos / 3 decimales |
| created_at | DateTimeField | no |  |

Restricciones de base: `uniq_order_part_reservation`, `reservation_quantity_nonnegative`, `reservation_consumed_nonnegative`, `reservation_returned_nonnegative`, `reservation_consumed_bounded`, `reservation_returned_bounded`.

## Proveedores · Supplier

Tabla: `workshop_supplier`. Ruta: `/data/suppliers/`. Una fila corresponde a una instancia de Supplier.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| name | CharField | no | máximo 200 caracteres |
| phone | CharField | no | máximo 40 caracteres |
| email | CharField | no | máximo 254 caracteres |

## Compras · PurchaseOrder

Tabla: `workshop_purchaseorder`. Ruta: `/data/purchases/`. Una fila corresponde a una instancia de PurchaseOrder.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| supplier | ForeignKey | no | → Supplier.id; PROTECT |
| number | CharField | no | único, máximo 50 caracteres |
| status | CharField | no | draft: Borrador; ordered: Pedida; partial: Parcial; received: Recibida; cancelled: Cancelada, máximo 12 caracteres |
| created_at | DateTimeField | no |  |

## Partidas de compra · PurchaseLine

Tabla: `workshop_purchaseline`. Ruta: `/data/purchase-lines/`. Una fila corresponde a una instancia de PurchaseLine.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| purchase_order | ForeignKey | no | → PurchaseOrder.id; PROTECT |
| part | ForeignKey | no | → Part.id; PROTECT |
| quantity | DecimalField | no | 12 dígitos / 3 decimales |
| received | DecimalField | no | 12 dígitos / 3 decimales |
| unit_cost | DecimalField | no | 14 dígitos / 2 decimales |

Restricciones de base: `purchase_line_quantity_positive`, `purchase_line_received_nonnegative`, `purchase_line_received_bounded`.

## Tiempos de trabajo · TimeEntry

Tabla: `workshop_timeentry`. Ruta: `/data/time/`. Una fila corresponde a una instancia de TimeEntry.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| work_order | ForeignKey | no | → WorkOrder.id; PROTECT |
| technician | ForeignKey | no | → User.id; PROTECT |
| minutes | PositiveIntegerField | no |  |
| notes | TextField | no |  |
| created_at | DateTimeField | no |  |

## Control de calidad · QualityCheck

Tabla: `workshop_qualitycheck`. Ruta: `/data/quality/`. Una fila corresponde a una instancia de QualityCheck.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| work_order | ForeignKey | no | → WorkOrder.id; PROTECT |
| result | CharField | no | pass: Aprobada; fail: Rechazada, máximo 4 caracteres |
| notes | TextField | no |  |
| checked_by | ForeignKey | no | → User.id; PROTECT |
| created_at | DateTimeField | no |  |

## Comprobantes administrativos · Invoice

Tabla: `workshop_invoice`. Ruta: `/data/invoices/`. Una fila corresponde a una instancia de Invoice.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| work_order | OneToOneField | no | → WorkOrder.id; PROTECT, único |
| number | CharField | no | único, máximo 50 caracteres |
| subtotal | DecimalField | no | 14 dígitos / 2 decimales |
| tax | DecimalField | no | 14 dígitos / 2 decimales |
| total | DecimalField | no | 14 dígitos / 2 decimales |
| issued_at | DateTimeField | no |  |
| due_at | DateTimeField | no |  |
| voided_at | DateTimeField | sí |  |

## Pagos · Payment

Tabla: `workshop_payment`. Ruta: `/data/payments/`. Una fila corresponde a una instancia de Payment.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| invoice | ForeignKey | no | → Invoice.id; PROTECT |
| amount | DecimalField | no | 14 dígitos / 2 decimales |
| method | CharField | no | máximo 30 caracteres |
| reference | CharField | no | máximo 120 caracteres |
| idempotency_key | CharField | no | único, máximo 128 caracteres |
| received_at | DateTimeField | no |  |
| created_by | ForeignKey | no | → User.id; PROTECT |

Restricciones de base: `payment_positive`.

## Contratos de flotilla · FleetContract

Tabla: `workshop_fleetcontract`. Ruta: `/data/contracts/`. Una fila corresponde a una instancia de FleetContract.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| customer | ForeignKey | no | → Customer.id; PROTECT |
| name | CharField | no | máximo 200 caracteres |
| start_date | DateField | no |  |
| end_date | DateField | no |  |
| monthly_fee | DecimalField | no | 14 dígitos / 2 decimales |
| sla_hours | PositiveIntegerField | sí |  |
| status | CharField | no | draft: Borrador; active: Activo; expired: Vencido; cancelled: Cancelado, máximo 12 caracteres |

## Mantenimiento programado · MaintenancePlan

Tabla: `workshop_maintenanceplan`. Ruta: `/data/maintenance/`. Una fila corresponde a una instancia de MaintenancePlan.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| vehicle | ForeignKey | no | → Vehicle.id; PROTECT |
| description | CharField | no | máximo 250 caracteres |
| due_date | DateField | sí |  |
| due_odometer | PositiveIntegerField | sí |  |
| status | CharField | no | scheduled: Programado; completed: Completado; cancelled: Cancelado, máximo 12 caracteres |
| work_order | ForeignKey | sí | → WorkOrder.id; PROTECT |

## Servicios de grúa · TowService

Tabla: `workshop_towservice`. Ruta: `/data/tows/`. Una fila corresponde a una instancia de TowService.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| customer | ForeignKey | no | → Customer.id; PROTECT |
| vehicle | ForeignKey | sí | → Vehicle.id; PROTECT |
| origin | CharField | no | máximo 250 caracteres |
| destination | CharField | no | máximo 250 caracteres |
| status | CharField | no | requested: Solicitado; assigned: Asignado; en_route: En camino; arrived: En sitio; completed: Completado; cancelled: Cancelado, máximo 12 caracteres |
| operator_name | CharField | no | máximo 150 caracteres |
| safety_reference | CharField | no | máximo 200 caracteres |
| requested_at | DateTimeField | no |  |
| arrived_at | DateTimeField | sí |  |
| completed_at | DateTimeField | sí |  |
| notes | TextField | no |  |

## Ejecuciones de agentes · AgentRun

Tabla: `workshop_agentrun`. Ruta: `/data/agent-runs/`. Una fila corresponde a una instancia de AgentRun.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| agent | CharField | no | máximo 80 caracteres |
| mode | CharField | no | máximo 30 caracteres |
| status | CharField | no | máximo 20 caracteres |
| started_at | DateTimeField | no |  |
| finished_at | DateTimeField | sí |  |
| evidence | JSONField | no |  |
| output | JSONField | no |  |
| error | TextField | no |  |
| source_fingerprint | CharField | no | máximo 128 caracteres |
| model_invoked | BooleanField | no |  |

## Propuestas · Proposal

Tabla: `workshop_proposal`. Ruta: `/data/proposals/`. Una fila corresponde a una instancia de Proposal.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| run | ForeignKey | no | → AgentRun.id; PROTECT |
| kind | CharField | no | máximo 80 caracteres |
| title | CharField | no | máximo 250 caracteres |
| body | TextField | no |  |
| evidence | JSONField | no |  |
| status | CharField | no | pending: Pendiente; accepted: Aceptada; rejected: Rechazada; stale: Obsoleta, máximo 12 caracteres |
| entity_type | CharField | no | máximo 80 caracteres |
| entity_id | CharField | no | máximo 80 caracteres |
| fingerprint | CharField | no | máximo 128 caracteres |
| created_at | DateTimeField | no |  |
| reviewed_by | ForeignKey | sí | → User.id; PROTECT |
| reviewed_at | DateTimeField | sí |  |

## Acciones de seguimiento · ActionTask

Tabla: `workshop_actiontask`. Ruta: `/data/tasks/`. Una fila corresponde a una instancia de ActionTask.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| proposal | OneToOneField | sí | → Proposal.id; PROTECT, único |
| work_order | ForeignKey | sí | → WorkOrder.id; PROTECT |
| title | CharField | no | máximo 250 caracteres |
| description | TextField | no |  |
| assigned_to | ForeignKey | sí | → User.id; SET_NULL |
| due_at | DateTimeField | sí |  |
| status | CharField | no | open: Abierta; in_progress: En curso; completed: Completada; dismissed: Descartada, máximo 16 caracteres |
| outcome | TextField | no |  |
| created_at | DateTimeField | no |  |
| completed_at | DateTimeField | sí |  |

## Bitácora de cambios · AuditEvent

Tabla: `workshop_auditevent`. Ruta: `/data/audit/`. Una fila corresponde a una instancia de AuditEvent.

| Campo | Tipo | Nulo | Relación / opciones / unicidad |
| --- | --- | --- | --- |
| id | BigAutoField | no | único |
| actor | ForeignKey | no | → User.id; PROTECT |
| entity_type | CharField | no | máximo 80 caracteres |
| entity_id | CharField | no | máximo 80 caracteres |
| action | CharField | no | máximo 100 caracteres |
| before | JSONField | no |  |
| after | JSONField | no |  |
| created_at | DateTimeField | no |  |

## Captura e integridad

Clientes, vehículos y refacciones pueden cargarse por CSV con previsualización, recibo firmado y confirmación atómica. Órdenes, cotizaciones, compras, movimientos, cobros, grúas y propuestas pasan por servicios de dominio; el explorador de fuentes es de consulta. La bitácora registra actor, entidad, acción y antes/después. No es almacenamiento inmutable frente a un administrador del equipo con acceso directo a SQLite. Las cuentas/sesiones y secretos de autenticación no forman parte de este explorador.
