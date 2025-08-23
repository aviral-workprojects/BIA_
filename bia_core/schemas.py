"""
Data schemas and models for BIA application using Pydantic.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from bia_core import SUPPORTED_CITIES, WASTE_TYPES

class UserProfile(BaseModel):
    """User profile data model"""
    username: str = Field(..., min_length=3, max_length=50)
    password_hash: str
    entity_name: str = Field(..., min_length=2, max_length=100)
    city: str
    waste_type: str
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    
    @validator('city')
    def validate_city(cls, v):
        if v not in SUPPORTED_CITIES:
            raise ValueError(f"City must be one of: {', '.join(SUPPORTED_CITIES)}")
        return v
    
    @validator('waste_type')
    def validate_waste_type(cls, v):
        if v not in WASTE_TYPES:
            raise ValueError(f"Waste type must be one of: {', '.join(WASTE_TYPES)}")
        return v

class WasteLog(BaseModel):
    """Waste log entry data model"""
    username: str
    date: date
    waste_tons: float = Field(..., gt=0, le=1000)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    
    @validator('waste_tons')
    def validate_waste_amount(cls, v):
        if v <= 0:
            raise ValueError("Waste amount must be positive")
        if v > 1000:
            raise ValueError("Waste amount seems unreasonably high (>1000 tons)")
        return v

class ForecastInput(BaseModel):
    """Input parameters for forecasting"""
    historical_data: List[float]
    forecast_horizon: int = Field(..., ge=1, le=365)
    growth_rate: Optional[float] = Field(default=0.02, ge=-0.5, le=1.0)
    
    @validator('forecast_horizon')
    def validate_horizon(cls, v):
        if v < 1 or v > 365:
            raise ValueError("Forecast horizon must be between 1 and 365 days")
        return v

class FinancialParameters(BaseModel):
    """Financial calculation parameters"""
    yield_rate: float = Field(..., gt=0, le=3000)  # kWh/ton
    capacity_factor: float = Field(..., gt=0, le=1)  # fraction
    tariff: float = Field(..., gt=0, le=20)  # ₹/kWh
    opex_per_ton: float = Field(..., ge=0, le=5000)  # ₹/ton
    fixed_opex: float = Field(..., ge=0)  # ₹/year
    capex: float = Field(..., gt=0)  # ₹
    discount_rate: float = Field(..., gt=0, le=1)  # fraction
    horizon_years: int = Field(..., ge=1, le=50)
    
    @validator('yield_rate')
    def validate_yield(cls, v):
        if v < 100 or v > 3000:
            raise ValueError("Yield rate should be between 100-3000 kWh/ton")
        return v
    
    @validator('capacity_factor')
    def validate_capacity_factor(cls, v):
        if v <= 0 or v > 1:
            raise ValueError("Capacity factor must be between 0 and 1")
        return v
    
    @validator('tariff')
    def validate_tariff(cls, v):
        if v <= 0 or v > 20:
            raise ValueError("Tariff should be between 0-20 ₹/kWh")
        return v

class FacilityData(BaseModel):
    """Facility information data model"""
    name: str
    city: str
    state: str
    type: str
    capacity_mw: float = Field(..., ge=0)
    status: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    source: str
    
    @validator('capacity_mw')
    def validate_capacity(cls, v):
        if v < 0:
            raise ValueError("Capacity cannot be negative")
        return v

class CashflowItem(BaseModel):
    """Single year cashflow item"""
    year: int
    waste_tons: float
    electricity_kwh: float
    revenue: float
    opex: float
    ncf: float  # Net cash flow
    
    @validator('year')
    def validate_year(cls, v):
        if v < 1:
            raise ValueError("Year must be positive")
        return v

class NPVResults(BaseModel):
    """NPV calculation results"""
    npv: float
    payback_years: float
    roi_percent: float
    total_revenue: float
    total_opex: float
    co2_savings_tons: float
    trees_equivalent: int
