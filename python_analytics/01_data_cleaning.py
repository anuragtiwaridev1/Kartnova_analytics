"""
01 - DATA QUALITY AUDIT & CLEANING
==================================
WHY: Every downstream number is only as trustworthy as the data under it. Before any analysis
we profile the raw extracts, quantify each defect, apply an explicit documented fix and write
a data-quality log (so a reviewer can see exactly what changed and how many rows were affected).

OUTPUT: data/clean/*.csv (used by Python, SQL *and* Power BI), outputs/tables/data_quality_log.csv
"""
import numpy as np, pandas as pd
from utils import RAW, CLEAN, save_table

log = []
def note(table, issue, rows, action):
    log.append(dict(table=table, issue=issue, rows_affected=int(rows), action=action))
    print(f"[{table:14s}] {issue:50s} {int(rows):>6,d}  -> {action}")

rd = lambda n, **k: pd.read_csv(RAW / f"{n}.csv", **k)
cust, prod = rd("customers", parse_dates=["signup_date"]), rd("products")
orders = rd("orders", parse_dates=["order_date", "ship_date", "delivery_date"])
items, rets, mkt = rd("order_items"), rd("returns", parse_dates=["return_date"]), rd("marketing_spend", parse_dates=["month_start"])

# ---------------- customers
n = cust.duplicated("customer_id").sum();  note("customers", "duplicate customer_id", n, "drop")
cust = cust.drop_duplicates("customer_id")
bad_city = (cust.city != cust.city.str.strip().str.title()).sum()
cust["city"] = cust.city.str.strip().str.title();  note("customers", "inconsistent city casing / whitespace", bad_city, "strip + title-case")
bad_age = ((cust.age < 18) | (cust.age > 80)).sum()
cust.loc[(cust.age < 18) | (cust.age > 80), "age"] = np.nan;  note("customers", "impossible age (<18 or >80)", bad_age, "set NaN")
miss_age = cust.age.isna().sum()
med_age = cust.groupby("city_tier").age.transform("median")
cust["age"] = cust.age.fillna(med_age).round().astype(int);  note("customers", "missing age (incl. invalid)", miss_age, "impute median by city_tier")
miss_g = cust.gender.isna().sum(); cust["gender"] = cust.gender.fillna("Unknown");  note("customers", "missing gender", miss_g, "label 'Unknown'")
bins = [17, 24, 34, 44, 54, 120]; cust["age_group"] = pd.cut(cust.age, bins, labels=["18-24", "25-34", "35-44", "45-54", "55+"]).astype(str)

# ---------------- orders
n = orders.duplicated("order_id").sum();  note("orders", "duplicate order rows", n, "drop")
orders = orders.drop_duplicates("order_id")
bad = (orders.delivery_date < orders.order_date).sum()
orders.loc[orders.delivery_date < orders.order_date, "delivery_date"] = orders.order_date + pd.Timedelta(days=5)
note("orders", "delivery_date earlier than order_date", bad, "re-impute order_date + 5d (≈ median lead time)")
miss = orders.payment_method.isna().sum(); orders["payment_method"] = orders.payment_method.fillna("Unknown");  note("orders", "missing payment_method", miss, "label 'Unknown'")
orph = (~orders.customer_id.isin(cust.customer_id)).sum();  note("orders", "orphan customer_id (FK check)", orph, "none found" if orph == 0 else "drop")
orders["delivery_days"] = (orders.delivery_date - orders.order_date).dt.days

# ---------------- order_items
n = items.duplicated("order_item_id").sum();  note("order_items", "duplicate line items", n, "drop")
items = items.drop_duplicates("order_item_id")
neg = (items.quantity <= 0).sum();  items.loc[items.quantity <= 0, "quantity"] = 1;  note("order_items", "non-positive quantity", neg, "set to 1")
orph = (~items.order_id.isin(orders.order_id)).sum();  note("order_items", "orphan order_id (FK check)", orph, "drop" if orph else "none found")
items = items[items.order_id.isin(orders.order_id)]
orph = (~items.product_id.isin(prod.product_id)).sum();  note("order_items", "orphan product_id (FK check)", orph, "none found" if orph == 0 else "drop")

# ---------------- returns
orph = (~rets.order_item_id.isin(items.order_item_id)).sum();  note("returns", "orphan order_item_id (FK check)", orph, "drop" if orph else "none found")
rets = rets[rets.order_item_id.isin(items.order_item_id)]

# ---------------- date dimension (India fiscal year Apr-Mar)
d = pd.DataFrame({"date": pd.date_range("2023-01-01", "2026-12-31")})
d["date_key"] = d.date.dt.strftime("%Y%m%d").astype(int)
d["year"], d["quarter"], d["month_num"] = d.date.dt.year, d.date.dt.quarter, d.date.dt.month
d["month_name"], d["month_short"] = d.date.dt.month_name(), d.date.dt.strftime("%b")
d["year_month"] = d.date.dt.strftime("%Y-%m")
d["week_of_year"] = d.date.dt.isocalendar().week.astype(int)
d["day_name"], d["is_weekend"] = d.date.dt.day_name(), (d.date.dt.dayofweek >= 5).astype(int)
d["fiscal_year"] = np.where(d.month_num >= 4, "FY" + (d.year + 1).astype(str).str[-2:], "FY" + d.year.astype(str).str[-2:])
d["is_festive_season"] = d.month_num.isin([10, 11]).astype(int)
note("dim_date", "generated calendar 2023-2026 (+fiscal, festive flag)", len(d), "created")

for name, df in dict(customers=cust, products=prod, orders=orders, order_items=items, returns=rets,
                     marketing_spend=mkt, dim_date=d).items():
    df.to_csv(CLEAN / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    print(f"  saved clean/{name}.csv  ({len(df):,} rows)")
save_table(pd.DataFrame(log), "data_quality_log")
