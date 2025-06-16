from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID

class DateRange(BaseModel):
    after: Optional[datetime] = None
    before: Optional[datetime] = None


class SensorMetadataQuery(BaseModel):
    sensor_ids: Optional[List[UUID]] = Field(default=None, alias="sensor_ids")
    name_filter: Optional[List[str]] = Field(default=None, alias="name_filter")
    locations: Optional[List[str]] = Field(default=None, alias="location_filter")
    models: Optional[List[str]] = Field(default=None, alias="model_filter")
    is_active: Optional[bool] = Field(default=None, alias="is_active")

    created_at: Optional[DateRange] = Field(default=None, alias="created_at")
    updated_at: Optional[DateRange] = Field(default=None, alias="updated_at")

    page: int = Field(default=1, alias="page")
    page_size: Optional[int] = Field(default=None, alias="page_size")

    class Config:
        populate_by_name = True

