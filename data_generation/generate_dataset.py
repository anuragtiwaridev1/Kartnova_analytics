"""
generate_dataset.py
-------------------
Builds the synthetic KartNova dataset (an Indian omnichannel e-commerce retailer,
Jan-2023 -> Dec-2025). Fully reproducible (fixed seed).

Business dynamics deliberately baked in so the analytics have real signal to find:
  * Upward growth trend + festive seasonality (Oct/Nov Diwali peak, Jan/Aug sales)
  * Heterogeneous customers (Gamma-distributed purchase rate, channel-dependent churn)
  * Category-level margins & return rates (Fashion returns >> Grocery)
  * Higher discounts in festive months; COD orders cancel more
  * Product bundles (e.g. Laptop -> Laptop Accessories) for market-basket analysis
  * Regional delivery-time differences
Raw files intentionally contain data-quality issues (duplicates, casing, nulls,
impossible dates, outlier ages) that 01_data_cleaning.py detects and fixes.
"""
import os
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
START, END = pd.Timestamp("2023-01-01"), pd.Timestamp("2025-12-31")

# ----------------------------------------------------------------- PRODUCTS
CATALOG = {
    "Electronics": {"margin": .27, "price": (999, 80000), "subs": ["Smartphones", "Laptops", "Laptop Accessories", "Headphones"]},
    "Fashion": {"margin": .62, "price": (399, 5999), "subs": ["Men's Wear", "Women's Wear", "Footwear", "Fashion Accessories"]},
    "Home & Kitchen": {"margin": .48, "price": (299, 14999), "subs": ["Cookware", "Furniture", "Home Decor", "Appliances"]},
    "Beauty & Personal Care": {"margin": .66, "price": (149, 3999), "subs": ["Skincare", "Haircare", "Fragrances", "Grooming"]},
    "Grocery & Gourmet": {"margin": .32, "price": (99, 1499), "subs": ["Snacks", "Beverages", "Staples", "Organic Foods"]},
    "Sports & Fitness": {"margin": .50, "price": (299, 19999), "subs": ["Gym Equipment", "Sportswear", "Outdoor Gear", "Yoga"]},
    "Books & Stationery": {"margin": .42, "price": (99, 1999), "subs": ["Fiction", "Academic", "Office Supplies", "Art Supplies"]},
}
BRANDS = ["Aurora", "Zenith", "Nimbus", "Vertex", "Kiara", "Orbit", "Pinnacle", "Lumen", "Sahara", "Tarang", "Meridian", "Indus"]
SPECIAL_PRICE = {"Laptop Accessories": (299, 4999), "Laptops": (29999, 89999), "Smartphones": (8999, 69999)}

prod, pid = [], 1
for cat, meta in CATALOG.items():
    for sub in meta["subs"]:
        n = 6 if cat == "Electronics" else 5
        lo, hi = SPECIAL_PRICE.get(sub, meta["price"])
        prices = np.exp(rng.uniform(np.log(lo), np.log(hi), n))
        for k in range(n):
            price = round(prices[k] / 10) * 10 - 1
            m = np.clip(rng.normal(meta["margin"], .05), .08, .7)
            brand = rng.choice(BRANDS)
            prod.append(dict(product_id=f"P{pid:03d}", product_name=f"{brand} {sub} Model {k + 1}",
                             category=cat, sub_category=sub, brand=brand,
                             list_price=float(price), unit_cost=round(price * (1 - m), 2)))
            pid += 1
products = pd.DataFrame(prod)

# --------------------------------------------------------------- CUSTOMERS
CITIES = [("Mumbai", "Maharashtra", "West", 1, .14), ("Delhi", "Delhi", "North", 1, .13), ("Bengaluru", "Karnataka", "South", 1, .12),
          ("Hyderabad", "Telangana", "South", 1, .07), ("Chennai", "Tamil Nadu", "South", 1, .06), ("Kolkata", "West Bengal", "East", 1, .06),
          ("Pune", "Maharashtra", "West", 1, .07), ("Ahmedabad", "Gujarat", "West", 2, .04), ("Jaipur", "Rajasthan", "North", 2, .04),
          ("Lucknow", "Uttar Pradesh", "North", 2, .035), ("Chandigarh", "Chandigarh", "North", 2, .025), ("Kochi", "Kerala", "South", 2, .03),
          ("Indore", "Madhya Pradesh", "Central", 2, .03), ("Guwahati", "Assam", "North-East", 3, .015), ("Bhubaneswar", "Odisha", "East", 2, .02),
          ("Patna", "Bihar", "East", 3, .02), ("Surat", "Gujarat", "West", 2, .03), ("Nagpur", "Maharashtra", "West", 2, .03)]
