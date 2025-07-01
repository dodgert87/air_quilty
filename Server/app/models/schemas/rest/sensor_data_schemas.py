#  SENSOR DATA SCHEMAS OVERVIEW
# This module defines all data models used for sensor data ingestion, storage, filtering, and querying.
# All sensor data is expected in a fixed format — every field is required unless explicitly noted.
# Swagger/OpenAPI will use these definitions for documentation and validation.

from uuid import UUID
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.constants.sensor_fields import ALLOWED_SENSOR_FIELDS


# ────────────────────────────────────────────────────────
# CORE SENSOR DATA
# ────────────────────────────────────────────────────────

class SensorDataIn(BaseModel):
    """Full sensor data payload as sent by the device. All fields are expected and fixed in format."""
    # Core identifiers
    device_id: UUID = Field(alias="sensorid", description="Sensor UUID (sent as 'sensorid')")
    timestamp: datetime = Field(alias="timestamp", description="Timestamp of the reading")

    # Aggregated environmental metrics
    temperature: float
    humidity: float

    pm1_0: float
    pm2_5: float
    pm10: float

    tvoc: float
    eco2: float
    aqi: float

    # Particulate matter concentrations (in air)
    pmInAir1_0: int
    pmInAir2_5: int
    pmInAir10: int

    # Particle counts by size (in 0.1L of air)
    particles0_3: int
    particles0_5: int
    particles1_0: int
    particles2_5: int
    particles5_0: int
    particles10: int

    # Compensated and raw sensor values
    compT: float
    compRH: float
    rawT: float
    rawRH: float

    # Gas sensor resistances
    rs0: int
    rs1: int
    rs2: int
    rs3: int

    # Carbon dioxide concentration
    co2: int

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"
    )


class SensorDataOut(SensorDataIn):
    """Sensor data record as returned from the database, with ID."""
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class SensorDataPartialOut(BaseModel):
    """Partial sensor data for query results or filtered responses.

    Only includes available fields (all optional) — useful for projections.
    """
    device_id: UUID = Field(alias="sensorid", description="Sensor UUID (sent as 'sensorid')")
    timestamp: datetime

    temperature: Optional[float] = None
    humidity: Optional[float] = None

    pm1_0: Optional[float] = None
    pm2_5: Optional[float] = None
    pm10: Optional[float] = None

    tvoc: Optional[float] = None
    eco2: Optional[float] = None
    aqi: Optional[float] = None

    pmInAir1_0: Optional[int] = None
    pmInAir2_5: Optional[int] = None
    pmInAir10: Optional[int] = None

    particles0_3: Optional[int] = None
    particles0_5: Optional[int] = None
    particles1_0: Optional[int] = None
    particles2_5: Optional[int] = None
    particles5_0: Optional[int] = None
    particles10: Optional[int] = None

    compT: Optional[float] = None
    compRH: Optional[float] = None
    rawT: Optional[float] = None
    rawRH: Optional[float] = None

    rs0: Optional[int] = None
    rs1: Optional[int] = None
    rs2: Optional[int] = None
    rs3: Optional[int] = None

    co2: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="ignore"
    )


# ────────────────────────────────────────────────────────
# SENSOR METADATA MODELS
# ────────────────────────────────────────────────────────

class SensorMetadataIn(BaseModel):
    """Metadata about the sensor unit itself (description, location, etc.)"""
    id: str = Field(..., description="Device ID, must match the sensorid in sensor data")
    location: Optional[str] = Field(None, description="Optional location or area label")
    description: Optional[str] = Field(None, description="Human-readable description")
    model: Optional[str] = Field(None, description="Sensor hardware model or series")
    is_active: bool = Field(default=True, description="If False, this sensor will be ignored")


class SensorMetadataOut(SensorMetadataIn):
    """Extended sensor metadata as returned from the database."""
    created_at: datetime = Field(..., description="Timestamp when the sensor was registered")


# ────────────────────────────────────────────────────────
# SENSOR QUERY INPUT MODELS
# ────────────────────────────────────────────────────────

class SensorRangeQuery(BaseModel):
    """Query sensor data by range filters across multiple fields.

    Each entry in 'ranges' maps a field name to a [min, max] range.
    Use `null` to represent infinity (i.e., no bound).
    Only fields listed in ALLOWED_SENSOR_FIELDS are permitted.
    """
    page: int = Field(..., ge=1, description="Pagination page number (starts from 1)")
    ranges: Dict[str, List[Optional[float]]] = Field(..., description="Map of field name to [min, max] values")

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


class SensorTimestampQuery(BaseModel):
    """Query sensor data by one or more timestamps.

    Use `exact=True` for exact matches; otherwise treated as inclusive range [min(ts), max(ts)].
    """
    timestamps: List[datetime] = Field(..., description="List of datetime values")
    exact: bool = Field(default=False, description="Match timestamps exactly or as a range")
    page: int = Field(..., ge=1, description="Pagination page number")


class SensorQuery(BaseModel):
    """Query all data from a single sensor by its ID (paginated)."""
    sensor_id: UUID = Field(..., description="Sensor UUID")
    page: int = Field(..., ge=1, description="Pagination page number")


class SensorListInput(BaseModel):
    """Filter query that accepts multiple sensor UUIDs."""
    sensor_ids: Optional[List[UUID]] = Field(default=None, description="List of sensor UUIDs")


class SensorIdOnly(BaseModel):
    """Lightweight wrapper for operations needing only the sensor ID."""
    sensor_id: UUID = Field(..., description="Sensor UUID")
