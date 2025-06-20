from uuid import UUID, uuid4
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, conlist
from app.constants.sensor_fields import ALLOWED_SENSOR_FIELDS



class SensorDataIn(BaseModel):
    # ───────────────────────── Core Identifiers ────────────────────────────
    # The sensor sends "sensorid": "sensor1". Until you convert this to a
    # real UUID, store a constant / random placeholder UUID.
    device_id: UUID = Field(alias="sensorid")
    timestamp: datetime = Field(alias="timestamp")

    # ───────────────────────── Aggregated Metrics ──────────────────────────
    temperature: float
    humidity: float

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


    # ─── Override sensorid alias and map it to a fixed UUID ────────────────

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )


class SensorDataOut(SensorDataIn):
    id: UUID

    model_config = {
        "from_attributes": True
    }



class SensorDataPartialOut(BaseModel):
    device_id: UUID = Field(alias="sensorid")
    timestamp: datetime

    temperature: Optional[float] = None
    humidity:    Optional[float] = None

    pm1_0:   Optional[float] = None
    pm2_5:   Optional[float] = None
    pm10:    Optional[float] = None

    tvoc:    Optional[float] = None
    eco2:    Optional[float] = None
    aqi:     Optional[float] = None

    pmInAir1_0: Optional[int] = None
    pmInAir2_5: Optional[int] = None
    pmInAir10:  Optional[int] = None

    particles0_3: Optional[int] = None
    particles0_5: Optional[int] = None
    particles1_0: Optional[int] = None
    particles2_5: Optional[int] = None
    particles5_0: Optional[int] = None
    particles10:  Optional[int] = None

    compT:  Optional[float] = None
    compRH: Optional[float] = None
    rawT:   Optional[float] = None
    rawRH:  Optional[float] = None

    rs0: Optional[int] = None
    rs1: Optional[int] = None
    rs2: Optional[int] = None
    rs3: Optional[int] = None

    co2: Optional[int] = None

    model_config = ConfigDict(
      from_attributes=True,
      populate_by_name=True,
      extra="ignore",
    )

class SensorMetadataIn(BaseModel):
    id: str = Field(..., description="Device ID, same as used in sensor_data")
    location: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    is_active: bool = True


class SensorMetadataOut(SensorMetadataIn):
    created_at: datetime


class SensorRangeQuery(BaseModel):
    page: int = Field(..., ge=1)
    ranges: Dict[str, List[Optional[float]]]  # Maps sensor field to [min, max] values

    @model_validator(mode="after")
    def validate_ranges(self) -> "SensorRangeQuery":
        for attr, bounds in self.ranges.items():
            if attr not in ALLOWED_SENSOR_FIELDS:
                raise ValueError(f"Invalid field: '{attr}' is not allowed.")

            if not isinstance(bounds, list) or len(bounds) != 2:
                raise ValueError(f"'{attr}' must be a list of two items [min, max].")

            min_val, max_val = bounds
            if min_val is not None and (not isinstance(min_val, (int, float)) or min_val < 0):
                raise ValueError(f"'{attr}': min must be a number ≥ 0 or null.")
            if max_val is not None and (not isinstance(max_val, (int, float)) or max_val < 0):
                raise ValueError(f"'{attr}': max must be a number ≥ 0 or null.")
            if min_val is not None and max_val is not None and min_val > max_val:
                raise ValueError(f"'{attr}': min ({min_val}) cannot be greater than max ({max_val}).")

        return self


class SensorIdOnly(BaseModel):
    sensor_id: UUID

class SensorListInput(BaseModel):
    sensor_ids: Optional[List[UUID]] = Field(default=None, description="List of sensor UUIDs")

class SensorTimestampQuery(BaseModel):
    timestamps: List[datetime] = Field(..., description="List of full timestamps")
    exact: bool = Field(default=False, description="Match exact timestamps or range")
    page: int = Field(..., ge=1)

class SensorQuery(BaseModel):
    sensor_id: UUID
    page: int