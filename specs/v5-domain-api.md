# V5 domain contract (implementation interface)

This is the integration contract for the Django `workshop` app. Every service takes
an authenticated `actor: User`; `DomainError` is a Django `ValidationError`.
Callers must not directly mutate financial amounts, stock, approval states, or
work-order lifecycle fields. Models expose ordinary Django managers for reads.
Money and quantities are `Decimal`; money uses two decimal places. All timestamps
are timezone-aware. The app is one workshop, not multi-tenant.

## Models and primary fields

| Model | Fields and statuses |
| --- | --- |
| `Customer` | `name`, `phone`, `email`, `kind` (`individual`,`fleet`), `notes` |
| `Vehicle` | `customer`, `plate`, `vin`, `make`, `model`, `year`, `odometer` |
| `Appointment` | `vehicle`, `scheduled_at`, `reason`, `status` (`scheduled`,`confirmed`,`completed`,`cancelled`) |
| `WorkOrder` | `vehicle`, unique `number`, `status` (`intake`,`inspection`,`awaiting_approval`,`approved`,`in_progress`,`waiting_parts`,`quality`,`ready`,`delivered`,`cancelled`), `complaint`, nullable `assigned_to`, nullable `promised_at`, `odometer`, `created_at`, `updated_at`, `version` |
| `Inspection` | `work_order`, `area`, `result` (`okay`,`watch`,`urgent`), `notes`, optional `photo`, `created_by`, `created_at` |
| `Quote` | `work_order`, `version`, `status` (`draft`,`sent`,`approved`,`rejected`,`superseded`), `approval_name`, `approval_reference`, `authorized_at`, `tax_rate`, `created_at` |
| `QuoteLine` | `quote`, `description`, `kind` (`labor`,`part`,`service`), `quantity`, `unit_price`, nullable `unit_cost`, nullable `part` |
| `Supplier` | `name`, `phone`, `email` |
| `Part` | unique `sku`, `name`, `unit`, `cost`, `sale_price`, `reorder_point`, `stock`, `reserved` |
| `StockMovement` | `part`, optional `work_order`, optional `purchase_order`, `kind` (`receipt`,`consume`,`return`,`adjustment`), signed `quantity`, `unit_cost`, `reference`, `created_by`, `created_at` |
| `Reservation` | `work_order`, `part`, `quantity`, `consumed`, `returned`, `created_at` |
| `PurchaseOrder` / `PurchaseLine` | supplier, number, status (`draft`,`ordered`,`partial`,`received`,`cancelled`); line `part`, ordered and received quantities, `unit_cost` |
| `TimeEntry` | `work_order`, `technician`, `minutes`, `notes`, `created_at` |
| `QualityCheck` | `work_order`, `result` (`pass`,`fail`), `notes`, `checked_by`, `created_at` |
| `Invoice` | unique `work_order`, unique `number`, `subtotal`, `tax`, `total`, `issued_at`, `due_at`, `voided_at` nullable |
| `Payment` | `invoice`, `amount`, `method`, `reference`, unique `idempotency_key`, `received_at`, `created_by` |
| `AuditEvent` | `actor`, `entity_type`, `entity_id`, `action`, JSON `before` and `after`, `created_at` |
| `FleetContract` | fleet `customer`, `name`, `start_date`, `end_date`, `monthly_fee`, `sla_hours`, `status` (`draft`,`active`,`expired`,`cancelled`) |
| `MaintenancePlan` | `vehicle`, `description`, `due_date`, `due_odometer`, `status` (`scheduled`,`completed`,`cancelled`), nullable `work_order` |
| `TowService` | `customer`, nullable `vehicle`, `origin`, `destination`, `status` (`requested`,`assigned`,`en_route`,`arrived`,`completed`,`cancelled`), `operator_name`, `safety_reference`, `requested_at`, `arrived_at`, `completed_at`, `notes` |
| `AgentRun` | `agent`, `mode`, `status`, `started_at`, `finished_at`, JSON `evidence`,`output`, `error`, `source_fingerprint`, `model_invoked` |
| `Proposal` | `run`, `kind`, `title`, `body`, JSON `evidence`, `status` (`pending`,`accepted`,`rejected`,`stale`), `entity_type`,`entity_id`,`fingerprint`,`created_at`,`reviewed_by`,`reviewed_at` |
| `ActionTask` | unique nullable `proposal`, nullable `work_order`, `title`,`description`, nullable `assigned_to`,`due_at`,`status` (`open`,`in_progress`,`completed`,`dismissed`),`outcome`,`created_at`,`completed_at` |

