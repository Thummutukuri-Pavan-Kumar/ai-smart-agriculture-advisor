# backend/routes.py
import os
import uuid
import traceback
import hashlib
import math
import joblib
from io import BytesIO
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session
from PIL import Image
import numpy as np

# optional tensorflow import (lazy use)
try:
    import tensorflow as tf
except Exception:
    tf = None

from .db import SessionLocal
from . import models, schemas
from .utils import call_openweather_city, estimate_next_24h_rain_mm
from .schemas import FertilizerRequest
from .models import FertilizerLog

router = APIRouter()

# ----------------------
# DB dependency
# ----------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------
# Model holders
# ----------------------
crop_model: Optional[Dict[str, Any]] = None         # expected dict {"model": ..., "label_encoder": ..., "feature_cols": [...]}
_disease_model: Optional[Any] = None                # tensorflow model if available
_index_to_label: Dict[int, str] = {}

# Yield model holder
_yield_model: Optional[Any] = None

# ----------------------
# Upload / model paths + helpers
# ----------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ML_MODELS_DIR = os.path.join(BASE_DIR, "ml_models")
UPLOAD_DIR = os.path.join(ML_MODELS_DIR, "uploads")
MODEL_PATH = os.path.join(ML_MODELS_DIR, "disease_model.h5")
CROP_MODEL_PATH = os.path.join(ML_MODELS_DIR, "crop_rec.joblib")
CLASS_INDICES_PATH = os.path.join(ML_MODELS_DIR, "disease_class_indices.npy")
YIELD_MODEL_PATH = os.path.join(ML_MODELS_DIR, "yield_model.joblib")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Default disease meta (index -> {disease, treatment})
DISEASE_META = {
    0: {"disease": "healthy", "treatment": "No action needed; monitor crop."},
    1: {"disease": "bacterial_spot", "treatment": "Remove infected leaves; apply recommended antibacterial spray; improve drainage."},
    2: {"disease": "early_blight", "treatment": "Use recommended fungicide (e.g. mancozeb); remove crop debris and improve sanitation."},
    3: {"disease": "late_blight", "treatment": "Remove affected plants; apply a systemic fungicide as advised by extension."},
    4: {"disease": "powdery_mildew", "treatment": "Apply sulfur/micronutrient sprays; increase airflow and reduce humidity around canopy."},
}

# Maximum allowed upload size in bytes (12 MB default)
MAX_UPLOAD_BYTES = 12 * 1024 * 1024

def _safe_filename(name: str) -> str:
    """Return a sanitized filename (very simple)."""
    base = os.path.basename(name)
    # remove suspicious characters
    allowed = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    safe = "".join(c for c in base if c in allowed).strip()
    if not safe:
        safe = uuid.uuid4().hex
    return safe

def _preprocess_image_for_model(pil_image: Image.Image, target_size=(224, 224)):
    """
    Preprocessing: convert to RGB, resize, scale to 0-1 and return numpy batch shape (1, H, W, C).
    If the model requires different preprocessing, update here.
    """
    img = pil_image.convert("RGB").resize(target_size)
    arr = np.array(img).astype("float32") / 255.0
    return np.expand_dims(arr, 0)

