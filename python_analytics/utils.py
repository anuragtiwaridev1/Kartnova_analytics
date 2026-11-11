"""Shared helpers: paths, data loading, the enriched fact table, plotting theme."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
OUT_FIG = Path(__file__).resolve().parent / "outputs" / "figures"
OUT_TBL = Path(__file__).resolve().parent / "outputs" / "tables"
for p in (CLEAN, OUT_FIG, OUT_TBL):
    p.mkdir(parents=True, exist_ok=True)

PALETTE = ["#1F4E79", "#2E86AB", "#F18F01", "#C73E1D", "#3B8EA5", "#6C757D", "#8FB339"]
SNAPSHOT_DATE = pd.Timestamp("2025-12-31")     # "today" for recency-type calculations


def set_style():
    sns.set_theme(style="whitegrid", context="notebook", palette=PALETTE)
    plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 150, "axes.titleweight": "bold",
                         "axes.titlesize": 13, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.autolayout": True})


def savefig(name):
    plt.savefig(OUT_FIG / f"{name}.png", bbox_inches="tight")
    plt.close()


def save_table(df, name, index=False):
    df.to_csv(OUT_TBL / f"{name}.csv", index=index)


def inr_cr(x, _=None):  return f"₹{x / 1e7:.1f} Cr"
def inr_lakh(x, _=None): return f"₹{x / 1e5:.0f}L"


def load_clean():
    """Return the cleaned tables as a dict of DataFrames (dates parsed)."""
    d = {n: pd.read_csv(CLEAN / f"{n}.csv") for n in
         ["customers", "products", "orders", "order_items", "returns", "marketing_spend", "dim_date"]}
    for t, cols in {"customers": ["signup_date"], "orders": ["order_date", "ship_date", "delivery_date"],
                    "returns": ["return_date"], "marketing_spend": ["month_start"], "dim_date": ["date"]}.items():
        for c in cols:
            d[t][c] = pd.to_datetime(d[t][c])
    return d


def build_fact(d=None, delivered_only=True):
    """Line-level fact table with revenue, COGS, margin, return & customer attributes.

    gross_sales  = qty * list_price
    net_revenue  = gross_sales * (1 - discount)          (what the customer is invoiced, ex-shipping)
    refund       = net_revenue * refund_pct for returned lines
    net_of_returns revenue = net_revenue - refund
    gross_profit = net_of_returns - COGS(on kept units)   (returned units assumed restocked, COGS reversed)
    """
    d = d or load_clean()
    f = (d["order_items"]
         .merge(d["orders"], on="order_id")
         .merge(d["products"][["product_id", "product_name", "category", "sub_category", "brand", "unit_cost"]], on="product_id")
         .merge(d["customers"][["customer_id", "city", "state", "region", "city_tier", "acquisition_channel",
                                "signup_date", "gender", "age"]], on="customer_id")
         .merge(d["returns"][["order_item_id", "return_date", "return_reason", "refund_pct"]], on="order_item_id", how="left"))
    if delivered_only:
        f = f[f.order_status == "Delivered"].copy()
    f["gross_sales"] = f.quantity * f.unit_price
    f["discount_amt"] = f.gross_sales * f.discount_pct / 100
    f["net_revenue"] = f.gross_sales - f.discount_amt
    f["is_returned"] = f.return_date.notna()
    f["refund_amt"] = np.where(f.is_returned, f.net_revenue * f.refund_pct.fillna(0), 0.0)
    f["cogs"] = f.quantity * f.unit_cost
    f["kept_revenue"] = f.net_revenue - f.refund_amt
    restock = np.where(f.is_returned, f.refund_pct.fillna(0), 0.0)   # share of units restocked on return
    f["gross_profit"] = f.kept_revenue - f.cogs * (1 - restock)
    f["order_month"] = f.order_date.dt.to_period("M").dt.to_timestamp()
    f["order_year"] = f.order_date.dt.year
    return f
