-- Aggregate each relation before joining to avoid vehicle/opportunity fan-out.
WITH opportunities AS (
 SELECT fleet_account_id,COUNT(*) AS open_opportunities,SUM(value_cents) AS pipeline_cents
 FROM v_opportunities WHERE status NOT IN ('won','lost') GROUP BY fleet_account_id
), vehicles AS (
 SELECT customer_id,COUNT(*) AS known_vehicles FROM v_vehicles GROUP BY customer_id
)
SELECT a.id,c.name,a.fleet_size AS declared_fleet_size,COALESCE(v.known_vehicles,0) AS captured_vehicles,
       COALESCE(o.open_opportunities,0) AS open_opportunities,COALESCE(o.pipeline_cents,0) AS pipeline_cents
FROM v_fleet_accounts a JOIN v_customers c ON c.id=a.customer_id
LEFT JOIN opportunities o ON o.fleet_account_id=a.id LEFT JOIN vehicles v ON v.customer_id=a.customer_id
ORDER BY a.id;
