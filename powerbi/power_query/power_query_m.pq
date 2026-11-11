// =====================================================================================================
//  KartNova  |  POWER QUERY (M) - one block per query. Create each as a separate query in Power BI.
//  Data source: the SAME cleaned CSVs used by Python and SQL  (../data/clean/*.csv)
//  Design principle: keep the model a clean STAR SCHEMA; push row-level maths to Power Query (computed once
//  at refresh, stored compressed) and keep DAX for aggregation / context-aware logic.
// =====================================================================================================

// ------------------------------------------------------------------ Parameter: DataFolder
//  Home > Transform data > Manage Parameters > New.  Type: Text.  Value example:  C:\Projects\KartNova_Analytics\data\clean\
//  (Must end with a backslash.)  Changing this one value repoints every query - no hard-coded paths.
//  Query name: DataFolder        (M source:)
"C:\Projects\KartNova_Analytics\data\clean\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]


// ------------------------------------------------------------------ Function: fnLoadCsv
//  Query name: fnLoadCsv     (reusable CSV loader -> DRY, one place to change delimiter / encoding)
(fileName as text) as table =>
let
    Source   = Csv.Document(File.Contents(DataFolder & fileName), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
in
    Promoted


// ------------------------------------------------------------------ Fact_Orders  (grain: 1 row per ORDER, all statuses)
//  Used for cancellation rate and delivery SLA, which need cancelled orders too.
let
    Raw   = fnLoadCsv("orders.csv"),
    Typed = Table.TransformColumnTypes(Raw,
        {{"order_id", type text}, {"customer_id", type text}, {"order_date", type date}, {"ship_date", type date},
         {"delivery_date", type date}, {"order_status", type text}, {"payment_method", type text}, {"device", type text},
         {"shipping_fee", type number}, {"delivery_days", Int64.Type}}, "en-US"),
    AddMonth = Table.AddColumn(Typed, "order_month", each Date.StartOfMonth([order_date]), type date),
    IsLate   = Table.AddColumn(AddMonth, "is_late_delivery", each if [delivery_days] <> null and [delivery_days] > 7 then 1 else 0, Int64.Type)
in
    IsLate


// ------------------------------------------------------------------ Fact_Sales  (grain: 1 row per DELIVERED order LINE)
//  Business rules are IDENTICAL to sql/01_schema.sql (vw_order_lines) and python_analytics/utils.py (build_fact)
let
    Items = Table.TransformColumnTypes(fnLoadCsv("order_items.csv"),
        {{"order_item_id", type text}, {"order_id", type text}, {"product_id", type text},
         {"quantity", Int64.Type}, {"unit_price", type number}, {"discount_pct", type number}}, "en-US"),

    // 1) attach order header attributes (inner join keeps delivered orders only)
    DeliveredOrders = Table.SelectRows(Fact_Orders, each [order_status] = "Delivered"),
    OrderCols  = Table.SelectColumns(DeliveredOrders, {"order_id", "customer_id", "order_date", "order_month", "payment_method", "device", "delivery_days"}),
    JoinOrders = Table.NestedJoin(Items, {"order_id"}, OrderCols, {"order_id"}, "O", JoinKind.Inner),
    ExpOrders  = Table.ExpandTableColumn(JoinOrders, "O", {"customer_id", "order_date", "order_month", "payment_method", "device", "delivery_days"}),

    // 2) attach unit cost
    Prod = Table.TransformColumnTypes(Table.SelectColumns(fnLoadCsv("products.csv"), {"product_id", "unit_cost"}), {{"unit_cost", type number}}, "en-US"),
    JoinProd = Table.NestedJoin(ExpOrders, {"product_id"}, Prod, {"product_id"}, "P", JoinKind.LeftOuter),
    ExpProd  = Table.ExpandTableColumn(JoinProd, "P", {"unit_cost"}),

    // 3) attach return info (left join: most lines are not returned)
    Ret = Table.TransformColumnTypes(Table.SelectColumns(fnLoadCsv("returns.csv"), {"order_item_id", "return_reason", "refund_pct"}), {{"refund_pct", type number}}, "en-US"),
    JoinRet = Table.NestedJoin(ExpProd, {"order_item_id"}, Ret, {"order_item_id"}, "R", JoinKind.LeftOuter),
    ExpRet  = Table.ExpandTableColumn(JoinRet, "R", {"return_reason", "refund_pct"}),

    // 4) money columns
    Typed0 = Table.TransformColumnTypes(ExpRet, {{"order_date", type date}, {"order_month", type date}, {"delivery_days", Int64.Type}}),
    GrossSales = Table.AddColumn(Typed0, "gross_sales",  each [quantity] * [unit_price], type number),
    NetRev     = Table.AddColumn(GrossSales, "net_revenue", each [gross_sales] * (1 - [discount_pct] / 100), type number),
    IsRet      = Table.AddColumn(NetRev, "is_returned",  each if [refund_pct] = null then 0 else 1, Int64.Type),
    Refund     = Table.AddColumn(IsRet, "refund_amt",    each if [refund_pct] = null then 0 else [net_revenue] * [refund_pct], type number),
    Cogs       = Table.AddColumn(Refund, "cogs",         each [quantity] * [unit_cost], type number),
    GProfit    = Table.AddColumn(Cogs, "gross_profit",   each [net_revenue] - [refund_amt] - [cogs] * (1 - (if [refund_pct] = null then 0 else [refund_pct])), type number),
    Discount   = Table.AddColumn(GProfit, "discount_band", each if [discount_pct] = 0 then "0%" else if [discount_pct] <= 10 then "1-10%" else if [discount_pct] <= 20 then "11-20%" else ">20%", type text),
    Clean      = Table.RemoveColumns(Discount, {"unit_cost"})
in
    Clean


// ------------------------------------------------------------------ Dim_Customer
let
    Raw = fnLoadCsv("customers.csv"),
    Typed = Table.TransformColumnTypes(Raw,
        {{"customer_id", type text}, {"signup_date", type date}, {"gender", type text}, {"age", Int64.Type}, {"city", type text},
         {"state", type text}, {"region", type text}, {"city_tier", Int64.Type}, {"acquisition_channel", type text}, {"age_group", type text}}, "en-US")
in
    Typed


// ------------------------------------------------------------------ Dim_Product
let
    Raw = fnLoadCsv("products.csv"),
    Typed = Table.TransformColumnTypes(Raw,
        {{"product_id", type text}, {"product_name", type text}, {"category", type text}, {"sub_category", type text},
         {"brand", type text}, {"list_price", type number}, {"unit_cost", type number}}, "en-US")
in
    Typed


// ------------------------------------------------------------------ Fact_Marketing  (grain: month x channel)
let
    Raw = fnLoadCsv("marketing_spend.csv"),
    Typed = Table.TransformColumnTypes(Raw, {{"month_start", type date}, {"channel", type text}, {"marketing_spend", type number}}, "en-US")
in
    Typed


// ------------------------------------------------------------------ Dim_Channel  (conformed dimension: lets spend and customers share one slicer)
let
    Source   = Table.SelectColumns(Dim_Customer, {"acquisition_channel"}),
    Distinct = Table.Distinct(Source),
    Renamed  = Table.RenameColumns(Distinct, {{"acquisition_channel", "channel"}}),
    Sorted   = Table.Sort(Renamed, {{"channel", Order.Ascending}})
in
    Sorted
