-- Each row is a current state count; not a temporal conversion funnel.
SELECT c.segment,w.status,COUNT(*) AS order_count
FROM v_work_orders w JOIN v_customers c ON c.id=w.customer_id
GROUP BY c.segment,w.status ORDER BY c.segment,w.status;
