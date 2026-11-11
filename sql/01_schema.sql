-- =====================================================================================
-- 01_schema.sql  |  Star-schema DDL, indexes and the analytical base view
-- Dialect: SQLite (ANSI SQL; see README for PostgreSQL / SQL Server translation notes)
-- =====================================================================================
PRAGMA foreign_keys = ON;

CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY, date TEXT NOT NULL, year INTEGER, quarter INTEGER, month_num INTEGER,
    month_name TEXT, month_short TEXT, year_month TEXT, week_of_year INTEGER, day_name TEXT,
    is_weekend INTEGER, fiscal_year TEXT, is_festive_season INTEGER);
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY, signup_date TEXT NOT NULL, gender TEXT, age INTEGER, city TEXT, state TEXT,
    region TEXT, city_tier INTEGER, acquisition_channel TEXT, age_group TEXT);
CREATE TABLE products (
    product_id TEXT PRIMARY KEY, product_name TEXT, category TEXT, sub_category TEXT, brand TEXT,
    list_price REAL NOT NULL, unit_cost REAL NOT NULL);
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    order_date TEXT NOT NULL, ship_date TEXT, delivery_date TEXT,
    order_status TEXT CHECK (order_status IN ('Delivered','Cancelled')), payment_method TEXT, device TEXT,
    shipping_fee REAL, delivery_days INTEGER);
CREATE TABLE order_items (
    order_item_id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(order_id),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    quantity INTEGER CHECK (quantity > 0), unit_price REAL, discount_pct REAL);
CREATE TABLE returns (
    return_id TEXT PRIMARY KEY, order_item_id TEXT NOT NULL UNIQUE REFERENCES order_items(order_item_id),
    return_date TEXT, return_reason TEXT, refund_pct REAL);
CREATE TABLE marketing_spend (month_start TEXT, channel TEXT, marketing_spend REAL, PRIMARY KEY (month_start, channel));

CREATE INDEX ix_orders_customer ON orders(customer_id);
CREATE INDEX ix_orders_date     ON orders(order_date);
CREATE INDEX ix_items_order     ON order_items(order_id);
CREATE INDEX ix_items_product   ON order_items(product_id);

-- Analytical base view: one row per DELIVERED order line with all money metrics defined ONCE.
-- Business rules (identical in Python and DAX so all three layers reconcile):
--   net_revenue  = qty * unit_price * (1 - discount%)
--   refund_amt   = net_revenue * refund_pct          (returned lines only)
--   gross_profit = net_revenue - refund_amt - COGS * (1 - refund_pct)   (returned units are restocked)
CREATE VIEW vw_order_lines AS
SELECT  oi.order_item_id, o.order_id, o.customer_id, o.order_date,
        strftime('%Y', o.order_date)    AS order_year,
        strftime('%Y-%m', o.order_date) AS order_month,
        o.payment_method, o.device, o.delivery_days,
        c.region, c.city, c.city_tier, c.acquisition_channel, c.signup_date,
        p.product_id, p.product_name, p.category, p.sub_category,
        oi.quantity, oi.unit_price, oi.discount_pct,
        oi.quantity * oi.unit_price                                   AS gross_sales,
        oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)   AS net_revenue,
        CASE WHEN r.return_id IS NOT NULL THEN 1 ELSE 0 END           AS is_returned,
        CASE WHEN r.return_id IS NOT NULL
             THEN oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0) * r.refund_pct ELSE 0 END AS refund_amt,
        oi.quantity * p.unit_cost                                     AS cogs,
        oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)
          - CASE WHEN r.return_id IS NOT NULL THEN oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0) * r.refund_pct ELSE 0 END
          - oi.quantity * p.unit_cost * (1 - COALESCE(r.refund_pct, 0)) AS gross_profit
FROM order_items oi
JOIN orders    o ON o.order_id   = oi.order_id AND o.order_status = 'Delivered'
JOIN customers c ON c.customer_id = o.customer_id
JOIN products  p ON p.product_id  = oi.product_id
LEFT JOIN returns r ON r.order_item_id = oi.order_item_id;
