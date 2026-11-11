"""
07 - MARKET BASKET ANALYSIS (association rules, implemented from scratch)
=========================================================================
WHY: Which products are bought together? That drives cross-sell widgets, bundle offers and store/site layout.
METRICS: support  = P(A and B)           how common the pair is
         confidence = P(B | A)           how reliable "A -> B" is
         lift = confidence / P(B)        >1 means a real affinity beyond popularity
(No mlxtend dependency: pairwise counting is exact and fast at this scale.)
"""
import itertools, numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from collections import Counter
from utils import *
set_style(); f = build_fact()

def rules(level, min_count):
    b = f.groupby("order_id")[level].agg(lambda s: sorted(set(s)))
    N = len(b); item = Counter(i for l in b for i in l); pair = Counter(p for l in b for p in itertools.combinations(l, 2))
    rows = []
    for (a, c), n in pair.items():
        if n < min_count: continue
        for x, y in ((a, c), (c, a)):
            rows.append(dict(antecedent=x, consequent=y, orders_together=n, support=n / N, confidence=n / item[x], lift=(n / item[x]) / (item[y] / N)))
    return pd.DataFrame(rows).sort_values("lift", ascending=False), N

sub, N = rules("sub_category", 40); print(f"Orders analysed: {N:,} | multi-item rules (sub-category): {len(sub)}")
top = sub[sub.lift > 1.5].head(15); print(top.round(3).to_string(index=False)); save_table(sub.round(4), "basket_rules_subcategory")
fig, ax = plt.subplots(figsize=(10, 6)); t = top.assign(rule=top.antecedent + "  →  " + top.consequent).iloc[::-1]
ax.barh(t.rule, t.lift, color=PALETTE[1]); ax.axvline(1, color="k", ls="--"); ax.set_xlabel("Lift"); ax.set_title("Strongest cross-sell affinities (sub-category level)")
for i, (l, c) in enumerate(zip(t.lift, t.confidence)): ax.text(l + .05, i, f"conf {c:.0%}", va="center", fontsize=8)
savefig("07_basket_top_rules")

prod, _ = rules("product_name", 8); save_table(prod.head(50).round(4), "basket_rules_product_top50")
best = sub[sub.lift > 1.2].sort_values(["antecedent", "lift"], ascending=[True, False]).groupby("antecedent").head(1)
save_table(best.round(4), "cross_sell_recommendations"); print("\nTop product-level pair:\n", prod.head(3).round(3).to_string(index=False))
