#  GRAPHQL INPUT SCHEMAS
# These input types define how clients filter and query sensor data or metadata via GraphQL.
# Strawberry GraphQL auto-generates documentation from these classes in the GraphiQL explorer.
# Field names are camelCase (enforced via `name=...`) for frontend compatibility.

from typing import Optional, List
from datetime import datetime
from uuid import UUID
import strawberry


# ────────────────────────────────────────────────────────
# SHARED FILTER TYPES
# ────────────────────────────────────────────────────────

@strawberry.input
class FieldRangeInput:
    """Filter a specific numeric field using optional min and max bounds.

    Example: `{ field: "temperature", min: 20.0, max: 30.0 }`
    Set min or max to null to make it unbounded.
    """
    field: str
    min: Optional[float] = None
    max: Optional[float] = None


@strawberry.input
class TimestampFilterInput:
    """Filter data by exact timestamps or an inclusive time range.

    - If `exact=True`, only entries with the listed timestamps are matched.
    - If `exact=False`, entries within [min(timestamps), max(timestamps)] are returned.
    """
    timestamps: List[datetime]
    exact: bool = False


@strawberry.input
class DateRangeInput:
    """Filter metadata by a time range on a datetime field (e.g., created_at)."""
    after: Optional[datetime] = None
    before: Optional[datetime] = None


# ────────────────────────────────────────────────────────
# SENSOR DATA QUERY INPUT
# ────────────────────────────────────────────────────────

@strawberry.input
class SensorDataQueryInput:
    """
    Input type for querying historical sensor readings.

    Supports:
    - Sensor UUID filtering
    - Metadata filters: location, model, is_active
    - Time filters: exact timestamps or inclusive time range
    - Field filters: numeric fields with [min, max] values
    - Pagination: page and page_size
    """
    sensor_ids: Optional[List[UUID]] = strawberry.field(default=None, name="sensor_ids")
    location_filter: Optional[List[str]] = strawberry.field(default=None, name="location_filter")
    model_filter: Optional[List[str]] = strawberry.field(default=None, name="model_filter")
    is_active: Optional[bool] = strawberry.field(default=None, name="is_active")

    timestamp_filter: Optional[TimestampFilterInput] = strawberry.field(default=None, name="timestamp_filter")
    range_filters: Optional[List[FieldRangeInput]] = strawberry.field(default=None, name="range_filters")

    page: int = strawberry.field(default=1, name="page")
    page_size: Optional[int] = strawberry.field(default=None, name="page_size")


# ────────────────────────────────────────────────────────
# SENSOR METADATA QUERY INPUT
# ────────────────────────────────────────────────────────

@strawberry.input
class SensorMetadataQueryInput:
    """
    Input type for querying sensor metadata records.

    Supports:
    - Sensor IDs
    - Metadata fields: name, location, model, is_active
    - Timestamp filters: created_at and updated_at
    - Pagination
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
