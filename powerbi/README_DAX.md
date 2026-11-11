# Power BI + DAX Layer — Explained

> **Same dataset, separate toolchain.** This folder rebuilds the analytics of the Python and SQL layers *inside Power BI*,
> from the same cleaned CSVs in `data/clean/`. Nothing here depends on the Python/SQL outputs, which is what makes the
> reconciliation at the bottom meaningful: three independent implementations, one set of numbers.

## 0. What is in this folder

| File | Purpose |
|---|---|
| `power_query/power_query_m.pq` | Power Query (M) for all 7 queries: parameterised folder path, reusable CSV loader, fact/dim shaping, row-level money maths |
| `DATA_MODEL.md` | Star-schema design, relationships, filter directions and the reasoning behind them |
| `dax/01_calculated_tables_and_columns.dax` | Date table, what-if/disconnected tables, customer-level calculated columns (RFM scores, cohort month, 12-month LTV) |
| `dax/02_measures.dax` | ~80 measures in 9 display folders |
| `dax/03_dax_queries.dax` | 10 `EVALUATE` queries for **DAX Query View**: reconciliation, ranking, cohort matrix, what-if |
| `theme/KartNova_Theme.json` | Importable report theme (View → Themes → Browse for themes) |
| `DASHBOARD_BLUEPRINT.md` | Page-by-page report design: visuals, measures, interactions, drill-through, RLS |
| `reference_dashboard_preview.png` | Reference layout of page 1 (matplotlib mock-up from the real data, **not** a Power BI screenshot) |

> **Honest note on what is and isn't included:** a `.pbix` is a proprietary binary that can only be authored in Power BI Desktop,
> so it is not shipped. Everything needed to rebuild it in ~30–45 minutes is: load the M queries, create the relationships,
> paste the DAX, import the theme, then follow the blueprint. The DAX was written to mirror the SQL view line-for-line and
> includes validation queries with expected values, so you can prove it ties out the moment you build it.

## 1. Build steps (30–45 min)

