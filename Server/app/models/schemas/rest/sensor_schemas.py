#  SENSOR METADATA SCHEMAS
# These models define input and output formats for managing sensor metadata:
# - Creating and updating sensor info (location, model, description)
# - Returning registered sensor metadata from the database
# All identifiers use UUIDs and all responses are designed for clean Swagger documentation.
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ────────────────────────────────────────────────────────
# SENSOR METADATA INPUT MODELS
# ────────────────────────────────────────────────────────

class SensorCreate(BaseModel):
    """Payload to register a new sensor and its metadata."""
    sensor_id: UUID = Field(..., description="Globally unique identifier for the sensor")
    name: str = Field(..., description="Human-readable name for the sensor (e.g. 'Hallway Sensor')")
    location: Optional[str] = Field(None, description="Optional physical location or area label")
    model: Optional[str] = Field(None, description="Hardware model or version string")
    is_active: bool = Field(default=True, description="Whether the sensor is active and queryable")


class SensorUpdate(BaseModel):
    """Partial metadata update for an existing sensor."""
    location: Optional[str] = Field(None, description="Updated location string")
    description: Optional[str] = Field(None, description="Optional description or notes")
    model: Optional[str] = Field(None, description="New model name or revision")
    is_active: Optional[bool] = Field(None, description="Enable/disable the sensor")


# ────────────────────────────────────────────────────────
# SENSOR METADATA OUTPUT MODELS
# ────────────────────────────────────────────────────────

class SensorOut(SensorCreate):
    """Full sensor metadata as returned from the database."""
    created_at: datetime = Field(..., description="Timestamp when the sensor was registered")
    updated_at: datetime = Field(..., description="Timestamp of the last metadata update")

    model_config = ConfigDict(from_attributes=True)


# ────────────────────────────────────────────────────────
# WRAPPER PAYLOADS
# ────────────────────────────────────────────────────────

class SensorIdPayload(BaseModel):
    """Payload for operations that require a sensor ID only."""
    sensor_id: UUID = Field(..., description="UUID of the target sensor")


class SensorUpdatePayload(BaseModel):
    """Payload for updating an existing sensor's metadata."""
    sensor_id: UUID = Field(..., description="UUID of the sensor to update")
    update: SensorUpdate = Field(..., description="Fields to modify for the selected sensor")