CH = ["Organic Search", "Paid Search", "Social Media", "Referral", "Email Marketing", "Affiliate"]
CH_P = [.28, .22, .20, .12, .08, .10]
CH_LIFE_MONTHS = {"Organic Search": 17, "Paid Search": 10, "Social Media": 9, "Referral": 22, "Email Marketing": 15, "Affiliate": 8}
N_CUST = 9000
days = (END - START).days
u = rng.beta(1.35, 1.0, N_CUST)                      # signups skew to later months (growth)
signup = np.sort((u * (days - 20)).astype(int))
city_p = np.array([c[4] for c in CITIES]); city_p = city_p / city_p.sum()
ci = rng.choice(len(CITIES), N_CUST, p=city_p)
customers = pd.DataFrame({
    "customer_id": [f"C{i:05d}" for i in range(1, N_CUST + 1)],
    "signup_date": START + pd.to_timedelta(signup, unit="D"),
    "gender": rng.choice(["Female", "Male", "Other"], N_CUST, p=[.47, .50, .03]),
    "age": np.clip(rng.normal(32, 9, N_CUST), 18, 70).astype(int),
    "city": [CITIES[i][0] for i in ci], "state": [CITIES[i][1] for i in ci],
    "region": [CITIES[i][2] for i in ci], "city_tier": [CITIES[i][3] for i in ci],
    "acquisition_channel": rng.choice(CH, N_CUST, p=CH_P),
})

# ------------------------------------------------------------------ ORDERS
MONTH_W = {1: 1.05, 2: .88, 3: .95, 4: .9, 5: .95, 6: 1.0, 7: .95, 8: 1.05, 9: 1.0, 10: 1.4, 11: 1.45, 12: 1.15}
MAXW = max(MONTH_W.values())
DISC_SCALE = {1: 1.0, 2: .6, 3: .7, 4: .6, 5: .8, 6: .9, 7: .8, 8: 1.4, 9: .9, 10: 2.0, 11: 2.2, 12: 1.2}
PAY = ["UPI", "Credit Card", "Debit Card", "Cash on Delivery", "Net Banking", "Wallet"]; PAY_P = [.42, .18, .12, .18, .06, .04]
DEV = ["Mobile App", "Mobile Web", "Desktop"]; DEV_P = [.55, .22, .23]
REG_DELIV = {"West": 3.2, "North": 3.8, "South": 3.5, "East": 4.8, "Central": 4.2, "North-East": 6.2}
CAT_NAMES = list(CATALOG)
bundles = {"Laptops": ("Laptop Accessories", .45), "Smartphones": ("Headphones", .30), "Skincare": ("Haircare", .22),
           "Gym Equipment": ("Sportswear", .25), "Cookware": ("Appliances", .15), "Fiction": ("Art Supplies", .10),
           "Men's Wear": ("Footwear", .25), "Women's Wear": ("Fashion Accessories", .28), "Snacks": ("Beverages", .35)}
by_sub = {s: products[products.sub_category == s].index.values for s in products.sub_category.unique()}
cat_idx = {c: products[products.category == c].index.values for c in CAT_NAMES}
CAT_BASE = np.array([.09, .24, .16, .16, .15, .11, .09])
DISC_CHOICES = np.array([0, 0, 5, 5, 10, 10, 15, 20, 25, 30])
DISC_CAP = {"Electronics": 12, "Grocery & Gourmet": 15, "Books & Stationery": 25}   # category discount ceilings (%)

