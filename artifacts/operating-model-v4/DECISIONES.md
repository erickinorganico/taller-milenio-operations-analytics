# Milenio / Cuaderno de revisión

Escenario sintético. Propuestas pendientes: ninguna equivale a autorización ni se ha ejecutado.

Abra `review_queue.csv` para priorizar y asignar revisores. Conserve el original sellado y trabaje en una copia para registrar decisiones humanas.

## intake_admin

Línea base offline por reglas: leads:L-001 tiene status='new' en la versión 1; revíselo con la cola acotada (open_leads=4, pending_appointments=1, M-B2C-LEADS=112, M-B2C-WON=0.964286, M-B2C-QUOTE-MATCH=0.964286).

Modo: `rules`. Inferencia observada: `False`.

### Borrador 1 / followup

Borrador interno de revisión para leads:L-001: confirme el registro citado antes de cualquier acción.

Siguientes pasos para revisión:

- Una persona revisora confirma el valor citado y su contexto.
- Una persona revisora registra cualquier decisión; este workbench no ejecuta acciones externas.

[Resultado y referencias](agent_runs/intake_admin/result.json) · [Traza](agent_runs/intake_admin/tool_trace.jsonl)

## operations_controller

Línea base offline por reglas: work_orders:WO-003 tiene status='waiting_parts' en la versión 1; revíselo con la cola acotada (open_work_orders=7, waiting_parts=1, busy_bays=4, M-WIP-OPEN=7, M-WIP-WAITING-PARTS=0.142857, M-BAY-OCCUPANCY=1.0, M-SERVICE-CYCLE=12.0, M-PROCESS-WAIT=2715.002, M-STOCK-ON-HAND=53, M-STOCK-RESERVED=1, M-STOCK-AVAILABLE=52, M-STOCK-REORDER=0.666667).

Modo: `rules`. Inferencia observada: `False`.

### Borrador 1 / followup

Borrador interno de revisión para work_orders:WO-003: confirme el registro citado antes de cualquier acción.

Siguientes pasos para revisión:

- Una persona revisora confirma el valor citado y su contexto.
- Una persona revisora registra cualquier decisión; este workbench no ejecuta acciones externas.

[Resultado y referencias](agent_runs/operations_controller/result.json) · [Traza](agent_runs/operations_controller/tool_trace.jsonl)

## maintenance_planner

Línea base offline por reglas: maintenance:M-001 tiene status='scheduled' en la versión 1; revíselo con la cola acotada (maintenance_due=3, open_work_orders=7, M-FLEET-MAINTENANCE=0, M-FLEET-ACTIVE-CONTRACTS=1, M-SERVICE-CYCLE=12.0).

Modo: `rules`. Inferencia observada: `False`.

### Borrador 1 / followup

Borrador interno de revisión para maintenance:M-001: confirme el registro citado antes de cualquier acción.

Siguientes pasos para revisión:

- Una persona revisora confirma el valor citado y su contexto.
- Una persona revisora registra cualquier decisión; este workbench no ejecuta acciones externas.

[Resultado y referencias](agent_runs/maintenance_planner/result.json) · [Traza](agent_runs/maintenance_planner/tool_trace.jsonl)

## fleet_sales_research

Línea base offline por reglas: opportunities:OP-001 tiene status='proposal' en la versión 1; revíselo con la cola acotada (open_opportunities=2, active_contracts=1, M-FLEET-OPEN-OPPS=2, M-FLEET-PIPELINE=2030000, M-FLEET-ACCOUNT-COVERAGE=1.0, M-FLEET-ACTIVE-CONTRACTS=1).

Modo: `rules`. Inferencia observada: `False`.

### Borrador 1 / followup

Borrador interno de revisión para opportunities:OP-001: confirme el registro citado antes de cualquier acción.

Siguientes pasos para revisión:

- Una persona revisora confirma el valor citado y su contexto.
- Una persona revisora registra cualquier decisión; este workbench no ejecuta acciones externas.

[Resultado y referencias](agent_runs/fleet_sales_research/result.json) · [Traza](agent_runs/fleet_sales_research/tool_trace.jsonl)

## fleet_sla_watcher

Línea base offline por reglas: contracts:CT-001 tiene status='active' en la versión 1; revíselo con la cola acotada (active_contracts=1, open_work_orders=7, M-FLEET-SLA-ELIGIBILITY=0.509434, M-FLEET-SLA-RISK=unknown, M-FLEET-MAINTENANCE=0, M-FLEET-ACTIVE-CONTRACTS=1, M-SERVICE-CYCLE=12.0, M-AR-RECEIVABLE=3901250).

Modo: `rules`. Inferencia observada: `False`.

### Borrador 1 / followup

Borrador interno de revisión para contracts:CT-001: confirme el registro citado antes de cualquier acción.

Siguientes pasos para revisión:

- Una persona revisora confirma el valor citado y su contexto.
- Una persona revisora registra cualquier decisión; este workbench no ejecuta acciones externas.

