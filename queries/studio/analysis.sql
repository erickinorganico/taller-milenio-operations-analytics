-- Consultas de lectura para warehouse.sqlite de la entrega v2.
-- Todos los importes *_cents son enteros en centavos MXN.

-- 1. Conciliacion financiera: diferencia debe ser cero.
SELECT SUM(invoiced_cents) AS facturado,
       SUM(paid_cents) AS cobrado,
       SUM(balance_cents) AS saldo,
       SUM(invoiced_cents-paid_cents-balance_cents) AS diferencia
FROM mart_receivables;

-- 2. Casos que requieren revisar bloqueo, retrabajo o SLA.
SELECT work_order_id,status,cycle_hours,waiting_parts_hours,sla_status
FROM mart_service_journey
WHERE status IN ('waiting_parts','rework') OR sla_status IN ('breached','at_risk')
ORDER BY cycle_hours DESC;

-- 3. Cartera pendiente: no confundir pagos parciales con factura liquidada.
SELECT customer_id,COUNT(*) AS facturas_con_saldo,SUM(balance_cents) AS saldo
FROM mart_receivables WHERE balance_cents>0
GROUP BY customer_id ORDER BY saldo DESC;

-- 4. Cobertura del historial y retrabajo: no rellenar ausencias con cero.
SELECT COUNT(*) AS entregadas,SUM(history_available) AS con_historia,
       SUM(rework_observed) AS retrabajo_observado
FROM mart_service_journey WHERE status='delivered';

-- 5. SLA de flotillas: denominador elegible separado de desconocidos.
SELECT fleet_account_id,eligible_delivered,sla_met,sla_breached,sla_unknown
FROM mart_fleet_scorecard;

-- 6. Faltantes potenciales: recepciones y reservas, no ordenes de compra.
SELECT part_id,name,on_hand,reserved,available,reorder_point
FROM mart_inventory WHERE available<=reorder_point;
