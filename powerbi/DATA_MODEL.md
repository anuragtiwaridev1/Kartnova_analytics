# Power BI Data Model (Star Schema)

```
                         ┌──────────────┐
                         │  Dim_Date    │  (DAX calculated table, marked as Date table)
                         └──────┬───────┘
          1 ┌───────────────────┼─────────────────────────┐ 1
            │ *                 │ *                       │ *
   ┌────────┴───────┐   ┌───────┴────────┐        ┌───────┴────────┐
   │  Fact_Sales    │   │  Fact_Orders   │        │ Fact_Marketing │
   │ (delivered     │   │ (all orders:   │        │ (month×channel │
   │  order lines)  │   │  cancel / SLA) │        │  spend)        │
   └───┬────────┬───┘   └───────┬────────┘        └───────┬────────┘
     * │      * │             * │                         │ *
     1 │      1 │             1 │                         │ 1
 ┌─────┴────┐ ┌─┴───────────────┴──┐                 ┌────┴──────┐
 │Dim_Product│ │   Dim_Customer     │ ───── * : 1 ───►│Dim_Channel│
 └──────────┘ └────────────────────┘ (acquisition_    └───────────┘
                                       channel → channel)
 Disconnected helper tables: Offsets (cohort month index), Top N, Metric Selector
```

| Relationship | From (many) → To (one) | Cardinality | Filter direction | Active |
|---|---|---|---|---|
| Sales → Date | Fact_Sales[order_date] → Dim_Date[date] | * : 1 | Single | Yes |
| Orders → Date | Fact_Orders[order_date] → Dim_Date[date] | * : 1 | Single | Yes |
| Marketing → Date | Fact_Marketing[month_start] → Dim_Date[date] | * : 1 | Single | Yes |
| Sales → Customer | Fact_Sales[customer_id] → Dim_Customer[customer_id] | * : 1 | Single | Yes |
| Orders → Customer | Fact_Orders[customer_id] → Dim_Customer[customer_id] | * : 1 | Single | Yes |
| Sales → Product | Fact_Sales[product_id] → Dim_Product[product_id] | * : 1 | Single | Yes |
| Customer → Channel | Dim_Customer[acquisition_channel] → Dim_Channel[channel] | * : 1 | Single | Yes |
| Marketing → Channel | Fact_Marketing[channel] → Dim_Channel[channel] | * : 1 | Single | Yes |

## Modelling decisions (and why)
1. **Two fact tables at different grains.** `Fact_Sales` is line-level (revenue, margin, returns); `Fact_Orders` is order-level and keeps
   *cancelled* orders, which are needed for cancellation rate and delivery SLA but must not pollute revenue.
2. **Single-direction filters only.** Bi-directional filters cause ambiguity and slow queries; where a "reverse" filter is needed it is done
   explicitly in DAX (e.g. `CALCULATE(..., FILTER(Dim_Customer, ...))`).
3. **Conformed `Dim_Channel`.** Marketing spend (channel grain) and customers (customer grain) share one slicer, which is what makes
   CAC = spend ÷ new customers possible on a single visual.
4. **Row-level maths in Power Query, aggregation in DAX.** `net_revenue`, `refund_amt`, `gross_profit` are computed once at refresh,
   so measures are fast `SUM`s while time-intelligence / ranking / segmentation logic stays in DAX.
5. **Hide** all key columns, `order_month`, raw money columns (users should use measures), and mark `Dim_Date` as the date table.
6. **Sort-by-column:** `Dim_Date[Month Name]` by `[Month Number]`; `[Discount Band]` by a helper rank column; RFM segments by a rank column.
