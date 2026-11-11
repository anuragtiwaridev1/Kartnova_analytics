"""Run the full pipeline end-to-end: data generation -> cleaning -> 8 analytics modules -> SQL layer."""
import subprocess, sys
from pathlib import Path
R = Path(__file__).parent
steps = [R/"data_generation/generate_dataset.py", R/"python_analytics/01_data_cleaning.py"] + sorted((R/"python_analytics").glob("0[2-9]_*.py")) + [R/"sql/run_sql_pipeline.py"]
for s in steps:
    print(f"\n{'='*70}\n>>> {s.relative_to(R)}\n{'='*70}")
    r = subprocess.run([sys.executable, s.name], cwd=s.parent)
    if r.returncode: sys.exit(f"FAILED: {s}")
print("\nPipeline complete.")
