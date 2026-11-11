"""
08 - STATISTICAL HYPOTHESIS TESTING & DISCOUNT EFFECTIVENESS
============================================================
WHY: "Looks different" is not evidence. Before recommending a policy change we test whether the difference
is statistically significant AND practically meaningful (effect size + confidence interval).
TESTS: (1) COD vs prepaid cancellation (chi-square / 2-prop CI)   (2) Discount depth vs return rate
       (3) Delivery time across regions (Kruskal-Wallis)          (4) 12-m LTV across channels (Kruskal)
       (5) Festive vs non-festive AOV (bootstrap CI)              (6) Discount depth vs units & margin
Non-parametric tests are used where distributions are heavily skewed (revenue, days).
"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from scipy import stats
from utils import *
set_style(); d = load_clean(); f = build_fact(d); o = d["orders"]; out = []
def rec(test, h0, stat, p, effect, verdict): out.append(dict(test=test, null_hypothesis=h0, statistic=round(stat, 3), p_value=float(f"{p:.3g}"), effect=effect, conclusion=verdict))
sig = lambda p: "REJECT H0 (significant)" if p < .05 else "Fail to reject H0"

# 1 COD vs prepaid cancellation
o["cod"] = o.payment_method.eq("Cash on Delivery"); o["canc"] = o.order_status.eq("Cancelled")
ct = pd.crosstab(o.cod, o.canc); chi, p, *_ = stats.chi2_contingency(ct)
p1, p2 = o[o.cod].canc.mean(), o[~o.cod].canc.mean(); n1, n2 = o.cod.sum(), (~o.cod).sum()
se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2); ci = (p1 - p2 + np.array([-1.96, 1.96]) * se) * 100
rec("COD vs prepaid cancellation", "Cancellation rate equal", chi, p, f"COD {p1:.1%} vs {p2:.1%}; diff 95% CI [{ci[0]:.1f}, {ci[1]:.1f}] pp", sig(p))

# 2 Discount band vs return rate
f["disc_band"] = pd.cut(f.discount_pct, [-1, 0, 10, 20, 100], labels=["0%", "1-10%", "11-20%", ">20%"])
ct = pd.crosstab(f.disc_band, f.is_returned); chi, p, *_ = stats.chi2_contingency(ct)
rr = f.groupby("disc_band", observed=True).is_returned.mean() * 100
rec("Discount band vs return rate", "Return rate independent of discount band", chi, p, "return % by band: " + ", ".join(f"{k}={v:.1f}" for k, v in rr.items()), sig(p))

# 3 Delivery days across regions
dd = o[o.order_status == "Delivered"].merge(d["customers"][["customer_id", "region"]], on="customer_id")
grp = [g.delivery_days.values for _, g in dd.groupby("region")]; H, p = stats.kruskal(*grp)
med = dd.groupby("region").delivery_days.median()
rec("Delivery days across regions", "Same distribution of delivery days", H, p, "median days: " + ", ".join(f"{k}={v:.0f}" for k, v in med.items()), sig(p))

# 4 12-month LTV across channels
cust = d["customers"]; m = cust[cust.signup_date <= "2024-12-31"][["customer_id", "acquisition_channel", "signup_date"]]
x = f.drop(columns="signup_date").merge(m[["customer_id", "signup_date"]], on="customer_id"); x = x[x.order_date <= x.signup_date + pd.Timedelta(days=365)]
m = m.join(x.groupby("customer_id").gross_profit.sum().rename("gp12"), on="customer_id").fillna({"gp12": 0})
H, p = stats.kruskal(*[g.gp12.values for _, g in m.groupby("acquisition_channel")])
mm = m.groupby("acquisition_channel").gp12.median().sort_values(ascending=False)
rec("12-m gross profit per customer by channel", "Same LTV distribution across channels", H, p, "median ₹: " + ", ".join(f"{k.split()[0]}={v:,.0f}" for k, v in mm.items()), sig(p))

# 5 Festive vs non-festive AOV (bootstrap)
ao = f.groupby(["order_id", "order_date"]).net_revenue.sum().reset_index(); ao["fest"] = ao.order_date.dt.month.isin([10, 11])
a, b = ao[ao.fest].net_revenue.values, ao[~ao.fest].net_revenue.values; rng = np.random.default_rng(1)
boot = np.array([rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(2000)]); lo, hi = np.percentile(boot, [2.5, 97.5])
U, p = stats.mannwhitneyu(a, b); rec("Festive vs non-festive AOV", "AOV equal", U, p, f"ΔAOV ₹{a.mean() - b.mean():,.0f}, bootstrap 95% CI [₹{lo:,.0f}, ₹{hi:,.0f}]", sig(p))

# 6 Discount depth vs units & margin (within-category to avoid mix bias)
r, p = stats.spearmanr(f.discount_pct, f.quantity); rec("Discount % vs units per line (Spearman)", "No monotonic relation", r, p, f"rho={r:.3f}", sig(p))
band = f.groupby("disc_band", observed=True).agg(lines=("order_item_id", "count"), avg_qty=("quantity", "mean"), return_pct=("is_returned", lambda s: s.mean() * 100),
                                                   revenue=("kept_revenue", "sum"), profit=("gross_profit", "sum")); band["margin_pct"] = band.profit / band.revenue * 100
print(band.round(2).to_string()); save_table(band.round(3).reset_index(), "discount_band_economics")

res = pd.DataFrame(out); save_table(res, "hypothesis_tests"); pd.set_option("display.max_colwidth", 90); print("\n", res.to_string(index=False))
fig, axs = plt.subplots(1, 3, figsize=(15, 4.3))
sns.barplot(data=band.reset_index(), x="disc_band", y="margin_pct", color=PALETTE[0], ax=axs[0]); axs[0].set_title("Gross margin % by discount band")
sns.barplot(data=band.reset_index(), x="disc_band", y="return_pct", color=PALETTE[3], ax=axs[1]); axs[1].set_title("Return rate % by discount band")
sns.barplot(data=band.reset_index(), x="disc_band", y="avg_qty", color=PALETTE[2], ax=axs[2]); axs[2].set_title("Avg units per line by discount band"); axs[2].set_ylim(1, None)
savefig("08_discount_effectiveness")

# 7 Discount-cap scenario (what-if). Same logic as DAX measure [Profit Uplift @ Cap] and used in Power BI.
# Assumption: zero volume loss - justified by test #6 (discount depth has no relationship with units per line).
rows = []
for cap in (0, 5, 10, 15, 20, 30):
    uplift = (f.gross_sales * (1 - f.discount_pct.clip(upper=cap) / 100) - f.net_revenue).sum()
    rows.append(dict(discount_cap_pct=cap, profit_uplift_inr=round(uplift), pct_of_gross_profit=round(uplift / f.gross_profit.sum() * 100, 2)))
scen = pd.DataFrame(rows); print("\nDiscount-cap scenarios (no volume loss assumed)\n", scen.to_string(index=False)); save_table(scen, "discount_cap_scenarios")
