# Dashboard Blueprint — "KartNova Retail Performance"

Canvas 1280×720 · Theme `theme/KartNova_Theme.json` · Font Segoe UI · Max 6–7 visuals per page (decision-first, not chart-dump).
Every page opens with a one-line **business question** and ends with a **"so what"** text box written from the data.
Reference layout for page 1: `reference_dashboard_preview.png`.

**Global slicers (synced across pages):** Year · Region · Category · Acquisition Channel · Metric Selector (page 1 only)
**Global navigation:** page-navigator buttons + a "Reset filters" bookmark.

| # | Page | Business question | Visuals (measures) |
|---|---|---|---|
| 1 | **Executive Summary** | Are we growing profitably? | 6 KPI cards (`Net Revenue`, `Gross Margin %`, `Orders`, `AOV`, `Active Customers`, `Return Rate %`) each with `YoY Arrow` subtitle · line+column monthly trend using `Selected Metric` + `Revenue Rolling 3M Avg` · bar: revenue by category · filled map/bar: region · seasonality line (`Seasonality Index`) |
| 2 | **Sales & Product** | Where does money and profit come from? | Treemap category→sub-category (`Net Revenue`, colour = `Gross Margin %`) · Pareto combo (columns `Net Revenue`, line `Cumulative Revenue %`, Top-N slicer) · table of products with `ABC Class`, `Return Rate %` (data bars + conditional icons) · scatter: `Gross Margin %` × `Return Rate %`, size `Net Revenue` · discount-band column chart (`Gross Margin %`, `Return Rate %`) |
| 3 | **Customers & Retention** | Who are our best customers and who are we losing? | RFM segment bar (`Customers in Segment` vs `Segment Revenue Share %`, sorted by `RFM Segment Order`) · cohort matrix (rows `Cohort Month`, columns `Offsets[Offset]`, `Cohort Retention %`, blue colour scale, blanks for censored cells) · cards `Repeat Customer Rate %`, `Lapsed Customers 180d`, `Lapsed Customer Value`, `Top 10% Customer Revenue Share %` · new vs returning stacked column (`New Customers`, `Returning Customers`) |
| 4 | **Marketing ROI** | Which channels deserve more budget? | Channel table (`Marketing Spend`, `CAC`, `LTV 12M Gross Profit`, `LTV to CAC`, `CAC Payback Months`, `Channel Health` with icon/colour rules) · quadrant scatter CAC × LTV (size = `New Customers`) · blended CAC trend · stacked spend by channel · **keep date slicer = All** (see README_DAX §3.7) |
| 5 | **Operations & Returns** | Where do we lose margin after the sale? | Region matrix: `Avg Delivery Days`, `Late Delivery %`, `Cancellation Rate %`, `Return Rate %` (heatmap) · cancellation by payment method (`COD Share of Orders %` callout) · return-reason bar by category (Fashion → Size/Fit) · card `Top Return Reason` |
| 6 | **Pricing What-If** | What if we capped discounts? | `Discount Cap` slicer · cards `Net Revenue @ Cap`, `Profit Uplift @ Cap`, `Uplift % of Gross Profit` · waterfall: actual → uplift by category · text box stating the **zero-volume-loss assumption** and the statistical evidence behind it |
| D | **Customer Drill-through** (hidden) | Tell me about this customer | Drill-through field `Dim_Customer[customer_id]`: profile card, order timeline, category mix, RFM segment, lifetime value |
| T | **Tooltip page** (hidden) | — | Mini trend + margin% for hover on category/region bars |

## Interactions & UX
* **Bookmarks:** "Executive view" (all filters off), "Festive season" (Oct–Nov), "Metric toggle" panel for the `Metric Selector`.
* **Conditional formatting (field value):** `YoY Color`, `Margin Status Color`; data bars on revenue columns; icon sets for `Channel Health`.
* **Dynamic titles:** `Dynamic Page Title`, `Selected Metric Title`; footer `Data Refreshed Through`.
* **Accessibility:** ≥4.5:1 contrast, alt text on every visual, tab order set, no colour-only encoding (arrows + text with colour).
* **Mobile layout:** page 1 only (KPI cards + trend).

## Row-Level Security (optional governance demo)
Modeling → Manage roles: create roles `West`, `South`, `North`, `East`, `Central`, `North-East` with DAX filter on `Dim_Customer`:
`[region] = "West"` (etc.). Test with *View as*. In production replace with a mapping table + `USERPRINCIPALNAME()` for dynamic RLS.

## Performance checklist
Run **Performance Analyzer**; target < 1 s per visual. Levers used: star schema, row maths in Power Query, hidden raw columns, no bi-directional filters, `DIVIDE`/`VAR`, limited visuals per page. Customer RFM columns iterate 9k² rows at refresh (a few seconds) rather than at query time.
