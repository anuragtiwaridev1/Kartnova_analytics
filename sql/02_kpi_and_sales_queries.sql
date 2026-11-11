-- =====================================================================================
-- 02_kpi_and_sales_queries.sql  |  Executive KPIs & sales performance
-- Techniques: CTEs, window functions (LAG, SUM OVER, RANK, ROW_NUMBER), conditional aggregation
-- =====================================================================================

-- name: q01_kpi_scorecard_by_year
-- WHY: single source of truth for headline KPIs; reconciles to the Python scorecard and Power BI cards.
SELECT order_year,
       ROUND(SUM(net_revenue), 0)                                            AS net_revenue,
       ROUND(SUM(refund_amt), 0)                                             AS refunds,
       ROUND(SUM(net_revenue - refund_amt), 0)                               AS kept_revenue,
       ROUND(SUM(gross_profit), 0)                                           AS gross_profit,
       ROUND(100.0 * SUM(gross_profit) / SUM(net_revenue - refund_amt), 2)   AS gross_margin_pct,
       COUNT(DISTINCT order_id)                                              AS orders,
       COUNT(DISTINCT customer_id)                                           AS active_customers,
       ROUND(SUM(net_revenue) / COUNT(DISTINCT order_id), 0)                 AS aov,
       ROUND(100.0 * AVG(is_returned), 2)                                    AS return_rate_pct
FROM vw_order_lines GROUP BY order_year ORDER BY order_year;

-- name: q02_monthly_revenue_mom_yoy
-- WHY: growth rates tell direction; MoM = momentum, YoY strips out seasonality. LAG(1) vs LAG(12).
WITH m AS (
    SELECT order_month, SUM(net_revenue) AS revenue, COUNT(DISTINCT order_id) AS orders
    FROM vw_order_lines GROUP BY order_month)
SELECT order_month, ROUND(revenue, 0) AS revenue, orders,
       ROUND(100.0 * (revenue / LAG(revenue, 1)  OVER (ORDER BY order_month) - 1), 1) AS mom_growth_pct,
       ROUND(100.0 * (revenue / LAG(revenue, 12) OVER (ORDER BY order_month) - 1), 1) AS yoy_growth_pct,
       ROUND(AVG(revenue) OVER (ORDER BY order_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0) AS revenue_3m_ma
FROM m ORDER BY order_month;

-- name: q03_ytd_running_revenue
-- WHY: YTD run-rate vs. same period last year is the standard monthly business-review view.
WITH m AS (SELECT order_year, order_month, SUM(net_revenue) AS revenue FROM vw_order_lines GROUP BY 1, 2)
SELECT order_year, order_month, ROUND(revenue, 0) AS revenue,
       ROUND(SUM(revenue) OVER (PARTITION BY order_year ORDER BY order_month), 0) AS ytd_revenue,
       ROUND(100.0 * revenue / SUM(revenue) OVER (PARTITION BY order_year), 1)    AS pct_of_year
FROM m ORDER BY order_month;

-- name: q04_category_profitability
-- WHY: revenue ≠ profit. Shows where margin is made and where returns leak it.
SELECT category,
       ROUND(SUM(net_revenue), 0) AS net_revenue,
       ROUND(100.0 * SUM(net_revenue) / SUM(SUM(net_revenue)) OVER (), 1)                  AS revenue_share_pct,
       ROUND(SUM(gross_profit), 0) AS gross_profit,
       ROUND(100.0 * SUM(gross_profit) / SUM(net_revenue - refund_amt), 1)                 AS gross_margin_pct,
       ROUND(100.0 * AVG(is_returned), 1)                                                  AS return_rate_pct,
       ROUND(100.0 * SUM(gross_profit) / SUM(SUM(gross_profit)) OVER (), 1)                AS profit_share_pct
FROM vw_order_lines GROUP BY category ORDER BY net_revenue DESC;

-- name: q05_product_pareto_abc
-- WHY: ABC classification drives inventory policy (A = never stock out, C = candidates to delist).
WITH p AS (SELECT product_id, product_name, category, SUM(net_revenue) AS revenue FROM vw_order_lines GROUP BY 1, 2, 3),
     c AS (SELECT *, SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER () AS cum_share,
                  ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rnk FROM p)
SELECT rnk, product_id, product_name, category, ROUND(revenue, 0) AS revenue, ROUND(100 * cum_share, 1) AS cum_revenue_pct,
       CASE WHEN cum_share <= .70 THEN 'A' WHEN cum_share <= .90 THEN 'B' ELSE 'C' END AS abc_class
FROM c ORDER BY rnk;

-- name: q06_top3_products_per_category
-- WHY: "top-N per group" pattern with ROW_NUMBER() - the canonical interview question, used for merchandising.
WITH p AS (SELECT category, product_name, SUM(net_revenue) AS revenue, SUM(quantity) AS units FROM vw_order_lines GROUP BY 1, 2),
     r AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) AS rn FROM p)
SELECT category, rn AS rank_in_category, product_name, ROUND(revenue, 0) AS revenue, units FROM r WHERE rn <= 3 ORDER BY category, rn;

-- name: q07_city_ranking_within_region
-- WHY: regional managers need to know which cities carry the region (RANK + share-of-region window).
WITH c AS (SELECT region, city, SUM(net_revenue) AS revenue, COUNT(DISTINCT customer_id) AS customers FROM vw_order_lines GROUP BY 1, 2)
SELECT region, city, ROUND(revenue, 0) AS revenue, customers, ROUND(revenue / customers, 0) AS revenue_per_customer,
       RANK() OVER (PARTITION BY region ORDER BY revenue DESC) AS rank_in_region,
       ROUND(100.0 * revenue / SUM(revenue) OVER (PARTITION BY region), 1) AS pct_of_region
FROM c ORDER BY region, rank_in_region;

-- name: q08_discount_band_economics
-- WHY: do deeper discounts buy volume or just give away margin?
SELECT CASE WHEN discount_pct = 0 THEN '0%' WHEN discount_pct <= 10 THEN '1-10%' WHEN discount_pct <= 20 THEN '11-20%' ELSE '>20%' END AS discount_band,
       COUNT(*) AS lines, ROUND(AVG(quantity), 2) AS avg_units_per_line,
       ROUND(100.0 * AVG(is_returned), 2) AS return_rate_pct,
       ROUND(100.0 * SUM(gross_profit) / SUM(net_revenue - refund_amt), 2) AS gross_margin_pct
FROM vw_order_lines GROUP BY 1 ORDER BY MIN(discount_pct);