# ----------------------
# Load models at module import / startup
# ----------------------
def load_models_at_startup():
    """
    Loads crop model, class indices, tensor model (if available), and yield model.
    This is safe to call multiple times; each loader handles exceptions internally.
    """
    global crop_model, _disease_model, _index_to_label, DISEASE_META, _yield_model

    # load crop model (joblib)
    try:
        if os.path.exists(CROP_MODEL_PATH):
            crop_model = joblib.load(CROP_MODEL_PATH)
            print(f"[models] Loaded crop model: {CROP_MODEL_PATH}")
        else:
            crop_model = None
            print("[models] No crop_rec.joblib found; crop_model left as None.")
    except Exception as e:
        crop_model = None
        print("[models] Error loading crop model:", e)
        traceback.print_exc()

    # load class indices mapping if present
    try:
        if os.path.exists(CLASS_INDICES_PATH):
            loaded = np.load(CLASS_INDICES_PATH, allow_pickle=True)
            if isinstance(loaded, np.ndarray) and loaded.shape == ():
                mapping = loaded.item()
            else:
                try:
                    mapping = dict(loaded)
                except Exception:
                    mapping = {}
            _index_to_label = {int(v): str(k) for k, v in mapping.items()}
            new_meta = {}
            for idx, label in _index_to_label.items():
                existing = DISEASE_META.get(idx, {})
                treatment = existing.get("treatment", f"General recommendation for {label}: remove infected tissue and consult local agronomist.")
                new_meta[idx] = {"disease": label, "treatment": treatment}
            DISEASE_META = new_meta
            print("[models] Loaded class indices mapping:", _index_to_label)
        else:
            print("[models] No disease_class_indices.npy found; using default DISEASE_META.")
    except Exception as e:
        print("[models] Failed to load class indices:", e)
        traceback.print_exc()

    # load TensorFlow model if available
    try:
        if os.path.exists(MODEL_PATH) and tf is not None:
            _disease_model = tf.keras.models.load_model(MODEL_PATH)
            print("[models] Loaded disease model:", MODEL_PATH)
        else:
            _disease_model = None
            if not os.path.exists(MODEL_PATH):
                print("[models] No disease_model.h5 found; using placeholder heuristic.")
            else:
                print("[models] TensorFlow not available; cannot load disease model.")
    except Exception as e:
        _disease_model = None
        print("[models] Error loading disease model:", e)
        traceback.print_exc()

    # load yield model (joblib pipeline) if present
    try:
        if os.path.exists(YIELD_MODEL_PATH):
            _yield_model = joblib.load(YIELD_MODEL_PATH)
            print("[models] Loaded yield model:", YIELD_MODEL_PATH)
        else:
            _yield_model = None
            print("[models] No yield_model.joblib found; falling back to heuristic for yield predictions.")
    except Exception as e:
        _yield_model = None
        print("[models] Error loading yield model:", e)
        traceback.print_exc()

# run model loader on import so uvicorn shows statuses
load_models_at_startup()

# ----------------------
# Farmer register
# ----------------------
@router.post("/register_farmer", response_model=schemas.FarmerOut)
def register_farmer(payload: schemas.FarmerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Farmer).filter(models.Farmer.mobile == payload.mobile).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mobile already registered")
    f = models.Farmer(name=payload.name, mobile=payload.mobile, language=payload.language)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f