orders, items = [], []
oid = iid = 1
for c in customers.itertuples():
    rate = rng.gamma(1.4, 2.6)                                         # orders / year
    if c.acquisition_channel in ("Referral", "Organic Search"):
        rate *= 1.15
    life = rng.exponential(CH_LIFE_MONTHS[c.acquisition_channel] * 1.3) * 30.4 + 20   # active days
    churn_date = c.signup_date + pd.Timedelta(days=float(life))
    aff = rng.dirichlet(CAT_BASE * 6)                                  # personal category affinity
    t = c.signup_date + pd.Timedelta(days=int(rng.integers(0, 3)))
    first = True
    while True:
        if not first:
            t = t + pd.Timedelta(days=max(1, int(rng.exponential(365 / max(rate, .3)))))
        if t > END or t > churn_date:
            break
        if not first and rng.random() > MONTH_W[t.month] / MAXW:         # seasonality via thinning
            continue
        first = False
        n_items = min(6, 1 + rng.poisson(.9))
        picks = []
        for _ in range(n_items):
            cat = rng.choice(CAT_NAMES, p=aff)
            pool = cat_idx[cat]
            w = 1 / (np.arange(1, len(pool) + 1) ** .8); w = w / w.sum()  # popularity skew inside category
            p = pool[rng.choice(len(pool), p=w)]
            picks.append(p)
            sub = products.at[p, "sub_category"]
            if sub in bundles and rng.random() < bundles[sub][1]:
                picks.append(rng.choice(by_sub[bundles[sub][0]]))
        picks = list(dict.fromkeys(picks))[:7]
        pay = rng.choice(PAY, p=PAY_P)
        scale = DISC_SCALE[t.month]
        bonus = 5 if c.acquisition_channel == "Email Marketing" else 0
        subtotal = 0.0
        ship_lag = int(rng.integers(1, 4))
        deliv_days = max(2, int(rng.normal(REG_DELIV[c.region], 1.3)))
        cancel_p = .03 + (.06 if pay == "Cash on Delivery" else 0) + (.02 if c.region == "North-East" else 0)
        status = "Cancelled" if rng.random() < cancel_p else "Delivered"
        for p in picks:
            lp = products.at[p, "list_price"]
            disc = int(min(DISC_CAP.get(products.at[p, "category"], 40), rng.choice(DISC_CHOICES) * scale // 5 * 5 + bonus))
            heavy = products.at[p, "category"] in ("Grocery & Gourmet", "Books & Stationery")
            qty = 1 if lp > 8000 else int(1 + rng.poisson(.35 + (.5 if heavy else 0)))
            items.append((iid, oid, products.at[p, "product_id"], qty, lp, disc))
            subtotal += lp * qty * (1 - disc / 100); iid += 1
        ship_fee = 0 if subtotal >= 499 else 49
        orders.append((oid, c.customer_id, t, t + pd.Timedelta(days=ship_lag),
                       t + pd.Timedelta(days=ship_lag + deliv_days), status, pay,
                       rng.choice(DEV, p=DEV_P), ship_fee))
        oid += 1

orders = pd.DataFrame(orders, columns=["order_id", "customer_id", "order_date", "ship_date", "delivery_date",
                                       "order_status", "payment_method", "device", "shipping_fee"])
items = pd.DataFrame(items, columns=["order_item_id", "order_id", "product_id", "quantity", "unit_price", "discount_pct"])
orders["order_id"] = orders["order_id"].map(lambda x: f"ORD{x:07d}")
items["order_id"] = items["order_id"].map(lambda x: f"ORD{x:07d}")
items["order_item_id"] = items["order_item_id"].map(lambda x: f"OI{x:08d}")
orders.loc[orders.order_status == "Cancelled", ["ship_date", "delivery_date"]] = pd.NaT

# ----------------------------------------------------------------- RETURNS
RET_RATE = {"Electronics": .07, "Fashion": .18, "Home & Kitchen": .05, "Beauty & Personal Care": .06,
            "Grocery & Gourmet": .02, "Sports & Fitness": .08, "Books & Stationery": .03}
REASONS = {"Fashion": ["Size/Fit Issue", "Not as Described", "Quality Issue", "Changed Mind"],
           "Electronics": ["Defective Product", "Not as Described", "Changed Mind", "Wrong Item Delivered"]}
DEFAULT_R = ["Quality Issue", "Not as Described", "Changed Mind", "Damaged in Transit"]
m = (items.merge(orders[["order_id", "order_status", "delivery_date"]], on="order_id")
          .merge(products[["product_id", "category"]], on="product_id"))
m = m[m.order_status == "Delivered"]
p = m.category.map(RET_RATE) * (1 + m.discount_pct / 100)
r = m[rng.random(len(m)) < p.values].copy()
returns = pd.DataFrame({
    "return_id": [f"R{i:06d}" for i in range(1, len(r) + 1)],
    "order_item_id": r.order_item_id.values,
    "return_date": (r.delivery_date + pd.to_timedelta(rng.integers(2, 15, len(r)), unit="D")).values,
    "return_reason": [rng.choice(REASONS.get(c, DEFAULT_R)) for c in r.category],
    "refund_pct": rng.choice([1, 1, 1, .9, .8], len(r)),
})
returns = returns[returns.return_date <= END].reset_index(drop=True)
returns["return_id"] = [f"R{i:06d}" for i in range(1, len(returns) + 1)]

# --------------------------------------------------------- MARKETING SPEND
newc = (customers.assign(month=customers.signup_date.dt.to_period("M").dt.to_timestamp())
        .groupby(["month", "acquisition_channel"]).size())
CAC = {"Organic Search": 180, "Paid Search": 720, "Social Media": 610, "Referral": 260, "Email Marketing": 150, "Affiliate": 540}
FIXED = {"Organic Search": 40000, "Paid Search": 120000, "Social Media": 90000, "Referral": 15000, "Email Marketing": 25000, "Affiliate": 30000}
rows = []
for mth in pd.date_range(START, END, freq="MS"):
    for ch in CH:
        n = newc.get((mth, ch), 0)
        spend = FIXED[ch] * (1 + .35 * (mth.month in (10, 11))) + n * CAC[ch] * rng.uniform(.75, 1.25)
        rows.append((mth, ch, round(spend, -2)))
spend = pd.DataFrame(rows, columns=["month_start", "channel", "marketing_spend"])

# ------------------------------------------------ INJECT RAW DATA QUALITY ISSUES
cust_raw = customers.copy()
cust_raw["age"] = cust_raw["age"].astype(float)
cust_raw.loc[cust_raw.sample(frac=.04, random_state=1).index, "age"] = np.nan
cust_raw.loc[cust_raw.sample(8, random_state=2).index, "age"] = [150, 0, -5, 999, 120, 1, 200, 17]
for i in cust_raw.sample(frac=.05, random_state=4).index:             # inconsistent city casing/whitespace
    v = cust_raw.at[i, "city"]
    cust_raw.at[i, "city"] = [v.upper(), v.lower(), f" {v} "][int(rng.integers(0, 3))]
cust_raw.loc[cust_raw.sample(frac=.02, random_state=5).index, "gender"] = np.nan
ord_raw = orders.copy()
ord_raw.loc[ord_raw.sample(frac=.025, random_state=6).index, "payment_method"] = np.nan
bad = ord_raw[ord_raw.order_status == "Delivered"].sample(25, random_state=7).index
ord_raw.loc[bad, "delivery_date"] = ord_raw.loc[bad, "order_date"] - pd.Timedelta(days=2)   # impossible dates
ord_raw = pd.concat([ord_raw, ord_raw.sample(frac=.01, random_state=8)], ignore_index=True)  # duplicate rows
items_raw = items.copy()
items_raw.loc[items_raw.sample(12, random_state=9).index, "quantity"] = -1                  # invalid qty
items_raw = pd.concat([items_raw, items_raw.sample(30, random_state=10)], ignore_index=True)

os.makedirs(OUT, exist_ok=True)
for name, df in dict(customers=cust_raw, products=products, orders=ord_raw, order_items=items_raw,
                     returns=returns, marketing_spend=spend).items():
    df.to_csv(os.path.join(OUT, f"{name}.csv"), index=False)
    print(f"{name:16s}{len(df):>9,d} rows")