[Resultado y referencias](agent_runs/fleet_sla_watcher/result.json) · [Traza](agent_runs/fleet_sla_watcher/tool_trace.jsonl)

## tow_dispatch_assistant

Línea base offline por reglas: tows:TW-002 tiene status='en_route' en la versión 1; revíselo con la cola acotada (active_tows=2, M-TOW-OPEN=2, M-TOW-HUMAN-REFS=0.6, M-TOW-CLOSE-HOURS=4.0).

Modo: `rules`. Inferencia observada: `False`.

### Borrador 1 / followup

Borrador interno de revisión para tows:TW-002: confirme el registro citado antes de cualquier acción.

Siguientes pasos para revisión:

- Una persona revisora confirma el valor citado y su contexto.
- Una persona revisora registra cualquier decisión; este workbench no ejecuta acciones externas.

[Resultado y referencias](agent_runs/tow_dispatch_assistant/result.json) · [Traza](agent_runs/tow_dispatch_assistant/tool_trace.jsonl)

## collections_assistant

Línea base offline por reglas: invoices:INV-H160 tiene status='issued' en la versión 1; revíselo con la cola acotada (issued_invoices=164, unpaid_invoices=56, invoice_payment_summary=[{'invoice_id': 'INV-H159', 'amount_cents': 127500, 'paid_cents': 63750, 'balance_cents': 63750, 'payment_count': 1}, {'invoice_id': 'INV-H156', 'amount_cents': 90000, 'paid_cents': 45000, 'balance_cents': 45000, 'payment_count': 1}, {'invoice_id': 'INV-H160', 'amount_cents': 140000, 'paid_cents': 140000, 'balance_cents': 0, 'payment_count': 1}, {'invoice_id': 'INV-H158', 'amount_cents': 115000, 'paid_cents': 115000, 'balance_cents': 0, 'payment_count': 1}, {'invoice_id': 'INV-H157', 'amount_cents': 102500, 'paid_cents': 102500, 'balance_cents': 0, 'payment_count': 1}, {'invoice_id': 'INV-H155', 'amount_cents': 77500, 'paid_cents': 77500, 'balance_cents': 0, 'payment_count': 1}], M-FIN-QUOTES=21593000, M-FIN-INVOICED=20982500, M-FIN-PAID=17081250, M-AR-RECEIVABLE=3901250, M-AR-OVERDUE=3227500, M-FIN-CASH-NET=6652000, M-FIN-EXPENSES=117000).

Modo: `rules`. Inferencia observada: `False`.

### Borrador 1 / followup

Borrador interno de revisión para invoices:INV-H160: confirme el registro citado antes de cualquier acción.

Siguientes pasos para revisión:

- Una persona revisora confirma el valor citado y su contexto.
- Una persona revisora registra cualquier decisión; este workbench no ejecuta acciones externas.

[Resultado y referencias](agent_runs/collections_assistant/result.json) · [Traza](agent_runs/collections_assistant/tool_trace.jsonl)

## marketing_planner

Línea base offline por reglas: campaigns:CAM-001 tiene status='review' en la versión 1; revíselo con la cola acotada (review_campaigns=1, M-B2C-LEADS=112, M-B2C-QUOTE-MATCH=0.964286, M-WEEKLY-EXCEPTIONS=unknown, M-WEEKLY-PROPOSALS=2).

Modo: `rules`. Inferencia observada: `False`.

### Borrador 1 / followup

Borrador interno de revisión para campaigns:CAM-001: confirme el registro citado antes de cualquier acción.

Siguientes pasos para revisión:

- Una persona revisora confirma el valor citado y su contexto.
- Una persona revisora registra cualquier decisión; este workbench no ejecuta acciones externas.

[Resultado y referencias](agent_runs/marketing_planner/result.json) · [Traza](agent_runs/marketing_planner/tool_trace.jsonl)

## weekly_operator

Línea base offline por reglas: work_orders:WO-003 tiene status='waiting_parts' en la versión 1; revíselo con la cola acotada (open_work_orders=7, active_tows=2, unpaid_invoices=56, M-AR-OVERDUE=3227500, M-FLEET-SLA-RISK=unknown, M-TOW-OPEN=2, M-WEEKLY-EXCEPTIONS=unknown, M-WEEKLY-PROPOSALS=2, M-WIP-OPEN=7, M-B2C-LEADS=112, M-B2C-WON=0.964286, M-B2C-QUOTE-MATCH=0.964286, +22 métricas disponibles en el paquete).

Modo: `rules`. Inferencia observada: `False`.

### Borrador 1 / followup

Borrador interno de revisión para work_orders:WO-003: confirme el registro citado antes de cualquier acción.

Siguientes pasos para revisión:

- Una persona revisora confirma el valor citado y su contexto.
- Una persona revisora registra cualquier decisión; este workbench no ejecuta acciones externas.

[Resultado y referencias](agent_runs/weekly_operator/result.json) · [Traza](agent_runs/weekly_operator/tool_trace.jsonl)
