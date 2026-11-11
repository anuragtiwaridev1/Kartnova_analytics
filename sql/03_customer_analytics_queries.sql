-- =====================================================================================
-- 03_customer_analytics_queries.sql  |  Customer value, retention & behaviour
-- Techniques: NTILE, multi-step CTEs, self-referencing windows (LAG), cohort date arithmetic
-- =====================================================================================

-- name: q09_rfm_scoring_ntile
-- WHY: RFM in pure SQL so CRM can refresh segments inside the warehouse with no Python dependency.
WITH base AS (
    SELECT customer_id, MAX(order_date) AS last_order, COUNT(DISTINCT order_id) AS frequency, SUM(net_revenue - refund_amt) AS monetary
    FROM vw_order_lines GROUP BY customer_id),
scored AS (
    SELECT customer_id, frequency, ROUND(monetary, 0) AS monetary,
           CAST(julianday('2025-12-31') - julianday(last_order) AS INTEGER) AS recency_days,
           6 - NTILE(5) OVER (ORDER BY julianday('2025-12-31') - julianday(last_order))  AS r_score,
           NTILE(5) OVER (ORDER BY frequency, customer_id) AS f_score,
           NTILE(5) OVER (ORDER BY monetary,  customer_id) AS m_score
    FROM base)
SELECT CASE WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 4                  THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2                  THEN 'New / Promising'
            WHEN r_score >= 3 AND f_score >= 3                  THEN 'Potential Loyalists'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN 'Can''t Lose Them'
            WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost'
            ELSE 'Needs Attention' END AS segment,
       COUNT(*) AS customers, ROUND(SUM(monetary), 0) AS revenue,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS revenue_pct,
       ROUND(AVG(recency_days), 0) AS avg_recency_days, ROUND(AVG(frequency), 1) AS avg_orders
FROM scored GROUP BY 1 ORDER BY revenue DESC;

-- name: q10_cohort_retention
-- WHY: retention by first-purchase month cohort. Month index via year/month arithmetic (portable, no date-diff function).
WITH o AS (SELECT DISTINCT customer_id, order_id, order_month FROM vw_order_lines),
first_m AS (SELECT customer_id, MIN(order_month) AS cohort_month FROM o GROUP BY customer_id),
act AS (
    SELECT f.cohort_month,
           (CAST(substr(o.order_month, 1, 4) AS INT) - CAST(substr(f.cohort_month, 1, 4) AS INT)) * 12
         + (CAST(substr(o.order_month, 6, 2) AS INT) - CAST(substr(f.cohort_month, 6, 2) AS INT)) AS month_n,
           COUNT(DISTINCT o.customer_id) AS active_customers
    FROM o JOIN first_m f USING (customer_id) GROUP BY 1, 2)
SELECT cohort_month, month_n, active_customers,
       FIRST_VALUE(active_customers) OVER (PARTITION BY cohort_month ORDER BY month_n) AS cohort_size,
       ROUND(100.0 * active_customers / FIRST_VALUE(active_customers) OVER (PARTITION BY cohort_month ORDER BY month_n), 1) AS retention_pct
FROM act WHERE month_n <= 12 AND cohort_month >= '2024-01' ORDER BY cohort_month, month_n;

-- name: q11_repeat_purchase_and_inter_order_gap
-- WHY: how many customers come back, and how fast? Drives the timing of post-purchase journeys.
WITH ord AS (
    SELECT customer_id, order_date, order_id,
           julianday(order_date) - julianday(LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id)) AS gap_days,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS order_seq
    FROM (SELECT DISTINCT customer_id, order_id, order_date FROM vw_order_lines))
SELECT order_seq AS nth_order, COUNT(*) AS customers_reaching, ROUND(AVG(gap_days), 1) AS avg_days_since_previous,
       ROUND(100.0 * COUNT(*) / FIRST_VALUE(COUNT(*)) OVER (ORDER BY order_seq), 1) AS pct_of_first_time_buyers
FROM ord WHERE order_seq <= 8 GROUP BY order_seq ORDER BY order_seq;

-- name: q12_customer_revenue_concentration
-- WHY: if the top decile is 60% of revenue the business is exposed to a few customers - a board-level risk metric.
WITH c AS (SELECT customer_id, SUM(net_revenue - refund_amt) AS rev FROM vw_order_lines GROUP BY 1),
     d AS (SELECT *, NTILE(10) OVER (ORDER BY rev DESC) AS decile FROM c)
SELECT decile, COUNT(*) AS customers, ROUND(SUM(rev), 0) AS revenue,
       ROUND(100.0 * SUM(rev) / SUM(SUM(rev)) OVER (), 1) AS pct_of_revenue,
       ROUND(100.0 * SUM(SUM(rev)) OVER (ORDER BY decile) / SUM(SUM(rev)) OVER (), 1) AS cumulative_pct
FROM d GROUP BY decile ORDER BY decile;

-- name: q13_first_purchase_category_and_repeat_rate
-- WHY: which category is the best "gateway" to a loyal customer? (acquire with it, then cross-sell).
WITH fo AS (
    SELECT customer_id, order_id FROM (SELECT customer_id, order_id, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date, order_id) rn
                                       FROM (SELECT DISTINCT customer_id, order_id, order_date FROM vw_order_lines)) WHERE rn = 1),
fc AS (SELECT customer_id, category FROM (
          SELECT fo.customer_id, v.category,
                 ROW_NUMBER() OVER (PARTITION BY fo.customer_id ORDER BY v.net_revenue DESC, v.order_item_id) AS rn
          FROM fo JOIN vw_order_lines v ON v.order_id = fo.order_id) WHERE rn = 1),
cnt AS (SELECT customer_id, COUNT(DISTINCT order_id) AS n_orders, SUM(net_revenue - refund_amt) AS rev FROM vw_order_lines GROUP BY 1)
SELECT fc.category AS first_order_main_category, COUNT(*) AS customers,
       ROUND(100.0 * AVG(CASE WHEN n_orders >= 2 THEN 1.0 ELSE 0 END), 1) AS repeat_rate_pct, ROUND(AVG(n_orders), 2) AS avg_orders, ROUND(AVG(rev), 0) AS avg_lifetime_revenue
FROM fc JOIN cnt USING (customer_id) GROUP BY 1 ORDER BY repeat_rate_pct DESC;
