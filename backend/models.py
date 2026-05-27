# backend/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from .db import Base
from datetime import datetime
from typing import Optional

class Farmer(Base):
    __tablename__ = "farmers"

    id: int = Column(Integer, primary_key=True, index=True)
    name: Optional[str] = Column(String(100), nullable=True)
    mobile: Optional[str] = Column(String(20), unique=True, index=True, nullable=False)
    language: Optional[str] = Column(String(20), nullable=True)
    created_at: DateTime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    crop_requests = relationship("CropRequest", back_populates="farmer", cascade="all, delete-orphan", lazy="select")
    disease_detections = relationship("DiseaseDetection", back_populates="farmer", cascade="all, delete-orphan", lazy="select")
    irrigation_logs = relationship("IrrigationLog", back_populates="farmer", cascade="all, delete-orphan", lazy="select")
    fertilizer_logs = relationship("FertilizerLog", back_populates="farmer", cascade="all, delete-orphan", lazy="select")

    def __repr__(self):
        return f"<Farmer id={self.id} mobile={self.mobile} name={self.name}>"

class CropRequest(Base):
    __tablename__ = "crop_requests"

    id: int = Column(Integer, primary_key=True, index=True)
    farmer_id: Optional[int] = Column(Integer, ForeignKey("farmers.id"), nullable=True, index=True)
    soil_type: Optional[str] = Column(String(50), nullable=True)
    rainfall: Optional[float] = Column(Float, nullable=True)
    temperature: Optional[float] = Column(Float, nullable=True)
    recommended_crop: Optional[str] = Column(String(200), nullable=True)
    created_at: DateTime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship to farmer
    farmer = relationship("Farmer", back_populates="crop_requests", lazy="joined")

    def __repr__(self):
        return f"<CropRequest id={self.id} farmer_id={self.farmer_id} rec={self.recommended_crop}>"

class DiseaseDetection(Base):
    __tablename__ = "disease_detections"

    id: int = Column(Integer, primary_key=True, index=True)
    farmer_id: Optional[int] = Column(Integer, ForeignKey("farmers.id"), nullable=True, index=True)
    crop: Optional[str] = Column(String(100), nullable=True)
    disease: Optional[str] = Column(String(200), nullable=True)
    confidence: Optional[float] = Column(Float, nullable=True)
    notes: Optional[str] = Column(Text, nullable=True)
    created_at: DateTime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship to farmer
    farmer = relationship("Farmer", back_populates="disease_detections", lazy="joined")

    def __repr__(self):
        return f"<DiseaseDetection id={self.id} disease={self.disease} conf={self.confidence}>"

class IrrigationLog(Base):
    __tablename__ = "irrigation_logs"

    id: int = Column(Integer, primary_key=True, index=True)
    farmer_id: Optional[int] = Column(Integer, ForeignKey("farmers.id"), nullable=True, index=True)
    crop: Optional[str] = Column(String(100), nullable=True)
    recommended_at: DateTime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    recommendation: Optional[str] = Column(Text, nullable=True)

    # Relationship to farmer
    farmer = relationship("Farmer", back_populates="irrigation_logs", lazy="joined")

    def __repr__(self):
        return f"<IrrigationLog id={self.id} farmer_id={self.farmer_id}>"

class FertilizerLog(Base):
    __tablename__ = "fertilizer_logs"

    id: int = Column(Integer, primary_key=True, index=True)
    farmer_id: Optional[int] = Column(Integer, ForeignKey("farmers.id"), nullable=True, index=True)
    crop: Optional[str] = Column(String(100), nullable=True)
    n: Optional[float] = Column(Float, nullable=True)
    p: Optional[float] = Column(Float, nullable=True)
    k: Optional[float] = Column(Float, nullable=True)
    plan: Optional[str] = Column(Text, nullable=True)
    estimated_cost: Optional[float] = Column(Float, nullable=True)
    created_at: DateTime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship to farmer
    farmer = relationship("Farmer", back_populates="fertilizer_logs", lazy="joined")

    def __repr__(self):
        return f"<FertilizerLog id={self.id} crop={self.crop} est_cost={self.estimated_cost}>"