## Service signatures

All write services are atomic and append an `AuditEvent`; caller supplies `actor`.
They raise `DomainError` on invalid input. A repeated idempotency key returns
the same payment; a different payload under that key is rejected.

```python
create_work_order(*, actor, vehicle, complaint, number=None, assigned_to=None,
                  promised_at=None, odometer=None) -> WorkOrder
transition_work_order(*, actor, work_order, status, expected_version=None) -> WorkOrder
add_inspection(*, actor, work_order, area, result, notes='', photo=None) -> Inspection
create_quote(*, actor, work_order, tax_rate=Decimal('0')) -> Quote
add_quote_line(*, actor, quote, description, kind, quantity, unit_price,
               unit_cost=None, part=None) -> QuoteLine
send_quote(*, actor, quote) -> Quote
approve_quote(*, actor, quote, approval_name, approval_reference) -> Quote
reject_quote(*, actor, quote, reason='') -> Quote
reserve_part(*, actor, work_order, part, quantity) -> Reservation
consume_reservation(*, actor, reservation, quantity) -> Reservation
release_reservation(*, actor, reservation, quantity) -> Reservation
return_consumed_part(*, actor, reservation, quantity) -> Reservation
create_purchase_order(*, actor, supplier, number) -> PurchaseOrder
add_purchase_line(*, actor, purchase_order, part, quantity, unit_cost) -> PurchaseLine
place_purchase_order(*, actor, purchase_order) -> PurchaseOrder
receive_purchase_line(*, actor, line, quantity, reference='') -> PurchaseLine
adjust_stock(*, actor, part, quantity, reason) -> StockMovement
add_time_entry(*, actor, work_order, minutes, notes='') -> TimeEntry
record_quality_check(*, actor, work_order, result, notes='') -> QualityCheck
issue_invoice(*, actor, work_order, number, due_at) -> Invoice
record_payment(*, actor, invoice, amount, method, reference,
               idempotency_key, received_at=None) -> Payment
create_tow_service(*, actor, customer, origin, destination, vehicle=None,
                   notes='') -> TowService
transition_tow_service(*, actor, tow_service, status, operator_name='',
                       safety_reference='') -> TowService
```

`WorkOrder` transitions are one stage at a time except `cancelled` before
invoicing. Approval requires a named external human approval reference; work
cannot enter execution without an approved quote. Delivery requires a passing
quality check after work. Invoice uses the approved immutable quote, not live
mutable lines. Negative money, overpayment, negative available/physical stock,
unbacked consumption and duplicate receipt are rejected. This local record is
administrative, never a fiscal CFDI or bank ledger.

`receive_purchase_line` requires a nonempty external receipt/reference even
though its Python argument defaults to `''`; retrying the same line, reference
and quantity returns the original result without adding stock, whereas a changed
quantity under that reference fails. `manager` may perform every write. Other service
roles: `advisor` for reception/approval/grúa, `technician` for work/QC,
`parts` for stock/purchases, and `finance` for invoices/payments. An inactive,
anonymous or `viewer` actor is rejected. Views remain responsible for CSRF and
matching route permissions.

The `technician` role may write only its assigned work orders. `manager` and
`advisor` may cover unassigned work. Delivery and cancellation require
`reception` capability. Fleet contracts require a fleet customer, ordered dates,
nonnegative fee and positive declared SLA. Maintenance plans require a due date
or odometer; a linked work order must be for the same vehicle, and completion
requires that order to have been delivered.

Agent authors may create `AgentRun` and `Proposal` records but must keep evidence
and source fingerprints current. Accepting proposals and creating tasks is the
intelligence service's responsibility; `ActionTask.proposal` is unique for
idempotency. No model has authority to send messages, spend, dispatch or move
money.
