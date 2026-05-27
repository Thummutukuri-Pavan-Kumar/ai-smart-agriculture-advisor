# tools/train_yield_from_csv.py
import os, joblib, numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

CSV_PATH = os.path.join("dataset", "crop_yield.csv")
OUT_MODEL = os.path.join("ml_models", "yield_model.joblib")
os.makedirs("ml_models", exist_ok=True)

print("Loading CSV:", CSV_PATH)
df = pd.read_csv(CSV_PATH, low_memory=False)

print("Columns found:", list(df.columns))

# Heuristics to find target (yield)
candidate_targets = [
    "yield_per_acre","yield_per_hectare","yield","production","production_tonnes","yield_ton_per_acre",
    "Yield","YIELD","production_ton"
]
target = None
for c in candidate_targets:
    if c in df.columns:
        target = c
        break

# if no obvious target, try combination production/area -> compute per-acre yield
if target is None:
    if ("production" in df.columns or "Production" in df.columns) and ("area" in df.columns or "area_acres" in df.columns or "Area" in df.columns):
        prod_col = "production" if "production" in df.columns else ("Production" if "Production" in df.columns else None)
        area_col = "area" if "area" in df.columns else ("area_acres" if "area_acres" in df.columns else ("Area" if "Area" in df.columns else None))
        if prod_col and area_col:
            df["yield_per_acre"] = df[prod_col].astype(float).fillna(0) / df[area_col].astype(float).replace(0, np.nan).fillna(1)
            target = "yield_per_acre"

if target is None:
    raise SystemExit("Could not auto-detect a yield target column. Check the CSV with tools/inspect_dataset.py and re-run.")

print("Using target column:", target)

# pick candidate feature columns
possible_crops = [c for c in df.columns if "crop" in c.lower() or c.lower() in ["crop_name","crop","Crop","CROP"]]
crop_col = possible_crops[0] if possible_crops else None

# Numeric features to try (common)
numeric_candidates = ["n","p","k","N","P","K","ph","avg_temp","temperature","rainfall_30d","total_rainfall_30d","prev_yield_per_acre","area_acres","area","Area"]
numerics = []
for c in numeric_candidates:
    if c in df.columns:
        numerics.append(c)
# fallback: any numeric columns excluding target
if not numerics:
    numerics = [c for c in df.select_dtypes(include=[np.number]).columns.tolist() if c != target]
print("Detected numeric features:", numerics)
print("Detected crop column:", crop_col)

# Prepare dataframe for training
train_df = df.copy()
# keep only cols we will use + target
use_cols = []
if crop_col:
    use_cols.append(crop_col)
use_cols += numerics
# ensure we have at least one feature
if not use_cols:
    raise SystemExit("No usable features detected. You need numeric features or a crop column.")

# drop rows with missing target
train_df = train_df.dropna(subset=[target])
X = train_df[use_cols]
y = train_df[target].astype(float)

# Fill missing numeric values with median
for nc in numerics:
    if nc in X.columns:
        med = pd.to_numeric(X[nc], errors='coerce').median()
        X[nc] = pd.to_numeric(X[nc], errors='coerce').fillna(med)

# If crop column exists, ensure string type and fill
if crop_col:
    X[crop_col] = X[crop_col].astype(str).fillna("unknown")

# Define preprocessing
cat_cols = [crop_col] if crop_col else []
num_cols = [c for c in X.columns if c not in cat_cols]

preprocessor = ColumnTransformer(transformers=[
    ("cat", OneHotEncoder(handle_unknown="ignore", sparse=False), cat_cols) if cat_cols else ("noop_cat", "passthrough", []),
    ("num", StandardScaler(), num_cols)
], remainder="drop")

pipe = Pipeline([
    ("pre", preprocessor),
    ("rf", RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1))
])

print("Splitting data...")
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.15, random_state=42)

print("Training pipeline...")
pipe.fit(X_train, y_train)

print("Train R^2:", pipe.score(X_train, y_train))
print("Val R^2:", pipe.score(X_val, y_val))

print("Saving model to", OUT_MODEL)
joblib.dump(pipe, OUT_MODEL)
print("Done.")