# ----------------------
# Crop recommendation
# ----------------------
@router.post("/predict_crop")
async def predict_crop(request: Request, payload: schemas.CropRequestIn, db: Session = Depends(get_db)):
    """
    Predict crop; returns JSON by default but if client requests text/plain (Accept header or ?format=plain)
    returns human-readable structured text.
    """
    global crop_model
    recs = []
    reasons_list = []
    probabilities: Dict[str, float] = {}

    try:
        if crop_model and isinstance(crop_model, dict) and crop_model.get("model") is not None:
            model = crop_model["model"]
            le = crop_model.get("label_encoder")
            feature_cols = crop_model.get("feature_cols") or []

            try:
                X_row = []
                for f in feature_cols:
                    val = payload.dict().get(f, 0.0)
                    try:
                        X_row.append(float(val))
                    except Exception:
                        X_row.append(0.0)
                X = [X_row]
                pred_encoded = model.predict(X)
                pred_val = pred_encoded[0] if hasattr(pred_encoded, "__iter__") else pred_encoded
                if le:
                    try:
                        pred_decoded = le.inverse_transform([pred_val])
                        recs = [str(pred_decoded[0])]
                    except Exception:
                        recs = [str(pred_val)]
                else:
                    recs = [str(pred_val)]

                reasons_list.append("After analyzing your soil's nutrient profile (N-P-K) and analyzing current rainfall patterns, our model has identified the optimal crop for your land.")

                # probabilities if available
                try:
                    if hasattr(model, "predict_proba"):
                        probs = model.predict_proba(X)[0]
                        classes = getattr(model, "classes_", None)
                        if classes is not None:
                            for cls, p in zip(classes, probs):
                                cls_name = cls
                                try:
                                    if le is not None and hasattr(le, "inverse_transform"):
                                        cls_name = le.inverse_transform([cls])[0]
                                except Exception:
                                    cls_name = cls
                                probabilities[str(cls_name)] = float(round(float(p), 6))
                except Exception:
                    pass

            except Exception as e:
                reasons_list.append(f"Model prediction error: {e}")
                traceback.print_exc()
        else:
            reasons_list.append("Model not loaded; using fallback heuristic.")
            try:
                rf = float(payload.rainfall or 0.0)
            except Exception:
                rf = 0.0
            if rf >= 250:
                recs = ["rice"]
            elif 100 <= rf < 250:
                recs = ["maize"]
            elif 30 <= rf < 100:
                recs = ["pigeonpeas"]
            else:
                recs = ["unknown"]
    except Exception as e:
        reasons_list.append(f"Unhandled error during prediction: {e}")
        traceback.print_exc()
        if not recs:
            recs = ["unknown"]

    # persist request (best-effort)
    try:
        cr = models.CropRequest(
            soil_type=payload.soil_type or "",
            rainfall=payload.rainfall or 0.0,
            temperature=payload.temperature or 0.0,
            recommended_crop=",".join(recs)
        )
        db.add(cr)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    json_response = {"recommended": recs, "reasons": "; ".join(reasons_list) or "No reasons available"}
    if probabilities:
        json_response["probabilities"] = probabilities

    qs_format = str(request.query_params.get("format", "")).lower()
    accept = request.headers.get("accept", "")
    want_plain = (qs_format in ("plain", "text", "struct")) or ("text/plain" in accept)

    if want_plain:
        top_crop = recs[0] if recs else "unknown"
        lines = [f"Predicted crop: {top_crop}", "", "Why recommended:"]
        if reasons_list:
            for r in reasons_list:
                lines.append(f"- {r}")
        else:
            lines.append("- No specific reason provided.")
        if probabilities:
            lines.append("")
            lines.append("Top probabilities:")
            for crop_name, p in sorted(probabilities.items(), key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"- {crop_name}: {(float(p) * 100):.1f}%")
        return PlainTextResponse("\n".join(lines))

    return JSONResponse(content=json_response)

