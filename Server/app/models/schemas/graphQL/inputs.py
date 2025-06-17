from typing import Optional, List
import strawberry
from datetime import datetime
from uuid import UUID


@strawberry.input
class FieldRangeInput:
    """Filter a specific numeric field with optional min/max bounds"""
    field: str
    min: Optional[float] = None
    max: Optional[float] = None


@strawberry.input
class TimestampFilterInput:
    """Allow filtering by a list of timestamps, exact match or inclusive range"""
    timestamps: List[datetime]
    exact: bool = False


@strawberry.input
class SensorDataQueryInput:
    """
    Unified input for filtering sensor data:
    - By sensor UUIDs
    - By metadata (location, model, is_active)
    - By timestamps
    - By field ranges
    """
    sensor_ids: Optional[List[UUID]] = None
    location_filter: Optional[List[str]] = None
    model_filter: Optional[List[str]] = None
    is_active: Optional[bool] = None
    timestamp_filter: Optional[TimestampFilterInput] = None
    range_filters: Optional[List[FieldRangeInput]] = None

    page: int = strawberry.field(default=1, name="page")
    page_size: Optional[int] = strawberry.field(default=None, name="page_size")

@strawberry.input
class DateRangeInput:
    """Range input for datetime fields (e.g. created_at, updated_at)"""
    after: Optional[datetime] = None
    before: Optional[datetime] = None


@strawberry.input
class SensorMetadataQueryInput:
    """
    Unified input for sensor metadata filtering.
    Supports: ID, name, location, model, status, and timestamp ranges.
    """
    sensor_ids: Optional[List[UUID]] = strawberry.field(default=None, name="sensor_ids")
    name_filter: Optional[List[str]] = strawberry.field(default=None, name="name_filter")
    location_filter: Optional[List[str]] = strawberry.field(default=None, name="location_filter")
    model_filter: Optional[List[str]] = strawberry.field(default=None, name="model_filter")
    is_active: Optional[bool] = strawberry.field(default=None, name="is_active")

    created_at: Optional[DateRangeInput] = strawberry.field(default=None, name="created_at")
    updated_at: Optional[DateRangeInput] = strawberry.field(default=None, name="updated_at")

    page: int = strawberry.field(default=1, name="page")
    page_size: Optional[int] = strawberry.field(default=None, name="page_size")