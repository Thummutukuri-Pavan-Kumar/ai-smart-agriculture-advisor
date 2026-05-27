# tools/train_yield_model.py
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os

# -- assumptions: you have CSV with columns:
# crop, state, area_acres, prev_yield_per_acre, n, p, k, ph, avg_temp, total_rainfall_30d, yield_per_acre (target)
df = pd.read_csv("data/yield_dataset.csv")

# simple feature engineering
df = df.dropna(subset=["yield_per_acre", "crop", "state"])
# one-hot for crop/state
X = pd.get_dummies(df[["crop", "state", "area_acres", "prev_yield_per_acre", "n", "p", "k", "ph", "avg_temp", "total_rainfall_30d"]].fillna(0))
y = df["yield_per_acre"].astype(float)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("rf", RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1))
])
pipe.fit(X_train, y_train)

preds = pipe.predict(X_test)
print("MAE:", mean_absolute_error(y_test, preds))
print("R2:", r2_score(y_test, preds))

os.makedirs("ml_models", exist_ok=True)
joblib.dump(pipe, "ml_models/yield_model.joblib")
print("Saved model to ml_models/yield_model.joblib")
