-- =====================================================================================
-- 05_data_quality_checks.sql  |  Automated assertions - every row returned is a FAILURE (0 rows = healthy)
-- =====================================================================================

-- name: dq01_orphan_foreign_keys
SELECT 'order_items -> orders' AS check_name, COUNT(*) AS failures FROM order_items oi LEFT JOIN orders o USING (order_id) WHERE o.order_id IS NULL
UNION ALL SELECT 'orders -> customers', COUNT(*) FROM orders o LEFT JOIN customers c USING (customer_id) WHERE c.customer_id IS NULL
UNION ALL SELECT 'order_items -> products', COUNT(*) FROM order_items oi LEFT JOIN products p USING (product_id) WHERE p.product_id IS NULL
UNION ALL SELECT 'returns -> order_items', COUNT(*) FROM returns r LEFT JOIN order_items oi USING (order_item_id) WHERE oi.order_item_id IS NULL;

-- name: dq02_business_rule_violations
SELECT 'delivery before order'            AS check_name, COUNT(*) AS failures FROM orders WHERE delivery_date < order_date
UNION ALL SELECT 'return before delivery',              COUNT(*) FROM returns r JOIN order_items oi USING (order_item_id) JOIN orders o USING (order_id) WHERE r.return_date < o.delivery_date
UNION ALL SELECT 'discount outside 0-100',              COUNT(*) FROM order_items WHERE discount_pct < 0 OR discount_pct > 100
UNION ALL SELECT 'price below cost (list)',             COUNT(*) FROM products WHERE list_price < unit_cost
UNION ALL SELECT 'cancelled order with a return',       COUNT(*) FROM returns r JOIN order_items oi USING (order_item_id) JOIN orders o USING (order_id) WHERE o.order_status = 'Cancelled';

-- name: dq03_reconciliation_to_python
-- Total delivered net revenue (SQL view) vs. the figure produced by Python (compare in run_sql_pipeline.py output).
SELECT ROUND(SUM(net_revenue), 2) AS sql_net_revenue, ROUND(SUM(gross_profit), 2) AS sql_gross_profit, COUNT(DISTINCT order_id) AS delivered_orders FROM vw_order_lines;
