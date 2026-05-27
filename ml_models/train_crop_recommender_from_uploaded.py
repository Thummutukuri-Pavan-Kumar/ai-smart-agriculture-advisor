# ml_models/train_crop_recommender_from_uploaded.py

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from joblib import dump
import os

# 👉 Your local dataset path
CSV_PATH = r"E:\agri_advisor\dataset\Crop_recommendation.csv"

# Load CSV
df = pd.read_csv(CSV_PATH)

# Your dataset columns (verified earlier)
target_col = "label"
feature_cols = ["N","P","K","temperature","humidity","ph","rainfall"]

# Ensure features are numeric
df[feature_cols] = df[feature_cols].apply(pd.to_numeric, errors='coerce')
df = df.dropna(subset=feature_cols + [target_col])

X = df[feature_cols]
y = df[target_col].astype(str).str.lower().str.strip()

le = LabelEncoder()
y_enc = le.fit_transform(y)

X_train, X_test, y_train, y_test = train_test_split(
    X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
)

model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

os.makedirs("ml_models", exist_ok=True)
dump({"model": model, "label_encoder": le, "feature_cols": feature_cols},
     "ml_models/crop_rec.joblib")

print("Training complete! Model saved to: ml_models/crop_rec.joblib")
print("Test Accuracy:", model.score(X_test, y_test))
