# tools/inspect_dataset.py
import os, pandas as pd, sys

CSV = os.path.join("dataset", "crop_yield.csv")  # relative path from project root

if not os.path.exists(CSV):
    print("File not found:", CSV)
    sys.exit(1)

df = pd.read_csv(CSV, low_memory=False)
print("File:", CSV)
print("Rows:", len(df))
print("Columns:", list(df.columns))
print("\nColumn dtypes:")
print(df.dtypes)
print("\nFirst 10 rows:")
print(df.head(10).to_string(index=False))
print("\nSome column summary (numeric):")
print(df.describe(include=[float, int]).transpose().head(30))