# ----------------------
# Fertilizer recommendation
# ----------------------
@router.post("/fertilizer")
def fertilizer_recommendation(payload: FertilizerRequest, db: Session = Depends(get_db)):
    # --- crop target nutrients (kg nutrient / acre) ---
    crop_targets = {
        "rice": {"N": 120.0, "P": 60.0, "K": 40.0},
        "maize": {"N": 90.0, "P": 50.0, "K": 40.0},
        "groundnut": {"N": 20.0, "P": 40.0, "K": 20.0},
        "blackgram": {"N": 20.0, "P": 40.0, "K": 20.0},
        "kidneybeans": {"N": 25.0, "P": 40.0, "K": 25.0},
        "paddy": {"N": 120.0, "P": 60.0, "K": 40.0},
        "wheat": {"N": 120.0, "P": 60.0, "K": 40.0},
        "default": {"N": 60.0, "P": 30.0, "K": 30.0}
    }
    UREA_N = 0.46
    DAP_N = 0.18
    DAP_P = 0.20
    MOP_K = 0.60
    price_per_kg = {"Urea": 0.6, "DAP": 0.8, "MOP": 0.5, "SSP": 0.3}

    crop_key = (payload.crop or "default").strip().lower()
    if crop_key in ["paddy", "rice"]:
        target = crop_targets["rice"]
    elif crop_key in ["maize", "corn"]:
        target = crop_targets["maize"]
    elif crop_key in ["groundnut", "peanut"]:
        target = crop_targets["groundnut"]
    elif crop_key in ["blackgram", "urd", "urad"]:
        target = crop_targets["blackgram"]
    elif crop_key in ["kidneybeans", "rajma"]:
        target = crop_targets["kidneybeans"]
    else:
        target = crop_targets.get(crop_key, crop_targets["default"])

    try:
        cur_n = float(payload.n or 0.0)
    except Exception:
        cur_n = 0.0
    try:
        cur_p = float(payload.p or 0.0)
    except Exception:
        cur_p = 0.0
    try:
        cur_k = float(payload.k or 0.0)
    except Exception:
        cur_k = 0.0

    deficit_n = max(target["N"] - cur_n, 0.0)
    deficit_p = max(target["P"] - cur_p, 0.0)
    deficit_k = max(target["K"] - cur_k, 0.0)

    plan_parts = []
    cost_breakdown = {}
    total_cost = 0.0

    dap_kg = 0.0
    n_from_dap = 0.0
    if deficit_p > 0 and DAP_P > 0:
        dap_kg = round(deficit_p / DAP_P, 2)
        n_from_dap = round(dap_kg * DAP_N, 2)
        dap_cost = round(dap_kg * price_per_kg.get("DAP", 0.0), 2)
        plan_parts.append(f"Apply DAP at sowing: {dap_kg} kg/acre to provide ~{round(deficit_p,1)} kg P (DAP also supplies ~{n_from_dap} kg N).")
        cost_breakdown["DAP"] = {"kg": dap_kg, "cost": dap_cost}
        total_cost += dap_cost

    mop_kg = 0.0
    mop_cost = 0.0
    if deficit_k > 0 and MOP_K > 0:
        mop_kg = round(deficit_k / MOP_K, 2)
        mop_cost = round(mop_kg * price_per_kg.get("MOP", 0.0), 2)
        plan_parts.append(f"Apply MOP: {mop_kg} kg/acre to provide ~{round(deficit_k,1)} kg K.")
        cost_breakdown["MOP"] = {"kg": mop_kg, "cost": mop_cost}
        total_cost += mop_cost

    remaining_n_deficit = max(deficit_n - n_from_dap, 0.0)
    urea_kg = 0.0
    urea_cost = 0.0
    if remaining_n_deficit > 0 and UREA_N > 0:
        urea_kg = round(remaining_n_deficit / UREA_N, 2)
        urea_cost = round(urea_kg * price_per_kg.get("Urea", 0.0), 2)
        plan_parts.append(f"Apply Urea (split doses): {urea_kg} kg/acre to supply ~{round(remaining_n_deficit,1)} kg N.")
        cost_breakdown["Urea"] = {"kg": urea_kg, "cost": urea_cost}
        total_cost += urea_cost

    if not plan_parts:
        plan_parts.append("Soil nutrient levels are adequate for the crop based on the provided values.")

    fertilizer_plan = " ; ".join(plan_parts)
    estimated_cost = round(total_cost, 2)

    try:
        flog = FertilizerLog(
            crop=payload.crop or "",
            n=cur_n, p=cur_p, k=cur_k,
            plan=fertilizer_plan,
            estimated_cost=estimated_cost
        )
        db.add(flog)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    return JSONResponse(content={
        "fertilizer_plan": fertilizer_plan,
        "cost_breakdown": cost_breakdown,
        "estimated_cost": estimated_cost
    })

