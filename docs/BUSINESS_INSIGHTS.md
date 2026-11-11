# Business Insights & Recommendations — KartNova (Jan-2023 → Dec-2025)

> **Context:** Synthetic dataset modelled on an Indian omnichannel e-commerce retailer (9,000 customers, 29,107 orders, 62,700 order lines, ₹26.2 Cr net revenue).
> The data is simulated with realistic dynamics, so the *findings are properties of the simulation*; the **methods, rigour and decision framing are what transfer** to a real business.
> All figures below come from the code in this repo (see `python_analytics/outputs/tables`, `sql/results`).

## Executive summary
KartNova grew net revenue **129% in 2024 and 50% in 2025** (₹3.9 Cr → ₹8.9 Cr → ₹13.4 Cr) at a **stable ~32% gross margin**. Growth is healthy but quality is uneven:
revenue is **concentrated** (top 10% of customers = 49%; 25% of SKUs = 80%), **margin is category-dependent** (Electronics 58% of revenue at 22% margin), **retention is thin** (18.8% buy again within a month, 13.8% at month 6), and **discounting buys no extra volume**.

## Findings → Recommendations

| # | Finding (evidence) | Recommendation | Est. impact |
|---|---|---|---|
| 1 | **Discounts don't drive volume.** Spearman ρ(discount, units per line) = 0.004 (p=0.29). Margin falls from 38.5% (no discount) to 24.4% (11–20% band). >20% discounts raise returns to 12.9% vs ~8.5% (χ² p<0.001) | Cap line discounts at 10% outside festive peaks; A/B test the cap to validate the zero-volume-loss assumption | **+₹83.9 L gross profit (+10.9%)** upper bound at 10% cap |
| 2 | **Electronics: big revenue, thin margin.** 58% of revenue, 22% margin, 39% of profit. Fashion: 14% of revenue, 55% margin, **19% return rate** | Protect Electronics with bundles (Laptop→Accessories lift 13×, 47% conf.) to raise attach margin; cut Fashion returns via size guides (Size/Fit is #1 reason) | Margin mix ↑; each 1pp fewer Fashion returns ≈ ₹3.7 L less refunds*  |
| 3 | **Acquisition spend is mis-allocated.** 12-month LTV:CAC — Referral 12.5×, Organic 11.2×, Email 5.4×, Affiliate 3.7×, Social 3.2×, **Paid Search 2.5×** (payback 4.8 months). Referral/Organic also retain best | Scale referral programme; hold Paid Search to a stricter CAC cap and shift part of its budget (₹60 L spent over 3 years, the largest line of ₹1.6 Cr total) toward referral/email | Higher profit per ₹ of marketing; kills <3× channel |
| 4 | **Customer base is top-heavy.** Champions (17% of customers) = 43% of revenue; "Can't Lose Them" (645 customers, ₹3.7 Cr lifetime) have been silent ~17 months | VIP programme for Champions; personal win-back for Can't-Lose-Them; stop discounting "Lost" (1,297 customers = 1.3% of revenue) | Protect ~₹14 Cr of revenue base |
| 5 | **Churn is predictable.** Logistic model ROC-AUC 0.83 (gradient boosting 0.81 did *not* beat it). Recency dominates. Top 4 risk deciles contain 54% of churners; 3,617 "High" risk customers carry ₹5.8 Cr historical value | Trigger win-back at ~1.5× a customer's usual re-order gap; target by revenue-at-risk, not by probability alone | Focus retention budget on ~half the base |
| 6 | **Retention is the growth ceiling.** M1/M3/M6 = 18.8% / 16.3% / 13.8%; 62% make a 2nd order, on average after ~95 days | Post-purchase journeys at days 30/60/90 (email/app push) | +1pp M1 retention compounds across every cohort |
| 7 | **COD hurts operations.** Cancellation 8.9% COD vs 3.3% prepaid (95% CI of gap: 4.8–6.4 pp); COD = 18% of orders | Prepaid incentive (small UPI cashback) or COD fee/OTP-confirmation on high-value COD orders | ~5pp of COD orders saved from cancellation |
| 8 | **North-East & East logistics lag.** NE avg 7.7 days, 54% of orders >7 days, 7.8% cancellations; East 6.3 days. Kruskal-Wallis across regions p<0.001 | Regional fulfilment partner / forward-stock best sellers for NE & East | Lower cancellations & returns in 2 regions |
| 9 | **Festive peak is real and relative.** Oct–Nov index ≈1.4–1.6× average. Festive AOV is *lower* (−₹529, bootstrap 95% CI −983…−89) most likely because of deeper festive discounting (not tested causally) | Pre-build inventory for A-class SKUs by September; use targeted offers rather than blanket discounting | Fewer stock-outs; protects peak-season margin |
| 10 | **Forecast.** Log-trend + seasonal model (backtest MAPE 14.5% vs 30.5% for linear) projects Jan–Jun 2026 at ₹1.23, 1.00, 1.09, 1.34, 1.22, 1.20 Cr/month (80% interval roughly −16% / +19% around the point forecast) | Use as a planning baseline for inventory and budgets; re-fit monthly | Inventory & cash planning |

\* illustrative: Fashion net revenue ≈ ₹3.7 Cr, so 1% of it ≈ ₹3.7 lakh.

## Caveats a senior analyst would state
* **Synthetic data** — patterns were designed; real data will be noisier and require more cleaning/feature work.
* **What-if scenarios assume no volume response** to a discount cap; this must be validated with an experiment before roll-out.
* **LTV is a 12-month gross-profit proxy** (not a probabilistic BG/NBD model) and CAC is channel-level with fixed + variable spend; blended CAC fell from ₹2,441 (2023) to ₹1,536 (2025) as fixed spend was amortised.
* **Seasonality index is growth-confounded** (a growing business inflates late-year months); read it as relative shape. A STL/X-13 decomposition would be the next refinement.
* **Churn labels** are "no purchase in the next 180 days" — a definition that should be agreed with the business; the model is evaluated on a random hold-out within one temporal cut (a production version would also validate on a later cut).
* Gradient boosting not beating logistic regression is itself a finding: features are dominated by recency, so a simpler, explainable model is the right choice.
