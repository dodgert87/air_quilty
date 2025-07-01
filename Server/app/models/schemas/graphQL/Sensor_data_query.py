# SENSOR DATA ADVANCED QUERY SCHEMA
# This model defines a unified input structure for advanced filtering of sensor data via graphQL.
# It supports filtering by:
# - sensor IDs
# - timestamps (exact list or range)
# - numeric field values (via [min, max])
# - sensor metadata (location, model, is_active)
# Pagination is supported via `page` and `page_size`.

from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from typing import Optional, List, Dict
from datetime import datetime


class SensorDataAdvancedQuery(BaseModel):
    # Sensor filtering
    sensor_ids: Optional[List[UUID]] = Field(
        default=None,
        description="List of sensor UUIDs to include in the query"
    )

    # Timestamp filtering
    timestamps: Optional[List[datetime]] = Field(
        default=None,
        description="List of exact timestamps to match"
    )
    timestamp_range_start: Optional[datetime] = Field(
        default=None,
        description="Start of the timestamp range (inclusive)"
    )
    timestamp_range_end: Optional[datetime] = Field(
        default=None,
        description="End of the timestamp range (inclusive)"
    )

    # Field-based numeric filtering
    field_ranges: Optional[Dict[str, List[Optional[float]]]] = Field(
        default=None,
        description="Dictionary mapping field names to [min, max] filters. Use null for open-ended bounds."
    )

    # Sensor metadata filtering
    locations: Optional[List[str]] = Field(
        default=None,
        description="List of location tags to filter sensors by"
    )
    models: Optional[List[str]] = Field(
        default=None,
        description="List of sensor model names to include"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Whether the sensor must be active"
    )

    # Pagination
    page: int = Field(
        default=1,
        ge=1,
        description="Page number for pagination (starts from 1)"
    )
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Number of results per page (max 200)"
    )

    @field_validator("field_ranges")
    def validate_field_ranges(cls, v):
        if not v:
            return v
        for key, value in v.items():
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError(f"Field '{key}' must be a list of two values [min, max].")
            min_val, max_val = value
            if min_val is not None and not isinstance(min_val, (int, float)):
                raise ValueError(f"Field '{key}' min value must be numeric or null.")
            if max_val is not None and not isinstance(max_val, (int, float)):
                raise ValueError(f"Field '{key}' max value must be numeric or null.")
            if min_val is not None and max_val is not None and min_val > max_val:
                raise ValueError(f"Field '{key}': min ({min_val}) cannot be greater than max ({max_val}).")
        return v