# ----------------------
# Disease detection endpoint (kept robust)
# ----------------------
@router.post("/detect_disease")
async def detect_disease(file: UploadFile = File(...), db: Session = Depends(get_db)):
    original_filename = file.filename or f"{uuid.uuid4().hex}.jpg"
    safe_name = _safe_filename(original_filename)
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Unsupported file type"})

    try:
        file_bytes = await file.read()
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": f"Failed to read upload: {e}"})

    if len(file_bytes) == 0:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Empty file uploaded"})
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, content={"error": f"File too large (max {MAX_UPLOAD_BYTES} bytes)"})

    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(os.path.abspath(UPLOAD_DIR), saved_name)
    try:
        with open(saved_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": f"Failed to save file: {e}"})

    try:
        pil_img = Image.open(BytesIO(file_bytes)).convert("RGB")
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": f"Invalid image: {e}"})

    try:
        if _disease_model is not None:
            inp = _preprocess_image_for_model(pil_img, target_size=(224, 224))
            preds = _disease_model.predict(inp)
            if isinstance(preds, np.ndarray):
                if preds.ndim == 2:
                    probs = preds[0]
                    class_idx = int(np.argmax(probs))
                    confidence = float(round(float(probs[class_idx]), 4))
                else:
                    try:
                        class_idx = int(np.argmax(preds))
                        confidence = float(round(float(np.max(preds)), 4))
                    except Exception:
                        class_idx = 0
                        confidence = 1.0
            else:
                try:
                    arr = np.array(preds)
                    class_idx = int(np.argmax(arr))
                    confidence = float(round(float(np.max(arr)), 4))
                except Exception:
                    class_idx = 0
                    confidence = 1.0

            meta = DISEASE_META.get(class_idx, {"disease": f"class_{class_idx}", "treatment": "No treatment info available."})
            result = {
                "disease": meta.get("disease", f"class_{class_idx}"),
                "confidence": confidence,
                "treatment": meta.get("treatment", ""),
                "model_used": True,
                "saved_image": saved_path
            }
        else:
            arr = np.array(pil_img.resize((64, 64))).astype("float32")
            g_mean = float(arr[:, :, 1].mean())
            if g_mean < 90:
                disease = "leaf_spot_placeholder"
                treatment = "Possible leaf stress or disease detected. Provide clearer leaf image and consult extension services."
                confidence = 0.55
            else:
                disease = "healthy"
                treatment = "No obvious disease visible (placeholder heuristic)."
                confidence = 0.6
            result = {
                "disease": disease,
                "confidence": confidence,
                "treatment": treatment,
                "model_used": False,
                "saved_image": saved_path
            }
    except Exception as e:
        traceback.print_exc()
        result = {
            "disease": "unknown",
            "confidence": 0.0,
            "treatment": "Model prediction failed. See server logs.",
            "model_used": bool(_disease_model),
            "error": str(e),
            "saved_image": saved_path
        }

    try:
        if hasattr(models, "DiseaseDetection"):
            dd = models.DiseaseDetection(crop="", disease=result.get("disease", ""), confidence=float(result.get("confidence") or 0.0), notes=result.get("treatment",""))
            db.add(dd)
            db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    return JSONResponse(status_code=status.HTTP_200_OK, content=result)

# ----------------------
# Irrigation advice (improved and structured)
# ----------------------
@router.post("/irrigation_advice")
def irrigation_advice(payload: schemas.IrrigationRequest, db: Session = Depends(get_db)):
    """
    Improved irrigation advice:
      Input (IrrigationRequest): location (str), crop (str), soil_moisture (float), area_acres (float), optional pump_flow_lph
      Returns JSON:
        {
          "when": "Irrigate soon" | "No immediate irrigation needed" | ...,
          "how_much_mm": float,
          "how_much_liters": int,
          "pump_duration_minutes": int,
          "notes": "..."
        }
    """
    try:
        location = (payload.location or "").strip()
        crop = (payload.crop or "").strip().lower()
        soil_moisture = payload.soil_moisture if payload.soil_moisture is not None else None
        area_acres = float(payload.area_acres or 1.0)
        pump_flow_lph = float(getattr(payload, "pump_flow_lph", None) or 3600.0)

        # crop defaults (root zone mm and target moisture%)
        crop_root_mm = {"paddy": 200, "rice": 200, "maize": 150, "cotton": 150, "groundnut": 100, "default": 150}
        target_moisture = {"paddy": 60, "rice": 60, "maize": 55, "cotton": 50, "groundnut": 50, "default": 55}

        root_mm = crop_root_mm.get(crop, crop_root_mm["default"])
        target_pct = target_moisture.get(crop, target_moisture["default"])

        # get weather (onecall preferred)
        ow = call_openweather_city(location) if location else None

        # debug log - print a short JSON snippet to server logs for inspection
        try:
            import json
            print("[routes.irrigation_advice] openweather response for", location, "->", json.dumps(ow, default=str)[:2000], flush=True)
        except Exception:
            print("[routes.irrigation_advice] openweather response present?", bool(ow), flush=True)

        expected_rain_mm = estimate_next_24h_rain_mm(ow)
        print(f"[routes.irrigation_advice] expected_rain_mm={expected_rain_mm}", flush=True)

        notes_parts = []
        if ow:
            notes_parts.append(f"Expected rain (24h): {expected_rain_mm:.1f} mm (from weather).")
        else:
            notes_parts.append("Weather data not available; using heuristics.")

        # compute need
        if soil_moisture is not None:
            try:
                sm = float(soil_moisture)
            except Exception:
                sm = None
            if sm is None:
                when = "Check soil moisture"
                how_much_mm = 0.0
                how_much_liters = 0.0
                pump_minutes = 0
                notes_parts.append("Invalid soil moisture value provided.")
            else:
                if sm >= target_pct:
                    when = "No immediate irrigation needed"
                    how_much_mm = 0.0
                    how_much_liters = 0.0
                    pump_minutes = 0
                    notes_parts.append(f"Soil moisture {sm:.0f}% >= target {target_pct}%.")
                else:
                    deficit_pct = max(target_pct - sm, 0.0)
                    how_much_mm = round((deficit_pct / 100.0) * root_mm, 1)
                    how_much_mm_after_rain = max(how_much_mm - expected_rain_mm, 0.0)
                    area_m2_per_acre = 4046.86
                    total_liters = how_much_mm_after_rain * area_acres * area_m2_per_acre
                    pump_hours = total_liters / max(pump_flow_lph, 1.0)
                    pump_minutes = int(round(pump_hours * 60))
                    how_much_liters = int(round(total_liters))
                    when = "Irrigate soon" if how_much_mm_after_rain > 0 else "Wait for rain"
                    notes_parts.append(f"Deficit: {deficit_pct:.1f}% of root zone ({root_mm} mm).")
                    if expected_rain_mm > 0:
                        notes_parts.append(f"After expected rain (-{expected_rain_mm:.1f} mm): need {how_much_mm_after_rain:.1f} mm.")
        else:
            # fallback heuristics when soil moisture is unknown
            if ow and ow.get("current"):
                temp = ow["current"].get("temp")
                humidity = ow["current"].get("humidity")
                if temp is not None and temp > 30 and (humidity is None or humidity < 50):
                    when = "Irrigate today (hot and dry)"
                    how_much_mm = 10.0
                else:
                    when = "No immediate irrigation needed"
                    how_much_mm = 0.0
            else:
                when = "No data"
                how_much_mm = 0.0
            how_much_liters = int(round(how_much_mm * area_acres * 4046.86)) if how_much_mm > 0 else 0
            pump_minutes = int(round((how_much_liters / max(pump_flow_lph, 1.0)) * 60)) if how_much_liters > 0 else 0

        response = {
            "when": when,
            "how_much_mm": round(float(how_much_mm if 'how_much_mm' in locals() else 0.0), 1),
            "how_much_liters": int(how_much_liters if 'how_much_liters' in locals() else 0),
            "pump_duration_minutes": pump_minutes,
            "notes": " ".join(notes_parts)
        }

        # log to DB (best-effort)
        try:
            if hasattr(models, "IrrigationLog"):
                log = models.IrrigationLog(
                    farmer_id = getattr(payload, "farmer_id", None),
                    crop = payload.crop or "",
                    recommended_at = None,
                    recommendation = f"When: {response['when']}; How much: {response['how_much_mm']} mm; Notes: {response['notes']}"
                )
                db.add(log)
                db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

        return JSONResponse(content=response)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------
# Market price (placeholder)
# ----------------------
@router.post("/market_price", response_model=schemas.MarketOut)
def market_price(payload: schemas.MarketRequest):
    """
    Mock but useful market price implementation for testing the frontend.
    - Uses crop base prices and a deterministic location-based modifier so different locations
      get different prices but results are reproducible.
    - Returns structure: { current_prices: { location: price }, predicted_trend, best_market }
    """
    # base price per crop (INR per quintal or unit you prefer)
    base_prices = {
        "rice": 1800,
        "maize": 1400,
        "wheat": 1600,
        "tomato": 3500,
        "potato": 900,
        "groundnut": 4500,
        "default": 2000
    }

    crop_key = (payload.crop or "").strip().lower()
    base = base_prices.get(crop_key, base_prices["default"])

    # deterministic location factor (so same input always maps to same price)
    loc = (payload.location or "unknown").strip().lower()
    # create a small pseudo-random modifier using SHA1 hash (reproducible)
    h = hashlib.sha1(f"{crop_key}|{loc}".encode("utf-8")).hexdigest()
    # take last 6 hex chars, convert to int, map to [-0.12, +0.12] (±12%)
    v = int(h[-6:], 16)
    frac = (v / float(0xFFFFFF))  # [0,1)
    # center around 0 => [-0.12..+0.12]
    modifier = (frac - 0.5) * 0.24
    price = int(max(0, math.ceil(base * (1 + modifier))))  # ensure positive, round up

    # produce small set of nearby market prices for demonstration (nearby markets)
    nearby = [loc]
    # create 2 synthetic nearby market names for UI variety
    nearby.append(loc + "-market-1")
    nearby.append(loc + "-market-2")

    current_prices = {}
    for i, m in enumerate(nearby):
        # derive slightly different price per market using additional hash tweak
        hh = hashlib.sha1(f"{crop_key}|{m}|{i}".encode("utf-8")).hexdigest()
        vv = int(hh[-4:], 16) / float(0xFFFF)
        tweak = (vv - 0.5) * 0.08  # ±4%
        p = int(max(0, math.ceil(price * (1 + tweak))))
        current_prices[m] = p

    # pick best market as the one with highest price (simple heuristic)
    best_market = max(current_prices.items(), key=lambda kv: kv[1])[0]
    # simple trend inference: if modifier > 0.05 => rising, < -0.05 => falling else stable
    predicted_trend = "rising" if modifier > 0.05 else ("falling" if modifier < -0.05 else "stable")

    return {"current_prices": current_prices, "predicted_trend": predicted_trend, "best_market": best_market}

# ----------------------
# Yield prediction
# ----------------------
@router.post("/predict_yield")
def predict_yield(payload: schemas.YieldRequest):
    """
    Input: expected fields:
      - crop (str), area_acres (float)
    Optional (frontend can send): prev_yield_per_acre, n, p, k, ph, avg_temp, total_rainfall_30d, expected_price_per_unit
    Uses a loaded pipeline if available, otherwise falls back to a simple per-crop baseline.
    """
    crop = (payload.crop or "").strip().lower()
    area = float(payload.area_acres or 1.0)

    # Attempt model prediction
    try:
        global _yield_model
        if _yield_model is not None:
            # build input row with optional fields and defaults
            features = {
                "crop": crop,
                "area_acres": area,
                "prev_yield_per_acre": float(getattr(payload, "prev_yield_per_acre", 0.0) or 0.0),
                "n": float(getattr(payload, "n", 0.0) or 0.0),
                "p": float(getattr(payload, "p", 0.0) or 0.0),
                "k": float(getattr(payload, "k", 0.0) or 0.0),
                "ph": float(getattr(payload, "ph", 7.0) or 7.0),
                "avg_temp": float(getattr(payload, "avg_temp", 25.0) or 25.0),
                "total_rainfall_30d": float(getattr(payload, "total_rainfall_30d", 0.0) or 0.0),
            }
            # convert to DataFrame and call pipeline
            import pandas as pd
            df = pd.DataFrame([features])

            # Some pipelines expect specific column order or one-hot columns.
            # If the pipeline was trained to accept raw DataFrame with "crop" column and does encoding inside,
            # this will work. If not, train a pipeline that accepts these raw columns.
            pred = _yield_model.predict(df)
            pred_yield_per_acre = float(pred[0]) if (hasattr(pred, "__iter__") and len(pred) > 0) else float(pred)
            pred_yield_per_acre = max(pred_yield_per_acre, 0.0)
            total_harvest = pred_yield_per_acre * area
            est_price = float(getattr(payload, "expected_price_per_unit", 1900.0) or 1900.0)
            est_income = total_harvest * est_price
            return {"predicted_yield_per_acre": round(pred_yield_per_acre, 2), "total_harvest": round(total_harvest, 2), "estimated_income": round(est_income, 2)}
    except Exception as e:
        # model failure: print server logs and fall back gracefully
        print("Yield model prediction failed:", e)
        traceback.print_exc()

    # fallback heuristic using simple per-crop baseline (replace with real regional averages)
    baseline = {
        "paddy": 30, "rice": 30, "maize": 20, "groundnut": 8, "tomato": 20, "wheat": 25, "default": 10
    }
    per_acre = baseline.get(crop, baseline["default"])
    total = per_acre * area
    est_price = float(getattr(payload, "expected_price_per_unit", 1900.0) or 1900.0)
    est_income = total * est_price
    return {"predicted_yield_per_acre": per_acre, "total_harvest": total, "estimated_income": est_income}



#(.venv) PS E:\agri_advisor\frontend> python -m http.server 5500 --bind 127.0.0.1  . this is for running frontend
#(.venv) PS E:\agri_advisor> python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000  .this for running backend