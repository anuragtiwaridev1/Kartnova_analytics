"""
05 - CUSTOMER CHURN PREDICTION (supervised ML, leakage-safe)
============================================================
WHY: Acquiring a customer costs 5-7x more than retaining one. If we can rank customers by their probability
of going silent we can spend the retention budget (vouchers, outreach) only where it changes behaviour.

DESIGN (what makes this production-grade rather than a toy):
  * Temporal split: features are built ONLY from data on/before CUTOFF (2025-06-30);
    the label is "no delivered order in the following 180 days". No future information leaks into features.
  * Baseline (Logistic Regression) vs. challenger (Gradient Boosting) - complexity must earn its place.
  * Evaluated with ROC-AUC, PR-AUC, Brier score, decile lift & expected-revenue-at-risk, not just accuracy.
"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import make_pipeline
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, roc_curve, precision_recall_curve
from utils import *
set_style()
CUTOFF, HORIZON_END = pd.Timestamp("2025-06-30"), pd.Timestamp("2025-12-31")
d = load_clean(); f_all = build_fact(d, delivered_only=True)
hist = f_all[f_all.order_date <= CUTOFF]; fut = f_all[(f_all.order_date > CUTOFF) & (f_all.order_date <= HORIZON_END)]

# ---------------- feature engineering (history only)
g = hist.groupby("customer_id")
orders_h = hist.drop_duplicates("order_id").sort_values(["customer_id", "order_date"])
gap = orders_h.groupby("customer_id").order_date.apply(lambda s: s.diff().dt.days.mean()).rename("avg_days_between_orders")
X = pd.DataFrame({
    "recency_days": (CUTOFF - g.order_date.max()).dt.days,
    "frequency": g.order_id.nunique(),
    "monetary": g.kept_revenue.sum(),
    "avg_order_value": g.net_revenue.sum() / g.order_id.nunique(),
    "tenure_days": (CUTOFF - g.order_date.min()).dt.days,
    "avg_discount_pct": g.discount_pct.mean(),
    "return_rate": g.is_returned.mean(),
    "avg_delivery_days": g.delivery_days.mean(),
    "n_categories": g.category.nunique(),
    "electronics_share": hist.assign(e=hist.category.eq("Electronics") * hist.net_revenue).groupby("customer_id").e.sum() / g.net_revenue.sum(),
    "orders_last_90d": hist[hist.order_date > CUTOFF - pd.Timedelta(days=90)].groupby("customer_id").order_id.nunique(),
    "cod_share": hist.drop_duplicates("order_id").assign(c=lambda x: x.payment_method.eq("Cash on Delivery")).groupby("customer_id").c.mean(),
    "app_share": hist.drop_duplicates("order_id").assign(c=lambda x: x.device.eq("Mobile App")).groupby("customer_id").c.mean(),
}).join(gap)
X["orders_last_90d"] = X.orders_last_90d.fillna(0)
X["avg_days_between_orders"] = X.avg_days_between_orders.fillna(X.tenure_days.clip(lower=30))   # single-order customers
X["recency_to_gap_ratio"] = X.recency_days / X.avg_days_between_orders.clip(lower=1)
cu = d["customers"].set_index("customer_id")
X = X.join(pd.get_dummies(cu.loc[X.index, ["acquisition_channel", "region"]], dtype=int)).join(cu.loc[X.index, "age"])
y = pd.Series((~X.index.isin(fut.customer_id.unique())).astype(int), index=X.index)              # 1 = churned
print(f"Customers modelled: {len(X):,} | churn rate over next 180d: {y.mean():.1%}")

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=.25, stratify=y, random_state=42)
models = {"Logistic Regression (baseline)": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=.5)),
          "Gradient Boosting": HistGradientBoostingClassifier(max_depth=4, learning_rate=.05, max_iter=250, l2_regularization=1.0, random_state=42)}
res, prob = [], {}
for n, m in models.items():
    m.fit(Xtr, ytr); p = m.predict_proba(Xte)[:, 1]; prob[n] = p
    res.append(dict(model=n, roc_auc=roc_auc_score(yte, p), pr_auc=average_precision_score(yte, p), brier=brier_score_loss(yte, p)))
res = pd.DataFrame(res).round(4); print(res.to_string(index=False)); save_table(res, "churn_model_metrics")
best = "Gradient Boosting" if res.roc_auc[1] >= res.roc_auc[0] else "Logistic Regression (baseline)"; pbest = prob[best]; print("Selected:", best)

# ---------------- decile lift & revenue at risk
te = pd.DataFrame({"churn": yte.values, "p": pbest, "monetary": Xte.monetary.values}, index=Xte.index)
te["decile"] = pd.qcut(te.p.rank(method="first", ascending=False), 10, labels=range(1, 11))
lift = te.groupby("decile", observed=True).agg(customers=("churn", "size"), actual_churn=("churn", "mean"), avg_p=("p", "mean"), hist_revenue=("monetary", "sum"))
lift["lift"] = lift.actual_churn / te.churn.mean(); lift["cum_capture_pct"] = lift.customers.mul(lift.actual_churn).cumsum() / te.churn.sum() * 100
print(lift.round(3).to_string()); save_table(lift.round(4).reset_index(), "churn_decile_lift")

# ---------------- permutation importance
pi = permutation_importance(models[best], Xte, yte, scoring="roc_auc", n_repeats=8, random_state=42)
imp = pd.Series(pi.importances_mean, index=Xte.columns).sort_values(ascending=False).head(12); print("\nTop drivers (ΔAUC when shuffled):\n", imp.round(4).to_string()); save_table(imp.rename("delta_auc").reset_index(), "churn_feature_importance")

fig, axs = plt.subplots(1, 3, figsize=(17, 4.8))
for n, p in prob.items():
    fpr, tpr, _ = roc_curve(yte, p); axs[0].plot(fpr, tpr, lw=2, label=f"{n.split(' (')[0]} (AUC {roc_auc_score(yte, p):.3f})")
axs[0].plot([0, 1], [0, 1], "k--", lw=1); axs[0].set_title("ROC curve"); axs[0].legend(fontsize=8); axs[0].set_xlabel("FPR"); axs[0].set_ylabel("TPR")
imp.iloc[::-1].plot.barh(ax=axs[1], color=PALETTE[0]); axs[1].set_title("Permutation importance (ΔAUC)")
axs[2].bar(lift.index.astype(int), lift.lift, color=PALETTE[1]); axs[2].axhline(1, color="k", ls="--"); axs[2].set_title("Lift by risk decile (1 = highest predicted risk)"); axs[2].set_xlabel("Decile")
savefig("05_churn_model_evaluation")

# ---------------- score everyone & prioritise by value-at-risk
Xall_p = models[best].predict_proba(X)[:, 1]
scored = pd.DataFrame({"customer_id": X.index, "churn_probability": Xall_p.round(4), "historical_value": X.monetary.round(0), "recency_days": X.recency_days})
scored["revenue_at_risk"] = (scored.churn_probability * scored.historical_value).round(0)
scored["priority"] = pd.cut(scored.churn_probability, [0, .5, .75, 1], labels=["Low", "Medium", "High"], include_lowest=True)
scored = scored.sort_values("revenue_at_risk", ascending=False); save_table(scored, "churn_scored_customers")
print("\nPriority mix:\n", scored.groupby("priority", observed=True).agg(customers=("customer_id", "count"), revenue_at_risk=("revenue_at_risk", "sum")).round(0).to_string())
