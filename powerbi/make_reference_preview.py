"""Renders a REFERENCE layout of Page 1 (Executive Summary) from the real data, so the target design is visible
before building in Power BI Desktop. This is a matplotlib mock-up, NOT a Power BI screenshot."""
import sys; sys.path.insert(0, "../python_analytics")
import matplotlib.pyplot as plt, matplotlib.ticker as mt, numpy as np
from matplotlib.patches import FancyBboxPatch
from utils import *
f = build_fact(); y = f[f.order_year == 2025]; p = f[f.order_year == 2024]
fig = plt.figure(figsize=(16, 9), facecolor="#F4F6F9")
fig.text(.03, .95, "KartNova | Executive Summary  (reference layout - FY 2025)", fontsize=18, fontweight="bold", color="#1F4E79")
fig.text(.03, .915, "Slicers: Year · Region · Category · Channel        |   Data through 31 Dec 2025", fontsize=10, color="#6C757D")
cards = [("Net Revenue", f"₹{y.net_revenue.sum()/1e7:.1f} Cr", y.net_revenue.sum()/p.net_revenue.sum()-1),
         ("Gross Margin %", f"{y.gross_profit.sum()/y.kept_revenue.sum():.1%}", None),
         ("Orders", f"{y.order_id.nunique():,}", y.order_id.nunique()/p.order_id.nunique()-1),
         ("AOV", f"₹{y.net_revenue.sum()/y.order_id.nunique():,.0f}", None),
         ("Active Customers", f"{y.customer_id.nunique():,}", y.customer_id.nunique()/p.customer_id.nunique()-1),
         ("Return Rate %", f"{y.is_returned.mean():.1%}", None)]
for i, (t, v, g) in enumerate(cards):
    ax = fig.add_axes([.03 + i * .16, .78, .15, .11]); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02", fc="white", ec="#E3E8EF", transform=ax.transAxes))
    ax.text(.08, .72, t, fontsize=10, color="#6C757D"); ax.text(.08, .30, v, fontsize=22, fontweight="bold", color="#1F4E79")
    if g is not None: ax.text(.62, .72, f"{'▲' if g>=0 else '▼'} {g:+.0%} YoY", fontsize=9, color="#2E7D32" if g >= 0 else "#C62828")
m = f.groupby("order_month").net_revenue.sum()
a1 = fig.add_axes([.04, .42, .55, .30]); a1.bar(m.index, m.values, width=22, color=PALETTE[1], alpha=.6); a1.plot(m.index, m.rolling(3).mean(), color=PALETTE[0], lw=2.5)
a1.yaxis.set_major_formatter(mt.FuncFormatter(inr_cr)); a1.set_title("Monthly Net Revenue + Rolling 3M Avg", loc="left")
c = f.groupby("category").net_revenue.sum().sort_values(); a2 = fig.add_axes([.69, .42, .28, .30]); a2.barh(c.index, c.values, color=PALETTE[0]); a2.xaxis.set_major_formatter(mt.FuncFormatter(inr_cr)); a2.set_title("Net Revenue by Category", loc="left"); a2.tick_params(labelsize=8)
r = f.groupby("region").net_revenue.sum().sort_values(ascending=False); a3 = fig.add_axes([.04, .06, .27, .28]); a3.bar(r.index, r.values, color=PALETTE[2]); a3.yaxis.set_major_formatter(mt.FuncFormatter(inr_cr)); a3.set_title("Revenue by Region", loc="left"); a3.tick_params(labelsize=8)
g = f.groupby("category").apply(lambda d: d.gross_profit.sum()/d.kept_revenue.sum()*100, include_groups=False).sort_values(); a4 = fig.add_axes([.38, .06, .27, .28]); a4.barh(g.index, g.values, color=[PALETTE[3] if v < 30 else PALETTE[4] for v in g.values]); a4.set_title("Gross Margin % by Category", loc="left"); a4.tick_params(labelsize=8)
q = f.groupby(f.order_date.dt.month).net_revenue.sum(); a5 = fig.add_axes([.72, .06, .25, .28]); a5.plot(q.index, q.values / q.mean(), marker="o", color=PALETTE[0]); a5.axhline(1, color="k", ls="--", lw=1); a5.set_title("Seasonality Index (festive peak Oct–Nov)", loc="left"); a5.set_xticks(range(1, 13))
fig.savefig("reference_dashboard_preview.png", dpi=110, facecolor=fig.get_facecolor())
