"""
02 - EXECUTIVE KPIs & EXPLORATORY ANALYSIS
==========================================
WHY: Leadership needs a single trustworthy view of "how is the business doing and where is the money
made / lost". This script defines the KPI layer (revenue, margin, AOV, return & cancel rate, growth),
and drills into category, region, payment/device and delivery performance.

HOW IT HELPS: surfaces the high-margin vs. high-return categories, seasonality to plan inventory and
marketing, and operational drags (late delivery regions, COD cancellations).
"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
import matplotlib.ticker as mt
from utils import *
set_style()
d = load_clean()
f = build_fact(d)                                       # delivered lines only
allo = d["orders"]

# ------------------------------------------------------------ 1. KPI scorecard by year
def kpis(g):
    orders = g.order_id.nunique()
    return pd.Series({
        "net_revenue": g.net_revenue.sum(), "refunds": g.refund_amt.sum(), "kept_revenue": g.kept_revenue.sum(),
        "gross_profit": g.gross_profit.sum(), "gross_margin_pct": g.gross_profit.sum() / g.kept_revenue.sum() * 100,
        "orders": orders, "customers": g.customer_id.nunique(), "aov": g.net_revenue.sum() / orders,
        "units": g.quantity.sum(), "avg_discount_pct": g.discount_amt.sum() / g.gross_sales.sum() * 100,
        "return_rate_pct": g.is_returned.mean() * 100})
kp = f.groupby("order_year").apply(kpis, include_groups=False)
cancel = allo.assign(y=allo.order_date.dt.year).groupby("y").apply(lambda g: (g.order_status == "Cancelled").mean() * 100, include_groups=False)
kp["cancel_rate_pct"] = cancel
kp["revenue_yoy_pct"] = kp.net_revenue.pct_change() * 100
print(kp.round(1).T.to_string()); save_table(kp.round(2).reset_index(), "kpi_scorecard_by_year")

# ------------------------------------------------------------ 2. Monthly trend + seasonality
m = f.groupby("order_month").agg(revenue=("net_revenue", "sum"), profit=("gross_profit", "sum"), orders=("order_id", "nunique")).reset_index()
m["revenue_3m_ma"] = m.revenue.rolling(3).mean()
m["mom_pct"] = m.revenue.pct_change() * 100
fig, ax = plt.subplots(figsize=(11, 4.5))
ax.bar(m.order_month, m.revenue, width=22, color=PALETTE[1], alpha=.55, label="Monthly net revenue")
ax.plot(m.order_month, m.revenue_3m_ma, color=PALETTE[0], lw=2.5, label="3-month moving avg")
for yr in (2023, 2024, 2025):
    for mo in (10, 11):
        ax.axvspan(pd.Timestamp(yr, mo, 1), pd.Timestamp(yr, mo, 28), color=PALETTE[2], alpha=.12)
ax.yaxis.set_major_formatter(mt.FuncFormatter(inr_cr)); ax.set_title("Monthly Net Revenue — growth with festive (Oct–Nov) peaks shaded"); ax.legend()
savefig("02_monthly_revenue_trend")

seas = f.assign(mo=f.order_date.dt.month, yr=f.order_year).groupby(["yr", "mo"]).net_revenue.sum().unstack(0)
seas_idx = (seas / seas.mean()).mean(axis=1)           # average share vs. year mean
fig, ax = plt.subplots(figsize=(9, 4)); sns.barplot(x=seas_idx.index, y=seas_idx.values, color=PALETTE[1], ax=ax)
ax.axhline(1, color="k", ls="--", lw=1); ax.set_xlabel("Month"); ax.set_ylabel("Seasonality index"); ax.set_title("Seasonality Index (1.0 = average month)")
savefig("02_seasonality_index"); save_table(seas_idx.rename("index").reset_index(), "seasonality_index")

# ------------------------------------------------------------ 3. Category economics
cat = f.groupby("category").agg(revenue=("net_revenue", "sum"), profit=("gross_profit", "sum"), units=("quantity", "sum"),
                                 return_rate=("is_returned", "mean"), avg_disc=("discount_pct", "mean")).reset_index()
cat["margin_pct"] = cat.profit / (f.groupby("category").kept_revenue.sum().values) * 100
cat["rev_share_pct"] = cat.revenue / cat.revenue.sum() * 100; cat["return_rate"] *= 100
cat = cat.sort_values("revenue", ascending=False); print(cat.round(1).to_string(index=False)); save_table(cat.round(2), "category_economics")
fig, ax = plt.subplots(figsize=(8.5, 5.5))
sc = ax.scatter(cat.margin_pct, cat.return_rate, s=cat.revenue / cat.revenue.max() * 2200, c=PALETTE[:len(cat)], alpha=.75, edgecolor="w")
for r in cat.itertuples(): ax.annotate(r.category, (r.margin_pct, r.return_rate), ha="center", va="center", fontsize=8, fontweight="bold")
ax.set_xlabel("Gross margin % (after returns)"); ax.set_ylabel("Return rate % (line items)"); ax.set_title("Category Portfolio: Margin vs Returns (bubble = revenue)")
ax.margins(.18); savefig("02_category_margin_vs_returns")

# ------------------------------------------------------------ 4. Pareto (80/20) on products
pp = f.groupby("product_id").net_revenue.sum().sort_values(ascending=False).reset_index()
pp["cum_pct"] = pp.net_revenue.cumsum() / pp.net_revenue.sum() * 100; pp["sku_pct"] = (np.arange(len(pp)) + 1) / len(pp) * 100
sku80 = pp.loc[pp.cum_pct >= 80, "sku_pct"].iloc[0]
fig, ax = plt.subplots(figsize=(8, 4.5)); ax.plot(pp.sku_pct, pp.cum_pct, color=PALETTE[0], lw=2.5)
ax.axhline(80, color=PALETTE[3], ls="--"); ax.axvline(sku80, color=PALETTE[3], ls="--")
ax.set_title(f"Pareto: {sku80:.0f}% of SKUs generate 80% of revenue"); ax.set_xlabel("% of SKUs"); ax.set_ylabel("Cumulative % revenue")
savefig("02_pareto_products"); print(f"\nPareto: {sku80:.1f}% of SKUs -> 80% revenue")

# ------------------------------------------------------------ 5. Regional + operations
reg = f.groupby("region").agg(revenue=("net_revenue", "sum"), customers=("customer_id", "nunique"), orders=("order_id", "nunique"),
                               avg_delivery_days=("delivery_days", "mean"), return_rate=("is_returned", "mean")).reset_index()
reg["rev_per_customer"] = reg.revenue / reg.customers; reg["return_rate"] *= 100
reg = reg.sort_values("revenue", ascending=False); print(reg.round(1).to_string(index=False)); save_table(reg.round(2), "region_performance")
canc = allo.assign(cod=allo.payment_method.eq("Cash on Delivery")).groupby("payment_method").apply(lambda g: (g.order_status == "Cancelled").mean() * 100, include_groups=False).sort_values()
fig, axs = plt.subplots(1, 2, figsize=(13, 4.5))
sns.barplot(data=reg, x="avg_delivery_days", y="region", color=PALETTE[1], ax=axs[0]); axs[0].set_title("Avg delivery days by region")
sns.barplot(x=canc.values, y=canc.index, color=PALETTE[3], ax=axs[1]); axs[1].set_title("Cancellation rate % by payment method")
savefig("02_operations_delivery_cancellation"); save_table(canc.rename("cancel_rate_pct").round(2).reset_index(), "cancellation_by_payment")

# ------------------------------------------------------------ 6. Channel / device mix
ch = f.groupby("device").agg(revenue=("net_revenue", "sum"), orders=("order_id", "nunique")).assign(aov=lambda x: x.revenue / x.orders)
print("\n", ch.round(0).to_string())
save_table(ch.round(2).reset_index(), "device_performance")
