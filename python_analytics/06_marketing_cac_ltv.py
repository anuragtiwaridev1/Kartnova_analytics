"""
06 - MARKETING EFFICIENCY: CAC, 12-MONTH LTV, LTV:CAC & PAYBACK BY CHANNEL
=========================================================================
WHY: "Which channel is cheapest?" is the wrong question. The right one is "which channel returns the most
profit per rupee spent?" - that needs Customer Acquisition Cost (from spend) joined with customer lifetime
value (from behaviour). A channel with low CAC but short-lived customers can destroy value.
HOW IT HELPS: Directly informs budget re-allocation between channels.
"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from utils import *
set_style(); d = load_clean(); f = build_fact(d)
cust, spend = d["customers"], d["marketing_spend"]

# CAC per channel (all-time and trend)
new_c = cust.groupby(["acquisition_channel"]).size().rename("new_customers")
sp = spend.groupby("channel").marketing_spend.sum()
cac = pd.concat([new_c, sp], axis=1); cac["cac"] = cac.marketing_spend / cac.new_customers

# 12-month value per customer: only customers with a full 12-month window (signup <= 2024-12-31)
mature = cust[cust.signup_date <= "2024-12-31"][["customer_id", "acquisition_channel", "signup_date"]]
x = f.merge(mature[["customer_id", "signup_date"]].rename(columns={"signup_date": "sd"}), on="customer_id")
x = x[x.order_date <= x.sd + pd.Timedelta(days=365)]
v = x.groupby("customer_id").agg(gp12=("gross_profit", "sum"), rev12=("kept_revenue", "sum"), orders12=("order_id", "nunique"))
mature = mature.join(v, on="customer_id").fillna({"gp12": 0, "rev12": 0, "orders12": 0})
ltv = mature.groupby("acquisition_channel").agg(mature_customers=("customer_id", "count"), ltv12_revenue=("rev12", "mean"), ltv12_gross_profit=("gp12", "mean"),
                                                  orders_12m=("orders12", "mean"), pct_repeat=("orders12", lambda s: (s >= 2).mean() * 100))
out = cac.join(ltv); out["ltv_to_cac"] = out.ltv12_gross_profit / out.cac
out["payback_months_approx"] = out.cac / (out.ltv12_gross_profit / 12)
out.index.name = "acquisition_channel"; out = out.sort_values("ltv_to_cac", ascending=False).round(2); print(out.to_string()); save_table(out.reset_index(), "channel_cac_ltv")

fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
o = out.reset_index().sort_values("ltv_to_cac")
axs[0].barh(o.acquisition_channel, o.ltv_to_cac, color=[PALETTE[3] if v < 3 else PALETTE[0] for v in o.ltv_to_cac]); axs[0].axvline(3, color="k", ls="--"); axs[0].set_title("12-month LTV : CAC (3x = health benchmark)")
sc = axs[1].scatter(out.cac, out.ltv12_gross_profit, s=out.new_customers / 4, color=PALETTE[1], alpha=.7)
for n, r in out.iterrows(): axs[1].annotate(n, (r.cac, r.ltv12_gross_profit), fontsize=8, xytext=(5, 5), textcoords="offset points")
axs[1].set_xlabel("CAC (₹)"); axs[1].set_ylabel("12-month gross profit per customer (₹)"); axs[1].set_title("Channel quadrant (bubble = customers acquired)")
savefig("06_channel_ltv_cac")

mt = spend.assign(month=spend.month_start).groupby("month").marketing_spend.sum().to_frame().join(cust.assign(month=cust.signup_date.dt.to_period("M").dt.to_timestamp()).groupby("month").size().rename("new"))
mt["blended_cac"] = mt.marketing_spend / mt.new; save_table(mt.round(1).reset_index(), "blended_cac_monthly")
fig, ax = plt.subplots(figsize=(10, 4)); ax.plot(mt.index, mt.blended_cac, color=PALETTE[0], lw=2); ax.set_title("Blended CAC by month (₹) - fixed spend amortised as volume scales"); savefig("06_blended_cac_trend")
print("\nBlended CAC 2023 vs 2025: ₹%.0f -> ₹%.0f" % (mt.loc["2023"].marketing_spend.sum() / mt.loc["2023"].new.sum(), mt.loc["2025"].marketing_spend.sum() / mt.loc["2025"].new.sum()))