1. **Get Data → Blank query → Advanced editor**; paste each block from `power_query_m.pq` as its own query. Create the `DataFolder` parameter first (path to `data/clean/` ending in `\`). Load order: `fnLoadCsv` → `Fact_Orders` → `Fact_Sales`, `Dim_Customer`, `Dim_Product`, `Fact_Marketing` → `Dim_Channel`. Disable load for `fnLoadCsv` and `DataFolder`.
2. **Model view**: create the 8 relationships in `DATA_MODEL.md` (all single-direction, many-to-one).
3. **New table** → paste `Dim_Date`; **Mark as date table** on `[Date]`. Add the other calculated tables.
4. Add the **calculated columns** on `Dim_Customer` (they depend on each other, so add in file order).
5. Create `_Measures` home table; paste measures from `02_measures.dax` (one at a time or via Tabular Editor / TMDL view) and set display folders.
6. **Validate** with `03_dax_queries.dax` Q1 against the table in §5.
7. Import theme, build pages per `DASHBOARD_BLUEPRINT.md`.

## 2. Why measures instead of calculated columns (and the split used here)

| Logic | Where | Why |
|---|---|---|
| Line-level money (`net_revenue`, `refund_amt`, `gross_profit`) | **Power Query** | Computed once at refresh, column-compressed; measures become cheap `SUM`s |
| Anything that must respond to slicers (rates, ratios, YoY, ranks, shares) | **DAX measure** | Measures are evaluated in the *filter context* of each visual cell; columns are frozen at refresh |
| Customer-level attributes that segment customers (RFM, cohort, 12-m LTV) | **DAX calculated column** | They become slicer/axis fields (you can put "RFM Segment" on an axis); measures cannot be used as axes |

## 3. Measure library — what each group does, why it exists, how it helps

### 3.1 Sales & Profit (folder `1 Sales`)
`Net Revenue`, `Gross Sales`, `Discount %`, `Refunds`, `Kept Revenue`, `Gross Profit`, `Gross Margin %`, `Orders`, `Active Customers`, `AOV`, `Units per Order`, `Revenue per Customer`, `Avg Selling Price`

* **Why:** one shared definition of "revenue" and "profit" stops the classic argument where two reports show two different numbers.
  Revenue is split into *net* (invoiced after discount) and *kept* (after returns) because on a 9% return rate — 19% in Fashion — the gap is material.
* **Business rule encoded (identical in SQL & Python):** `gross_profit = net_revenue − refund − COGS × (1 − refund%)`, i.e. returned units are restocked so their COGS is reversed.
* **How useful:** these are the KPI cards on page 1 and the building blocks of everything else. `AOV` and `Units per Order` separate *basket-size* growth from *order-count* growth.
* **DAX concepts:** `SUM`, `DISTINCTCOUNT`, `DIVIDE` (never `/`, so no divide-by-zero errors).

### 3.2 Returns & Operations (folder `2 Ops`)
`Return Rate %`, `Refund % of Revenue`, `Cancellation Rate %`, `Avg Delivery Days`, `Late Delivery %`, `COD Share of Orders %`, `Top Return Reason`

* **Why:** margin leaks after the sale. Cancellations live in `Fact_Orders` (all orders) while revenue lives in `Fact_Sales` (delivered lines) — two grains, so rates are computed on the correct denominator.
* **How useful:** surfaced that COD orders cancel at 8.9% vs 3.3% prepaid, and North-East delivery is slow (54% of orders take >7 days) — directly actionable for ops and payments teams.
* **DAX concepts:** `CALCULATE` with a column filter to change the numerator; `COUNTROWS` on the right fact; `TOPN` + `MAXX` to return a *text* answer ("Top Return Reason").

### 3.3 Time Intelligence (folder `3 Time`)
`Revenue PY`, `Revenue YoY %`, `Revenue PM`, `Revenue MoM %`, `Revenue MTD / QTD / YTD`, `Revenue YTD PY`, `Revenue FYTD`, `Revenue Rolling 3M (Avg)`, `Revenue L12M`, `Seasonality Index`, `Last Data Date`, `Is Period In Data`

* **Why:** leadership reads *growth*, not absolutes. YoY removes seasonality; MoM shows momentum; rolling-3M smooths noise; **FYTD uses India's April–March fiscal year** (`TOTALYTD(..., "3/31")`).
* **The detail a senior analyst adds:** the calendar runs to Dec-2026 but data stops Dec-2025. Without a guard, 2026 months would show blank-vs-something nonsense. `Is Period In Data` + `Last Data Date` blank-out future periods cleanly.
* **`Seasonality Index`** = month revenue ÷ the average month of that year, computed by `AVERAGEX` over only months that have data, using `REMOVEFILTERS` inside an iterator so each month sees the full year. (A raw index inherits the growth trend; read Oct–Nov as *relative* peaks.)
* **DAX concepts:** `SAMEPERIODLASTYEAR`, `DATEADD`, `TOTALYTD` with year-end, `DATESINPERIOD`, variables to avoid a measure inside a boolean filter (a real DAX restriction).

### 3.4 Share, Ranking & Pareto (folder `4 Ranking`)
`Revenue % of Total`, `Revenue % of Category`, `Product Rank`, `Top N Value`, `Top N Product Revenue`, `Cumulative Revenue %`, `ABC Class`, `Category Margin Rank`, `Share of Profit %`

* **Why:** 25% of SKUs produce 80% of revenue. ABC classification (A = first 70% of revenue, B = next 20%, C = tail) tells merchandising what to never stock out of and what to delist.
* **`Cumulative Revenue %` walk-through:** for the product in the current row, `Cum` sums revenue of every product whose revenue is ≥ the current one (that is the running Pareto total without needing a sorted helper table); `Tot` is the total over the *same* slicer-filtered set (`ALLSELECTED`), so the curve always ends at 100% whatever the user has filtered.
* **`Top N`** is a **what-if parameter**: the viewer picks 3–20 and the visual re-ranks live.
* **DAX concepts:** `RANKX` (`SKIP` vs `DENSE` ties), `ALLSELECTED` vs `ALL`, `SUMX(FILTER(...))` running-total pattern, `SWITCH(TRUE(), ...)`.

### 3.5 Customer Analytics (folder `5 Customers`) + calculated columns
`New Customers`, `Returning Customers (%)`, `Repeat Customer Rate %`, `Orders per Customer`, `Customers in Segment`, `Segment Revenue Share %`, `Lapsed Customers 180d`, `Lapsed Customer Value`, `Top 10% Customer Revenue Share %`
Columns: `First Order Date`, `Cohort Month`, `Lifetime Orders/Revenue`, `Recency Days`, `R/F/M Score`, `RFM Segment`

* **Why:** growth quality. Are we buying revenue with new customers or growing from loyal ones? Which customers are slipping away? How concentrated is revenue?
* **RFM in DAX:** each customer row is turned into a filter on `Fact_Sales` (**context transition**) to compute Recency/Frequency/Monetary. Scores are quintiles built from a *unique sort key* (value, customer number) so ties break deterministically — the same rule as `NTILE(5) ... ORDER BY value, customer_id` in SQL. The same eight named segments (Champions → Lost) are produced by `SWITCH(TRUE())`.
* **`Lapsed Customer Value`** puts a rupee figure on churn: lifetime revenue sitting in customers silent for 180+ days — the budget justification for a win-back campaign.
* **`Top 10% Customer Revenue Share %`** is the concentration-risk metric (Python/SQL show the top decile ≈ 49% of revenue).
* **DAX concepts:** context transition, row vs filter context, `ADDCOLUMNS`/`TOPN` on virtual tables, `FILTER` over `VALUES`.

### 3.6 Cohort Retention (folder `6 Cohort`)
`Cohort Size`, `Cohort Active Customers`, `Cohort Retention %`, `Avg Retention M3 %`, `Last Data Month`

* **Why:** the cleanest read on product-market fit; shows whether newer cohorts are better than older ones.
* **How it works:** a matrix has `Dim_Customer[Cohort Month]` on rows and the disconnected `Offsets[Offset]` (0–12) on columns. For each cell the measure asks *"of the customers whose first purchase was in month C, how many bought in month C + Offset?"* via `EDATE`.
* **Right-censoring:** if `C + Offset` is beyond the last data month the cell returns `BLANK()`, not 0 — otherwise recent cohorts would look like they churned 100%. This is the most common cohort mistake and it is handled explicitly.
* **DAX concepts:** disconnected table + `SELECTEDVALUE`, `REMOVEFILTERS`, `EDATE`, iterating a virtual table with `ADDCOLUMNS`.

### 3.7 Marketing Efficiency (folder `7 Marketing`)
`Marketing Spend`, `CAC`, `Revenue per Rupee Spent`, `Marketing % of Revenue`, `LTV 12M Gross Profit`, `LTV to CAC`, `CAC Payback Months`, `Channel Health`

* **Why:** "cheapest channel" is the wrong question; the right one is **profit returned per rupee**. The conformed `Dim_Channel` lets spend (channel grain) and customers (customer grain) sit on one visual.
* **`LTV 12M Gross Profit`:** a calculated column (`GP 12M`) sums each customer's gross profit in the 365 days after sign-up; the measure averages it over *mature* customers only (full 12-month window, sign-up ≤ 31-Dec-2024) to avoid under-counting recent sign-ups.
* **Result:** Referral and Organic return ~11–12× CAC with ~1-month payback; Paid Search is ~2.5× with ~4.8-month payback — **below the 3× benchmark** — and `Channel Health` labels it "Optimise / cut".
* **Tip:** on the channel page keep the date slicer on *All* — CAC responds to the date range but the 12-month LTV column does not.

### 3.8 Dynamic & UX (folder `8 UX`)
`Selected Metric`, `Selected Metric Title`, `YoY Arrow`, `YoY Color`, `Margin Status Color`, `Dynamic Page Title`, `Data Refreshed Through`

* **Why:** one trend chart can switch between Revenue / Profit / Orders / Customers / AOV via a slicer (`SWITCH` on a disconnected table), instead of five near-duplicate visuals. Colour measures drive conditional formatting ("field value") so green/red logic lives in one place. Titles update to the current filter selection.

### 3.9 Pricing What-If (folder `9 What-if`)
`Discount Cap Value`, `Net Revenue @ Cap`, `Profit Uplift @ Cap`, `Uplift % of Gross Profit`

* **Why:** turns an analytical finding into a decision tool. The Python statistical test (Spearman ρ ≈ 0.004, p = 0.29) shows **discount depth has no relationship with units per line**, so deep discounts give margin away without buying volume. The slicer lets a pricing manager set a ceiling (0–40%) and see the profit effect instantly.
* **Reference result:** a 10% ceiling ≈ **+₹83.9 lakh (+10.9% of gross profit)**, assuming zero volume loss (this is an upper-bound scenario and the assumption is stated on the report).
* **DAX concepts:** `SUMX` row-by-row repricing with `MIN`, `SELECTEDVALUE` parameter.

## 4. DAX queries (`03_dax_queries.dax`)

Run in **DAX Query View** (Desktop → left rail). They double as *tests*: Q1 reconciles to SQL, Q6 to the SQL cohort query, Q8 to the SQL RFM query.
They also demonstrate query-only constructs: `DEFINE MEASURE` (local what-if without touching the model), `SUMMARIZECOLUMNS`, `TOPN`, `GROUPBY/CURRENTGROUP` on virtual tables, and `ORDER BY`.

## 5. Reconciliation table — expected values (Q1 should return exactly these)

| Year | Net Revenue | Kept Revenue | Gross Profit | Gross Margin % | Orders | Active Customers | AOV | Return Rate % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 38,809,309 | 35,389,487 | 11,215,182 | 31.69% | 4,022 | 1,956 | 9,649 | 9.50% |
| 2024 | 88,935,118 | 81,667,012 | 26,473,560 | 32.42% | 9,805 | 4,204 | 9,070 | 8.85% |
| 2025 | 133,807,961 | 122,073,461 | 39,524,593 | 32.38% | 14,044 | 5,573 | 9,528 | 9.27% |

All-time (no filters): Net Revenue **261,552,388** · Gross Profit **77,213,334** · Delivered orders **27,871** · Active customers **8,854** · Return rate **9.15%** ·
Orders placed **29,107** · Cancellation rate **4.25%** · Marketing spend **15,981,400**.
Other checks: Profit Uplift @ 10% cap = **8,387,185**; Referral LTV:CAC ≈ **12.50**, Paid Search ≈ **2.52**.

**If a number doesn't tie, check in this order:** (1) `Fact_Sales` should have **60,119** rows (62,700 order lines minus lines of cancelled orders) and `Fact_Orders` **29,107** — is the delivered filter applied? (2) relationships single-direction and active; (3) `order_date` typed as *Date* not text; (4) CSV locale — numbers parsed with `"en-US"` (already set in the M code).
RFM segment sizes can differ from Python/SQL by a handful of customers at quintile boundaries because Python uses pandas `qcut` and SQL/DAX use NTILE-style splitting; revenue shares agree to within ~0.1pp.

## 6. Best-practice checklist applied

* Star schema, single-direction filters, hidden keys/raw columns, measures in a dedicated home table with display folders
* `DIVIDE` everywhere; variables (`VAR`) for readability and single evaluation; no measure inside boolean filter shortcuts
* Continuous marked date table, fiscal calendar, future-period guards
* Heavy row maths pushed upstream (Power Query); parameterised source path (portable across machines, Gateway-friendly)
* Documented business rules identical across SQL, Python and DAX (single source of truth)
* Suggested governance: **RLS** role per region on `Dim_Customer[region]` (static roles: West / South / North / East / Central / North-East), see blueprint
* Optional next steps: move time-intelligence measures to a **Calculation Group** (Tabular Editor) to drop ~12 measures; Incremental Refresh on `Fact_Sales` by `order_date`; Performance Analyzer to benchmark visuals
