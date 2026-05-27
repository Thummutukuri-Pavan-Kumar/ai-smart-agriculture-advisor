from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# ----------------------------
# Farmer Schemas
# ----------------------------
class FarmerCreate(BaseModel):
    name: str
    mobile: str
    language: Optional[str] = "en"

class FarmerOut(BaseModel):
    id: int
    name: str
    mobile: str
    language: str

    class Config:
        orm_mode = True

# ----------------------------
# Crop Recommendation
# ----------------------------
class CropRequestIn(BaseModel):
    # Inputs expected by the ML model
    N: Optional[float] = None
    P: Optional[float] = None
    K: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    ph: Optional[float] = None
    rainfall: Optional[float] = None
    soil_type: Optional[str] = None
    area_acres: Optional[float] = None

class CropRecommendationOut(BaseModel):
    recommended: List[str]
    reasons: Optional[str] = None

# ----------------------------
# Fertilizer Request
# ----------------------------
class FertilizerRequest(BaseModel):
    n: float
    p: float
    k: float
    crop: Optional[str] = "default"

class FertilizerOut(BaseModel):
    fertilizer_plan: str
    cost_breakdown: Optional[Dict[str, Dict[str, Any]]] = None
    estimated_cost: Optional[float] = None

# ----------------------------
# Disease Detection
# ----------------------------
class DiseaseOut(BaseModel):
    disease: str
    confidence: float
    treatment: Optional[str] = None
    model_used: bool
    saved_image: Optional[str] = None
    error: Optional[str] = None

# ----------------------------
# Irrigation Advice (UPDATED)
# ----------------------------
class IrrigationRequest(BaseModel):
    # Required fields (based on your screenshot)
    location: str
    crop: str
    soil_moisture: float  # <--- This was missing and caused the error
    area_acres: float           # <--- Added this to match your frontend input
    
    # Optional fields (if you want to keep them for future logic)
    farmer_id: Optional[int] = None
    sowing_date: Optional[str] = None
    last_irrigation_date: Optional[str] = None

class IrrigationOut(BaseModel):
    when: str
    how_much: str
    notes: Optional[str] = None

# ----------------------------
# Market & Yield
# ----------------------------
class MarketRequest(BaseModel):
    crop: str
    location: str

class MarketOut(BaseModel):
    current_prices: Dict[str, float]
    predicted_trend: str
    best_market: Optional[str] = None

class YieldRequest(BaseModel):
    crop: str
    area_acres: float
    soil_N: Optional[float] = None
    soil_P: Optional[float] = None
    soil_K: Optional[float] = None
    ph: Optional[float] = None
    rainfall: Optional[float] = None
    temperature: Optional[float] = None

class YieldOut(BaseModel):
    predicted_yield_per_acre: float
    total_harvest: float
    estimated_income: Optional[float] = None
