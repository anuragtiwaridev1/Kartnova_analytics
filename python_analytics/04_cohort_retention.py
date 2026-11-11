"""
04 - COHORT RETENTION ANALYSIS
==============================
WHY: Aggregate revenue growth can hide a leaky bucket. Cohort analysis groups customers by first-purchase
month and tracks the % who come back in month 1, 2, 3...  It is the cleanest read on product-market fit
and on whether newer cohorts are better or worse than older ones.
HOW IT HELPS: Retention curves by acquisition channel tell marketing where to spend (a cheap channel with
poor retention can be more expensive than a pricey channel with loyal customers).
"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from utils import *
set_style(); f = build_fact()
o = f.drop_duplicates("order_id")[["order_id", "customer_id", "order_date", "acquisition_channel"]].copy()
o["order_m"] = o.order_date.dt.to_period("M")
first = o.groupby("customer_id").order_m.min().rename("cohort")
o = o.join(first, on="customer_id"); o["age_m"] = (o.order_m - o.cohort).apply(lambda x: x.n)
cohort = o.groupby(["cohort", "age_m"]).customer_id.nunique().unstack(fill_value=0)
size = cohort[0]; ret = cohort.div(size, axis=0) * 100
# right-censor: blank out cells that lie beyond the data window
last = pd.Period("2025-12", "M")
for c in ret.index: ret.loc[c, [a for a in ret.columns if c + a > last]] = np.nan
ret = ret[ret.index >= "2023-01"]; ret_plot = ret.loc[:, :12]
fig, ax = plt.subplots(figsize=(13, 9)); sns.heatmap(ret_plot, annot=True, fmt=".0f", cmap="YlGnBu", cbar_kws={"label": "% of cohort active"}, ax=ax, annot_kws={"size": 7})
ax.set_yticklabels([str(i) for i in ret_plot.index], fontsize=7); ax.set_title("Monthly Cohort Retention (% of customers purchasing in month N after first order)"); ax.set_xlabel("Months since first order"); ax.set_ylabel("Acquisition cohort")
savefig("04_cohort_retention_heatmap"); save_table(ret.round(1).reset_index().astype({"cohort": str}), "cohort_retention_pct")

# weighted average retention curve by channel (cohorts with >= 6 months of data for fair comparison)
ch = o.groupby(["acquisition_channel", "cohort", "age_m"]).customer_id.nunique().reset_index(name="active")
sz = ch[ch.age_m == 0][["acquisition_channel", "cohort", "active"]].rename(columns={"active": "size"})
ch = ch.merge(sz, on=["acquisition_channel", "cohort"]); ch = ch[(ch.cohort + 6 <= last) & (ch.age_m <= 6)]
curve = ch.groupby(["acquisition_channel", "age_m"]).apply(lambda g: g.active.sum() / g["size"].sum() * 100, include_groups=False).unstack(0)
fig, ax = plt.subplots(figsize=(9, 5)); curve.loc[1:].plot(ax=ax, marker="o", lw=2); ax.set_title("Retention curve by acquisition channel (months 1–6)"); ax.set_ylabel("% of cohort active"); ax.set_xlabel("Months since first order")
savefig("04_retention_by_channel"); save_table(curve.round(2).reset_index(), "retention_by_channel")
print("Avg M1/M3/M6 retention (all cohorts, size-weighted):")
for a in (1, 3, 6):
    v = cohort[a][ret[a].notna()].sum() / size[ret[a].notna()].sum() * 100; print(f"  month {a}: {v:.1f}%")
print("\nRetention by channel at month 1/3/6:\n", curve.loc[[1, 3, 6]].round(1).T.to_string())
