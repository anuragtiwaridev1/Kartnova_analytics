"""
03 - RFM SEGMENTATION + K-MEANS CLUSTERING
==========================================
WHY: Not all customers are equal; ~20% typically drive most revenue. RFM (Recency, Frequency, Monetary)
is the industry-standard behavioural lens. We do it two ways:
  (a) rule-based quintile scoring -> business-friendly named segments (Champions, At Risk, ...)
  (b) unsupervised K-Means on log-scaled RFM -> data-driven validation (silhouette-selected k)
HOW IT HELPS: CRM/marketing can target win-back for "At Risk / Can't Lose", loyalty for "Champions",
and stop wasting discounts on "Lost" customers.
"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from utils import *
set_style(); f = build_fact()

rfm = f.groupby("customer_id").agg(last_order=("order_date", "max"), frequency=("order_id", "nunique"),
                                    monetary=("kept_revenue", "sum")).reset_index()
rfm["recency"] = (SNAPSHOT_DATE - rfm.last_order).dt.days
rfm["R"] = pd.qcut(rfm.recency, 5, labels=[5, 4, 3, 2, 1]).astype(int)               # recent = high score
rfm["F"] = pd.qcut(rfm.frequency.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M"] = pd.qcut(rfm.monetary.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

def segment(r):
    if r.R >= 4 and r.F >= 4 and r.M >= 4: return "Champions"
    if r.R >= 3 and r.F >= 4:               return "Loyal Customers"
    if r.R >= 4 and r.F <= 2:               return "New / Promising"
    if r.R >= 3 and r.F >= 3:               return "Potential Loyalists"
    if r.R <= 2 and r.F >= 4 and r.M >= 4:  return "Can't Lose Them"
    if r.R <= 2 and r.F >= 3:               return "At Risk"
    if r.R <= 2 and r.F <= 2 and r.M <= 2:  return "Lost"
    return "Needs Attention"
rfm["segment"] = rfm.apply(segment, axis=1)
seg = rfm.groupby("segment").agg(customers=("customer_id", "count"), revenue=("monetary", "sum"), avg_recency=("recency", "mean"),
                                  avg_freq=("frequency", "mean"), avg_monetary=("monetary", "mean")).reset_index()
seg["cust_pct"] = seg.customers / seg.customers.sum() * 100; seg["rev_pct"] = seg.revenue / seg.revenue.sum() * 100
seg = seg.sort_values("revenue", ascending=False); print(seg.round(1).to_string(index=False)); save_table(seg.round(2), "rfm_segment_summary")

fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
o = seg.sort_values("rev_pct")
axs[0].barh(o.segment, o.cust_pct, color=PALETTE[5], alpha=.5, label="% customers"); axs[0].barh(o.segment, o.rev_pct, color=PALETTE[0], height=.4, label="% revenue")
axs[0].legend(); axs[0].set_title("Customer share vs. revenue share by RFM segment")

# --- K-Means validation on log-scaled RFM
X = StandardScaler().fit_transform(np.log1p(rfm[["recency", "frequency", "monetary"]]))
inertia = []; sil = []
ks = range(3, 9)   # k=2 is a trivial active-vs-lapsed split; k>=3 gives actionable granularity
for k in ks:
    km = KMeans(k, n_init=10, random_state=42).fit(X); inertia.append(km.inertia_); sil.append(silhouette_score(X, km.labels_, sample_size=4000, random_state=42))
best_k = list(ks)[int(np.argmax(sil))]; print(f"\nSilhouette by k: {dict(zip(ks, np.round(sil, 3)))} -> best k = {best_k}")
rfm["cluster"] = KMeans(best_k, n_init=20, random_state=42).fit_predict(X)
cl = rfm.groupby("cluster").agg(customers=("customer_id", "count"), recency=("recency", "mean"), frequency=("frequency", "mean"), monetary=("monetary", "mean")).round(1)
print(cl.to_string()); save_table(cl.reset_index(), "kmeans_cluster_profile")
axs[1].plot(list(ks), sil, marker="o", color=PALETTE[0]); axs[1].axvline(best_k, color=PALETTE[3], ls="--"); axs[1].set_title("K-Means: silhouette score by k"); axs[1].set_xlabel("k")
savefig("03_rfm_segments_and_kmeans")

fig, ax = plt.subplots(figsize=(8, 5.5)); sns.scatterplot(data=rfm, x="frequency", y="monetary", hue="segment", s=18, alpha=.6, ax=ax)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_title("RFM segments in Frequency × Monetary space (log)"); ax.legend(fontsize=7, loc="lower right")
savefig("03_rfm_scatter"); save_table(rfm.drop(columns="last_order"), "rfm_customer_scores")
