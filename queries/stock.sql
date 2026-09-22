-- Purchase promises never count as stock. Only journal movements do.
WITH movement AS (
 SELECT part_id,SUM(CASE WHEN move_type='consume' THEN -quantity ELSE quantity END) AS on_hand
 FROM v_stock_moves GROUP BY part_id
), reserve AS (
 SELECT part_id,SUM(quantity) AS reserved FROM v_reservations WHERE status='reserved' GROUP BY part_id
)
SELECT p.id,p.sku,COALESCE(m.on_hand,0) AS on_hand,COALESCE(r.reserved,0) AS reserved,
       COALESCE(m.on_hand,0)-COALESCE(r.reserved,0) AS available,p.reorder_point
FROM v_parts p LEFT JOIN movement m ON m.part_id=p.id LEFT JOIN reserve r ON r.part_id=p.id
ORDER BY p.id;
