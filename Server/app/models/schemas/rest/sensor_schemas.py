from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SensorCreate(BaseModel):
    sensor_id: UUID
    name: str
    location: Optional[str] = None
    model: Optional[str] = None
    is_active: bool = True


class SensorUpdate(BaseModel):
    location: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    is_active: Optional[bool] = None


class SensorOut(SensorCreate):
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class SensorIdPayload(BaseModel):
    sensor_id: UUID

class SensorUpdatePayload(BaseModel):
    sensor_id: UUID
    update: SensorUpdate