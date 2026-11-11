"""Builds retail.db from data/clean/*.csv, executes every named query in the .sql files, saves results to sql/results/."""
import re, sqlite3, pandas as pd
from pathlib import Path
HERE = Path(__file__).parent; CLEAN = HERE.parent / "data" / "clean"; DB = HERE / "retail.db"; RES = HERE / "results"; RES.mkdir(exist_ok=True)
DB.unlink(missing_ok=True)
con = sqlite3.connect(DB); con.executescript((HERE / "01_schema.sql").read_text())
for t in ["dim_date", "customers", "products", "orders", "order_items", "returns", "marketing_spend"]:
    df = pd.read_csv(CLEAN / f"{t}.csv", dtype=str if t == "dim_date" else None); df.to_sql(t, con, if_exists="append", index=False)
    print(f"loaded {t:16s}{len(df):>8,d} rows")
con.commit()
ok = 0
for f in sorted(HERE.glob("0[2-5]_*.sql")):
    for blk in re.split(r"(?m)^-- name: ", f.read_text())[1:]:
        name, sql = blk.split("\n", 1); name = name.strip()
        df = pd.read_sql_query(sql, con); df.to_csv(RES / f"{name}.csv", index=False); ok += 1
        print(f"\n--- {name}  ({len(df)} rows)"); print(df.head(6).to_string(index=False)[:900])
print(f"\n{ok} queries executed OK -> sql/results/")
