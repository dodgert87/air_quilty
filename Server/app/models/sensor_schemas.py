from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SensorCreate(BaseModel):
    id: str = Field(..., description="Sensor device ID")
    location: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    is_active: bool = True


class SensorUpdate(BaseModel):
    location: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    is_active: Optional[bool] = None


class SensorOut(SensorCreate):
    created_at: datetime
