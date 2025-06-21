from pydantic import BaseModel, UUID4, Field
from datetime import datetime

class SensorCreatedPayload(BaseModel):
    sensor_id: UUID4
    name: str
    created_at: datetime
    location: str | None = None
    model: str | None = None