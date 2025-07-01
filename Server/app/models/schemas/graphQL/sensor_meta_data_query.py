# SENSOR METADATA QUERY SCHEMA
# This model defines graphQL input for filtering sensor metadata records.
# It supports filters by:
# - UUIDs
# - Name, location, model, is_active
# - Created/updated date ranges
# - Pagination
# Aliases are used to keep the request field names consistent with GraphQL-style camelCase.

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DateRange(BaseModel):
    """Optional date range filter for timestamp fields."""
    after: Optional[datetime] = Field(None, description="Start of the range (inclusive)")
    before: Optional[datetime] = Field(None, description="End of the range (inclusive)")


class SensorMetadataQuery(BaseModel):
    """Advanced query model for filtering sensor metadata records.

    Supports multiple filter types: IDs, names, locations, models, activation status,
    and timestamp-based created/updated ranges. Paginated.
    """
    sensor_ids: Optional[List[UUID]] = Field(
        default=None,
        alias="sensor_ids",
        description="List of sensor UUIDs to include"
    )
    name_filter: Optional[List[str]] = Field(
        default=None,
        alias="name_filter",
        description="List of sensor name substrings to match"
    )
    locations: Optional[List[str]] = Field(
        default=None,
        alias="location_filter",
        description="List of location labels to include"
    )
    models: Optional[List[str]] = Field(
        default=None,
        alias="model_filter",
        description="List of sensor model names to include"
    )
    is_active: Optional[bool] = Field(
        default=None,
        alias="is_active",
        description="Whether the sensor must be currently active"
    )

    created_at: Optional[DateRange] = Field(
        default=None,
        alias="created_at",
        description="Filter based on creation timestamp"
    )
    updated_at: Optional[DateRange] = Field(
        default=None,
        alias="updated_at",
        description="Filter based on last update timestamp"
    )

    page: int = Field(
        default=1,
        alias="page",
        description="Pagination page number (starts at 1)"
    )
    page_size: Optional[int] = Field(
        default=None,
        alias="page_size",
        description="Maximum number of results per page"
    )

    model_config = ConfigDict(populate_by_name=True)
