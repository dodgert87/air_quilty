from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from typing import Optional, List, Dict
from datetime import datetime


class SensorDataAdvancedQuery(BaseModel):
    # Sensor filters
    sensor_ids: Optional[List[UUID]] = None

    # Timestamp filters
    timestamps: Optional[List[datetime]] = None
    timestamp_range_start: Optional[datetime] = None
    timestamp_range_end: Optional[datetime] = None

    # Field-based numeric filtering
    field_ranges: Optional[Dict[str, List[Optional[float]]]] = None  # {"pm2_5": [None, 50]}

    # Metadata filters
    locations: Optional[List[str]] = None
    models: Optional[List[str]] = None
    is_active: Optional[bool] = None

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)

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
