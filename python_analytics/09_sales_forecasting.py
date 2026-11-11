"""
09 - REVENUE FORECASTING WITH ROLLING-ORIGIN BACKTEST
=====================================================
WHY: Finance & supply-chain need a defensible 6-month outlook for inventory and budget. We don't just fit
one model - we compare candidates with a rolling-origin backtest (train on the past, predict the next 6
months, slide forward) and pick on out-of-sample MAPE, then publish an 80% prediction interval.
CANDIDATES: (A) Seasonal-naive x trailing growth  (B) OLS log(y) ~ log(t)+month  (C) OLS log(y) ~ t+month
"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt, matplotlib.ticker as mt
from sklearn.linear_model import Ridge
from utils import *
set_style(); f = build_fact()
y = f.groupby("order_month").net_revenue.sum(); y = y[y.index >= "2023-04-01"]    # drop ramp-up months before the platform had scale
idx = y.index; T = np.arange(len(y)) + 1; H = 6

def design(ix, t0, kind):
    M = pd.get_dummies(ix.month).reindex(columns=range(1, 13), fill_value=0).astype(float).values
    tt = np.arange(len(ix)) + t0
    return np.column_stack([np.log(tt) if kind == "logt" else tt, M])

def fit_predict(train, h, kind):
    if kind == "snaive":
        g = train.iloc[-12:].sum() / train.iloc[-24:-12].sum()
        return np.array([train.iloc[-12 + i] * g for i in range(h)]), None
    Xt = design(train.index, 1, kind); m = Ridge(alpha=1e-3).fit(Xt, np.log(train.values))
    fut = pd.date_range(train.index[-1] + pd.offsets.MonthBegin(1), periods=h, freq="MS")
    resid = np.log(train.values) - m.predict(Xt)
    return np.exp(m.predict(design(fut, len(train) + 1, kind))), resid.std(ddof=14)

rows = []
for origin in range(len(y) - 18, len(y) - H + 1, 3):            # rolling origins
    tr, te = y.iloc[:origin], y.iloc[origin:origin + H]
    for kind in ("snaive", "logt", "lint"):
        pr, _ = fit_predict(tr, len(te), kind); rows.append(dict(origin=tr.index[-1].strftime("%Y-%m"), model=kind, mape=np.mean(np.abs(pr - te.values) / te.values) * 100))
bt = pd.DataFrame(rows).pivot(index="origin", columns="model", values="mape").round(2); bt.loc["MEAN"] = bt.mean().round(2)
print("Backtest MAPE % (rows = training end month, horizon 6m)\n", bt.to_string()); save_table(bt.reset_index(), "forecast_backtest_mape")
best = bt.loc["MEAN"].idxmin(); print("Selected model:", best)

pr, sd = fit_predict(y, H, best if best != "snaive" else "logt")
fut = pd.date_range(y.index[-1] + pd.offsets.MonthBegin(1), periods=H, freq="MS")
fc = pd.DataFrame({"month": fut, "forecast": pr}); z = 1.2816
if sd is not None: fc["lo80"], fc["hi80"] = pr * np.exp(-z * sd), pr * np.exp(z * sd)
fc[fc.columns[1:]] = fc[fc.columns[1:]].round(0); print(fc.to_string(index=False)); save_table(fc, "revenue_forecast_next_6_months")
fig, ax = plt.subplots(figsize=(11, 4.6)); ax.plot(y.index, y.values, color=PALETTE[0], lw=2.2, label="Actual")
ax.plot(fc.month, fc.forecast, color=PALETTE[2], lw=2.5, marker="o", label=f"Forecast ({best})")
if "lo80" in fc: ax.fill_between(fc.month, fc.lo80, fc.hi80, color=PALETTE[2], alpha=.25, label="80% interval")
ax.yaxis.set_major_formatter(mt.FuncFormatter(inr_cr)); ax.set_title("Net revenue — actual & 6-month forecast"); ax.legend(); savefig("09_revenue_forecast")
