from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class SensorDataIn(BaseModel):
    device_id: str
    timestamp: datetime
    temperature: float
    humidity: float
    o2: float
    pm1_0: float
    pm2_5: float
    pm10: float
    tvoc: float
    eco2: float
    aqi: float
    pmInAir1_0: int
    pmInAir2_5: int
    pmInAir10: int
    particles0_3: int
    particles0_5: int
    particles1_0: int
    particles2_5: int
    particles5_0: int
    particles10: int
    compT: float
    compRH: float
    rawT: float
    rawRH: float
    rs0: int
    rs1: int
    rs2: int
    rs3: int
    co2: int


class SensorDataOut(SensorDataIn):
    id: UUID


class SensorMetadataIn(BaseModel):
    id: str = Field(..., description="Device ID, same as used in sensor_data")
    location: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    is_active: bool = True


class SensorMetadataOut(SensorMetadataIn):
    created_at: datetime
