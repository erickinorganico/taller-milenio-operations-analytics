# Analytical metric specification

All metrics use the fixed synthetic cutoff. Ratios carry numerator, denominator, rate and status; denominator zero yields `unknown`, never a measured zero.

| Metric ID | Grain / formula | Fallback and limitation |
|---|---|---|
| M-B2C-LEADS | count particular leads | snapshot state, not arrivals over period |
| M-B2C-WON | particular leads status won / particular leads | current-state ratio, not attributed conversion |
| M-B2C-QUOTE-MATCH | explicit `journey_links` / lead population in V2 synthetic studio; candidate customer+vehicle match in legacy snapshot | explicit link supports synthetic attribution; imported snapshot without links remains unknown |
| M-WIP-OPEN | work orders not delivered/cancelled | snapshot WIP |
| M-WIP-WAITING-PARTS | waiting_parts / open work orders | does not prove purchase resolves delay |
| M-BAY-OCCUPANCY | distinct busy bay IDs / bays | instantaneous occupancy, not utilization hours |
| M-SERVICE-CYCLE | `closed_at - opened_at` per delivered synthetic journey; p50/p90 over delivered | calendar cycle time, not paid labor time |
| M-PROCESS-WAIT | sum lifecycle interval hours by process stage | requires explicit validated lifecycle events; imported snapshot fallback unknown |
| M-STOCK-ON-HAND | sum receive/return/adjust − consume by part | fail if negative or valuation inconsistent |
| M-STOCK-RESERVED | active reservation quantity by part | unknown if references invalid (dataset rejects) |
| M-STOCK-AVAILABLE | on_hand − reserved | fail if negative |
| M-STOCK-REORDER | parts with available <= reorder_point / parts | review signal, not purchase instruction |
| M-FLEET-OPEN-OPPS | opportunity not won/lost | not contract or revenue |
| M-FLEET-PIPELINE | sum value_cents for open opportunities | hypothetical commercial value |
| M-FLEET-ACCOUNT-COVERAGE | accounts with any opportunity / accounts | coverage only |
| M-FLEET-ACTIVE-CONTRACTS | contract active and in effective window | approval/date required |
| M-FLEET-MAINTENANCE | due/scheduled items meeting due date or mileage rule | source odometer/date assumptions remain synthetic |
| M-FLEET-SLA-ELIGIBILITY | eligible contractual work / work linked to contract | unknown/excluded omitted from numerator |
| M-FLEET-SLA-RISK | at_risk/breached open eligible / open eligible | no real service promise |
| M-TOW-OPEN | tow not closed/cancelled | snapshot request count |
| M-TOW-HUMAN-REFS | tows with safety and approval refs / tows | presence, not authenticity or safety |
| M-TOW-CLOSE-HOURS | median closed_at − requested_at for valid closed tows | not response/arrival duration |
| M-FIN-QUOTES | sum all quote amount_cents | not invoiced/revenue |
| M-FIN-INVOICED | sum issued invoice amount_cents | managerial, non-fiscal |
| M-FIN-PAID | sum validated payment amount_cents | recorded collection, not revenue recognition |
| M-AR-RECEIVABLE | issued invoices − payments | reconcile or fail |
| M-AR-OVERDUE | positive receivable where due_at < cutoff | no automatic reminder |
| M-FIN-CASH-NET | cash payments − cash expenses | not bank balance |
| M-FIN-EXPENSES | sum expense amount_cents | observed managerial expense |
| M-WEEKLY-EXCEPTIONS | count exceptions by severity/module | zero may reflect missing coverage; inspect quality |
| M-WEEKLY-PROPOSALS | count validated pending proposals by agent | not action/completion count |
