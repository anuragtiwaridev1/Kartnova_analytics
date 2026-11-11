-- =====================================================================================
-- 04_marketing_operations_queries.sql  |  Acquisition economics, logistics, returns, basket
-- =====================================================================================

-- name: q14_channel_cac_ltv
-- WHY: ranks acquisition channels by profit return on spend, not by cheapness.
WITH sp  AS (SELECT channel, SUM(marketing_spend) AS spend FROM marketing_spend GROUP BY channel),
     nc  AS (SELECT acquisition_channel AS channel, COUNT(*) AS new_customers FROM customers GROUP BY 1),
     mat AS (SELECT customer_id, acquisition_channel AS channel, signup_date FROM customers WHERE signup_date <= '2024-12-31'),
     ltv AS (SELECT m.channel, COUNT(DISTINCT m.customer_id) AS mature_customers,
                    SUM(v.gross_profit) * 1.0 / COUNT(DISTINCT m.customer_id) AS ltv12_gp
             FROM mat m LEFT JOIN vw_order_lines v ON v.customer_id = m.customer_id AND v.order_date <= date(m.signup_date, '+365 day')
             GROUP BY m.channel)
SELECT sp.channel, nc.new_customers, ROUND(sp.spend, 0) AS spend, ROUND(sp.spend / nc.new_customers, 0) AS cac,
       ROUND(ltv.ltv12_gp, 0) AS ltv12_gross_profit, ROUND(ltv.ltv12_gp / (sp.spend / nc.new_customers), 2) AS ltv_to_cac,
       ROUND((sp.spend / nc.new_customers) / (ltv.ltv12_gp / 12), 1) AS payback_months
FROM sp JOIN nc USING (channel) JOIN ltv USING (channel) ORDER BY ltv_to_cac DESC;

-- name: q15_delivery_sla_by_region
-- WHY: logistics scorecard - average, p-style late share (>7 days) and cancellation by region.
WITH o AS (SELECT o.*, c.region FROM orders o JOIN customers c USING (customer_id))
SELECT region, COUNT(*) AS orders,
       ROUND(AVG(CASE WHEN order_status = 'Delivered' THEN delivery_days END), 1) AS avg_delivery_days,
       ROUND(100.0 * SUM(CASE WHEN order_status = 'Delivered' AND delivery_days > 7 THEN 1 ELSE 0 END)
             / SUM(CASE WHEN order_status = 'Delivered' THEN 1 ELSE 0 END), 1) AS late_delivery_pct,
       ROUND(100.0 * AVG(CASE WHEN order_status = 'Cancelled' THEN 1.0 ELSE 0 END), 1) AS cancel_rate_pct
FROM o GROUP BY region ORDER BY avg_delivery_days DESC;

-- name: q16_cancellation_by_payment_method
SELECT payment_method, COUNT(*) AS orders, SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled,
       ROUND(100.0 * AVG(CASE WHEN order_status = 'Cancelled' THEN 1.0 ELSE 0 END), 2) AS cancel_rate_pct
FROM orders GROUP BY payment_method ORDER BY cancel_rate_pct DESC;

-- name: q17_returns_reason_by_category
-- WHY: the reason mix tells ops whether to fix sizing charts (Fashion) or QC (Electronics).
WITH r AS (SELECT v.category, rt.return_reason, COUNT(*) AS n, SUM(v.refund_amt) AS refund_value
           FROM returns rt JOIN vw_order_lines v ON v.order_item_id = rt.order_item_id GROUP BY 1, 2)
SELECT category, return_reason, n AS returns, ROUND(refund_value, 0) AS refund_value,
       ROUND(100.0 * n / SUM(n) OVER (PARTITION BY category), 1) AS pct_of_category_returns,
       RANK() OVER (PARTITION BY category ORDER BY n DESC) AS reason_rank
FROM r ORDER BY category, reason_rank;

-- name: q18_market_basket_subcategory_lift
-- WHY: self-join on order lines to find sub-category pairs bought together (support / confidence / lift).
WITH basket AS (SELECT DISTINCT order_id, sub_category FROM vw_order_lines),
     tot AS (SELECT COUNT(DISTINCT order_id) AS n FROM basket),
     item AS (SELECT sub_category, COUNT(*) AS n FROM basket GROUP BY 1),
     pair AS (SELECT a.sub_category AS antecedent, b.sub_category AS consequent, COUNT(*) AS together
              FROM basket a JOIN basket b ON a.order_id = b.order_id AND a.sub_category <> b.sub_category GROUP BY 1, 2 HAVING COUNT(*) >= 40)
SELECT antecedent, consequent, together AS orders_together,
       ROUND(100.0 * together / tot.n, 2) AS support_pct,
       ROUND(100.0 * together / ia.n, 1) AS confidence_pct,
       ROUND((1.0 * together / ia.n) / (1.0 * ib.n / tot.n), 2) AS lift
FROM pair JOIN item ia ON ia.sub_category = pair.antecedent JOIN item ib ON ib.sub_category = pair.consequent, tot
ORDER BY lift DESC LIMIT 15;

-- name: q19_payment_device_mix
SELECT device, payment_method, COUNT(DISTINCT order_id) AS orders, ROUND(SUM(net_revenue), 0) AS revenue,
       ROUND(100.0 * COUNT(DISTINCT order_id) / SUM(COUNT(DISTINCT order_id)) OVER (PARTITION BY device), 1) AS pct_of_device_orders
FROM vw_order_lines GROUP BY device, payment_method ORDER BY device, orders DESC;
